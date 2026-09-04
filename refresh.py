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
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) D1BaseballNews/1.0"}
IMAGE_HEADERS = {**HEADERS, "Accept": "text/html,application/xhtml+xml"}
HOME_POST_COUNT = 5
DETAIL_POST_COUNT = 15
BLOCKED_PUBLISHERS = {"mshale"}
BLOCKED_TITLE_PATTERNS = (
    re.compile(r"^baseball\s+(?:vs\.?|at)\b", re.I),
    re.compile(r"(?:ticket central|d1baseball\s+x|x\s+d1baseball)", re.I),
    re.compile(r"(?:pro debut|pro ball|baseball cards|collectibles|minor league|usa baseball|18u training|open tryouts|cape cod|engulfed in flames|smoke plume|baseball schedule|baseball tournament|volleyball|fantasy baseball|dynasty rankings)", re.I),
    re.compile(r"^[^:]+\s+-\s+baseball(?:\s|$)", re.I),
)
ACC_SOURCE_QUERIES = (
    '"ACC baseball"',
    'site:d1baseball.com ACC baseball',
    'site:baseballamerica.com ACC baseball',
    'site:espn.com ACC college baseball',
    'site:theacc.com baseball',
    # Every current ACC baseball member with an official athletics source.
    'site:bceagles.com baseball',
    'site:calbears.com baseball',
    'site:clemsontigers.com baseball',
    'site:goduke.com baseball',
    'site:seminoles.com baseball',
    'site:ramblinwreck.com baseball',
    'site:gocards.com baseball',
    'site:miamihurricanes.com baseball',
    'site:goheels.com baseball',
    'site:gopack.com baseball',
    'site:fightingirish.com baseball',
    'site:pittsburghpanthers.com baseball',
    'site:gostanford.com baseball',
    'site:virginiasports.com baseball',
    'site:hokiesports.com baseball',
    'site:wakeforestsports.com baseball',
    # Additional established ACC team/beat coverage.
    'site:bcinterruption.com Boston College baseball',
    'site:theclemsoninsider.com Clemson baseball',
    'site:insidecarolina.com North Carolina baseball',
    'site:packpride.com NC State baseball',
    'site:stingtalk.com Georgia Tech baseball',
)

MID_MAJOR_SOURCE_QUERIES = (
    '"mid-major baseball"',
    '"AAC baseball"',
    '"Sun Belt baseball"',
    '"Conference USA baseball"',
    '"WCC baseball"',
    '"Mountain West baseball"',
    '"Missouri Valley baseball"',
    '"Coastal Athletic Association baseball"',
    '"Southern Conference baseball"',
    '"Big South baseball"',
    '"Atlantic 10 baseball"',
    '"ASUN baseball"',
    '"Horizon League baseball"',
    '"Ivy League baseball"',
    '"Patriot League baseball"',
    '"Northeast Conference baseball"',
    '"Ohio Valley baseball"',
    '"Southland baseball"',
    '"Summit League baseball"',
    'site:d1baseball.com mid-major baseball',
    'site:baseballamerica.com mid-major baseball',
    'site:theamerican.org baseball',
    'site:sunbeltsports.org baseball',
    'site:conferenceusa.com baseball',
    'site:wccsports.com baseball',
    'site:themw.com baseball',
    'site:mvc-sports.com baseball',
    'site:caasports.com baseball',
    'site:soconsports.com baseball',
    'site:bigsouthsports.com baseball',
    'site:atlantic10.com baseball',
    'site:asunsports.org baseball',
    'site:horizonleague.org baseball',
    'site:ivyleague.com baseball',
    'site:patriotleague.org baseball',
    'site:ovcsports.com baseball',
    'site:southland.org baseball',
    'site:thesummitleague.org baseball',
)

SEC_SOURCE_QUERIES = (
    '"SEC baseball"',
    'site:d1baseball.com SEC baseball',
    'site:baseballamerica.com SEC baseball',
    'site:wholehogsports.com Arkansas baseball',
    'site:theadvocate.com LSU baseball',
    'site:rolltide.com Alabama baseball',
    'site:arkansasrazorbacks.com baseball',
    'site:auburntigers.com baseball',
    'site:floridagators.com baseball',
    'site:georgiadogs.com baseball',
    'site:ukathletics.com baseball',
    'site:lsusports.net baseball',
    'site:olemisssports.com baseball',
    'site:hailstate.com baseball',
    'site:mutigers.com baseball',
    'site:soonersports.com baseball',
    'site:gamecocksonline.com baseball',
    'site:utsports.com baseball',
    'site:texaslonghorns.com baseball',
    'site:12thman.com baseball',
    'site:vucommodores.com baseball',
)

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
        "sourceQueries": SEC_SOURCE_QUERIES,
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
        "sourceQueries": ACC_SOURCE_QUERIES,
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
        "sourceQueries": MID_MAJOR_SOURCE_QUERIES,
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


def usable_image(url: str) -> bool:
    lowered = (url or "").lower()
    return (
        lowered.startswith(("https://", "http://"))
        and "googleusercontent.com" not in lowered
        and "news.google.com" not in lowered
    )


