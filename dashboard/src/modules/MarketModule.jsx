function fmt(n) {
  if (typeof n !== 'number' || Number.isNaN(n)) return '—'
  return n.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

export function MarketModule({ market }) {
  const m = market || {}
  const zones = m.lmp_by_zone && typeof m.lmp_by_zone === 'object' ? m.lmp_by_zone : {}
  const rows = Object.entries(zones).sort((a, b) => b[1] - a[1])

  return (
    <article className="module module--wide">
      <p className="module__label">04 · Market</p>
      <div className="market-stats">
        <div className="market-stat">
          <div className="market-stat__k">Zone avg ($/MWh)</div>
          <div className="market-stat__v">${fmt(m.zone_avg_mwh)}</div>
        </div>
        <div className="market-stat">
          <div className="market-stat__k">Spread ($/MWh)</div>
          <div className="market-stat__v">${fmt(m.spread_mwh)}</div>
        </div>
        <div className="market-stat">
          <div className="market-stat__k">Henry Hub</div>
          <div className="market-stat__v">${fmt(m.henry_hub_mmbtu)} / MMBtu</div>
        </div>
      </div>
      <h2 className="module__title">LMP by zone</h2>
      {rows.length ? (
        <div className="forecast-table-wrap">
          <table className="forecast-table">
            <thead>
              <tr>
                <th>Zone</th>
                <th>$/MWh</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(([z, price]) => (
                <tr key={z}>
                  <td>{z}</td>
                  <td>{fmt(price)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="module__muted">No zonal LMP parsed.</p>
      )}
    </article>
  )
}
