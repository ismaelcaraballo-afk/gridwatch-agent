export function OpsFooter({ recommendation, alertSent, actions, meta }) {
  const m = meta || {}
  const maint = Array.isArray(actions?.maintenance) ? actions.maintenance : []

  return (
    <footer className="ops-footer">
      <div className="ops-footer__block">
        <h3>Recommendation</h3>
        <p>{recommendation || '—'}</p>
      </div>
      <div className="ops-footer__row">
        <div className="ops-footer__block">
          <h3>Alert pushed</h3>
          <p>{alertSent ? 'Yes' : 'No'}</p>
        </div>
        <div className="ops-footer__block">
          <h3>Demand response</h3>
          <p>{actions?.demand_response || '—'}</p>
        </div>
      </div>
      <div className="ops-footer__block">
        <h3>Maintenance decisions</h3>
        {maint.length ? (
          <ul className="maint-list">
            {maint.map((row) => (
              <li key={row.unit}>
                <strong>{row.unit}</strong> — {row.decision}
                {row.reason ? <span className="maint-reason"> · {row.reason}</span> : null}
              </li>
            ))}
          </ul>
        ) : (
          <p className="module__muted">None parsed.</p>
        )}
      </div>
      <div className="ops-meta">
        <span>{m.timestamp || '—'}</span>
        <span>{m.model || '—'}</span>
        <span>
          Run cost:{' '}
          {typeof m.run_cost_usd === 'number' ? `$${m.run_cost_usd.toFixed(4)}` : '—'}
        </span>
      </div>
    </footer>
  )
}
