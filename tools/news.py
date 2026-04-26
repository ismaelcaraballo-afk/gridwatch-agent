import requests
import xml.etree.ElementTree as ET

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
            resp = requests.get(url, timeout=10, headers={"User-Agent": "gridwatch-agent/1.0"})
            if resp.status_code != 200:
                continue
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
    return "\n".join(headlines)
