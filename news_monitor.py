"""
news_monitor.py — Crude Oil News Fetcher and Sentiment Analyzer

Fetches news from:
  1. OilPrice.com RSS feed (primary, no API key needed)
  2. Reuters Business RSS feed (backup)
  3. NewsData.io API (optional, requires free API key)

Classifies each headline as BULLISH / BEARISH / NEUTRAL
based on keyword matching.
"""

import time
import hashlib
import threading
import feedparser
import requests
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import pytz

from config import (
    NEWS_RSS_FEEDS, NEWS_BEARISH_KEYWORDS, NEWS_BULLISH_KEYWORDS,
    NEWS_REFRESH_SECONDS, MAX_NEWS_ITEMS, NEWSDATA_API_KEY, IST_TIMEZONE
)

IST = pytz.timezone(IST_TIMEZONE)

# ─── Data Classes ──────────────────────────────────────────────────────────────

@dataclass
class NewsItem:
    """A single news headline with sentiment."""
    title: str = ""
    summary: str = ""
    url: str = ""
    source: str = ""
    sentiment: str = "NEUTRAL"    # "BULLISH", "BEARISH", "NEUTRAL"
    published: str = ""
    uid: str = ""

    @property
    def sentiment_emoji(self) -> str:
        if self.sentiment == "BULLISH":
            return "🟩"
        elif self.sentiment == "BEARISH":
            return "🟥"
        return "⬜"

    @property
    def sentiment_color(self) -> str:
        if self.sentiment == "BULLISH":
            return "#00C851"
        elif self.sentiment == "BEARISH":
            return "#FF4444"
        return "#AAAAAA"


# ─── Sentiment Classifier ─────────────────────────────────────────────────────

def classify_sentiment(title: str, summary: str = "") -> str:
    """
    Classify news as BULLISH, BEARISH, or NEUTRAL based on keywords.
    Checks both headline and summary.
    """
    text = (title + " " + summary).lower()

    bearish_score = sum(1 for kw in NEWS_BEARISH_KEYWORDS if kw.lower() in text)
    bullish_score = sum(1 for kw in NEWS_BULLISH_KEYWORDS if kw.lower() in text)

    if bearish_score > bullish_score:
        return "BEARISH"
    elif bullish_score > bearish_score:
        return "BULLISH"
    return "NEUTRAL"


# ─── News Fetcher ──────────────────────────────────────────────────────────────

class NewsMonitor:
    """
    Manages news fetching and provides the latest crude oil headlines.
    Runs fetch in background thread to avoid blocking the dashboard.
    """

    def __init__(self):
        self._news_items: list[NewsItem] = []
        self._lock = threading.Lock()
        self._last_fetch: float = 0.0
        self._overall_sentiment: str = "NEUTRAL"
        self._fetch_error: str = ""

    def _make_uid(self, title: str, source: str) -> str:
        return hashlib.md5(f"{title}{source}".encode()).hexdigest()[:12]

    def _fetch_rss_feeds(self) -> list[NewsItem]:
        """Fetch and parse all RSS feeds."""
        items = []
        for feed_url in NEWS_RSS_FEEDS:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:10]:
                    title = entry.get("title", "")
                    summary = entry.get("summary", "")
                    link = entry.get("link", "")
                    published = entry.get("published", "")
                    source = feed.feed.get("title", feed_url.split("/")[2])

                    # Only include crude-oil relevant articles
                    combined = (title + " " + summary).lower()
                    crude_keywords = ["crude", "oil", "opec", "petroleum", "brent", "wti", "energy", "refinery"]
                    if not any(kw in combined for kw in crude_keywords):
                        continue

                    uid = self._make_uid(title, source)
                    sentiment = classify_sentiment(title, summary)

                    items.append(NewsItem(
                        title=title,
                        summary=summary[:200] if summary else "",
                        url=link,
                        source=source,
                        sentiment=sentiment,
                        published=published,
                        uid=uid,
                    ))
            except Exception as e:
                print(f"[NewsMonitor] RSS error for {feed_url}: {e}")

        return items

    def _fetch_newsdata_api(self) -> list[NewsItem]:
        """Fetch from NewsData.io API if key is configured."""
        if not NEWSDATA_API_KEY:
            return []
        try:
            resp = requests.get(
                "https://newsdata.io/api/1/news",
                params={
                    "apikey": NEWSDATA_API_KEY,
                    "q": "crude oil OR OPEC OR petroleum",
                    "language": "en",
                    "category": "business",
                },
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            items = []
            for article in data.get("results", [])[:8]:
                title = article.get("title", "")
                desc = article.get("description", "")
                url = article.get("link", "")
                pub = article.get("pubDate", "")
                source = article.get("source_id", "NewsData")
                sentiment = classify_sentiment(title, desc)
                uid = self._make_uid(title, source)
                items.append(NewsItem(
                    title=title, summary=desc[:200] if desc else "",
                    url=url, source=source, sentiment=sentiment,
                    published=pub, uid=uid,
                ))
            return items
        except Exception as e:
            print(f"[NewsMonitor] NewsData.io error: {e}")
            return []

    def _compute_overall_sentiment(self, items: list[NewsItem]) -> str:
        """Determine dominant sentiment from recent headlines."""
        if not items:
            return "NEUTRAL"
        bullish = sum(1 for i in items if i.sentiment == "BULLISH")
        bearish = sum(1 for i in items if i.sentiment == "BEARISH")
        if bearish > bullish and bearish >= 2:
            return "BEARISH"
        elif bullish > bearish and bullish >= 2:
            return "BULLISH"
        return "NEUTRAL"

    def refresh(self):
        """Fetch fresh news. Respects cooldown to avoid hammering feeds."""
        now = time.time()
        if now - self._last_fetch < NEWS_REFRESH_SECONDS:
            return  # Still fresh

        self._last_fetch = now
        self._fetch_error = ""

        try:
            items = self._fetch_rss_feeds()
            if NEWSDATA_API_KEY:
                items.extend(self._fetch_newsdata_api())

            # Deduplicate by uid
            seen = set()
            unique = []
            for item in items:
                if item.uid not in seen:
                    seen.add(item.uid)
                    unique.append(item)

            # Sort by recency (most recent first) — use uid as fallback sort
            unique = unique[:MAX_NEWS_ITEMS]

            overall = self._compute_overall_sentiment(unique)

            with self._lock:
                self._news_items = unique
                self._overall_sentiment = overall

        except Exception as e:
            self._fetch_error = str(e)
            print(f"[NewsMonitor] Refresh error: {e}")

    def get_news(self) -> list[NewsItem]:
        """Return latest news items (thread-safe)."""
        with self._lock:
            return list(self._news_items)

    def get_overall_sentiment(self) -> str:
        """Return dominant sentiment: 'BULLISH', 'BEARISH', or 'NEUTRAL'."""
        with self._lock:
            return self._overall_sentiment

    def get_error(self) -> str:
        return self._fetch_error

    def force_refresh(self):
        """Force immediate refresh regardless of cooldown."""
        self._last_fetch = 0
        self.refresh()


# ─── Singleton instance ────────────────────────────────────────────────────────
_monitor_instance: Optional[NewsMonitor] = None

def get_news_monitor() -> NewsMonitor:
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = NewsMonitor()
    return _monitor_instance
