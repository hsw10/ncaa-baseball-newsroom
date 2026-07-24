#!/usr/bin/env python3
"""Fetch current Division I college baseball coverage by conference group."""
from __future__ import annotations

import email.utils
import html as html_lib
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) D1BaseballNews/1.0"}
HOME_POST_COUNT = 5
DETAIL_POST_COUNT = 15
BLOCKED_PUBLISHERS = {"mshale"}

# Google News searches are intentionally scoped to each league.  The final
# title check keeps general football/basketball stories out of this dashboard.
SECTIONS = [
    {
        "name": "NCAA Baseball News",
        "slug": "ncaa-baseball",
        "url": "https://www.ncaa.com/sports/baseball/d1",
        "query": '"NCAA baseball"',
        "keywords": ("baseball", "mlb draft", "college world series"),
        "logo": "https://www.ncaa.com/favicon.ico",
        "accent": "#006dae",
        "description": "Division I national news, postseason and college baseball coverage",
    },
    {
        "name": "SEC Baseball",
        "slug": "sec",
        "url": "https://www.secsports.com/sport/baseball",
        "query": '"SEC baseball"',
        "keywords": ("baseball", "mlb draft", "college world series"),
        "logo": "sec-logo.svg",
        "accent": "#1c2541",
        "description": "Southeastern Conference",
    },
    {
        "name": "ACC Baseball",
        "slug": "acc",
        "url": "https://theacc.com/sports/baseball",
        "query": '"ACC baseball"',
        "keywords": ("baseball", "mlb draft", "college world series"),
        "logo": "https://theacc.com/favicon.ico",
        "accent": "#005a9c",
        "description": "Atlantic Coast Conference",
    },
    {
        "name": "Big Ten Baseball",
        "slug": "big-ten",
        "url": "https://bigten.org/sports/baseball",
        "query": '"Big Ten baseball"',
        "keywords": ("baseball", "mlb draft", "college world series"),
        "logo": "big-ten-logo.svg",
        "accent": "#001e62",
        "description": "Big Ten Conference",
    },
    {
        "name": "Big 12 Baseball",
        "slug": "big-12",
        "url": "https://big12sports.com/sports/baseball",
        "query": '"Big 12 baseball"',
        "keywords": ("baseball", "mlb draft", "college world series"),
        "logo": "https://big12sports.com/favicon.ico",
        "accent": "#cf1d3b",
        "description": "Big 12 Conference",
    },
    {
        "name": "Mid-Major Baseball",
        "slug": "mid-major",
        "url": "https://d1baseball.com/",
        "query": '("mid-major baseball" OR "AAC baseball" OR "Sun Belt baseball" OR "Conference USA baseball" OR "WCC baseball")',
        "keywords": ("baseball", "mlb draft", "college world series"),
        "logo": "https://d1baseball.com/favicon.ico",
        "accent": "#167a5a",
        "description": "AAC, Sun Belt, C-USA, WCC and other Division I mid-majors",
    },
]


def fetch(url: str) -> str:
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=35) as response:
        return response.read().decode("utf-8", "replace")


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html_lib.unescape(text or ""))).strip()


def date_value(raw: str) -> str:
    try:
        return email.utils.parsedate_to_datetime((raw or "").strip()).astimezone(timezone.utc).isoformat()
    except Exception:
        return (raw or "").strip()


def news_posts(section: dict) -> list[dict]:
    """Prefer the recent window, then fill from 90-day coverage if necessary."""
    posts, seen = [], set()
    for window in (30, 90):
        params = {"q": f"{section['query']} when:{window}d", "hl": "en-US", "gl": "US", "ceid": "US:en"}
        root = ET.fromstring(fetch("https://news.google.com/rss/search?" + urllib.parse.urlencode(params)))
        for item in root.findall(".//item"):
            raw_title = clean(item.findtext("title") or "Untitled")
            title = re.sub(r"\s+-\s+[^-]+$", "", raw_title)
            publisher = clean(item.findtext("source") or "").lower()
            if publisher in BLOCKED_PUBLISHERS:
                continue
            if not any(keyword in title.lower() for keyword in section["keywords"]):
                continue
            url = (item.findtext("link") or "").strip()
            if not url or url in seen:
                continue
            seen.add(url)
            posts.append({
                "title": title,
                "url": url,
                "published": date_value(item.findtext("pubDate") or ""),
                "excerpt": clean(item.findtext("description") or "")[:220],
                "image": "",
            })
    return sorted(posts, key=lambda post: post["published"], reverse=True)[:DETAIL_POST_COUNT]


def collect(section: dict) -> dict:
    posts = news_posts(section)
    if len(posts) < HOME_POST_COUNT:
        raise RuntimeError(f"only parsed {len(posts)} relevant posts")
    return {**section, "posts": posts[:HOME_POST_COUNT], "allPosts": posts, "status": "ok"}


def main() -> None:
    results_by_name, errors = {}, []
    with ThreadPoolExecutor(max_workers=len(SECTIONS)) as pool:
        futures = {pool.submit(collect, section): section for section in SECTIONS}
        for future in as_completed(futures):
            section = futures[future]
            try:
                results_by_name[section["name"]] = future.result()
            except Exception as exc:
                errors.append(f"{section['name']}: {exc}")
                results_by_name[section["name"]] = {**section, "posts": [], "status": "error", "error": str(exc)}
    sections = [results_by_name[section["name"]] for section in SECTIONS]
    OUT.write_text(json.dumps({"refreshedAt": datetime.now().astimezone().isoformat(), "sections": sections, "errors": errors}, ensure_ascii=False, indent=2))
    print(json.dumps({"sections": len(sections), "successful": len(sections) - len(errors), "errors": errors}))
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()