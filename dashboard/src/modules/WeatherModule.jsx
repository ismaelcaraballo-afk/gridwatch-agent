export function WeatherModule({ weather }) {
  const alerts = Array.isArray(weather?.active_alerts) ? weather.active_alerts : []
  const forecast = weather?.forecast_12h || ''

  return (
    <article className="module">
      <p className="module__label">03 · Weather</p>
      <h2 className="module__title">Active alerts</h2>
      {alerts.length ? (
        <div>
          {alerts.map((a, i) => (
            <span className="alert-pill" key={i}>
              {a}
            </span>
          ))}
        </div>
      ) : (
        <p style={{ margin: '0 0 0.75rem', opacity: 0.75 }}>No active alerts.</p>
      )}
      <h2 className="module__title">12-hour outlook</h2>
      <div className="forecast-block">{forecast || '—'}</div>
    </article>
  )
}
