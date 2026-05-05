function fmt(n) {
  if (typeof n !== 'number' || Number.isNaN(n)) return '—'
  return n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export function MarketModule({ market }) {
  const m = market || {}

  return (
    <article className="module">
      <p className="module__label">04 · Market (NYISO LMP)</p>
      <div className="market-stats">
        <div className="market-stat">
          <div className="market-stat__k">Peak zone</div>
          <div className="market-stat__v">{m.lmp_peak_zone || '—'}</div>
        </div>
        <div className="market-stat">
          <div className="market-stat__k">Peak $/MWh</div>
          <div className="market-stat__v">${fmt(m.lmp_peak)}</div>
        </div>
        <div className="market-stat">
          <div className="market-stat__k">Zone avg</div>
          <div className="market-stat__v">${fmt(m.lmp_avg)}</div>
        </div>
        <div className="market-stat">
          <div className="market-stat__k">Spread</div>
          <div className="market-stat__v">${fmt(m.spread)}</div>
        </div>
      </div>
    </article>
  )
}
