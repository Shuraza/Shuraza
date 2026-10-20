import json
import os
import sys
import time
from datetime import date, datetime, timezone
from html import escape

import requests
from dateutil.relativedelta import relativedelta

USER = "Shuraza"
BIRTHDAY = "2005-09-17"
WIDTH = 52

API = "https://api.github.com"
TOKEN = os.environ.get("ACCESS_TOKEN") or os.environ.get("GITHUB_TOKEN")
HEADERS = {"Authorization": f"bearer {TOKEN}"} if TOKEN else {}

EMAIL = "Samueldesouza200512@gmail.com"

FONT = "ui-monospace, SFMono-Regular, Consolas, 'DejaVu Sans Mono', 'Liberation Mono', monospace"
THEMES = {
    "dark": dict(bg="#0d1117", bar="#161b22", border="#30363d", text="#c9d1d9", key="#ffa657", value="#a5d6ff",
                 dots="#484f58", prompt="#7ee787", path="#79c0ff", add="#3fb950", rem="#f85149"),
    "light": None,
}
PALETTE = ["#484f58", "#ff7b72", "#3fb950", "#d29922", "#58a6ff", "#bc8cff", "#39c5cf", "#b1bac4"]


def graphql(query, **variables):
    r = requests.post(f"{API}/graphql", json={"query": query, "variables": variables}, headers=HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data["data"]


def profile_stats():
    q = """query($login: String!) {
      user(login: $login) {
        createdAt
        followers { totalCount }
        owned: repositories(ownerAffiliations: OWNER, first: 100) {
          totalCount
          nodes { nameWithOwner stargazerCount }
        }
        contributed: repositoriesContributedTo(first: 100, includeUserRepositories: false,
          contributionTypes: [COMMIT, PULL_REQUEST, REPOSITORY]) {
          totalCount
          nodes { nameWithOwner }
        }
      }
    }"""
    u = graphql(q, login=USER)["user"]
    return {
        "created": datetime.fromisoformat(u["createdAt"].replace("Z", "+00:00")),
        "followers": u["followers"]["totalCount"],
        "repos": u["owned"]["totalCount"],
        "contributed": u["contributed"]["totalCount"],
        "stars": sum(n["stargazerCount"] for n in u["owned"]["nodes"]),
        "repo_names": [n["nameWithOwner"] for n in u["owned"]["nodes"] + u["contributed"]["nodes"]],
    }


def commit_count(created):
    q = """query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          totalCommitContributions
          restrictedContributionsCount
        }
      }
    }"""
    total = 0
    now = datetime.now(timezone.utc)
    for year in range(created.year, now.year + 1):
        start = max(created, datetime(year, 1, 1, tzinfo=timezone.utc))
        end = min(now, datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc))
        c = graphql(q, login=USER, **{"from": start.isoformat(), "to": end.isoformat()})["user"]["contributionsCollection"]
        total += c["totalCommitContributions"] + c["restrictedContributionsCount"]
    return total


def lines_of_code(repo_names):
    added = deleted = 0
    for name in repo_names:
        for _ in range(6):
            r = requests.get(f"{API}/repos/{name}/stats/contributors", headers=HEADERS, timeout=30)
            if r.status_code != 202:
                break
            time.sleep(3)
        if r.status_code != 200 or not r.json():
            continue
        for contributor in r.json():
            if (contributor.get("author") or {}).get("login", "").lower() == USER.lower():
                added += sum(w["a"] for w in contributor["weeks"])
                deleted += sum(w["d"] for w in contributor["weeks"])
    return added, deleted


def uptime():
    if not BIRTHDAY:
        return None
    d = relativedelta(date.today(), date.fromisoformat(BIRTHDAY))
    plural = lambda n, w: f"{n} {w}{'' if n == 1 else 's'}"
    return f"{plural(d.years, 'year')}, {plural(d.months, 'month')}, {plural(d.days, 'day')}"


def pair(key, value, width=WIDTH):
    fill = max(width - len(key) - len(value) - 3, 1)
    return [(key, "k"), (":", "p"), ("." * fill, "d"), (" ", "p"), (value, "v")]


def header(text, bold=False):
    return [(text, "u" if bold else "p"), (" " + "─" * (WIDTH - len(text) - 2), "d")]


