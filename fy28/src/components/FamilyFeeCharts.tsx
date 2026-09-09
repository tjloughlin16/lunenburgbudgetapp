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

/* ==========================================================================================
 *                              THE HOUSEHOLD BILL — THE TABLE
 * ==========================================================================================
 * The page is this table. A reader sets their own household above it and reads a yearly
 * figure off it; everything explaining how to read it comes after (rule 7a).
 *
 * FOUR BANDS, AND THE TABLE SHOWS ALL FOUR. `priced` is an amount a document states for the
 * year shown. `carried` is charged, at a rate last set in public in an earlier year.
 * `unpriced` is charged with no amount published anywhere — drawn hatched, with the request
 * that would price it. `no charge` is a charge a family might expect and does not pay, and
 * it is in the table at full size because the record showing a household bill going DOWN is
 * as much a finding as one going up (rule 8).
 *
 * SO THE TOTAL IS A FLOOR AND THE TABLE SAYS SO ON ITS FACE. Nothing here estimates an
 * unpriced row: rule 7 — the amounts are not in the archive, so a guess at them would be a
 * proxy standing in for the thing. The unpriced rows are a COUNT with a named remedy each.
 *
 * NOT ONE FIGURE IS TYPED IN THIS FILE (rule 2). Every amount, label, note and request
 * arrives from /data/what-families-pay.json.
 */

export type ChargeDef = {
  id: string; label: string; applies: string; basis: string; status: string
  quote: string | null; cite: string | null; request: string | null
}
export type BillRow = {
  id: string; band: string; amount: number | null; detail: string; note: string
  low?: number; high?: number; inferred?: boolean
}
export type Bill = {
  rows: BillRow[]; floor: number; carried: number; floor_carried: number
  unpriced_in_bill: number
}

const BAND_TONE: Record<string, string> = {
  priced: 'var(--text-primary)',
  carried: YEAR,
  unpriced: SEASON,
  'no charge': 'var(--text-muted)',
}

function Band({ band }: { band: string }) {
  return (
    <span className="text-[9.5px] font-bold uppercase tracking-widest whitespace-nowrap"
      style={{ color: BAND_TONE[band] ?? MUTED }}>{band}</span>
  )
}

/** One line of the bill. */
function Row({ r, def }: { r: BillRow; def: ChargeDef }) {
  const unpriced = r.band === 'unpriced'
  return (
    <tr style={{ borderTop: '1px solid var(--grid)' }}>
      <td className="py-2.5 pr-3 align-top">
        <div className="text-[13px] font-semibold">{def.label}</div>
        {r.detail && (
          <div className="text-[11.5px] mt-0.5" style={{ color: 'var(--text-secondary)' }}>
            {r.detail}
          </div>
        )}
        {def.applies && (
          <div className="text-[11px] mt-0.5" style={{ color: MUTED }}>
            who pays it: {def.applies}
          </div>
        )}
        {r.note && (
          <div className="text-[11px] mt-1.5 leading-snug pl-2"
            style={{ color: MUTED, borderLeft: '2px solid var(--grid)' }}>
            {r.note}
          </div>
        )}
        {unpriced && def.request && (
          <div className="text-[11px] mt-1.5 leading-snug pl-2"
            style={{ color: 'var(--text-secondary)', borderLeft: `2px solid ${SEASON}` }}>
            <span className="font-bold uppercase tracking-widest text-[9.5px]">
              what would price it&nbsp;
            </span>
            {def.request}
          </div>
        )}
      </td>
      <td className="py-2.5 pr-3 align-top whitespace-nowrap"><Band band={r.band} /></td>
      <td className="py-2.5 text-right align-top tabular-nums whitespace-nowrap">
        {r.amount === null
          ? <span className="text-[12px] font-semibold" style={{ color: SEASON }}>
              not published
            </span>
          : <span className="text-[15px] font-bold">{money(r.amount)}</span>}
        {r.low !== undefined && r.high !== undefined && r.high > r.low && (
          <div className="text-[10.5px] mt-0.5" style={{ color: MUTED }}>
            {money(r.low)}–{money(r.high)}
          </div>
        )}
      </td>
    </tr>
  )
}

