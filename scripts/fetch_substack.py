#!/usr/bin/env python3
import html
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html.parser import HTMLParser

FEED_URL = "https://quinnmatthewfox.substack.com/feed"
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
    text = re.sub(r"\\s+", " ", text).strip()
    return text

request = urllib.request.Request(
    FEED_URL,
    headers={"User-Agent": "Mozilla/5.0 (compatible; QuinnMFoxSite/1.0)"}
)

with urllib.request.urlopen(request, timeout=30) as response:
    xml_data = response.read()

root = ET.fromstring(xml_data)
channel = root.find("channel")
items = channel.findall("item") if channel is not None else []

posts = []
for item in items[:3]:
    title = plain_text(item.findtext("title"))
    url = (item.findtext("link") or "").strip()
    date = (item.findtext("pubDate") or "").strip()
    description = plain_text(item.findtext("description"))
    if len(description) > 180:
        description = description[:177].rsplit(" ", 1)[0] + "…"
    if title and url:
        posts.append({
            "title": title,
            "url": url,
            "date": date,
            "excerpt": description
        })

payload = {
    "updated_at": datetime.now(timezone.utc).isoformat(),
    "posts": posts
}

with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)
    f.write("\n")
