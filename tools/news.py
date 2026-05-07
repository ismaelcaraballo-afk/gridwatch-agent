import time
import defusedxml.ElementTree as ET

from tools.http import get_with_backoff

_cache = {"data": None, "ts": 0.0}
_CACHE_TTL = 15 * 60  # 15 minutes — RSS feeds don't update by the minute

RSS_FEEDS = [
    ("EIA Today in Energy", "https://www.eia.gov/rss/todayinenergy.xml"),
    ("OilPrice.com", "https://oilprice.com/rss/main"),
    ("Power Magazine", "https://www.powermag.com/feed/"),
    ("Utility Dive", "https://www.utilitydive.com/feeds/news/"),
]

def get_energy_news() -> str:
    """Get recent energy industry headlines from public RSS feeds."""
    if _cache["data"] and time.time() - _cache["ts"] < _CACHE_TTL:
        return _cache["data"]

    headlines = []
    for name, url in RSS_FEEDS:
        try:
            resp = get_with_backoff(url, timeout=10, headers={"User-Agent": "gridwatch-agent/1.0"})
            root = ET.fromstring(resp.content)
            items = root.findall(".//item")[:3]
            for item in items:
                title = item.findtext("title", "").strip()
                pub_date = item.findtext("pubDate", "").strip()
                if title:
                    date_str = f" ({pub_date})" if pub_date else ""
                    headlines.append(f"[{name}]{date_str} {title}")
        except Exception:
            continue

    if not headlines:
        return "No energy news headlines available at this time."
    result = "\n".join(headlines)
    _cache.update({"data": result, "ts": time.time()})
    return result


_SENTIMENT_KEYWORDS = {
    "bearish": [
        "spike", "surge", "crisis", "shortage", "outage", "disruption", "warning",
        "alert", "conflict", "sanctions", "cut", "decline", "risk", "threat",
        "record high", "ban", "war", "fail", "loss", "deficit", "curtail",
    ],
    "cautious": [
        "tight", "concern", "elevated", "above average", "potential", "possible",
        "monitor", "uncertain", "volatile", "watch", "delay", "stall", "oppose",
        "slow", "challenge", "pressure",
    ],
    "bullish": [
        "growth", "expand", "investment", "record low", "renewable", "clean",
        "new", "open", "ships", "launch", "advance", "capacity", "efficient",
        "approve", "gain", "increase", "boost", "strong",
    ],
}


def get_news_sentiment() -> str:
    """Score energy headlines by sentiment. Returns formatted string of percentages."""
    raw = get_energy_news()
    if raw == "No energy news headlines available at this time.":
        return "News sentiment — Bearish: 0% | Cautious: 0% | Neutral: 100% | Bullish: 0%"

    headlines = [line.split("] ", 1)[-1].lower() for line in raw.splitlines() if line]
    counts = {"bearish": 0, "cautious": 0, "neutral": 0, "bullish": 0}

    for headline in headlines:
        matched = None
        for bucket, keywords in _SENTIMENT_KEYWORDS.items():
            if any(kw in headline for kw in keywords):
                matched = bucket
                break
        counts[matched or "neutral"] += 1

    total = len(headlines)
    if total == 0:
        return "News sentiment — Bearish: 0% | Cautious: 0% | Neutral: 100% | Bullish: 0%"

    pct = {k: round(v / total * 100) for k, v in counts.items()}
    return (
        f"News sentiment — Bearish: {pct['bearish']}% | "
        f"Cautious: {pct['cautious']}% | "
        f"Neutral: {pct['neutral']}% | "
        f"Bullish: {pct['bullish']}%"
    )
