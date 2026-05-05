function impactTag(headline) {
  const h = (headline || '').toLowerCase()
  if (/alert|outage|blackout|emergency|conservation|spike|record/i.test(h)) {
    return 'HIGH'
  }
  if (/price|gas|demand|heat|storm|warning/i.test(h)) {
    return 'MEDIUM'
  }
  return 'LOW'
}

export function NewsModule({ news }) {
  const items = Array.isArray(news) ? news : []

  return (
    <article className="module module--full">
      <p className="module__label">05 · News + sentiment</p>
      <h2 className="module__title">Headlines</h2>
      {items.length ? (
        <ul className="news-list">
          {items.map((n) => {
            const tag = impactTag(n.headline)
            return (
              <li key={n.source + n.headline} className="news-item">
                <span className={`impact impact--${tag.toLowerCase()}`}>{tag}</span>
                <div className="news-body">
                  <div className="news-source">{n.source}</div>
                  <div className="news-headline">{n.headline}</div>
                </div>
              </li>
            )
          })}
        </ul>
      ) : (
        <p className="module__muted">No headlines returned.</p>
      )}
    </article>
  )
}
