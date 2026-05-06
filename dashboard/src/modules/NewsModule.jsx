const STATIC_HEADLINES = [
  {
    tier: 'HIGH',
    text: 'ERCOT issues conservation appeal…',
    url: 'https://www.ercot.com/news/',
    source: 'Reuters',
    ago: '14 min ago',
  },
  {
    tier: 'MED',
    text: 'Natural gas futures spike 8%…',
    source: 'Bloomberg',
    ago: '1h ago',
  },
  {
    tier: 'LOW',
    text: 'Wind farm capacity additions…',
    source: "Today's news",
    ago: '3h ago',
  },
]

function tierClass(tier) {
  const u = (tier || '').toUpperCase()
  if (u === 'HIGH') return 'news-tier news-tier--high'
  if (u === 'MED' || u === 'MEDIUM') return 'news-tier news-tier--med'
  return 'news-tier news-tier--low'
}

export function NewsModule({ news }) {
  const items = Array.isArray(news) && news.length >= 3
    ? news.slice(0, 3).map((n, i) => ({
        tier: inferTier(n.headline),
        text: n.headline || STATIC_HEADLINES[i].text,
        url: typeof n.url === 'string' ? n.url : undefined,
        source: n.source || STATIC_HEADLINES[i].source,
        ago: STATIC_HEADLINES[i].ago,
      }))
    : STATIC_HEADLINES

  return (
    <section className="brief-section briefing-card">
      <div className="brief-section__head">
        <span className="brief-section__num">05</span>
        <span className="brief-section__name">NEWS</span>
      </div>
      <div className="brief-section__divider" />
      <p className="news-subhead">Grid-Relevant Headlines + Sentiment</p>
      <ul className="news-feed">
        {items.map((item, i) => (
          <li key={i} className="news-feed__row" style={{ '--news-delay': i }}>
            <span className={tierClass(item.tier)}>
              {item.tier === 'MEDIUM' ? 'MED' : item.tier}
            </span>
            <div className="news-feed__body">
              <p className="news-feed__headline">
                {item.url ? (
                  <a
                    href={item.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="news-feed__link"
                  >
                    {item.text}
                  </a>
                ) : (
                  item.text
                )}
              </p>
              <p className="news-feed__meta">
                ({item.source}, {item.ago})
              </p>
            </div>
          </li>
        ))}
      </ul>
      <div className="sentiment">
        <div className="sentiment__bar">
          <div className="sentiment__seg sentiment__seg--bear" style={{ flex: '0 0 15%' }}>
            <span className="sentiment__lbl">Bearish 15%</span>
          </div>
          <div className="sentiment__seg sentiment__seg--cautious" style={{ flex: '0 0 30%' }}>
            <span className="sentiment__lbl">Cautious 30%</span>
          </div>
          <div className="sentiment__seg sentiment__seg--neutral" style={{ flex: '0 0 35%' }}>
            <span className="sentiment__lbl">Neutral 35%</span>
          </div>
          <div className="sentiment__seg sentiment__seg--bull" style={{ flex: '0 0 20%' }}>
            <span className="sentiment__lbl">Bullish 20%</span>
          </div>
        </div>
      </div>
    </section>
  )
}

function inferTier(headline) {
  const h = (headline || '').toLowerCase()
  if (/alert|outage|blackout|emergency|conservation|spike|record|appeal/i.test(h)) {
    return 'HIGH'
  }
  if (/price|gas|demand|heat|storm|warning|futures/i.test(h)) {
    return 'MED'
  }
  return 'LOW'
}
