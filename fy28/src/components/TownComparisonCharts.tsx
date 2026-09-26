import { useMemo, useState } from 'react'
import type { ChartProps } from './analysisCharts'

/* The charts for /analysis/towns-like-us, from /data/how-we-compare.json.
 * Rule 7f: a chart is a component, never an image. Nothing here computes a figure. */

/* WHY THE MAP IS HAND-DRAWN SVG AND NOT A CHART LIBRARY. A choropleth of real boundaries
 * is not a chart type recharts has, and the alternative -- a mapping library -- would want
 * tiles from a host the artifact CSP does not admit and would ship a megabyte to draw
 * thirty-two shapes. The polygons are already in the payload, already simplified by the
 * generator, and a projection is nine lines. What the component buys over the SVG in the
 * markdown is exactly what rule 7f says an image cannot give: a name and its figures under
 * the cursor, and a legend that filters. */

type Town = { rings: number[][][]; lat: number; lon: number }
type Row = {
  town: string; role: string; district: string
  bill: number | null; pp: number | null; cip: number | null
  rank: number | null; put: number; won: number; distance?: number
}
type Payload = {
  map: { towns: Record<string, Town>; outline: number[][][]; roles: Record<string, string> }
  local: Row[]; twins: Row[]; frame_size: number; fy: number; sy: number
  correlations: { key: string; r: number; text: string; label: string }[]
}

const ROLE_FILL: Record<string, string> = {
  lunenburg: '#1d4ed8', neighbour: '#0e7490', peer: '#7c3aed',
  structural: '#b45309', behavioural: '#be123c',
}
const ROLE_LABEL: Record<string, string> = {
  lunenburg: 'Lunenburg', neighbour: 'Shares a border', peer: 'Peer (our choice)',
  structural: 'Looks like Lunenburg', behavioural: 'Behaves like Lunenburg',
}
const ROLE_ORDER = ['lunenburg', 'neighbour', 'peer', 'structural', 'behavioural']

const usd = (n: number | null) =>
  n == null ? '—' : '$' + Math.round(n).toLocaleString('en-US')

export function TownsLikeUsMap({ data, alt }: ChartProps) {
  const d = data as Payload
  const [off, setOff] = useState<Set<string>>(new Set())
  const [over, setOver] = useState<string | null>(null)

  const rows = useMemo(() => {
    const by = new Map<string, Row>()
    // A town can be in both twin lists and in the local table. The first row wins, which
    // is the local one, because that is where its role was decided.
    for (const r of [...d.local, ...d.twins]) if (!by.has(r.town)) by.set(r.town, r)
    return by
  }, [d])

  const W = 756
  const proj = useMemo(() => {
    const xs: number[] = [], ys: number[] = []
    for (const ring of d.map.outline) for (const [x, y] of ring) { xs.push(x); ys.push(y) }
    const lon0 = Math.min(...xs), lon1 = Math.max(...xs)
    const lat0 = Math.min(...ys), lat1 = Math.max(...ys)
    const kx = Math.cos(((lat0 + lat1) / 2) * Math.PI / 180)
    const pad = 8
    const k = (W - 2 * pad) / ((lon1 - lon0) * kx)
    const H = Math.round(2 * pad + (lat1 - lat0) * k)
    return {
      H,
      px: (lon: number, lat: number): [number, number] =>
        [pad + (lon - lon0) * kx * k, pad + (lat1 - lat) * k],
    }
  }, [d])

  const shown = (t: string) => !off.has(d.map.roles[t])
  const rolesUsed = ROLE_ORDER.filter(r => Object.values(d.map.roles).includes(r))
  const hot = over ? rows.get(over) : null

  return (
    <>
      <div style={{
        display: 'flex', flexWrap: 'wrap', gap: '.4rem .8rem', marginBottom: '.6rem',
      }}>
        {rolesUsed.map(r => {
          const on = !off.has(r)
          return (
            <button
              key={r}
              onClick={() => setOff(p => {
                const n = new Set(p)
                if (n.has(r)) n.delete(r); else n.add(r)
                return n
              })}
              aria-pressed={on}
              style={{
                display: 'inline-flex', alignItems: 'center', gap: '.4rem',
                padding: '.3rem .6rem', minHeight: 32, cursor: 'pointer',
                borderRadius: 999, fontSize: 12.5,
                border: '1px solid var(--grid)',
                background: on ? 'var(--surface-1)' : 'transparent',
                color: on ? 'var(--text-primary)' : 'var(--text-secondary)',
                opacity: on ? 1 : 0.55,
              }}>
              <span style={{
                width: 10, height: 10, borderRadius: 999, background: ROLE_FILL[r],
              }} />
              {ROLE_LABEL[r]}
            </button>
          )
        })}
      </div>

      <div style={{ position: 'relative' }}>
        <svg viewBox={`0 0 ${W} ${proj.H}`} width="100%" height="auto"
             role="img" aria-label={alt}
             style={{ display: 'block', touchAction: 'manipulation' }}>
          {d.map.outline.map((ring, i) => (
            <polyline key={i} fill="none" stroke="var(--grid)" strokeWidth={0.5}
                      points={ring.map(([x, y]) => proj.px(x, y).join(',')).join(' ')} />
          ))}
          {Object.entries(d.map.towns).map(([name, t]) =>
            shown(name) ? t.rings.map((ring, i) => (
              <polygon
                key={name + i}
                points={ring.map(([x, y]) => proj.px(x, y).join(',')).join(' ')}
                fill={ROLE_FILL[d.map.roles[name]]}
                fillOpacity={over === name ? 0.68 : 0.3}
                stroke={ROLE_FILL[d.map.roles[name]]}
                strokeWidth={over === name ? 1.8 : 0.9} />
            )) : null)}
          {Object.entries(d.map.towns).map(([name, t]) => {
            if (!shown(name)) return null
            const [cx, cy] = proj.px(t.lon, t.lat)
            const me = d.map.roles[name] === 'lunenburg'
            return (
              <g key={'p' + name}
                 onMouseEnter={() => setOver(name)} onMouseLeave={() => setOver(null)}
                 onFocus={() => setOver(name)} onBlur={() => setOver(null)}
                 tabIndex={0} role="button" aria-label={name}
                 style={{ cursor: 'pointer', outline: 'none' }}>
                {/* A 13px invisible disc under a 3px dot: the visible mark is far below a
                    usable hit target, and on a phone the dot alone is unhittable. */}
                <circle cx={cx} cy={cy} r={13} fill="transparent" />
                <circle cx={cx} cy={cy} r={me ? 5.5 : 3.4}
                        fill={ROLE_FILL[d.map.roles[name]]}
                        stroke="var(--surface-1)" strokeWidth={1.2} />
              </g>
            )
          })}
          {shown('Lunenburg') && d.map.towns['Lunenburg'] && (() => {
            const [cx, cy] = proj.px(d.map.towns['Lunenburg'].lon, d.map.towns['Lunenburg'].lat)
            return (
              <text x={cx - 74} y={cy - 22} fontSize={11.5} fontWeight={700}
                    fill={ROLE_FILL.lunenburg} style={{ pointerEvents: 'none' }}>
                Lunenburg
              </text>
            )
          })()}
        </svg>

        {/* THE READOUT SITS BELOW THE MAP RATHER THAN FLOATING OVER IT. A tooltip pinned to
            the cursor is unreachable on a touch screen and covers the shape being read; a
            fixed row keeps the layout from reflowing as the pointer moves, which is what
            makes a map feel jumpy. */}
        <div style={{
          minHeight: 54, marginTop: '.5rem', padding: '.5rem .7rem',
          border: '1px solid var(--grid)', borderRadius: 8,
          background: 'var(--surface-1)', fontSize: 13,
        }}>
          {hot ? (
            <>
              <strong>{hot.town}</strong>
              <span style={{ color: 'var(--text-secondary)' }}>
                {' '}· {ROLE_LABEL[hot.role] ?? hot.role} · {hot.district}
              </span>
              <div style={{ marginTop: '.25rem', color: 'var(--text-secondary)' }}>
                {usd(hot.bill)} average bill FY{d.fy}
                {hot.rank ? ` (${hot.rank} of 351)` : ''}
                {' · '}{usd(hot.pp)} per pupil SY{d.sy}
                {hot.cip != null ? ` · ${hot.cip.toFixed(1)}% commercial` : ''}
                {' · '}{hot.won} of {hot.put} overrides won
              </div>
            </>
          ) : (
            <span style={{ color: 'var(--text-secondary)' }}>
              Point at a town for its tax bill, its per-pupil spending and its override
              record. Tap a colour above to hide that set.
            </span>
          )}
        </div>
      </div>
    </>
  )
}

