import json
import os
import re
from datetime import datetime, timezone
from html import escape

README = "README.md"
STORE = "guestbook.json"
START, END = "<!-- guestbook:start -->", "<!-- guestbook:end -->"
MAX_ENTRIES = 10
MAX_CHARS = 140


def clean(text):
    text = re.sub(r"<!--.*?-->", "", text or "", flags=re.S)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > MAX_CHARS:
        text = text[: MAX_CHARS - 1].rstrip() + "…"
    return escape(text)


def load():
    if os.path.exists(STORE):
        return json.load(open(STORE, encoding="utf-8"))
    return []


def render(entries):
    rows = []
    for e in entries[:MAX_ENTRIES]:
        msg = e["message"] or "<i>passed by and left a star</i>"
        rows.append(
            "  <tr>\n"
            f'    <td><a href="https://github.com/{e["user"]}"><img src="https://github.com/{e["user"]}.png?size=40" width="20" height="20"></a></td>\n'
            f'    <td><a href="https://github.com/{e["user"]}"><b>@{e["user"]}</b></a></td>\n'
            f"    <td>{msg}</td>\n"
            f"    <td><sub>{e['date']}</sub></td>\n"
            "  </tr>"
        )
    if not rows:
        rows.append('  <tr><td colspan="4"><i>no signatures yet, be the first</i></td></tr>')
    return "\n<div align=\"center\">\n<table align=\"center\">\n" + "\n".join(rows) + "\n</table>\n</div>\n"


def main():
    event = json.load(open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8"))
    issue = event["issue"]
    entries = load()
    if any(e.get("issue") == issue["number"] for e in entries):
        return
    title = (issue.get("title") or "").strip()
    message = clean(issue.get("body")) or ("" if title.lower().startswith("guestbook") else clean(title))
    entries.insert(0, {
        "issue": issue["number"],
        "user": issue["user"]["login"],
        "message": message,
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    })
    entries = entries[:MAX_ENTRIES]
    json.dump(entries, open(STORE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    readme = open(README, encoding="utf-8").read()
    head, rest = readme.split(START, 1)
    _, tail = rest.split(END, 1)
    open(README, "w", encoding="utf-8").write(head + START + render(entries) + END + tail)


if __name__ == "__main__":
    main()
