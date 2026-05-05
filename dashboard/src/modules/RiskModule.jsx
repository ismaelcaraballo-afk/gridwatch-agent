function riskClass(level) {
  const u = (level || 'GREEN').toUpperCase()
  if (u === 'RED') return 'risk-strip risk-strip--red'
  if (u === 'YELLOW') return 'risk-strip risk-strip--yellow'
  return 'risk-strip risk-strip--green'
}

export function RiskModule({ risk, alert }) {
  const factors = Array.isArray(risk?.factors) ? risk.factors : []

  return (
    <article className="module">
      <p className="module__label">01 · Risk level</p>
      <div className={riskClass(risk?.level)}>
        {(risk?.level || 'GREEN').toUpperCase()}
      </div>
      <h2 className="module__title" style={{ marginTop: '1rem' }}>
        Factors cited
      </h2>
      {factors.length ? (
        <ul>
          {factors.map((f, i) => (
            <li key={i}>{f}</li>
          ))}
        </ul>
      ) : (
        <p style={{ margin: 0, opacity: 0.75 }}>No bullet factors parsed.</p>
      )}
      <h2 className="module__title" style={{ marginTop: '1rem' }}>
        Alert channel
      </h2>
      <p style={{ margin: 0, fontSize: '0.88rem', opacity: 0.9 }}>
        <strong>{alert?.sent ? 'Sent' : 'Not sent'}</strong>
        {alert?.level ? ` · ${alert.level}` : ''}
      </p>
      <p style={{ margin: '0.35rem 0 0', fontSize: '0.82rem', opacity: 0.8 }}>
        {alert?.confirmation || '—'}
      </p>
    </article>
  )
}
