import json
from datetime import date
from pathlib import Path

import defusedxml.ElementTree as ET

from tools.http import get_with_backoff

SENTIMENT_HISTORY_FILE = Path(__file__).parent.parent / ".sentiment_history.json"

RSS_FEEDS = [
    ("EIA Today in Energy", "https://www.eia.gov/rss/todayinenergy.xml"),
    ("OilPrice.com", "https://oilprice.com/rss/main"),
    ("Power Magazine", "https://www.powermag.com/feed/"),
    ("Utility Dive", "https://www.utilitydive.com/feeds/news/"),
]

def get_energy_news() -> str:
    """Get recent energy industry headlines from public RSS feeds."""
    headlines = []
    for name, url in RSS_FEEDS:
        try:
            resp = get_with_backoff(url, timeout=10, headers={"User-Agent": "gridwatch-agent/1.0"})
            root = ET.fromstring(resp.content)
            items = root.findall(".//item")[:3]
            for item in items:
                title = item.findtext("title", "").strip()
                pub_date = item.findtext("pubDate", "").strip()
                link = item.findtext("link", "").strip()
                if title:
                    date_str = f" ({pub_date})" if pub_date else ""
                    link_str = f"\n    {link}" if link else ""
                    headlines.append(f"[{name}]{date_str} {title}{link_str}")
        except Exception:
            continue

    if not headlines:
        return "No energy news headlines available at this time."
    return "\n".join(headlines)


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
    today_str = date.today().isoformat()

    try:
        history = json.loads(SENTIMENT_HISTORY_FILE.read_text()) if SENTIMENT_HISTORY_FILE.exists() else {}
    except Exception:
        history = {}

    yesterday = {k: v for k, v in history.items() if k != "date"} if history else None
    history = {**pct, "date": today_str}
    try:
        SENTIMENT_HISTORY_FILE.write_text(json.dumps(history))
    except Exception:
        pass

    sentiment_str = (
        f"News sentiment — Bearish: {pct['bearish']}% | "
        f"Cautious: {pct['cautious']}% | "
        f"Neutral: {pct['neutral']}% | "
        f"Bullish: {pct['bullish']}%"
    )

    if yesterday and history.get("date") != yesterday.get("date"):
        bear_shift = pct["bearish"] - yesterday.get("bearish", pct["bearish"])
        bull_shift = pct["bullish"] - yesterday.get("bullish", pct["bullish"])
        if abs(bear_shift) >= 5:
            direction = "↑" if bear_shift > 0 else "↓"
            trend = f"Bearish {direction}{abs(bear_shift)}% vs yesterday — mood {'deteriorating' if bear_shift > 0 else 'improving'}"
            sentiment_str += f"\nSentiment shift: {trend}"
        elif abs(bull_shift) >= 5:
            direction = "↑" if bull_shift > 0 else "↓"
            trend = f"Bullish {direction}{abs(bull_shift)}% vs yesterday — mood {'improving' if bull_shift > 0 else 'deteriorating'}"
            sentiment_str += f"\nSentiment shift: {trend}"
    elif not yesterday:
        sentiment_str += "\nSentiment shift: first reading — no prior day to compare"

    return sentiment_str
