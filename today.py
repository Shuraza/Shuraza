import os
import sys
import time
from datetime import date, datetime, timezone
from html import escape

import requests
from dateutil.relativedelta import relativedelta

USER = "Shuraza"
BIRTHDAY = "2005-09-17"
WIDTH = 58

API = "https://api.github.com"
TOKEN = os.environ.get("ACCESS_TOKEN") or os.environ.get("GITHUB_TOKEN")
HEADERS = {"Authorization": f"bearer {TOKEN}"} if TOKEN else {}

THEMES = {
    "dark": {"bg": "#161b22", "border": "#30363d", "ascii": "#c9d1d9", "text": "#c9d1d9",
             "key": "#ffa657", "value": "#a5d6ff", "dots": "#616e7f", "add": "#3fb950", "del": "#f85149"},
    "light": {"bg": "#f6f8fa", "border": "#d0d7de", "ascii": "#24292f", "text": "#24292f",
              "key": "#953800", "value": "#0a3069", "dots": "#c2cfde", "add": "#1a7f37", "del": "#cf222e"},
}


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


def build_lines(stats):
    rows = [("title", "samuel@souza", None)]
    info = [
        ("OS", "Windows, Windows Server, Linux"),
        ("Uptime", uptime()),
        ("Host", "YUDO SA"),
        ("Kernel", "Software Engineering @ Univille"),
        ("IDE", "VS Code, IntelliJ IDEA"),
        None,
        ("Languages.Programming", "Python, SQL, JavaScript, PHP, Java"),
        ("Languages.Computer", "HTML, CSS, JSON, YAML"),
        ("Languages.Real", "Portuguese, English"),
        None,
        ("Work.Focus", "ERP integration, Python automation"),
        ("Certifications", "Azure Fundamentals (AZ-900)"),
    ]
    for item in info:
        if item is None:
            rows.append(("blank", None, None))
        elif item[1]:
            rows.append(("pair", item[0], item[1]))
    rows.append(("blank", None, None))
    rows.append(("section", "Contact", None))
    rows.append(("pair", "Email", "Samueldesouza200512@gmail.com"))
    rows.append(("pair", "LinkedIn", "samuel-de-souza-5607a8233"))
    rows.append(("blank", None, None))
    rows.append(("section", "GitHub Stats", None))
    rows.append(("stats1", stats, None))
    rows.append(("stats2", stats, None))
    rows.append(("loc", stats, None))
    return rows


def dots(n):
    return f'<tspan class="d">{"." * max(n, 1)}</tspan>' if n > 0 else ""


def pair(key, value, width=WIDTH):
    fill = width - len(key) - len(value) - 3
    return f'<tspan class="k">{escape(key)}</tspan>:{dots(fill)} <tspan class="v">{escape(value)}</tspan>'


def render_row(kind, a, b):
    if kind == "title":
        return f'<tspan class="t">{a}</tspan> {"─" * (WIDTH - len(a) - 2)}'
    if kind == "section":
        return f'- {a} {"─" * (WIDTH - len(a) - 4)}'
    if kind == "pair":
        return pair(a, b)
    if kind == "stats1":
        left = pair("Repos", f"{a['repos']} {{Contributed: {a['contributed']}}}", 34)
        right = pair("Stars", f"{a['stars']}", WIDTH - 36)
        return f"{left} | {right}"
    if kind == "stats2":
        left = pair("Commits", f"{a['commits']:,}", 34)
        right = pair("Followers", f"{a['followers']}", WIDTH - 36)
        return f"{left} | {right}"
    if kind == "loc":
        total = f"{a['added'] - a['deleted']:,}"
        detail = f" ( +{a['added']:,}, -{a['deleted']:,} )"
        fill = WIDTH - len("Lines of Code on GitHub") - len(total) - len(detail) - 3
        return (f'<tspan class="k">Lines of Code on GitHub</tspan>:{dots(fill)} <tspan class="v">{total}</tspan>'
                f' ( <tspan class="a">+{a["added"]:,}</tspan>, <tspan class="r">-{a["deleted"]:,}</tspan> )')
    return ""


def svg(theme, ascii_lines, rows):
    c = THEMES[theme]
    ascii_size, ascii_lh = 12.5, 15.6
    text_size, text_lh = 16, 20
    ascii_w = max(len(l) for l in ascii_lines) * ascii_size * 0.6
    text_x = 30 + ascii_w + 34
    width = int(text_x + WIDTH * text_size * 0.6 + 30)
    ascii_h = len(ascii_lines) * ascii_lh
    text_h = len(rows) * text_lh
    height = int(max(ascii_h, text_h) + 60)
    ascii_y = 30 + (height - 60 - ascii_h) / 2 + ascii_size
    text_y = 30 + (height - 60 - text_h) / 2 + text_size

    art = "\n".join(
        f'<tspan x="30" y="{ascii_y + i * ascii_lh:.1f}">{escape(l)}</tspan>' for i, l in enumerate(ascii_lines))
    info = "\n".join(
        f'<tspan x="{text_x:.0f}" y="{text_y + i * text_lh:.0f}">{render_row(*r)}</tspan>'
        for i, r in enumerate(rows))

    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" font-family="ConsolasFallback,Consolas,'Courier New',monospace" width="{width}px" height="{height}px" font-size="{text_size}px">
<style>
@font-face {{ src: local('Consolas'), local('Consolas Bold'); font-family: 'ConsolasFallback'; font-display: swap; -webkit-size-adjust: 109%; size-adjust: 109%; }}
.k {{ fill: {c["key"]}; }}
.v {{ fill: {c["value"]}; }}
.d {{ fill: {c["dots"]}; }}
.t {{ fill: {c["key"]}; font-weight: bold; }}
.a {{ fill: {c["add"]}; }}
.r {{ fill: {c["del"]}; }}
text, tspan {{ white-space: pre; }}
</style>
<rect width="{width}px" height="{height}px" fill="{c["bg"]}" stroke="{c["border"]}" rx="15"/>
<text fill="{c["ascii"]}" font-size="{ascii_size}px" xml:space="preserve">
{art}
</text>
<text fill="{c["text"]}" xml:space="preserve">
{info}
</text>
</svg>
'''


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "ascii.txt"), encoding="utf-8") as f:
        ascii_lines = f.read().rstrip("\n").split("\n")

    if "--offline" in sys.argv:
        stats = {"repos": 12, "contributed": 6, "stars": 12, "commits": 412, "followers": 13,
                 "added": 48210, "deleted": 9133}
    else:
        p = profile_stats()
        added, deleted = lines_of_code(p["repo_names"])
        stats = {**p, "commits": commit_count(p["created"]), "added": added, "deleted": deleted}

    rows = build_lines(stats)
    for theme in THEMES:
        with open(os.path.join(here, f"{theme}_mode.svg"), "w", encoding="utf-8") as f:
            f.write(svg(theme, ascii_lines, rows))


if __name__ == "__main__":
    main()
