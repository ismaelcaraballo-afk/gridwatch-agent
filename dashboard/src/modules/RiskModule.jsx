function riskClass(level) {
  const u = (level || 'GREEN').toUpperCase()
  if (u === 'RED') return 'risk-strip risk-strip--red'
  if (u === 'YELLOW') return 'risk-strip risk-strip--yellow'
  return 'risk-strip risk-strip--green'
}

export function RiskModule({ risk }) {
  const level = (risk?.level || 'GREEN').toUpperCase()
  const emoji = risk?.emoji || '🟢'

  return (
    <article className="module">
      <p className="module__label">01 · Risk gauge</p>
      <div className={riskClass(level)}>
        <span className="risk-strip__emoji" aria-hidden>
          {emoji}
        </span>
        {level}
      </div>
      <p className="module__hint">Level inferred from the briefing narrative.</p>
    </article>
  )
}
