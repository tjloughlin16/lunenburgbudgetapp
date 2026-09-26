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

type Town = { lat: number; lon: number }
type Row = {
  town: string; role: string; district: string
  bill: number | null; pp: number | null; cip: number | null
  rank: number | null; put: number; won: number; distance?: number
}
type Effort = { required_pp: number; state_pp: number; foundation_pp: number; share: number }
type Heat = {
  shapes: Record<string, number[][][]>
  measures: {
    key: string; label: string; kind: string; note: string; covered: number
    values: Record<string, number>; lo: number; hi: number; median: number
    lunenburg: number | null
  }[]
  n_towns: number
}
type Payload = {
  map: { towns: Record<string, Town>; roles: Record<string, string> }
  heatmap: Heat
  local: Row[]; twins: Row[]; frame_size: number; fy: number; sy: number
  correlations: { key: string; r: number; text: string; label: string }[]
  effort: Record<string, Effort>
}

const ROLE_FILL: Record<string, string> = {
  lunenburg: '#1d4ed8', neighbour: '#0e7490', peer: '#7c3aed',
  structural: '#b45309', behavioural: '#be123c',
}
/* A LEGEND HAS TO SAY WHAT THE COLOUR MEANS, not name our category for it.
 *
 * TJ, looking at the map: *"i dont know what the colors actually mean"*. The chips said
 * `Looks like us` and `Acts like us`, which are this project's shorthand for two cohorts
 * built by different arithmetic -- perfectly clear to whoever built them and opaque to
 * everybody else. `Peer town` was worse: it named a set without admitting whose choice it
 * was. A label on a map is read by somebody who has not read the method, so it has to carry
 * the method in four words. */
const ROLE_LABEL: Record<string, string> = {
  lunenburg: 'Lunenburg',
  neighbour: 'Shares our border',
  peer: 'We chose to compare',
  structural: 'Same kind of town',
  behavioural: 'Taxes and spends like us',
}
/* ...and the long form, on the readout, where there is room to say how it was decided. */
const ROLE_LONG: Record<string, string> = {
  lunenburg: 'Lunenburg',
  neighbour: 'Shares a border with Lunenburg',
  peer: 'A town this project chose to compare, not the state',
  structural: 'Same kind of town — matched on children, homes and incomes',
  behavioural: 'Taxes and spends like Lunenburg',
}
/* What each colour means, spelled out once under the map. The two matched groups are the
 * ones nobody can guess, so they get the measures they were matched on. */
const ROLE_MEANS: Record<string, string> = {
  neighbour: 'one of the six towns that touch Lunenburg on the map',
  peer: 'a town this project has long compared Lunenburg with — our choice, not the state’s',
  structural: 'closest to Lunenburg on things a town does not choose: how many children, how '
    + 'many are low-income or have a disability, what homes are worth, income per head, and '
    + 'how much of the tax base is business',
  behavioural: 'closest to Lunenburg on what it DOES: the size of the tax bill, spending per '
    + 'pupil, how often it asks voters for an override, and the trend in each',
}
const ROLE_ORDER = ['lunenburg', 'neighbour', 'peer', 'structural', 'behavioural']

const usd = (n: number | null) =>
  n == null ? '—' : '$' + Math.round(n).toLocaleString('en-US')

