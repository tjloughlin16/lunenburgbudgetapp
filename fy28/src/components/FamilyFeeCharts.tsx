import { usd } from '../model/engine'

/** The marks for /what-families-pay. Every rate arrives from /data/what-families-pay.json,
 *  written by scripts/build_what_families_pay.py. Nothing here has a figure typed into it
 *  (rule 2); what this file computes is the SCENARIO, from controls the reader sets, off
 *  rates that arrive measured and carry their own footing.
 *
 *  COLOUR CARRIES ONE DISTINCTION AND ONLY ONE: which reading of the cap's period a total
 *  is under. Everything else — tier, level, year — is a label, because a page whose whole
 *  subject is an ambiguity must not encode two ambiguities in one channel. Identity is
 *  never carried by colour alone: every bar is directly labelled and every chart has a
 *  table twin.
 *
 *  THE HATCH IS NOT DECORATION. A rate nobody published is drawn hatched wherever it
 *  appears, and the unknown band above every total has NO TOP — it is open-ended, because
 *  six fees the district sells have no published amount and drawing a ceiling on them
 *  would be inventing one. A total on this page is a floor. */

export const SEASON = 'var(--series-revenue)'
export const YEAR = 'var(--series-cost)'
export const MUTED = 'var(--text-muted)'

export const money = (n: number) =>
  n % 1 === 0 ? usd(n) : `$${n.toLocaleString('en-US', { minimumFractionDigits: 2,
    maximumFractionDigits: 2 })}`

/** A hatch, defined once. Used for anything the archive does not publish. */
export function Hatch({ id, hue }: { id: string; hue: string }) {
  return (
    <defs>
      <pattern id={id} width="6" height="6" patternUnits="userSpaceOnUse"
        patternTransform="rotate(45)">
        <rect width="6" height="6" fill="var(--surface-3)" />
        <line x1="0" y1="0" x2="0" y2="6" stroke={hue} strokeWidth="2.5" opacity="0.55" />
      </pattern>
    </defs>
  )
}

/** A row of choices. Not a dropdown: every option on this page is one of three or four,
 *  and a select hides the fact that there ARE only four — which on a page about what is
 *  and is not published is part of the finding. */
export function Choice<T extends string | number>({ label, value, setValue, options, note }: {
  label: string
  value: T
  setValue: (v: T) => void
  options: { value: T; label: string; disabled?: boolean; why?: string }[]
  note?: React.ReactNode
}) {
  return (
    <div className="card p-4">
      <h3 className="text-[13px] font-bold mb-2">{label}</h3>
      <div className="flex flex-wrap gap-1.5">
        {options.map(o => {
          const on = o.value === value
          return (
            <button key={String(o.value)} type="button" disabled={o.disabled}
              onClick={() => setValue(o.value)} title={o.why}
              aria-pressed={on}
              className="text-[12.5px] font-semibold rounded-[4px] px-3 min-h-[44px]
                         transition-opacity disabled:opacity-40 disabled:cursor-not-allowed"
              style={{
                background: on ? 'var(--text-primary)' : 'var(--surface-2)',
                color: on ? 'var(--surface-1)' : 'var(--text-secondary)',
                border: '1px solid var(--grid)',
              }}>
              {o.label}
            </button>
          )
        })}
      </div>
      {note && (
        <p className="text-[11.5px] leading-snug mt-2.5" style={{ color: 'var(--text-muted)' }}>
          {note}
        </p>
      )}
    </div>
  )
}

/** THE SCENARIO, BOTH READINGS, ON ONE SCALE — with the band above it that has no top.
 *
 *  Two bars on a common baseline, because the comparison the whole page exists to draw is
 *  a comparison of two lengths and the reader should not need arithmetic to see it. The
 *  scale is fixed to the larger of the two so the shorter bar is never drawn full width.
 *
 *  The open band is drawn as a fading strip continuing past the end of each bar, with no
 *  edge on its right. It is deliberately impossible to read a value off it. */
