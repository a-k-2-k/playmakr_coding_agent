"""Highlights / clips finder.

When a user asks for highlights or a recap, we search public sources for
short video clips. Strategy (best-effort, no paid deps required):

1. If TWITTER_BEARER_TOKEN is set, query X/Twitter recent search for posts
   with native video from sports accounts mentioning the player/team.
2. Always fall back to building deep links (X search, YouTube search) so the
   user gets something tappable even without API keys.

Returns a list of {title, url, source} dicts.
"""
from __future__ import annotations

import logging
import re
from typing import List
from urllib.parse import quote_plus

import httpx

from .config import config

logger = logging.getLogger("playmakr.highlights")

TWITTER_SEARCH_URL = "https://api.twitter.com/2/tweets/search/recent"
# Accounts that reliably post NBA highlight clips.
HIGHLIGHT_ACCOUNTS = ["NBA", "Ballislife", "BleacherReport", "HoopMixOnly", "legion_hoops"]


def _twitter_video_clips(query: str, max_results: int = 5) -> List[dict]:
    """Search X/Twitter recent search for posts containing native video."""
    if not config.TWITTER_BEARER_TOKEN:
        return []

    from_clause = " OR ".join(f"from:{a}" for a in HIGHLIGHT_ACCOUNTS)
    q = f"({query}) ({from_clause}) has:videos -is:retweet"
    params = {
        "query": q,
        "max_results": str(max(10, max_results)),
        "tweet.fields": "created_at,attachments,author_id",
        "expansions": "author_id",
        "user.fields": "username",
    }
    headers = {"Authorization": f"Bearer {config.TWITTER_BEARER_TOKEN}"}
    try:
        resp = httpx.get(TWITTER_SEARCH_URL, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:  # noqa: BLE001
        logger.error("Twitter highlight search failed: %s", e)
        return []

    users = {u["id"]: u["username"] for u in data.get("includes", {}).get("users", [])}
    clips: List[dict] = []
    for tw in data.get("data", [])[:max_results]:
        username = users.get(tw.get("author_id"), "i")
        url = f"https://x.com/{username}/status/{tw['id']}"
        text = (tw.get("text") or "").strip()
        title = re.sub(r"https?://\S+", "", text)[:80].strip() or "Highlight clip"
        clips.append({"title": title, "url": url, "source": "x"})
    return clips


def _search_links(query: str) -> List[dict]:
    """Fallback deep links the user can tap to watch highlights."""
    q = quote_plus(f"{query} highlights")
    return [
        {"title": f"X search: {query}", "url": f"https://x.com/search?q={q}&f=video", "source": "x"},
        {"title": f"YouTube: {query}", "url": f"https://www.youtube.com/results?search_query={q}", "source": "youtube"},
    ]


def find_highlights(query: str, max_results: int = 3) -> List[dict]:
    """Top entry point: return a list of highlight clip dicts for a query.

    `query` is a natural phrase like "LeBron James most recent game".
    """
    clips = _twitter_video_clips(query, max_results=max_results)
    if len(clips) < max_results:
        clips += _search_links(query)
    return clips[:max(max_results, 2)]


def format_highlights_sms(query: str, clips: List[dict]) -> str:
    """Render highlight clips into a concise SMS body."""
    if not clips:
        return f"Couldn't find clips for {query} right now. Try again shortly."
    lines = [f"Highlights: {query}"]
    for c in clips:
        lines.append(f"- {c['url']}")
    return "\n".join(lines)
