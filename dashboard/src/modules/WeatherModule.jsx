import { useMemo } from 'react'

const HOURLY_FALLBACK = [28, 32, 38, 44, 52, 68, 82, 94, 88, 76, 62, 48, 36]

function hourlyFromForecast(forecast) {
  const fc = forecast || []
  const temps = fc.map((r) => Number(r.temp_f)).filter((n) => !Number.isNaN(n))
  if (temps.length >= 6) return temps.slice(0, 13)
  return HOURLY_FALLBACK
}

function lerp(a, b, u) {
  return a + (b - a) * u
}

function clamp01(x) {
  return Math.min(1, Math.max(0, x))
}

function hsl(h, s, l) {
  return `hsl(${Math.round(h)}, ${Math.round(s)}%, ${Math.round(l)}%)`
}

/** Lime cap for cold hours (top of bar); blends toward yellow-green by 80°F */
const LIME_TOP = { h: 84, s: 82, l: 56 }
/** Top color just below the ≥80°F thermal strip */
const PRE_WARM_TOP = { h: 98, s: 72, l: 46 }

/**
 * Vertical ramps (bottom → top). No washed-out greens:
 * - &lt;80°F: deep green bottom; top is lime up to 60°F, then blends toward yellow-green by 80°
 * - ≥80°F: green (bottom) → yellow (mid) → orange (top); orange ramps from 80→100°F+
 */
function gradientFromTempF(tempF, temps) {
  const t = Number(tempF)
  if (!temps.length) {
    return `linear-gradient(to top, ${hsl(142, 54, 30)} 0%, ${hsl(LIME_TOP.h, LIME_TOP.s, LIME_TOP.l)} 100%)`
  }

  if (t >= 80) {
    const u = clamp01((t - 80) / 20)
    const bottom = hsl(138, 54, 38)
    const mid = hsl(lerp(54, 48, u), lerp(82, 90, u), lerp(53, 53, u))
    const top = hsl(lerp(44, 28, u), lerp(85, 92, u), lerp(52, 53, u))
    return `linear-gradient(to top, ${bottom} 0%, ${mid} 47%, ${top} 100%)`
  }

  const coldAnchor = Math.min(...temps)
  const span = Math.max(18, 80 - coldAnchor)
  const pos = clamp01((t - coldAnchor) / span)
  const bottomL = lerp(29, 34, pos)
  const bottom = hsl(lerp(143, 139, pos), lerp(54, 56, pos), bottomL)

  let topH
  let topS
  let topL
  if (t <= 60) {
    topH = LIME_TOP.h
    topS = LIME_TOP.s
    topL = LIME_TOP.l
  } else {
    const v = (t - 60) / 20
    topH = lerp(LIME_TOP.h, PRE_WARM_TOP.h, v)
    topS = lerp(LIME_TOP.s, PRE_WARM_TOP.s, v)
    topL = lerp(LIME_TOP.l, PRE_WARM_TOP.l, v)
  }
  const top = hsl(topH, topS, topL)
  return `linear-gradient(to top, ${bottom} 0%, ${top} 100%)`
}

function WeatherBars({ temps }) {
  const max = Math.max(...temps, 1)
  return (
    <div className="weather-bars">
      {temps.map((h, i) => (
        <div key={i} className="weather-bars__cell">
          <div
            className="weather-bars__bar"
            style={{
              height: `${(h / max) * 100}%`,
              opacity: 0.55 + (h / max) * 0.45,
              background: gradientFromTempF(h, temps),
            }}
          />
        </div>
      ))}
      <div className="weather-bars__labels">
        <span>6am</span>
        <span>6pm</span>
      </div>
    </div>
  )
}

function RenewRow({ label, level, pct, variant }) {
  return (
    <div className="renew-row">
      <span className="renew-row__label">{label}</span>
      <div className="renew-row__track">
        <div
          className={`renew-row__fill renew-row__fill--${variant}`}
          style={{ '--renew-pct': `${pct}%` }}
        />
      </div>
      <span className={`renew-row__badge renew-row__badge--${variant}`}>{level}</span>
    </div>
  )
}

function levelFromPct(pct) {
  if (pct >= 70) return { level: 'HIGH', variant: 'orange' }
  if (pct >= 35) return { level: 'MODERATE', variant: 'green' }
  return { level: 'LOW', variant: 'blue' }
}

export function WeatherModule({ weather, grid }) {
  const temps = useMemo(() => hourlyFromForecast(weather?.forecast), [weather?.forecast])
  const mix = grid?.generation_mix || {}
  const solar = Math.round(Number(mix.solar_pct) || 0)
  const wind = Math.round(Number(mix.wind_pct) || 0)
  const hydro = Math.round(Number(mix.hydro_pct) || 0)

  const peakTemp = temps.length ? Math.max(...temps) : 94
  const lowTemp = temps.length ? Math.min(...temps) : 62

  const solarL = levelFromPct(solar || 22)
  const windL = levelFromPct(wind || 22)
  const hydroL = levelFromPct(hydro || 22)

  return (
    <section className="brief-section briefing-card">
      <div className="brief-section__head">
        <span className="brief-section__num">03</span>
        <span className="brief-section__name">WEATHER</span>
      </div>
      <div className="brief-section__divider" />
      <div className="weather-layout">
        <div className="weather-col">
          <div className="weather-temp-row">
            <span className="weather-temp">{peakTemp}°F</span>
            <span className="weather-vs">peak in outlook · low {lowTemp}°F</span>
          </div>
          <p className="weather-surge">Hourly temps from briefing forecast ({temps.length} bars)</p>
          <WeatherBars temps={temps} />
        </div>
        <div className="weather-col weather-col--renew">
          <p className="weather-renew-title">Renewable share (generation mix)</p>
          <RenewRow label="Solar" level={solarL.level} pct={Math.min(100, solar || 18)} variant={solarL.variant} />
          <RenewRow label="Wind" level={windL.level} pct={Math.min(100, wind || 22)} variant={windL.variant} />
          <RenewRow label="Hydro" level={hydroL.level} pct={Math.min(100, hydro || 12)} variant={hydroL.variant} />
        </div>
      </div>
    </section>
  )
}