export function TownsLikeUsMap({ data, alt }: ChartProps) {
  const d = data as Payload
  const [off, setOff] = useState<Set<string>>(new Set())
  const [over, setOver] = useState<string | null>(null)
  // A TAP HAS NO HOVER. On a touch screen `onMouseEnter` fires once on tap and
  // `onMouseLeave` fires the moment the finger lifts, so the readout appeared and vanished
  // before it could be read. A tapped town stays selected until another is tapped.
  const [pinned, setPinned] = useState<string | null>(null)

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
    for (const rings of Object.values(d.heatmap.shapes))
      for (const ring of rings) for (const [x, y] of ring) { xs.push(x); ys.push(y) }
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

  /* THE WHOLE STATE STAYS VISIBLE, EVEN ON A PHONE -- and the first attempt at mobile got
   * this wrong in an instructive way.
   *
   * Giving the SVG a 620px minimum and letting its container scroll sideways made the
   * shapes bigger and the map WORSE: a 390px window opens on the left edge of the drawing,
   * which is western Massachusetts, where none of the compared towns are. The reader's own
   * town was off screen until they thought to swipe. Making a map bigger than the screen
   * means choosing which third of it somebody sees first, and there is no third that is
   * right for everybody.
   *
   * So the drawing always fits, the shapes stay small, and the TAP TARGET does the work:
   * every town carries an invisible 26px disc, which is a real finger target over a 7px
   * dot. Small and hittable beats large and hidden. */

  return (
    <>
      {/* THE MAP NEVER GROWS TALLER THAN THE SCREEN.
        *
        * Massachusetts is about 1.4 times wider than it is tall, so on a 2,000px browser
        * window the drawing came out roughly 1,450px tall -- and the readout pinned to its
        * foot sat below the fold. TJ, having clicked a town: *"i do NOT see the data because
        * its below"*. Pinning the panel inside the map is not enough if the map itself does
        * not fit on the screen.
        *
        * So the wrapper is capped by VIEWPORT HEIGHT and its width follows from the map's
        * own aspect ratio, which keeps the drawing filling its box exactly -- capping the
        * SVG's height directly would letterbox it with dead space down both sides. On a
        * phone the cap never binds: 390px of width is only ~280px of height. */}
      <div style={{
        position: 'relative',
        maxWidth: `calc(68vh * ${(W / proj.H).toFixed(3)})`,
        margin: '0 auto',
      }}>
        <svg viewBox={`0 0 ${W} ${proj.H}`} width="100%" height="auto"
             role="img" aria-label={alt}
             style={{ display: 'block', touchAction: 'manipulation' }}>
          {Object.entries(d.heatmap.shapes).map(([nm, rings]) => rings.map((ring, i) => (
            <polyline key={nm + i} fill="none" stroke="var(--grid)" strokeWidth={0.5}
                      points={ring.map(([x, y]) => proj.px(x, y).join(',')).join(' ')} />
          )))}
          {Object.entries(d.map.towns).map(([name]) =>
            shown(name) ? (d.heatmap.shapes[name] ?? []).map((ring, i) => (
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
                 onMouseEnter={() => setOver(name)}
                 onMouseLeave={() => setOver(o => (pinned ? o : null))}
                 onFocus={() => setOver(name)}
                 onBlur={() => setOver(o => (pinned ? o : null))}
                 onClick={() => { setPinned(name); setOver(name) }}
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
          {/* THE HIGHLIGHTED TOWN NAMES ITSELF, on a leader, like Lunenburg does.
            *
            * TJ: *"is there a way to put town labels on the map when they are highlighted?
            * with like a line to point to them?"* The readout under the map says WHICH town
            * you are on, but it is 400px away from the shape your cursor is over, so the eye
            * has to make the join. A label at the shape closes that.
            *
            * Drawn LAST so it sits above every polygon and pin, and only for the one town in
            * play -- thirty-two permanent labels at this scale is a smear, which is why only
            * Lunenburg carries one the rest of the time.
            *
            * The side is chosen from where the town IS: a label pinned to the right of a
            * town on the eastern edge runs off the drawing, and one above a town at the top
            * runs into the title. Both flip. */}
          {over && d.map.towns[over] && shown(over) && (() => {
            const [cx, cy] = proj.px(d.map.towns[over].lon, d.map.towns[over].lat)
            const wide = over.length * 6.4 + 10
            const left = cx > W * 0.6
            const up = cy > 48
            const tx = left ? cx - 22 - wide : cx + 22
            const ty = up ? cy - 20 : cy + 26
            const fill = ROLE_FILL[d.map.roles[over]]
            return (
              <g style={{ pointerEvents: 'none' }}>
                <line x1={cx} y1={cy} x2={left ? tx + wide : tx} y2={ty}
                      stroke={fill} strokeWidth={1.1} />
                <rect x={left ? tx : tx} y={ty - 10} width={wide} height={17} rx={3}
                      fill="var(--surface-1)" stroke={fill} strokeWidth={0.9} />
                <text x={tx + wide / 2} y={ty + 2.5} fontSize={11} fontWeight={700}
                      textAnchor="middle" fill={fill}>{over}</text>
              </g>
            )
          })()}
          {shown('Lunenburg') && d.map.towns['Lunenburg'] && over !== 'Lunenburg' && (() => {
            const [cx, cy] = proj.px(d.map.towns['Lunenburg'].lon, d.map.towns['Lunenburg'].lat)
            return (
              <text x={cx - 74} y={cy - 22} fontSize={11.5} fontWeight={700}
                    fill={ROLE_FILL.lunenburg} style={{ pointerEvents: 'none' }}>
                Lunenburg
              </text>
            )
          })()}
        </svg>

        {/* THE READOUT IS PINNED INSIDE THE MAP, not under it.
            TJ: *"hovering makes me scroll to see the info. it should popup somewhere on the
            map. i cant see it"* -- and he was right: the panel sat below a 470px-tall map,
            so the answer to "what is this town?" was off screen at the moment of asking.
            It is pinned to a CORNER rather than to the cursor: a tooltip that follows the
            pointer covers the shape being read and cannot be reached at all by touch, while
            a fixed corner never moves and never reflows the page. */}
        <div style={{
          position: 'absolute', left: 8, right: 8, bottom: 8, maxWidth: 460,
          pointerEvents: 'none',
          padding: '.5rem .7rem',
          border: '1px solid var(--grid)', borderRadius: 8,
          background: 'var(--surface-1)', fontSize: 13,
          boxShadow: hot ? '0 2px 12px rgba(0,0,0,.14)' : 'none',
          opacity: hot ? 1 : 0.92,
        }}>
          {hot ? (
            <>
              <strong>{hot.town}</strong>
              <span style={{ color: 'var(--text-secondary)' }}>
                {' '}· {ROLE_LONG[hot.role] ?? hot.role}
                {/* The district is named only when it is NOT the town. For a single-town
                    district the two are the same word and it printed `Douglas · Looks like
                    Lunenburg · Douglas`. */}
                {hot.district && hot.district !== hot.town ? ` · ${hot.district} district` : ''}
              </span>
              <div style={{ marginTop: '.25rem', color: 'var(--text-secondary)' }}>
                {usd(hot.bill)} average tax bill on a single-family home
                {hot.rank ? `, ${hot.rank}th highest of the 351 Massachusetts towns` : ''}
                <br />
                {usd(hot.pp)} spent per pupil{hot.pp != null ? ' (all funds)' : ''}
                {hot.cip != null
                  ? ` · ${hot.cip.toFixed(1)}% of its tax base is business` : ''}
                {hot.put != null
                  ? ` · ${hot.won} of ${hot.put} override questions passed` : ''}
                {/* THE TWO FIGURES THE REPORT IS ACTUALLY ABOUT. What a town is required to
                    raise for each of its own children, and how far above the state's own
                    state says its schools need it actually spends -- the only like-for-like
                    on the page, and the one a reader clicking a town wants. Published for
                    every town, including the ones in regional districts. */}
                {d.effort?.[hot.town] && (
                  <>
                    <br />
                    Required to raise {usd(d.effort[hot.town].required_pp)} per child; the
                    state adds {usd(d.effort[hot.town].state_pp)}
                    {hot.pp
                      ? ` · spends ${(hot.pp / d.effort[hot.town].foundation_pp).toFixed(2)}×`
                        + ' what the state says its schools need'
                      : ''}
                  </>
                )}
              </div>
            </>
          ) : (
            <span style={{ color: 'var(--text-secondary)' }}>
              Tap or point at a town for its tax bill, what its schools spend per pupil and
              its override record. Tap a colour below to hide that group.
            </span>
          )}
        </div>
      </div>

      {/* THE LEGEND SITS UNDER THE MAP, and says what each colour MEANS.
        * TJ: *"can you put a color chip legend into the map... or below"* and then the real
        * problem: *"i dont know what the colors actually mean"*. A chip that names our
        * category is not a legend; it is a label for people who already know. The chips
        * still filter, and the sentences under them say how each group was decided. */}
      <div style={{
        display: 'flex', flexWrap: 'wrap', gap: '.4rem .8rem', marginTop: '.6rem',
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
      <div style={{
        marginTop: '.6rem', fontSize: 12.5, lineHeight: 1.5,
        color: 'var(--text-secondary)',
      }}>
        {rolesUsed.filter(r => ROLE_MEANS[r]).map(r => (
          <div key={r} style={{ display: 'flex', gap: '.45rem', marginTop: '.2rem' }}>
            <span style={{
              flex: '0 0 auto', width: 9, height: 9, borderRadius: 999, marginTop: 5,
              background: ROLE_FILL[r],
            }} />
            <span style={{ minWidth: 0 }}>
              <strong style={{ color: 'var(--text-primary)' }}>{ROLE_LABEL[r]}</strong>
              {' \u2014 '}{ROLE_MEANS[r]}
            </span>
          </div>
        ))}
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

/* ---- where the money comes from, and where Lunenburg sits ------------------------- */

type FundRow = {
  town: string; pupils: number; per_pupil: number
  from_homes: number; from_business: number; from_state: number; above_foundation: number
}
type Dist = {
  key: string; label: string; kind: string; note: string; n: number
  lunenburg: number; rank: number; median: number; lo: number; hi: number
  p25: number; p75: number; values: number[]
}

const FUND_PARTS: [keyof FundRow, string, string][] = [
  ['from_homes', 'From homes', '#3b5bbf'],
  ['from_business', 'From business', '#ea8c00'],
  ['from_state', 'From the state', '#2f8f4e'],
  ['above_foundation', 'Spent above the state’s figure', '#7c3aed'],
]

const ord = (n: number) =>
  n % 100 >= 10 && n % 100 <= 20 ? `${n}th`
    : `${n}${({ 1: 'st', 2: 'nd', 3: 'rd' } as Record<number, string>)[n % 10] ?? 'th'}`

const fmtKind = (v: number, kind: string) =>
  kind === 'usd' ? usd(v)
    : kind === 'pct' ? `${v.toFixed(1)}%`
      : kind === 'pctdiff' ? `${v >= 0 ? '+' : ''}${v.toFixed(1)}%`
        : kind === 'ratio' ? `${v.toFixed(2)}×`
          : kind === 'rate' ? v.toFixed(2)
            : kind === 'pct2' ? `${v.toFixed(2)}%`
          : Math.round(v).toLocaleString('en-US')

/** Two bars a town: how many pupils, and what is spent on each, by where it comes from. */
export function TownsLikeUsFunding({ data, alt }: ChartProps) {
  const rows = (data as { funding: FundRow[] }).funding
  const [over, setOver] = useState<string | null>(null)
  const maxPup = Math.max(...rows.map(r => r.pupils))
  const maxSpend = Math.max(...rows.map(r => r.per_pupil))
  const hot = over ? rows.find(r => r.town === over) ?? null : null
  /* ONE GRID TEMPLATE, DECLARED ONCE. The header row and every data row read it, because a
   * header that drifts a column away from what it heads is worse than no header at all. */
  const COLS = 'minmax(84px,132px) minmax(48px,74px) minmax(0,1fr)'
  return (
    <>
      {/* A TITLE AND COLUMN HEADS.
        *
        * TJ: *"this chart needs a title, and column headers. the gray bars are not
        * obvious"*. The grey bar is the PUPIL COUNT -- the half of `pupils beside spend`
        * that this chart was built for -- and it carried no heading, no unit and no number,
        * so it read as decoration. A bar with no label is not a weak encoding, it is an
        * unlabelled one: rule 7b's bare number, drawn instead of printed. */}
      <h4 style={{ margin: '0 0 .15rem', fontSize: 15 }}>
        How many children, and what is spent on each
      </h4>
      <p style={{ margin: '0 0 .5rem', fontSize: 12.5, color: 'var(--text-secondary)' }}>
        Every bar is per pupil except the first, which is how many pupils there are.
      </p>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '.3rem .8rem', marginBottom: '.5rem' }}>
        {FUND_PARTS.map(([, label, colour]) => (
          <span key={label} style={{
            display: 'inline-flex', alignItems: 'center', gap: '.35rem', fontSize: 12,
            color: 'var(--text-secondary)',
          }}>
            <span style={{ width: 10, height: 10, borderRadius: 2, background: colour }} />
            {label}
          </span>
        ))}
      </div>
      <div style={{ display: 'grid', gap: 2 }}>
        <div style={{
          display: 'grid', gridTemplateColumns: COLS, alignItems: 'end', gap: '.4rem',
          padding: '0 .3rem .25rem', borderBottom: '1px solid var(--grid)',
          fontSize: 11, letterSpacing: '.03em', textTransform: 'uppercase',
          color: 'var(--text-secondary)',
        }}>
          <span>Town</span>
          <span>Pupils</span>
          <span>Spent per pupil, by where the money comes from</span>
        </div>
        {rows.map(r => {
          const me = r.town === 'Lunenburg'
          return (
            <div key={r.town}
                 onMouseEnter={() => setOver(r.town)} onMouseLeave={() => setOver(null)}
                 style={{
                   display: 'grid',
                   /* Name, pupils, then the stack. The stack is a fraction so the whole row
                      reflows at phone width instead of pushing the page sideways. */
                   gridTemplateColumns: COLS,
                   alignItems: 'center', gap: '.4rem',
                   padding: '.2rem .3rem', borderRadius: 4,
                   background: me ? 'var(--surface-2)' : over === r.town ? 'var(--surface-3)' : 'transparent',
                 }}>
              <span style={{ fontSize: 12, fontWeight: me ? 700 : 400 }}>{r.town}</span>
              <span style={{ position: 'relative', height: 14, display: 'flex', alignItems: 'center' }}
                    title={`${r.pupils.toLocaleString('en-US')} pupils`}>
                <span style={{
                  position: 'absolute', left: 0, top: 2, height: 10, borderRadius: 2,
                  width: `${(100 * r.pupils) / maxPup}%`, background: 'var(--text-muted)',
                  opacity: 0.4,
                }} />
                <span style={{
                  position: 'relative', fontSize: 10.5, fontWeight: me ? 700 : 400,
                  fontVariantNumeric: 'tabular-nums', color: 'var(--text-primary)',
                }}>{r.pupils.toLocaleString('en-US')}</span>
              </span>
              <span style={{ position: 'relative', height: 16, display: 'flex' }}>
                {FUND_PARTS.map(([key, label, colour]) => (
                  <span key={key} title={`${label}: ${usd(r[key] as number)}`}
                        style={{
                          width: `${(100 * (r[key] as number)) / maxSpend}%`,
                          background: colour, height: 14,
                        }} />
                ))}
                <span style={{
                  fontSize: 11, fontWeight: me ? 700 : 400, marginLeft: 5, whiteSpace: 'nowrap',
                  fontVariantNumeric: 'tabular-nums',
                }}>{usd(r.per_pupil)}</span>
              </span>
            </div>
          )
        })}
      </div>
      <div style={{
        minHeight: 40, marginTop: '.5rem', padding: '.45rem .6rem', fontSize: 12.5,
        border: '1px solid var(--grid)', borderRadius: 8, background: 'var(--surface-1)',
      }}>
        {hot ? (
          <>
            <strong>{hot.town}</strong>
            <span style={{ color: 'var(--text-secondary)' }}>
              {' '}· {hot.pupils.toLocaleString('en-US')} pupils · {usd(hot.per_pupil)} each
            </span>
            <div style={{ color: 'var(--text-secondary)', marginTop: '.2rem' }}>
              {usd(hot.from_homes)} from homes · {usd(hot.from_business)} from business ·{' '}
              {usd(hot.from_state)} from the state ·{' '}
              <strong style={{ color: 'var(--text-primary)' }}>
                {usd(hot.above_foundation)} above what the state says it needs
              </strong>
            </div>
          </>
        ) : (
          <span style={{ color: 'var(--text-secondary)' }}>
            Point at a town to see the four parts. They sum exactly to what it spends per
            pupil; the last one is what a town meeting decides.
          </span>
        )}
      </div>
      <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: '.4rem' }}>
        The local requirement is split between homes and business by each town’s own tax
        base — exact where one rate applies to all property, approximate where a town
        splits its rate. {alt ? '' : null}
      </p>
    </>
  )
}

/** Every measure on its own axis, all towns on it, Lunenburg marked. */
export function TownsLikeUsPositions({ data }: ChartProps) {
  const ds = (data as { distributions: Dist[] }).distributions
  return (
    <div style={{ display: 'grid', gap: '.65rem' }}>
      {ds.map(d => {
        const span = (d.hi - d.lo) || 1
        const X = (v: number) => (100 * (v - d.lo)) / span
        return (
          <div key={d.key} style={{
            display: 'grid', gridTemplateColumns: 'minmax(0,1fr)', gap: '.15rem',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '.5rem' }}>
              <span style={{ fontSize: 12.5 }}>{d.label}</span>
              <span style={{
                fontSize: 12, color: 'var(--text-secondary)', whiteSpace: 'nowrap',
                fontVariantNumeric: 'tabular-nums',
              }}>
                <strong style={{ color: 'var(--accent, #1d4ed8)' }}>
                  {fmtKind(d.lunenburg, d.kind)}
                </strong>
                {' · '}{ord(d.rank)} of {d.n}
              </span>
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{d.note}</div>
            <div style={{ position: 'relative', height: 20 }}>
              <span style={{
                position: 'absolute', left: 0, right: 0, top: 9, height: 1,
                background: 'var(--grid)',
              }} />
              {/* the middle half, so a position can be read as typical or not */}
              <span style={{
                position: 'absolute', top: 4, height: 12, background: '#c7d2fe', opacity: 0.55,
                left: `${X(d.p25)}%`, width: `${Math.max(X(d.p75) - X(d.p25), 0.4)}%`,
              }} />
              {d.values.map((v, i) => (
                <span key={i} style={{
                  position: 'absolute', top: 4, height: 12, width: 1,
                  left: `${X(v)}%`, background: 'var(--text-muted)', opacity: 0.4,
                }} />
              ))}
              <span style={{
                position: 'absolute', top: 1, height: 18, width: 1.5,
                left: `${X(d.median)}%`, background: 'var(--text-secondary)',
              }} />
              <span style={{
                position: 'absolute', top: 4, width: 11, height: 11, borderRadius: 999,
                left: `calc(${X(d.lunenburg)}% - 5.5px)`, background: '#1d4ed8',
                border: '1.5px solid var(--surface-1)',
              }} />
            </div>
          </div>
        )
      })}
    </div>
  )
}

/* ---- the whole state, shaded by whichever measure you pick ------------------------ */

/* WHY THE SHADE IS A RANK AND NOT A POSITION BETWEEN MIN AND MAX.
 *
 * TJ: *"basically hot and cold based on percent across min/max"* -- and min-to-max is the
 * obvious reading, but nearly every measure here is badly skewed. Boston has forty times
 * Lunenburg's pupils; a handful of towns hold most of the property value. Shading on the
 * raw range gives one town a deep colour and washes the other 350 into an indistinguishable
 * pale, which is a picture of the outlier and not of the state.
 *
 * Colouring by RANK spreads the map evenly and lets structure show. That trades away
 * magnitude, so the actual value is under the cursor on every town, the legend says which
 * is which, and the scale prints the real low, middle and high. */
const HEAT = ['#f7fbff', '#d7e6f5', '#a9cbe8', '#6fa8d4', '#3d7fb8', '#1d4ed8', '#12307a']

function heatColour(rank: number, n: number) {
  if (n <= 1) return HEAT[0]
  const i = Math.min(HEAT.length - 1, Math.floor((rank / (n - 1)) * HEAT.length))
  return HEAT[i]
}

/* AND THE READER CHOOSES WHICH TRADE TO TAKE.
 *
 * TJ, on finding Chilmark and Gosnold: *"lets have a toggle. LINEAR or by RANK. I think the
 * linear will show the real discrepancies."* He is right, and the note above was only half a
 * rule. Rank spreads the map evenly and shows STRUCTURE -- which towns sit together -- at
 * the cost of every magnitude: the gap between 1st and 2nd looks exactly like the gap
 * between 200th and 201st. Linear keeps the magnitudes and shows DISPERSION -- and on the
 * skewed measures it prints that skew as the picture, which is the honest thing about them.
 *
 * Taxable value per child is the case that settles it. Provincetown is $59.7M and Chilmark
 * $58.7M against Lunenburg's $1.43M, so on a linear ramp two towns take the dark end and
 * everywhere anybody lives is one pale block. That is not a failure of the drawing. It is
 * what the distribution looks like, and a reader who has only ever seen the rank version
 * does not know it. */
function linearColour(v: number, lo: number, hi: number) {
  if (!(hi > lo)) return HEAT[0]
  const f = Math.min(1, Math.max(0, (v - lo) / (hi - lo)))
  return HEAT[Math.min(HEAT.length - 1, Math.floor(f * HEAT.length))]
}

export function TownsLikeUsHeat({ data }: ChartProps) {
  const d = data as Payload
  const h = d.heatmap
  /* THE SAME MEASURE THE DOCUMENT'S CAPTION DESCRIBES. The component opened on whichever
   * measure happened to be first in the payload while the caption underneath described
   * spending per pupil -- so the picture and its own caption disagreed on first load. It is
   * also the measure the report is about. */
  const [pick, setPick] = useState(
    h.measures.some(x => x.key === 'per_pupil') ? 'per_pupil' : h.measures[0].key)
  const [over, setOver] = useState<string | null>(null)
  const m = h.measures.find(x => x.key === pick) ?? h.measures[0]
  const [scale, setScale] = useState<'rank' | 'linear'>('rank')

  const W = 756
  const proj = useMemo(() => {
    const xs: number[] = [], ys: number[] = []
    for (const rings of Object.values(h.shapes))
      for (const ring of rings) for (const [x, y] of ring) { xs.push(x); ys.push(y) }
    const lon0 = Math.min(...xs), lon1 = Math.max(...xs)
    const lat0 = Math.min(...ys), lat1 = Math.max(...ys)
    const kx = Math.cos(((lat0 + lat1) / 2) * Math.PI / 180)
    const pad = 6
    const k = (W - 2 * pad) / ((lon1 - lon0) * kx)
    return {
      H: Math.round(2 * pad + (lat1 - lat0) * k),
      px: (lon: number, lat: number): [number, number] =>
        [pad + (lon - lon0) * kx * k, pad + (lat1 - lat) * k],
    }
  }, [h])

  /* Rank once per measure, not once per town per render. */
  const ranked = useMemo(() => {
    const entries = Object.entries(m.values).sort((a, b) => a[1] - b[1])
    const r: Record<string, number> = {}
    entries.forEach(([t], i) => { r[t] = i })
    return { rank: r, n: entries.length }
  }, [m])

  const hot = over ? { town: over, value: m.values[over] } : null

  /* BOTH SIDES OF THE CHAPTER 70 EQUATION, whichever side you are shading.
   *
   * TJ: *"I think we need to show on the choropleth the foundation for chapter 70 too ... i
   * want to be able to see ... both sides of the equation for ch70"*. The three terms were
   * each available as their own shading and a reader could hold them apart but never see
   * them COMPOSE. They are one identity:
   *
   *     what the state says a town's children need
   *        = what the town is required to raise  +  what the state adds
   *
   * It is true by construction here -- the state term is the foundation budget minus the
   * required contribution, which is how DESE defines it and how this payload derives it --
   * so it is shown as an identity rather than offered as a finding. */
  const CH70 = ['foundation_pp', 'required_pp', 'state_pp', 'state_share']
  const term = (key: string, town: string) =>
    h.measures.find(x => x.key === key)?.values[town]
  const showEquation = CH70.includes(m.key)
  const fmt = (v: number | null | undefined) =>
    v == null ? 'not published for this town' : fmtKind(v, m.kind)

  /* BUTTONS, MAP, SCALE AND READOUT ALL ON ONE SCREEN.
   *
   * TJ: *"for the choropleth, i need the buttons and map to fit all on 1 screen, no
   * scrolling."* A map you have to scroll away from to change what it shows is two pictures,
   * not one instrument -- you lose the previous shading before you see the next.
   *
   * So the whole thing is a column capped at the viewport, the map takes whatever is left
   * after the controls, and the SVG is constrained by HEIGHT rather than width. That
   * letterboxes it on a wide screen, which is the right trade: the alternative is a map
   * whose bottom third is below the fold. */
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', gap: '.4rem',
      /* A DEFINITE HEIGHT, not a maximum. `max-height` leaves the column's height to be
       * resolved from its content, so the map's `height: 100%` had no definite parent to
       * resolve against, fell back to the SVG's intrinsic aspect ratio and drew at full
       * size -- overflowing the column and printing the legend, the readout and the next
       * SECTION of the page on top of one another. The fix is the thing flexbox needs to
       * distribute at all: a height to distribute. `min()` keeps the 420px floor without
       * reintroducing an auto height. */
      height: 'max(420px, 94vh)', overflow: 'hidden',
    }}>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '.25rem .35rem', flex: '0 0 auto' }}>
        {h.measures.map(x => (
          <button key={x.key} onClick={() => setPick(x.key)}
                  aria-pressed={x.key === pick}
                  style={{
                    padding: '.28rem .55rem', minHeight: 30, cursor: 'pointer',
                    borderRadius: 999, fontSize: 12, lineHeight: 1.3,
                    border: '1px solid var(--grid)',
                    background: x.key === pick ? '#1d4ed8' : 'var(--surface-1)',
                    color: x.key === pick ? '#fff' : 'var(--text-secondary)',
                    fontWeight: x.key === pick ? 600 : 400,
                  }}>
            {CH70.includes(x.key) && (
              /* WHICH BUTTONS ARE ONE EQUATION. Four of the thirteen shadings are the terms
               * of a single identity and the other nine are unrelated measures; nothing on
               * the row said so, so the four looked like four more metrics. TJ: *"Can you
               * mark the CH70 related toggles in the choropleth as [Ch70]"*. */
              <span style={{
                marginRight: '.3rem', fontSize: 10, fontWeight: 600,
                letterSpacing: '.02em', opacity: x.key === pick ? 0.85 : 0.7,
                color: x.key === pick ? '#fff' : '#1d4ed8',
              }}>[Ch70]</span>
            )}
            {x.label}
          </button>
        ))}
      </div>

     <div style={{ position: 'relative', flex: '1 1 auto', minHeight: 0 }}>
      <svg viewBox={`0 0 ${W} ${proj.H}`} role="img"
           preserveAspectRatio="xMidYMid meet"
           aria-label={`Every Massachusetts town shaded by ${m.label}, ${
             scale === 'rank' ? 'by rank' : 'by amount'}. Lunenburg is ${fmt(m.lunenburg)}.`}
           style={{
             display: 'block', touchAction: 'manipulation',
             width: '100%', height: '100%',
           }}>
        {/* THE COMPARISON TOWNS KEEP THEIR OUTLINE ON EVERY MEASURE.
          * TJ: *"ALWAYS show lunenburg AND the 'comparison towns' with at least a highlighted
          * border."* Without it the reader has to find thirty-two towns by eye on each of
          * thirteen shadings, which is the work the map exists to remove. The border carries
          * the town's ROLE -- the same colours as the signature map above -- so the fill can
          * go on carrying the measure. Line against area: the two do not compete. */}
        {Object.entries(h.shapes).map(([name, rings]) => {
          const v = m.values[name]
          /* A TOWN WITH NO FIGURE IS DRAWN, not dropped. On the measures that only cover
           * districts running their own K-12 school, 190 of the 351 have nothing to shade --
           * and painting those the page background broke Massachusetts into islands, so the
           * map stopped reading as the state. They get a flat grey and a visible edge: blank
           * means `not published for this town`, which is a fact worth seeing. */
          const fill = v == null ? '#eef0f3'
            : scale === 'linear' ? linearColour(v, m.lo, m.hi)
              : heatColour(ranked.rank[name], ranked.n)
          /* ONE TOWN IS OUTLINED, AND IT IS OURS.
           * Thirty-two comparison towns each carried a role-coloured border, and TJ:
           * *"lets also remove the highlighting for the comparison towns. the highlighting
           * looks odd. just show lunenburg in red highlighted"*. He is right -- a second
           * encoding competing with the fill turned a choropleth into a scatter of
           * outlines, and the eye read the borders as the data. The roles still carry the
           * signature map above, which is the picture they were built for. */
          const me = name === 'Lunenburg'
          const stroke = me ? '#dc2626'
            : over === name ? '#111827'
              : v == null ? '#dde1e6'
                : '#ffffff'
          const width = me ? 2.4 : over === name ? 1.8 : 0.4
          return rings.map((ring, i) => (
            <polygon key={name + i}
                     points={ring.map(([x, y]) => proj.px(x, y).join(',')).join(' ')}
                     fill={fill}
                     stroke={stroke}
                     strokeWidth={width}
                     onMouseEnter={() => setOver(name)}
                     onMouseLeave={() => setOver(null)}
                     onClick={() => setOver(name)}
                     style={{ cursor: 'pointer' }} />
          ))
        })}
      </svg>

      {/* THE READOUT SITS ON THE MAP, as it does on the signature map above.
        * TJ: *"hovering the choropleth needs to show the town and the relevant metric ... in
        * a hover popup similar to the first map"*. A panel in its own row below costs a row
        * of the one screen this is supposed to fit in, and puts the answer further from the
        * shape that raised the question. Pinned to a CORNER rather than the cursor: a
        * tooltip that follows the pointer covers what is being read and cannot be reached by
        * touch at all. Western Massachusetts is the emptiest part of this drawing on almost
        * every measure, so it goes bottom left. */}
      <div style={{
        position: 'absolute', left: 8, bottom: 14, right: 8, maxWidth: 480,
        pointerEvents: 'none', padding: '.45rem .65rem', fontSize: 12.5,
        border: '1px solid var(--grid)', borderRadius: 8, background: 'var(--surface-1)',
        boxShadow: hot ? '0 2px 12px rgba(0,0,0,.14)' : 'none',
        opacity: hot ? 1 : 0.93,
      }}>
        {hot ? (
          <>
            <strong>{hot.town}</strong>
            {d.map.roles[hot.town] && hot.town !== 'Lunenburg' && (
              <span style={{ color: ROLE_FILL[d.map.roles[hot.town]], fontWeight: 600 }}>
                {' · '}{ROLE_LABEL[d.map.roles[hot.town]]}
              </span>
            )}
            {hot.value != null && (
              <span style={{ color: 'var(--text-secondary)' }}>
                {' · '}{ord(ranked.n - ranked.rank[hot.town])} of {ranked.n} towns
                {scale === 'linear' && m.hi > m.lo && (
                  <>{' · '}{Math.round(100 * (hot.value - m.lo) / (m.hi - m.lo))}% of the way
                    from the lowest town to the highest</>
                )}
              </span>
            )}
            <div style={{ marginTop: '.15rem' }}>
              <span style={{ color: 'var(--text-secondary)' }}>{m.label}: </span>
              <strong>{fmt(hot.value)}</strong>
              <span style={{ color: 'var(--text-secondary)' }}>
                {' '}· Lunenburg {fmt(m.lunenburg)} · middle town {fmtKind(m.median, m.kind)}
              </span>
            </div>
            {showEquation && term('foundation_pp', hot.town) != null && (
              <div style={{ marginTop: '.2rem', color: 'var(--text-secondary)' }}>
                <strong style={{ color: 'var(--text-primary)' }}>
                  {usd(term('foundation_pp', hot.town) as number)}
                </strong>{' '}per child is what the state says they need ={' '}
                <strong style={{ color: 'var(--text-primary)' }}>
                  {usd(term('required_pp', hot.town) as number)}
                </strong>{' '}the town must raise +{' '}
                <strong style={{ color: 'var(--text-primary)' }}>
                  {usd(term('state_pp', hot.town) as number)}
                </strong>{' '}the state adds
                {term('state_share', hot.town) != null && (
                  <> ({(term('state_share', hot.town) as number).toFixed(0)}% of it)</>
                )}
              </div>
            )}
          </>
        ) : (
          <span style={{ color: 'var(--text-secondary)' }}>
            <strong style={{ color: '#dc2626' }}>Lunenburg</strong> outlined in red:{' '}
            <strong style={{ color: 'var(--text-primary)' }}>{fmt(m.lunenburg)}</strong>.
            {' '}Point at any town for its figure. {m.note}
          </span>
        )}
      </div>
     </div>

      {/* THE LEGEND IS A SIBLING OF THE MAP, not a child of it.
        * It was nested inside the map container, which is sized by the SVG -- so the
        * legend and its scale switch were laid out BELOW the drawing, past the column’s
        * `overflow: hidden`, and simply were not on the page. Measured: the column was
        * 846px with a scrollHeight of 899, and the 53px missing was exactly this row.
        * A control clipped out of existence looks identical to a control never built,
        * which is how it got reported as a lost feature rather than a layout bug. */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: '.5rem', flex: '0 0 auto',
        marginTop: '.25rem',
        fontSize: 11.5, color: 'var(--text-secondary)', flexWrap: 'wrap',
      }}>
        <span>{fmtKind(m.lo, m.kind)}</span>
        {HEAT.map(c => (
          <span key={c} style={{ width: 26, height: 11, background: c, border: '1px solid var(--grid)' }} />
        ))}
        <span>{fmtKind(m.hi, m.kind)}</span>
        <span style={{ marginLeft: '.4rem' }}>
          middle town {fmtKind(m.median, m.kind)} · shaded
        </span>
        {/* THE CONTROL SITS IN THE LEGEND, because it is a statement about what the colours
          * mean and that is what a legend is for. It also costs no row of the one screen. */}
        <span style={{ display: 'inline-flex', border: '1px solid var(--grid)', borderRadius: 999 }}>
          {([['rank', 'by RANK'], ['linear', 'by AMOUNT']] as const).map(([k, lab], i) => (
            <button key={k} onClick={() => setScale(k)} aria-pressed={scale === k}
                    style={{
                      padding: '.1rem .5rem', minHeight: 22, cursor: 'pointer', fontSize: 11,
                      border: 0, borderRadius: 999,
                      background: scale === k ? '#1d4ed8' : 'transparent',
                      color: scale === k ? '#fff' : 'var(--text-secondary)',
                      fontWeight: scale === k ? 600 : 400,
                      marginLeft: i ? 0 : undefined,
                    }}>
              {lab}
            </button>
          ))}
        </span>
        <span>
          {scale === 'rank'
            ? 'each shade holds the same NUMBER of towns'
            : 'each shade holds the same WIDTH of the range'}
        </span>
      </div>
    </div>
  )
}
