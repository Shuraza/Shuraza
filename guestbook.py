import html
import json
import os
import re
from datetime import datetime, timedelta, timezone

README = "README.md"
STORE = "guestbook.json"
START, END = "<!-- guestbook:start -->", "<!-- guestbook:end -->"
MAX_ENTRIES = 10
MAX_CHARS = 140
MAX_WORD = 24
BRT = timezone(timedelta(hours=-3))
MARKDOWN = {c: f"&#{ord(c)};" for c in "[]()*_`~|\\!"}


def clean(text):
    text = re.sub(r"<!--.*?-->", "", text or "", flags=re.S)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > MAX_CHARS:
        text = text[: MAX_CHARS - 1].rstrip() + "…"
    return html.escape(text)


def display(message):
    text = html.unescape(message)
    text = re.sub(r"https?://\S+|www\.\S+", "(link)", text)
    text = re.sub(rf"\S{{{MAX_WORD + 1},}}", lambda m: m.group()[: MAX_WORD - 1] + "…", text)
    text = html.escape(text, quote=False)
    return "".join(MARKDOWN.get(c, c) for c in text)


def signed_at(issue):
    created = issue.get("created_at")
    when = datetime.fromisoformat(created.replace("Z", "+00:00")) if created else datetime.now(timezone.utc)
    return when.astimezone(BRT).strftime("%Y-%m-%d %H:%M")


def short_date(value):
    try:
        d = datetime.strptime(value, "%Y-%m-%d %H:%M")
        return d.strftime("%d/%m&nbsp;%H:%M")
    except ValueError:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%d/%m")


def load():
    if os.path.exists(STORE):
        return json.load(open(STORE, encoding="utf-8"))
    return []


def render(entries):
    rows = []
    for e in entries[:MAX_ENTRIES]:
        user = e["user"]
        msg = display(e["message"]) if e["message"] else "<i>passed by and left a star</i>"
        rows.append(
            "  <tr>\n"
            f'    <td nowrap><a href="https://github.com/{user}"><img src="https://github.com/{user}.png?size=64" width="28" height="28" align="absmiddle">&nbsp;&nbsp;<b>@{user}</b></a></td>\n'
            f"    <td>{msg}</td>\n"
            f"    <td><sub>{short_date(e['date'])}</sub></td>\n"
            "  </tr>"
        )
    if not rows:
        rows.append('  <tr><td colspan="3"><i>no signatures yet, be the first</i></td></tr>')
    return '\n<div align="center">\n<table align="center">\n' + "\n".join(rows) + "\n</table>\n</div>\n"


def write_readme(entries):
    readme = open(README, encoding="utf-8").read()
    head, rest = readme.split(START, 1)
    _, tail = rest.split(END, 1)
    open(README, "w", encoding="utf-8").write(head + START + render(entries) + END + tail)


def main():
    event = json.load(open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8"))
    issue = event["issue"]
    entries = load()
    if any(e.get("issue") == issue["number"] for e in entries):
        write_readme(entries)
        return
    title = (issue.get("title") or "").strip()
    message = clean(issue.get("body")) or ("" if title.lower().startswith("guestbook") else clean(title))
    entries.insert(0, {
        "issue": issue["number"],
        "user": issue["user"]["login"],
        "message": message,
        "date": signed_at(issue),
    })
    entries = entries[:MAX_ENTRIES]
    json.dump(entries, open(STORE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    write_readme(entries)


if __name__ == "__main__":
    import sys
    if "--render" in sys.argv:
        write_readme(load())
    else:
        main()