def info_lines(s):
    rows = [header("samuel@souza", bold=True)]
    fields = [
        ("OS", "Windows, Windows Server, Linux"),
        ("Uptime", uptime()),
        ("Host", "YUDO SA"),
        ("Kernel", "IT Support Analyst"),
        ("Previous", "Front-end Developer @ Pichau"),
        ("IDE", "VS Code, IntelliJ IDEA"),
        None,
        ("Languages.Code", "Python, Java, PHP, JavaScript"),
        ("Languages.Data", "SQL Server, MySQL, Firebase"),
        ("Languages.Web", "HTML, CSS, React"),
        ("Languages.Real", "Portuguese, English"),
        None,
        ("ERP", "TOTVS Protheus"),
        ("Cloud", "Azure (AZ-900 certified)"),
        ("Education", "Software Engineering @ Univille"),
        ("Education.Tech", "Internet Computing @ Senac"),
    ]
    for f in fields:
        if f is None:
            rows.append([])
        elif f[1]:
            rows.append(pair(*f))
    half = WIDTH // 2 - 2
    rows += [
        [],
        header("- Contact"),
        pair("Email", EMAIL),
        pair("LinkedIn", "samuel-de-souza-5607a8233"),
        pair("GitHub", USER),
        [],
        header("- GitHub Stats"),
        pair("Repos", f"{s['repos']} {{+{s['contributed']}}}", half) + [(" | ", "p")]
        + pair("Stars", str(s["stars"]), WIDTH - half - 3),
        pair("Commits", f"{s['commits']:,}", half) + [(" | ", "p")]
        + pair("Followers", str(s["followers"]), WIDTH - half - 3),
    ]
    total = f"{s['added'] - s['deleted']:,}"
    add, rem = f"+{s['added']:,}", f"-{s['deleted']:,}"
    fill = max(WIDTH - len("Lines of Code") - len(total) - len(add) - len(rem) - 9, 1)
    rows.append([("Lines of Code", "k"), (":", "p"), ("." * fill, "d"), (" ", "p"), (total, "v"),
                 (" ( ", "p"), (add, "a"), (" ", "p"), (rem, "r"), (" )", "p")])
    rows += [[], "palette"]
    return rows


FRAME_TIME = 0.1


