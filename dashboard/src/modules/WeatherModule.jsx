export function WeatherModule({ weather }) {
  const w = weather || {}
  const alerts = Array.isArray(w.alerts) ? w.alerts : []
  const forecast = Array.isArray(w.forecast) ? w.forecast : []

  return (
    <article className="module module--wide">
      <p className="module__label">03 · Weather</p>
      <h2 className="module__title">Active alerts</h2>
      {alerts.length ? (
        <ul className="weather-alert-list">
          {alerts.map((a, i) => (
            <li key={i}>
              <span className="weather-severity">{a.severity}</span>{' '}
              <span>{a.event}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="module__muted">No active alerts.</p>
      )}
      <h2 className="module__title">12-hour forecast</h2>
      {forecast.length ? (
        <div className="forecast-table-wrap">
          <table className="forecast-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>°F</th>
                <th>Condition</th>
              </tr>
            </thead>
            <tbody>
              {forecast.map((row, i) => (
                <tr key={i}>
                  <td>{row.time}</td>
                  <td>{row.temp_f}</td>
                  <td>{row.condition}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="module__muted">No hourly rows parsed.</p>
      )}
    </article>
  )
}
