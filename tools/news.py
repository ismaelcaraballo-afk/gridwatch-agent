import requests
import xml.etree.ElementTree as ET

RSS_FEEDS = [
    ("E&E News", "https://www.eenews.net/rss/1"),
    ("S&P Global Energy", "https://www.spglobal.com/commodityinsights/en/rss-feed/energy"),
]

FALLBACK_FEED = "https://rss.app/feeds/energy-news.xml"

def get_energy_news() -> str:
    """Get recent energy industry headlines from public RSS feeds."""
    headlines = []
    for name, url in RSS_FEEDS:
        try:
            resp = requests.get(url, timeout=10, headers={"User-Agent": "gridwatch-agent/1.0"})
            if resp.status_code != 200:
                continue
            root = ET.fromstring(resp.content)
            items = root.findall(".//item")[:3]
            for item in items:
                title = item.findtext("title", "").strip()
                if title:
                    headlines.append(f"[{name}] {title}")
        except Exception:
            continue

    if not headlines:
        return "No energy news headlines available at this time."
    return "\n".join(headlines)