def svg(theme, frames, info):
    c = THEMES[theme] or THEMES["dark"]
    a_size, a_lh, i_size, i_lh = 11, 15, 14, 19.5
    cw_a, cw_i = a_size * 0.62, i_size * 0.62
    pad, bar = 24, 36
    prompt_y = bar + 30
    top = prompt_y + 18
    art_w = max(sum(len(t) for t, _ in l) for f in frames for l in f)
    info_x = pad + art_w * cw_a + 30
    width = int(info_x + WIDTH * cw_i + pad)
    art_rows = max(len(f) for f in frames)
    body_h = max(art_rows * a_lh, len(info) * i_lh)
    a_top = top + (body_h - art_rows * a_lh) / 2
    i_top = top + (body_h - len(info) * i_lh) / 2
    end_y = top + body_h + 30
    height = int(end_y + 22)

    ps1 = ('<tspan class="u">samuel@souza</tspan><tspan class="p">:</tspan>'
           '<tspan class="w">~</tspan><tspan class="p">$ </tspan>')
    ps1_len = len("samuel@souza:~$ ")
    cmd, t0, step = "neofetch", 0.4, 0.07
    out_start = t0 + len(cmd) * step + 0.35
    parts = []

    def typed(x, y, inner, n, begin, dur, idx):
        widths = ";".join(f"{k * cw_i:.1f}" for k in range(n + 1))
        return (f'<clipPath id="c{idx}"><rect x="{x:.1f}" y="{y - 16:.1f}" width="0" height="22">'
                f'<animate attributeName="width" values="{widths}" calcMode="discrete" '
                f'begin="{begin:.2f}s" dur="{dur:.2f}s" fill="freeze"/></rect></clipPath>'
                f'<text x="{x:.1f}" y="{y:.1f}" clip-path="url(#c{idx})">{inner}</text>')

    parts.append(f'<text x="{pad}" y="{prompt_y}">{ps1}</text>')
    parts.append(typed(pad + ps1_len * cw_i, prompt_y, f'<tspan class="p">{cmd}</tspan>',
                       len(cmd), t0, (len(cmd) + 1) * step, "cmd"))

    def row_svg(runs, y, intro):
        spans = "".join(f'<tspan fill="{col}">{escape(txt)}</tspan>' if col else escape(txt) for txt, col in runs)
        if intro is None:
            return f'<text class="art" x="{pad}" y="{y:.1f}">{spans}</text>'
        return (f'<text class="art" x="{pad}" y="{y:.1f}" opacity="0">{spans}'
                f'<set attributeName="opacity" to="1" begin="{intro:.2f}s" fill="freeze"/></text>')

    static = [all(f[i] == frames[0][i] for f in frames) for i in range(art_rows)]
    base = []
    heads = []
    for k, f in enumerate(frames):
        texts = []
        for i, runs in enumerate(f):
            y = a_top + a_size + i * a_lh
            intro = out_start + i * 0.025
            if static[i]:
                if k == 0:
                    base.append(row_svg(runs, y, intro))
            else:
                texts.append(row_svg(runs, y, intro if k == 0 else None))
        heads.append("".join(texts))
    parts.append("".join(base))

    t = out_start + 0.15
    for i, segs in enumerate(info):
        y = i_top + i_size + i * i_lh
        if segs == "palette":
            for k, color in enumerate(PALETTE):
                parts.append(f'<rect x="{info_x + k * 3 * cw_i:.1f}" y="{y - 13:.1f}" width="{3 * cw_i:.1f}" height="16" '
                             f'fill="{color}" opacity="0"><set attributeName="opacity" to="1" '
                             f'begin="{t + k * 0.06:.2f}s" fill="freeze"/></rect>')
            t += len(PALETTE) * 0.06
            continue
        if not segs:
            t += 0.06
            continue
        inner = "".join(f'<tspan class="{cls}">{escape(txt)}</tspan>' for txt, cls in segs)
        n = sum(len(txt) for txt, _ in segs)
        dur = n * 0.002 + 0.12
        parts.append(typed(info_x, y, inner, n, t, dur, i))
        t += dur + 0.025

    end = t + 0.3
    n = len(heads)
    spin = out_start + art_rows * 0.025 + 0.6
    loop = n * FRAME_TIME
    for k, texts in enumerate(heads):
        if k == 0:
            values, times = "1;0", f"0;{1 / n:.4f}"
        elif k == n - 1:
            values, times = "0;1", f"0;{k / n:.4f}"
        else:
            values, times = "0;1;0", f"0;{k / n:.4f};{(k + 1) / n:.4f}"
        parts.insert(k, f'<g opacity="{1 if k == 0 else 0}"><animate attributeName="opacity" values="{values}" '
                        f'keyTimes="{times}" calcMode="discrete" dur="{loop:.2f}s" begin="{spin:.2f}s" '
                        f'repeatCount="indefinite"/>{texts}</g>')
    parts.append(f'<text x="{pad}" y="{end_y:.1f}" opacity="0">{ps1}'
                 f'<set attributeName="opacity" to="1" begin="{end:.2f}s" fill="freeze"/></text>')
    parts.append(f'<rect class="cursor" x="{pad + ps1_len * cw_i:.1f}" y="{end_y - 14:.1f}" width="{cw_i:.1f}" '
                 f'height="17" opacity="0"><animate attributeName="opacity" values="1;0" dur="1.1s" '
                 f'begin="{end:.2f}s" repeatCount="indefinite" calcMode="discrete"/></rect>')

    style = f"""
text {{ font-family: {FONT}; font-size: {i_size}px; fill: {c['text']}; white-space: pre; }}
.art {{ font-size: {a_size}px; }}
.k {{ fill: {c['key']}; font-weight: 600; }}
.v {{ fill: {c['value']}; }}
.d {{ fill: {c['dots']}; }}
.a {{ fill: {c['add']}; }}
.r {{ fill: {c['rem']}; }}
.u {{ fill: {c['prompt']}; font-weight: 600; }}
.w {{ fill: {c['path']}; font-weight: 600; }}
.cursor {{ fill: {c['text']}; }}
"""
    body = "\n".join(parts)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<style>{style}</style>
<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="10" fill="{c['bg']}" stroke="{c['border']}"/>
<path d="M0.5 {bar} V10.5 a10 10 0 0 1 10 -10 H{width - 10.5} a10 10 0 0 1 10 10 V{bar} Z" fill="{c['bar']}"/>
<line x1="0.5" y1="{bar}" x2="{width - 0.5}" y2="{bar}" stroke="{c['border']}"/>
<circle cx="22" cy="{bar / 2}" r="6" fill="#ff5f57"/><circle cx="42" cy="{bar / 2}" r="6" fill="#febc2e"/><circle cx="62" cy="{bar / 2}" r="6" fill="#28c840"/>
<text x="{width / 2}" y="{bar / 2 + 4.5}" text-anchor="middle" style="font-size:12px;fill:{c['dots']}">samuel@souza: ~</text>
{body}
</svg>
'''


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "avatar_frames.json"), encoding="utf-8") as f:
        frames = json.load(f)

    if "--offline" in sys.argv:
        stats = {"repos": 12, "contributed": 6, "stars": 12, "commits": 412, "followers": 13,
                 "added": 48210, "deleted": 9133}
    else:
        p = profile_stats()
        added, deleted = lines_of_code(p["repo_names"])
        stats = {**p, "commits": commit_count(p["created"]), "added": added, "deleted": deleted}

    info = info_lines(stats)
    for theme in THEMES:
        with open(os.path.join(here, f"{theme}_mode.svg"), "w", encoding="utf-8") as f:
            f.write(svg(theme, frames, info))


if __name__ == "__main__":
    main()