export function BothReadings({ perSeason, perYear, bus, unpricedCount, capBinds }: {
  perSeason: number; perYear: number; bus: number | null
  unpricedCount: number; capBinds: boolean
}) {
  const top = Math.max(perSeason, perYear, 1)
  const rows = [
    { key: 'season', label: 'If the cap is per SEASON', amount: perSeason, hue: SEASON,
      note: capBinds ? 'the cap binds in at least one season here'
        : 'the cap does not bind — the family pays the full ladder' },
    { key: 'year', label: 'If the cap is per YEAR', amount: perYear, hue: YEAR,
      note: perYear < perSeason ? 'the cap binds' : 'the cap does not bind' },
  ]
  return (
    <div className="mt-5 flex flex-col gap-5">
      {rows.map(r => (
        <div key={r.key}>
          <div className="flex items-baseline justify-between gap-3 flex-wrap">
            <span className="text-[13.5px] font-semibold">{r.label}</span>
            <span className="text-[17px] font-bold tnum whitespace-nowrap"
              style={{ color: r.hue }}>
              {money(r.amount + (bus ?? 0))}{bus === null ? '+' : ''}
            </span>
          </div>
          <div className="mt-1.5 flex rounded-[3px] overflow-hidden"
            style={{ background: 'var(--surface-3)', height: 22 }}>
            <div style={{
              width: `${(r.amount / top) * 78}%`, background: r.hue, minWidth: 2,
            }} />
            {bus !== null && bus > 0 && (
              <div title="bus fee" style={{
                width: `${(bus / top) * 78}%`, background: r.hue, opacity: 0.45,
                borderLeft: '1px solid var(--surface-1)',
              }} />
            )}
            {/* THE BAND. No right edge, on purpose. */}
            <div style={{
              flex: 1,
              background: `linear-gradient(to right, var(--surface-3), transparent)`,
            }} />
          </div>
          <p className="text-[11.5px] mt-1" style={{ color: 'var(--text-muted)' }}>
            {r.note}
            {bus !== null && bus > 0 && <> · includes {money(bus)} of bus fee</>}
            {bus === null && <> · a bus fee applies and no amount for it is published</>}
            {' · '}plus {unpricedCount} named fees with no published amount
          </p>
        </div>
      ))}
    </div>
  )
}

/** THE LADDER EXHIBIT. Cumulative cost of one more child, one sport each, ONE SEASON,
 *  against the cap — the clearest thing on the page, and the reason the per-season reading
 *  is hard to believe.
 *
 *  Drawn as a column per family size with the cap as a rule across the top. Columns past
 *  the published ladder are hatched, and the two ways of carrying the ladder onward are
 *  drawn as a solid bar and a lighter extension so the conclusion can be seen to hold on
 *  either. */
export function LadderExhibit({ rows, cap, w = 640, h = 260 }: {
  rows: {
    children: number; published: boolean; footing: string
    cumulative_by_rule: number; cumulative_flat: number
  }[]
  cap: number; w?: number; h?: number
}) {
  const pad = { t: 26, r: 14, b: 46, l: 58 }
  const iw = w - pad.l - pad.r
  const ih = h - pad.t - pad.b
  const top = cap * 1.12
  const y = (v: number) => pad.t + ih - (v / top) * ih
  const bw = (iw / rows.length) * 0.62
  const cx = (i: number) => pad.l + (iw / rows.length) * (i + 0.5)

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-auto mt-4" role="img"
      aria-label="Cumulative athletic fee for one more child, one sport each, in one season,
                  against the family cap">
      <Hatch id="ladder-hatch" hue={SEASON} />
      {[0, 0.25, 0.5, 0.75, 1].map(f => (
        <g key={f}>
          <line x1={pad.l} x2={w - pad.r} y1={y(top * f)} y2={y(top * f)}
            stroke="var(--grid)" strokeWidth="1" />
          <text x={pad.l - 8} y={y(top * f) + 4} textAnchor="end"
            fontSize="10.5" fill="var(--text-muted)" className="tnum">
            {`$${Math.round((top * f) / 100) * 100}`}
          </text>
        </g>
      ))}
      {rows.map((r, i) => {
        const solid = Math.min(r.cumulative_by_rule, r.cumulative_flat)
        const upper = Math.max(r.cumulative_by_rule, r.cumulative_flat)
        return (
          <g key={r.children}>
            {upper > solid && (
              <rect x={cx(i) - bw / 2} y={y(upper)} width={bw} height={y(solid) - y(upper)}
                fill="url(#ladder-hatch)" />
            )}
            <rect x={cx(i) - bw / 2} y={y(solid)} width={bw} height={ih + pad.t - y(solid)}
              fill={r.published ? SEASON : 'url(#ladder-hatch)'} />
            <text x={cx(i)} y={y(upper) - 6} textAnchor="middle" fontSize="11"
              fontWeight="700" fill="var(--text-primary)" className="tnum">
              {money(upper)}
            </text>
            <text x={cx(i)} y={h - 26} textAnchor="middle" fontSize="11.5"
              fill="var(--text-secondary)">{r.children}</text>
            <text x={cx(i)} y={h - 12} textAnchor="middle" fontSize="9.5"
              fill="var(--text-muted)">{r.published ? 'published' : 'not published'}</text>
          </g>
        )
      })}
      <line x1={pad.l} x2={w - pad.r} y1={y(cap)} y2={y(cap)} stroke={YEAR}
        strokeWidth="2" strokeDasharray="6 4" />
      <text x={w - pad.r} y={y(cap) - 7} textAnchor="end" fontSize="11" fontWeight="700"
        fill={YEAR} className="tnum">family cap {money(cap)}</text>
      <line x1={pad.l} x2={w - pad.r} y1={pad.t + ih} y2={pad.t + ih}
        stroke="var(--axis)" strokeWidth="1" />
    </svg>
  )
}
