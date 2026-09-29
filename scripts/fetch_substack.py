#!/usr/bin/env python3
import html
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser

PUB = "https://quinnmatthewfox.substack.com"
API_URL = PUB + "/api/v1/posts?limit=3&offset=0"
FEED_URL = PUB + "/feed"
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
    parser.feed(html.unescape(str(value)))
    text = " ".join(parser.parts)
    return re.sub(r"\s+", " ", text).strip()

def fetch_json(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/140 Safari/537.36",
            "Accept": "application/json,text/plain,*/*",
            "Referer": PUB + "/",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)

def normalise_substack(data):
    if isinstance(data, dict) and isinstance(data.get("contents"), str):
        data = json.loads(data["contents"])
    if isinstance(data, dict) and isinstance(data.get("posts"), list):
        data = data["posts"]
    if not isinstance(data, list):
        return []

    out = []
    for item in data[:3]:
        if not isinstance(item, dict):
            continue
        title = plain_text(item.get("title"))
        slug = item.get("slug") or ""
        url = (
            item.get("canonical_url")
            or item.get("canonicalUrl")
            or item.get("url")
            or (PUB + "/p/" + slug if slug else "")
        )
        date = (
            item.get("post_date")
            or item.get("published_at")
            or item.get("publication_date")
            or item.get("date")
            or ""
        )
        desc = plain_text(
            item.get("subtitle")
            or item.get("truncated_body_text")
            or item.get("description")
            or ""
        )
        if len(desc) > 180:
            desc = desc[:177].rsplit(" ", 1)[0] + "…"
        if title and url:
            out.append({"title": title, "url": url, "date": date, "excerpt": desc})
    return out

def normalise_rss2json(data):
    if not isinstance(data, dict) or data.get("status") != "ok":
        return []
    out = []
    for item in (data.get("items") or [])[:3]:
        title = plain_text(item.get("title"))
        url = (item.get("link") or "").strip()
        date = (item.get("pubDate") or "").strip()
        desc = plain_text(item.get("description") or item.get("content") or "")
        if len(desc) > 180:
            desc = desc[:177].rsplit(" ", 1)[0] + "…"
        if title and url:
            out.append({"title": title, "url": url, "date": date, "excerpt": desc})
    return out

strategies = [
    ("direct Substack API", API_URL, normalise_substack),
    ("AllOrigins", "https://api.allorigins.win/get?url=" + urllib.parse.quote(API_URL, safe=""), normalise_substack),
    ("EveryOrigin", "https://everyorigin.jwvbremen.nl/get?url=" + urllib.parse.quote(API_URL, safe=""), normalise_substack),
    ("RSS2JSON", "https://api.rss2json.com/v1/api.json?rss_url=" + urllib.parse.quote(FEED_URL, safe=""), normalise_rss2json),
]

posts = []
errors = []
for name, url, parser in strategies:
    try:
        data = fetch_json(url)
        posts = parser(data)
        if posts:
            print(f"Success via {name}: {len(posts)} posts")
            break
        errors.append(f"{name}: returned no usable posts")
    except Exception as exc:
        errors.append(f"{name}: {type(exc).__name__}: {exc}")

if not posts:
    raise RuntimeError("All Substack fetch methods failed:\n" + "\n".join(errors))

payload = {
    "updated_at": datetime.now(timezone.utc).isoformat(),
    "posts": posts
}

with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)
    f.write("\n")
