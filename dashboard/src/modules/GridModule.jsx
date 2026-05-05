const MIX_LABELS = [
  ['natural_gas_pct', 'Natural gas'],
  ['nuclear_pct', 'Nuclear'],
  ['wind_pct', 'Wind'],
  ['hydro_pct', 'Hydro'],
  ['solar_pct', 'Solar'],
]

export function GridModule({ grid }) {
  const g = grid || {}
  const mix = g.generation_mix || {}

  return (
    <article className="module">
      <p className="module__label">02 · Grid status</p>
      <p className="demand">
        {(g.current_demand_mw ?? 0).toLocaleString()}
        <span>MW demand · {g.region || 'NYISO'}</span>
      </p>
      <p className="module__kpi">
        <strong>Renewable share:</strong> {Number(g.renewable_pct ?? 0).toFixed(1)}%
      </p>
      <p className="module__kpi">
        <strong>Forecast peak:</strong>{' '}
        {(g.forecast_peak_mw ?? 0).toLocaleString()} MW
        {g.forecast_peak_time ? ` · ${g.forecast_peak_time}` : ''}
      </p>
      <h2 className="module__title">Generation mix</h2>
      <div className="gen-mix">
        {MIX_LABELS.map(([key, label]) => {
          const pct = Number(mix[key] ?? 0)
          return (
            <div className="gen-row" key={key}>
              <span className="gen-row__name">{label}</span>
              <div className="gen-row__bar-wrap">
                <div
                  className="gen-row__bar"
                  style={{ width: `${Math.min(100, Math.max(0, pct))}%` }}
                />
              </div>
              <span className="gen-row__pct">{pct.toFixed(1)}%</span>
            </div>
          )
        })}
      </div>
    </article>
  )
}
