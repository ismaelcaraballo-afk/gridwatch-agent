const COLORS = [
  '#0ea5e9',
  '#8b5cf6',
  '#10b981',
  '#f59e0b',
  '#ef4444',
  '#64748b',
]

export function GridModule({ grid }) {
  const demand = grid?.demand_mw ?? 0
  const mix = grid?.gen_mix && typeof grid.gen_mix === 'object' ? grid.gen_mix : {}
  const entries = Object.entries(mix).sort((a, b) => b[1] - a[1])

  return (
    <article className="module">
      <p className="module__label">02 · Grid status</p>
      <p className="demand">
        {demand.toLocaleString()}
        <span>MW demand</span>
      </p>
      <h2 className="module__title">Generation mix</h2>
      {entries.length ? (
        <div className="gen-mix">
          {entries.map(([name, pct], i) => (
            <div className="gen-row" key={name}>
              <span className="gen-row__name" title={name}>
                {name}
              </span>
              <div className="gen-row__bar-wrap">
                <div
                  className="gen-row__bar"
                  style={{
                    width: `${Math.min(100, Math.max(0, pct))}%`,
                    background: COLORS[i % COLORS.length],
                  }}
                />
              </div>
              <span className="gen-row__pct">{pct.toFixed(1)}%</span>
            </div>
          ))}
        </div>
      ) : (
        <p style={{ margin: 0, opacity: 0.75 }}>No fuel mix in briefing payload.</p>
      )}
    </article>
  )
}
