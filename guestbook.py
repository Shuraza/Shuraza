import json
import os
import re
from datetime import datetime, timezone
from html import escape

README = "README.md"
START, END = "<!-- guestbook:start -->", "<!-- guestbook:end -->"
MAX_ENTRIES = 10
MAX_CHARS = 140
TEMPLATE_HINT = "Write your message"


def clean(text):
    text = re.sub(r"<!--.*?-->", "", text or "", flags=re.S)
    text = text.replace(TEMPLATE_HINT, "")
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > MAX_CHARS:
        text = text[: MAX_CHARS - 1].rstrip() + "…"
    return escape(text).replace("|", "&#124;")


def main():
    event = json.load(open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8"))
    issue = event["issue"]
    user = issue["user"]["login"]
    message = clean(issue.get("body"))
    if not message:
        message = "<i>passed by and left a star</i>"
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    row = f'| <a href="https://github.com/{user}"><img src="https://github.com/{user}.png?size=40" width="20"> @{user}</a> | {message} | {date} |'

    readme = open(README, encoding="utf-8").read()
    head, rest = readme.split(START, 1)
    block, tail = rest.split(END, 1)
    rows = [l for l in block.strip().splitlines() if l.startswith("| <a ")]
    rows = ([row] + rows)[:MAX_ENTRIES]
    table = "\n".join(["", "| visitor | message | date |", "|---|---|---|", *rows, ""])
    open(README, "w", encoding="utf-8").write(head + START + table + END + tail)


if __name__ == "__main__":
    main()