def fallback_image(section: dict, title: str) -> str:
    """Create a durable branded thumbnail when a publisher image is unavailable."""
    palette = {
        "ncaa-baseball": ("#006dae", "#e9f4fb"),
        "sec": ("#1c2541", "#f3c969"),
        "acc": ("#005a9c", "#e8f3fb"),
        "big-ten": ("#001e62", "#f0f4ff"),
        "big-12": ("#cf1d3b", "#fff0f2"),
        "mid-major": ("#167a5a", "#e7f7ef"),
    }
    dark, light = palette.get(section["slug"], ("#14233a", "#e8eef2"))
    words = clean(title).replace("&", "and")[:100]
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="800" height="450" viewBox="0 0 800 450">'
        f'<rect width="800" height="450" fill="{dark}"/>'
        f'<circle cx="690" cy="80" r="170" fill="{light}" opacity=".18"/>'
        f'<path d="M0 365h800v85H0z" fill="{light}" opacity=".12"/>'
        f'<text x="48" y="74" fill="{light}" font-family="Arial" font-size="20" font-weight="700" letter-spacing="3">{section["name"].upper()}</text>'
        f'<text x="48" y="230" fill="white" font-family="Georgia" font-size="30" font-weight="700">{words}</text>'
        f'<text x="48" y="405" fill="{light}" font-family="Arial" font-size="16" letter-spacing="2">COLLEGE BASEBALL NEWSROOM</text></svg>'
    )
    return "data:image/svg+xml," + quote(svg)


def article_image(url: str) -> str:
    """Extract a publisher image from Open Graph or Twitter metadata."""
    try:
        request = urllib.request.Request(url, headers=IMAGE_HEADERS)
        with urllib.request.urlopen(request, timeout=20) as response:
            page_url = response.geturl()
            body = response.read(500_000).decode("utf-8", "replace")
        candidates = []
        for pattern in (
            r'<meta[^>]+property=["\']og:image(?::secure_url)?["\'][^>]+content=["\']([^"\']+)',
            r'<meta[^>]+name=["\']twitter:image(?::src)?["\'][^>]+content=["\']([^"\']+)',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image(?::secure_url)?["\']',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image(?::src)?["\']',
        ):
            candidates.extend(re.findall(pattern, body, re.I))
        for candidate in candidates:
            resolved = urllib.parse.urljoin(page_url, html_lib.unescape(candidate.strip()))
            if usable_image(resolved):
                return resolved
    except Exception:
        pass
    return ""


def resolve_article_url(url: str) -> str:
    """Resolve a Google News redirect to the publisher's canonical article URL."""
    try:
        request = urllib.request.Request(url, headers=IMAGE_HEADERS)
        with urllib.request.urlopen(request, timeout=20) as response:
            final_url = response.geturl()
            if final_url.startswith("https://news.google.com/"):
                body = response.read(700_000).decode("utf-8", "replace")
                canonical = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)', body, re.I)
                if canonical and not canonical.group(1).startswith("https://news.google.com/"):
                    return html_lib.unescape(canonical.group(1))
            return final_url
    except Exception:
        return url


def add_images(posts: list[dict]) -> list[dict]:
    """Resolve selected article thumbnails concurrently without failing refresh."""
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(resolve_article_url, post["url"]): post for post in posts}
        for future in as_completed(futures):
            post = futures[future]
            post["url"] = future.result()
        futures = {pool.submit(article_image, post["url"]): post for post in posts}
        for future in as_completed(futures):
            futures[future]["image"] = future.result()
    return posts


def news_posts(section: dict) -> list[dict]:
    """Prefer the recent window, then fill from 90-day coverage if necessary."""
    posts, seen = [], set()
    for window in (30, 90):
        for query in section.get("sourceQueries", (section["query"],)):
            params = {"q": f"{query} when:{window}d", "hl": "en-US", "gl": "US", "ceid": "US:en"}
            root = ET.fromstring(fetch("https://news.google.com/rss/search?" + urllib.parse.urlencode(params)))
            for item in root.findall(".//item"):
                raw_title = clean(item.findtext("title") or "Untitled")
                title = re.sub(r"\s+-\s+[^-]+$", "", raw_title)
                publisher = clean(item.findtext("source") or "").lower()
                if publisher in BLOCKED_PUBLISHERS:
                    continue
                if any(pattern.search(title) for pattern in BLOCKED_TITLE_PATTERNS):
                    continue
                if not any(keyword in title.lower() for keyword in section["keywords"]):
                    continue
                url = (item.findtext("link") or "").strip()
                if not url or url in seen:
                    continue
                seen.add(url)
                posts.append({
                    "source": clean(item.findtext("source") or "News source"),
                    "title": title,
                    "url": url,
                    "published": date_value(item.findtext("pubDate") or ""),
                    "excerpt": clean(item.findtext("description") or "")[:220],
                    "image": "",
                })
    selected = sorted(posts, key=lambda post: post["published"], reverse=True)[:DETAIL_POST_COUNT]
    selected = add_images(selected)
    for post in selected:
        if not usable_image(post.get("image", "")):
            post["image"] = fallback_image(section, post["title"])
    return selected


def collect(section: dict) -> dict:
    posts = news_posts(section)
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