/** Each correlation as a signed bar, in the payload's own order. */
/* No `alt` here: every row is already a label and a value as real text, so a screen reader
 * reads the chart itself rather than a description of it. The caption `markdown.tsx` prints
 * from the image's alt still appears underneath. */
export function TownsLikeUsDrivers({ data }: ChartProps) {
  const d = data as Payload
  const [over, setOver] = useState<string | null>(null)
  const half = 100
  return (
    <div style={{ display: 'grid', gap: '.3rem' }}>
        {d.correlations.map(c => {
          const w = Math.max(Math.abs(c.r) * half, 0.6)
          const pos = c.r >= 0
          return (
            <div key={c.key}
                 onMouseEnter={() => setOver(c.key)} onMouseLeave={() => setOver(null)}
                 style={{
                   display: 'grid',
                   // The label column wraps rather than truncating, and the bar column is
                   // a fraction so the whole row reflows at phone width instead of
                   // pushing the page sideways.
                   gridTemplateColumns: 'minmax(0,1fr) minmax(90px,140px) 46px',
                   alignItems: 'center', gap: '.5rem',
                   padding: '.3rem .4rem', borderRadius: 6,
                   background: over === c.key ? 'var(--surface-2)' : 'transparent',
                 }}>
              <span style={{ fontSize: 12.5, minWidth: 0, overflowWrap: 'break-word' }}>
                {c.label}
              </span>
              <span style={{ position: 'relative', height: 14 }}>
                <span style={{
                  position: 'absolute', left: '50%', top: -2, bottom: -2, width: 1,
                  background: 'var(--grid)',
                }} />
                <span style={{
                  position: 'absolute', top: 1, height: 12, borderRadius: 2,
                  left: pos ? '50%' : `calc(50% - ${w / 2}%)`,
                  width: `${w / 2}%`,
                  background: pos ? '#1d4ed8' : '#be123c', opacity: 0.85,
                }} />
              </span>
              <span style={{
                fontSize: 12.5, fontWeight: 600, textAlign: 'right',
                fontVariantNumeric: 'tabular-nums',
              }}>{c.text}</span>
            </div>
          )
      })}
    </div>
  )
}
