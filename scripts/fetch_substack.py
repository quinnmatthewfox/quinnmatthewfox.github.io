#!/usr/bin/env python3
import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser

PUB = "https://quinnmatthewfox.substack.com"
ARCHIVE_API = PUB + "/api/v1/archive?sort=new&search=&offset=0&limit=3"
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

def get_text(url, attempts=1):
    last = None
    for n in range(attempts):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/140 Safari/537.36",
                    "Accept": "application/json,text/plain,text/html,*/*",
                    "Referer": PUB + "/",
                },
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                return response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            last = exc
            # Don't waste retries on a hard block.
            if exc.code in (401, 403):
                break
            if n < attempts - 1:
                time.sleep(3 * (n + 1))
        except Exception as exc:
            last = exc
            if n < attempts - 1:
                time.sleep(3 * (n + 1))
    raise last

def parse_archive_json(text):
    data = json.loads(text)
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

def parse_rss2json(text):
    data = json.loads(text)
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

def parse_jina_markdown(text):
    # Last-resort reader proxy: collect unique public post links from the archive page.
    pattern = re.compile(r"\[([^\]]+)\]\((https?://quinnmatthewfox\.substack\.com/p/[^)\s?#]+)[^)]*\)")
    out = []
    seen = set()
    for title, url in pattern.findall(text):
        url = url.rstrip("/")
        if url in seen:
            continue
        clean_title = plain_text(title)
        if not clean_title or clean_title.lower() in {"comments", "read more"}:
            continue
        seen.add(url)
        out.append({"title": clean_title, "url": url, "date": "", "excerpt": ""})
        if len(out) == 3:
            break
    return out

strategies = [
    ("direct Substack archive", ARCHIVE_API, parse_archive_json, 1),
    ("RSS2JSON", "https://api.rss2json.com/v1/api.json?rss_url=" + urllib.parse.quote(FEED_URL, safe=""), parse_rss2json, 3),
    ("AllOrigins archive", "https://api.allorigins.win/get?url=" + urllib.parse.quote(ARCHIVE_API, safe=""), parse_archive_json, 2),
    ("Jina reader", "https://r.jina.ai/http://quinnmatthewfox.substack.com/archive", parse_jina_markdown, 2),
]

posts = []
errors = []
for name, url, parser, attempts in strategies:
    try:
        raw = get_text(url, attempts=attempts)
        posts = parser(raw)
        if posts:
            print(f"Success via {name}: {len(posts)} posts")
            break
        errors.append(f"{name}: returned no usable posts")
    except Exception as exc:
        errors.append(f"{name}: {type(exc).__name__}: {exc}")

if not posts:
    # Important: keep the last known-good posts.json rather than failing the job.
    print("No source was reachable this run; keeping cached posts.")
    for error in errors:
        print(" - " + error)
    raise SystemExit(0)

payload = {
    "updated_at": datetime.now(timezone.utc).isoformat(),
    "posts": posts
}

with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)
    f.write("\n")
