#!/usr/bin/env python3
import html
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser

FEED_URL = "https://quinnmatthewfox.substack.com/feed"
PROXY_URL = "https://api.rss2json.com/v1/api.json?rss_url=" + urllib.parse.quote(FEED_URL, safe="")
OUTPUT = "posts.json"

class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
    def handle_data(self, data):
        self.parts.append(data)

def plain_text(value):
    if not value:
        return ""
    parser = TextExtractor()
    parser.feed(html.unescape(value))
    text = " ".join(parser.parts)
    return re.sub(r"\s+", " ", text).strip()

request = urllib.request.Request(
    PROXY_URL,
    headers={
        "User-Agent": "Mozilla/5.0 (compatible; QuinnMFoxSite/1.0)",
        "Accept": "application/json"
    }
)

with urllib.request.urlopen(request, timeout=30) as response:
    data = json.load(response)

if data.get("status") != "ok":
    raise RuntimeError("RSS proxy failed: " + str(data.get("message") or data))

posts = []
for item in (data.get("items") or [])[:3]:
    title = plain_text(item.get("title"))
    url = (item.get("link") or "").strip()
    date = (item.get("pubDate") or "").strip()
    description = plain_text(item.get("description") or item.get("content") or "")
    if len(description) > 180:
        description = description[:177].rsplit(" ", 1)[0] + "…"
    if title and url:
        posts.append({
            "title": title,
            "url": url,
            "date": date,
            "excerpt": description
        })

if not posts:
    raise RuntimeError("RSS proxy returned no posts")

payload = {
    "updated_at": datetime.now(timezone.utc).isoformat(),
    "posts": posts
}

with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)
    f.write("\n")