export function HouseholdBill({ bill, standing, defs, bandMeaning, summary }: {
  bill: Bill
  standing: BillRow[]
  defs: Record<string, ChargeDef>
  bandMeaning: Record<string, string>
  summary: React.ReactNode
}) {
  const priced = bill.rows.filter(r => r.band === 'priced' || r.band === 'carried')
  const unpricedInBill = bill.rows.filter(r => r.band === 'unpriced')
  const nocharge = standing.filter(r => r.band === 'no charge')
  const unpriced = [...unpricedInBill, ...standing.filter(r => r.band === 'unpriced')]

  return (
    <div className="card overflow-hidden">
      {/* THE ANSWER, FIRST. Not the method, not the caveat — the number. */}
      <div className="px-4 sm:px-5 py-5"
        style={{ background: 'var(--surface-2)', borderBottom: '1px solid var(--grid)' }}>
        <div className="text-[11px] font-bold uppercase tracking-widest"
          style={{ color: MUTED }}>this household pays, for the school year</div>
        <div className="text-[38px] sm:text-[46px] font-black leading-none mt-1.5 tabular-nums">
          {money(bill.floor_carried)}
        </div>
        <p className="text-[12.5px] leading-snug mt-2.5 max-w-2xl"
          style={{ color: 'var(--text-secondary)' }}>
          {summary}
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left" style={{ minWidth: 520 }}>
          <thead>
            <tr className="text-[10px] font-bold uppercase tracking-widest"
              style={{ color: MUTED }}>
              <th className="py-2 px-4 sm:px-5 font-bold">charge</th>
              <th className="py-2 pr-3 font-bold">footing</th>
              <th className="py-2 px-4 sm:px-5 text-right font-bold">a year</th>
            </tr>
          </thead>
          <tbody className="px-4">
            {priced.map(r => <Row key={r.id} r={r} def={defs[r.id]} />)}
          </tbody>
        </table>
      </div>

      {/* The two totals, and the difference between them is the honest part. */}
      <div className="px-4 sm:px-5 py-3.5"
        style={{ borderTop: '2px solid var(--text-primary)' }}>
        <div className="flex justify-between items-baseline gap-4">
          <span className="text-[12.5px] font-semibold">
            Amounts a document states for this year
          </span>
          <span className="text-[16px] font-bold tabular-nums">{money(bill.floor)}</span>
        </div>
        {bill.carried > 0 && (
          <div className="flex justify-between items-baseline gap-4 mt-1.5">
            <span className="text-[12.5px]" style={{ color: 'var(--text-secondary)' }}>
              …plus rates last set in public and not restated for this year
            </span>
            <span className="text-[14px] font-semibold tabular-nums"
              style={{ color: YEAR }}>{money(bill.carried)}</span>
          </div>
        )}
        <div className="flex justify-between items-baseline gap-4 mt-2 pt-2"
          style={{ borderTop: '1px solid var(--grid)' }}>
          <span className="text-[13px] font-bold">Total the household pays</span>
          <span className="text-[19px] font-black tabular-nums">
            {money(bill.floor_carried)}
          </span>
        </div>
      </div>

      {/* AND THEN WHAT SITS ABOVE IT. Named, counted, never estimated. */}
      {unpriced.length > 0 && (
        <div style={{ borderTop: '1px solid var(--grid)' }}>
          <div className="px-4 sm:px-5 pt-4 pb-1">
            <h3 className="text-[13px] font-bold">
              …and {unpriced.length} charges above that, with no published amount
            </h3>
            <p className="text-[11.5px] leading-snug mt-1" style={{ color: MUTED }}>
              {bandMeaning.unpriced}. Each is real — the district sells it or a family has
              said they paid it — so the total above is a floor rather than a bill. Nothing
              here estimates one: beside each is the document that would price it.
            </p>
          </div>
          <div className="overflow-x-auto px-1">
            <table className="w-full text-left" style={{ minWidth: 520 }}>
              <tbody>
                {unpriced.map(r => <Row key={r.id} r={r} def={defs[r.id]} />)}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* AND WHAT A FAMILY DOES NOT PAY. Rule 8: the record showing a bill going down. */}
      {nocharge.length > 0 && (
        <div style={{ borderTop: '1px solid var(--grid)' }}>
          <div className="px-4 sm:px-5 pt-4 pb-1">
            <h3 className="text-[13px] font-bold">What a family is not charged for</h3>
            <p className="text-[11.5px] leading-snug mt-1" style={{ color: MUTED }}>
              {bandMeaning['no charge']}.
            </p>
          </div>
          <div className="overflow-x-auto px-1 pb-2">
            <table className="w-full text-left" style={{ minWidth: 520 }}>
              <tbody>
                {nocharge.map(r => <Row key={r.id} r={r} def={defs[r.id]} />)}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
