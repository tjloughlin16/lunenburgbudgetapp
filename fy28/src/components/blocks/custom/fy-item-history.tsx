/** AN ITEM ACROSS THE YEARS: a school line's budget and spending, a fund's spending by kind, one
 *  point per year of the journal. Drawn on the item's own page (pages/FyItem.tsx) and in the fund
 *  popup's "Across the years" tab (fy-source-table.tsx) -- TJ, 28 October 2026: "its VERY VERY
 *  helpful to see trends" -- from the same /data/fy-breakdown/<line|fund>/<slug>.json, so the two
 *  cannot disagree. Every amount shown is the generator's own text (scripts/fy_items.py). */
import {
  Bar, CartesianGrid, ComposedChart, LabelList, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { H2 } from '../../report'
import type { MoveGroup } from './fy-fund-moves'
import type { ItemIndex } from './fy-items'

/** `gross` and `t.net` only in a year whose approved budget voted the line NET of money it counted on
 *  (collaborative tuitions, FY2025 on: the circuit breaker); `paid` is what each other fund paid
 *  toward the line that year -- scripts/fy_items.py */
export type LineHist = { fy: string; voted: number; budget: number; spent: number; other: number; all_in: number; left?: number; gross?: number
  paid: { fund: string; v: number; t: string }[]
  t: Record<'voted' | 'budget' | 'spent' | 'other' | 'all_in', string> & { gross?: string; net?: string; left?: string } }
export type FundHist = { fy: string; n: Record<string, number>; t: Record<string, string>; awards: { fund: string; name: string; t: string }[]; moves: MoveGroup[] }

const muted = { color: 'var(--text-muted)' }

const tick = { fontSize: 11, fill: 'var(--text-muted)' }
const usdk = (v: number) => Math.abs(v) >= 1e6 ? `$${(v / 1e6).toFixed(1)}M` : Math.abs(v) >= 1e3 ? `$${Math.round(v / 1e3)}k` : `$${Math.round(v)}`
const box = { background: 'var(--surface-1)', border: '1px solid var(--grid)', borderRadius: 8, fontSize: 12.5,
  color: 'var(--text-primary)', boxShadow: '0 2px 10px rgba(0,0,0,.12)', padding: '6px 10px' }

/** A tooltip that prints the generator's own formatted amounts, never a number formatted here. */
function TextTip({ active, label, rows }: { active?: boolean; label?: string; rows: { name: string; colour: string; text: (fy: string) => string | undefined }[] }) {
  if (!active || !label) return null
  return (
    <div style={box}>
      <p className="font-semibold">{label}</p>
      {rows.map(r => r.text(label) ? (
        <p key={r.name} className="flex justify-between gap-4"><span><span className="inline-block w-2 h-2 rounded-sm mr-1.5" style={{ background: r.colour }} />{r.name}</span>
          <span className="tabular-nums font-semibold">{r.text(label)}</span></p>) : null)}
    </div>)
}

function SpanNote({ ix }: { ix: ItemIndex }) {
  return <p className="text-[12px] mt-1" style={muted}>{ix.text.hist_span} · {ix.span}</p>
}

/** One series of a line's history: its key in the chart rows, and the generator's text for a year. */
type Series = { key: string; name: string; colour: string; dash?: string; text: (fy: string) => string | undefined }
/** the other funds take these in turn, in the order of their names, so a fund keeps its colour every year */
const FUND_COLOURS = ['var(--thread-3)', 'var(--thread-5)', 'var(--thread-6, var(--text-secondary))', 'var(--thread-2)', 'var(--thread-4)']

/** `bare`: under a heading of its own (the group page's 'both together') -- no heading here */
export function LineHistory({ h, ix, bare = false }: { h: LineHist[]; ix: ItemIndex; bare?: boolean }) {
  const t = ix.text
  const by = new Map(h.map(x => [x.fy, x]))
  const netted = h.filter(x => x.t.net)
  // every other fund that paid in any year, in a fixed order: the same fund, the same row, every year
  const funds = [...new Set(h.flatMap(x => x.paid.map(p => p.fund)))].sort((a, b) => a.localeCompare(b))
  const rows = h.map(x => ({ ...x, ...Object.fromEntries(x.paid.map(p => [`f${funds.indexOf(p.fund)}`, p.v])) }))
  const paidBy = (fy: string, fund: string) => by.get(fy)?.paid.find(p => p.fund === fund)?.t
  const school: Series = { key: 'spent', name: t.spent, colour: 'var(--thread-1)', text: fy => by.get(fy)?.t.spent }
  const others: Series[] = funds.map((f, i) => ({ key: `f${i}`, name: f, colour: FUND_COLOURS[i % FUND_COLOURS.length], text: fy => paidBy(fy, f) }))
  const allIn: Series = { key: 'all_in', name: t.all_in, colour: 'var(--text-primary)', text: fy => by.get(fy)?.t.all_in }
  const final: Series = { key: 'budget', name: t.budget, colour: 'var(--text-primary)', text: fy => by.get(fy)?.t.budget }
  const left: Series = { key: 'left', name: t.left_row, colour: 'var(--thread-5)', text: fy => by.get(fy)?.t.left }
  const gross: Series[] = netted.length
    ? [{ key: 'gross', name: t.gross, colour: 'var(--thread-4)', dash: '2 3', text: fy => by.get(fy)?.t.gross }] : []
  const tip = (series: Series[]) => (p: { active?: boolean; label?: string | number }) => (
    <TextTip active={p.active} label={p.label === undefined ? undefined : String(p.label)} rows={series} />)
  const axes = <>
    <CartesianGrid stroke="var(--grid)" vertical={false} />
    <XAxis dataKey="fy" tick={tick} />
    <YAxis tickFormatter={usdk} width={56} tick={tick} />
    <ReferenceLine y={0} stroke="var(--grid)" />
  </>
  const line = (s: Series, width = 2) => (
    <Line key={s.key} dataKey={s.key} name={s.name} stroke={s.colour} strokeWidth={width} strokeDasharray={s.dash}
      dot={{ r: 3 }} connectNulls={false} isAnimationActive={false} />)
  const chart = (title: string, series: Series[], bold?: string) => (
    <div className="min-w-0">
      <p className="font-semibold text-[14px]">{title}</p>
      <div style={{ width: '100%', height: 230 }}>
        <ResponsiveContainer>
          <LineChart data={rows} margin={{ top: 10, right: 12, left: 4, bottom: 4 }}>
            {axes}
            <Tooltip content={tip(series)} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            {series.map(s => line(s, s.key === bold ? 3 : 2))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>)
  return (
    <section className={bare ? 'mt-2' : 'mt-10'}>
      {bare ? null : <H2>{t.hist_h}</H2>}
      <SpanNote ix={ix} />
      {/* RULE 1: a budget and an actual are two tracks, never one series */}
      <div className="grid gap-6 md:grid-cols-2 mt-3">
        {chart(t.hist_budget, [{ key: 'voted', name: t.voted, colour: 'var(--thread-2)', dash: '5 4', text: fy => by.get(fy)?.t.voted },
          { ...final, colour: 'var(--thread-1)' }, ...gross])}
        {/* who paid, fund by fund, and everything together: flat all-in, or moving between payers */}
        {chart(t.hist_spend, [school, ...others, ...(others.length ? [allIn] : [])], 'all_in')}
      </div>
      {/* the two together: what it cost, stacked by who paid; what it was allowed, as lines over it */}
      <p className="font-semibold text-[14px] mt-6">{t.hist_both}</p>
      <div style={{ width: '100%', height: 260 }}>
        <ResponsiveContainer>
          <ComposedChart data={rows} margin={{ top: 10, right: 12, left: 4, bottom: 4 }}>
            {axes}
            <Tooltip content={tip([final, ...gross, school, ...others, ...(others.length ? [allIn] : []), left])} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            {[school, ...others].map(s => (
              <Bar key={s.key} dataKey={s.key} name={s.name} stackId="s" fill={s.colour} fillOpacity={0.75} isAnimationActive={false} />))}
            {line(final)}
            {gross.map(s => line(s))}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <LeftRow h={h} ix={ix} />
      {netted.length ? (
        <ul className="text-[12.5px] mt-2 max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
          {netted.map(x => <li key={x.fy}><span className="font-semibold">{x.fy}</span> · {x.t.net}</li>)}
        </ul>) : null}
      <p className="text-[12.5px] mt-2 max-w-3xl" style={muted}>{t.hist_rule}</p>
    </section>)
}

const KIND_COLOUR: Record<string, string> = { payee: 'var(--thread-2)', function: 'var(--thread-5)', later: 'var(--thread-3)',
  back: 'var(--thread-1)', capital: 'var(--thread-4)', between: 'var(--thread-6, var(--text-secondary))', none: 'var(--text-muted)' }

/** `bare`: inside a popup's tab, which already names it -- no heading of its own. */
export function FundHistory({ h, ix, cols, bare = false }: { h: FundHist[]; ix: ItemIndex; cols: { id: string; label: string }[]; bare?: boolean }) {
  const t = ix.text
  const by = new Map(h.map(x => [x.fy, x]))
  const kinds = cols.filter(c => c.id !== 'total' && h.some(x => Math.abs(x.n[c.id] ?? 0) >= 0.5))
  const data = h.map(x => ({ fy: x.fy, ...x.n }))
  return (
    <section className={bare ? '' : 'mt-10'}>
      {bare ? null : <H2>{t.hist_h}</H2>}
      <SpanNote ix={ix} />
      <p className="font-semibold text-[14px] mt-3">{t.hist_where}</p>
      <div style={{ width: '100%', height: 280 }}>
        <ResponsiveContainer>
          {/* bars for what each year was made of, a line for the total's trend */}
          <ComposedChart data={data} stackOffset="sign" margin={{ top: 10, right: 12, left: 4, bottom: 4 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tick={tick} />
            <YAxis tickFormatter={usdk} width={56} tick={tick} />
            <ReferenceLine y={0} stroke="var(--text-muted)" />
            <Tooltip content={(p: { active?: boolean; label?: string | number }) => (
              <TextTip active={p.active} label={p.label === undefined ? undefined : String(p.label)}
                rows={[...kinds.map(c => ({ name: c.label, colour: KIND_COLOUR[c.id], text: (fy: string) => Math.abs(by.get(fy)?.n[c.id] ?? 0) >= 0.5 ? by.get(fy)?.t[c.id] : undefined })),
                  { name: t.hist_total, colour: 'var(--text-primary)', text: (fy: string) => by.get(fy)?.t.total }]} />)} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            {kinds.map(c => <Bar key={c.id} dataKey={c.id} name={c.label} stackId="k" fill={KIND_COLOUR[c.id]} isAnimationActive={false} />)}
            <Line dataKey="total" name={t.hist_total} stroke="var(--text-primary)" strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <ul className="mt-3 text-[13px] max-w-3xl">
        {h.map(x => (
          <li key={x.fy} className="py-1 border-b" style={{ borderColor: 'var(--grid)' }}>
            <span className="font-semibold">{x.fy}</span> <span className="tabular-nums">· {x.t.total}</span>
            <span className="block text-[12px]" style={muted}>{x.awards.map(a => `${a.name} ${a.t}`).join(' · ')}</span></li>))}
      </ul>
    </section>)
}

/** A fund other than the school budget that paid toward a line, every year: what it put here,
 *  what it put on other school lines -- scripts/fy_items.py `trace` */
export type PayerTrace = { fund: string; href?: string; notes: string[]
  /** its largest other school lines across all the years: one fixed set, so colours hold */
  lines: { name: string; href: string }[]
  years: { fy: string; here: number; total: number; others: number
    t: { here: string; total: string; rest: string; elsewhere: string; others: string }
    /** what it put on each of `lines` that year, in their order */
    by: { v: number; t: string }[]
    top: { name: string; href: string; v: number; t: string }[]
    /** on a group: what it paid each member line */
    split?: { name: string; v: number; t: string }[] }[] }

/** WHERE ITS PAYERS WENT (TJ, 28 October 2026: "previously paid by circuit breaker in FY25, but then
 *  in FY26 circuit breaker went to XYZ"). One chart per fund: each year a bar of everything it spent
 *  on school lines, stacked -- THIS line at the bottom in a strong colour with its amount on it, then
 *  the fund's largest other lines (one fixed set across the years, so each keeps its colour and its
 *  place: object constancy), then every other line in grey. Redrawn 29 October 2026 after TJ found
 *  the per-year thin bars "VERY hard to understand". The sentences are the generator's. */
const TRACE_COLOURS = ['var(--thread-2)', 'var(--thread-5)', 'var(--thread-3)']
export function PayerTraces({ p, ix, fy }: { p: PayerTrace[]; ix: ItemIndex; fy: string }) {
  const t = ix.text
  if (!p.length) return null
  const link = { color: 'var(--link, var(--thread-2))' }
  const go = (href: string) => `${href}?fy=${encodeURIComponent(fy)}`
  return (
    <section className="mt-10">
      <H2>{t.payers_h}</H2>
      <p className="text-[13px] mb-3 max-w-3xl" style={{ color: 'var(--text-secondary)' }}>{t.payers_line}</p>
      <div className="grid gap-4 lg:grid-cols-2">
        {p.map(f => {
          const by = new Map(f.years.map(y => [y.fy, y]))
          const rows = f.years.map(y => ({ fy: y.fy, here: y.here, others: y.others,
            ...Object.fromEntries(y.by.map((x, i) => [`l${i}`, x.v])) }))
          const series = [
            { key: 'here', name: t.trace_here, colour: 'var(--thread-1)', opacity: 0.95, text: (q: string) => by.get(q)?.t.here },
            ...f.lines.map((l, i) => ({ key: `l${i}`, name: l.name, colour: TRACE_COLOURS[i % TRACE_COLOURS.length], opacity: 0.4,
              text: (q: string) => by.get(q)?.by[i]?.t || undefined })),
            { key: 'others', name: t.trace_rest, colour: 'var(--text-muted)', opacity: 0.25, text: (q: string) => by.get(q)?.t.others || undefined }]
          // the amount on this line's own segment: inside it where it fits, just above it where not
          const hereLabel = (q: { x?: number | string; y?: number | string; width?: number | string; height?: number | string; index?: number }) => {
            const y = f.years[q.index ?? -1]
            if (!y || !y.here) return null
            const [x, top, w, h] = [q.x, q.y, q.width, q.height].map(Number)
            const fits = h >= 16
            return <text x={x + w / 2} y={fits ? top + h / 2 + 4 : top - 4} textAnchor="middle" fontSize={11} fontWeight={600}
              fill={fits ? 'var(--bg, #fff)' : 'var(--text-primary)'}>{y.t.here}</text>
          }
          return (
            <div key={f.fund} className="rounded-lg border p-4 min-w-0" style={{ borderColor: 'var(--grid)' }}>
              <p className="font-semibold text-[15px]">{f.href ? <a href={go(f.href)} className="underline" style={link}>{f.fund}</a> : f.fund}</p>
              {f.notes.length ? (
                <ul className="mt-1 text-[12.5px] space-y-0.5" style={{ color: 'var(--text-secondary)' }}>
                  {f.notes.map(n => <li key={n}>{n}</li>)}
                </ul>) : null}
              <div className="mt-2" style={{ width: '100%', height: 240 }}>
                <ResponsiveContainer>
                  <ComposedChart data={rows} margin={{ top: 14, right: 8, left: 0, bottom: 4 }}>
                    <CartesianGrid stroke="var(--grid)" vertical={false} />
                    <XAxis dataKey="fy" tick={tick} />
                    <YAxis tickFormatter={usdk} width={52} tick={tick} />
                    <Tooltip content={(q: { active?: boolean; label?: string | number }) => (
                      <TextTip active={q.active} label={q.label === undefined ? undefined : String(q.label)}
                        rows={[...series, { name: t.on_lines, colour: 'transparent', text: (v: string) => by.get(v)?.t.total }]} />)} />
                    {/* the legend in the stack's own order, this line first -- not recharts' default, by name */}
                    <Legend wrapperStyle={{ fontSize: 12 }} itemSorter={(e: { dataKey?: unknown }) => series.findIndex(x => x.key === e.dataKey)} />
                    {series.map(s => (
                      <Bar key={s.key} dataKey={s.key} name={s.name} stackId="s" fill={s.colour} fillOpacity={s.opacity} isAnimationActive={false}>
                        {s.key === 'here' ? <LabelList dataKey="here" content={hereLabel} /> : null}
                      </Bar>))}
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
              {f.lines.length ? (
                <p className="mt-1 text-[12.5px]" style={muted}>{t.trace_lines} {f.lines.map((l, i) => (
                  <span key={l.href}>{i ? ' · ' : ''}<span className="inline-block w-2 h-2 rounded-sm mr-1"
                    style={{ background: TRACE_COLOURS[i % TRACE_COLOURS.length], opacity: 0.6 }} />
                    <a href={go(l.href)} className="underline" style={link}>{l.name}</a></span>))}</p>) : null}
            </div>)
        })}
      </div>
    </section>)
}

/** the group's lines take these in turn, in the order of their names; the rest is grey */
const MEMBER_COLOURS = ['var(--thread-1)', 'var(--thread-2)', 'var(--thread-5)', 'var(--thread-3)']

/** WHICH LINE EACH FUND PAID (TJ, 28 October 2026: "some chart that shoed changes over the years
 *  that show that hte circuit brekaer paid out different school lines"). One chart per fund; each
 *  year a bar of everything it spent on school lines, stacked by the group's lines and the rest. */
export function GroupSplit({ p, ix }: { p: PayerTrace[]; ix: ItemIndex }) {
  const t = ix.text
  const names = [...new Set(p.flatMap(f => f.years.flatMap(y => (y.split ?? []).map(x => x.name))))].sort((a, b) => a.localeCompare(b))
  if (!names.length) return null
  const colour = (i: number) => MEMBER_COLOURS[i % MEMBER_COLOURS.length]
  return (
    <section className="mt-10">
      <H2>{t.split_h}</H2>
      <p className="text-[13px] mb-3 max-w-3xl" style={{ color: 'var(--text-secondary)' }}>{t.split_line}</p>
      <div className="grid gap-6 md:grid-cols-2">
        {p.map(f => {
          const by = new Map(f.years.map(y => [y.fy, y]))
          const rows = f.years.map(y => ({ fy: y.fy, rest: y.total - y.here,
            ...Object.fromEntries((y.split ?? []).map(x => [`m${names.indexOf(x.name)}`, x.v])) }))
          const series = [...names.map((n, i) => ({ key: `m${i}`, name: n, colour: colour(i),
            text: (fy: string) => { const x = by.get(fy)?.split?.find(s => s.name === n); return x && x.v ? x.t : undefined } })),
            { key: 'rest', name: t.split_rest, colour: 'var(--text-muted)',
              text: (fy: string) => { const y = by.get(fy); return y && y.total - y.here >= 0.5 ? y.t.elsewhere : undefined } }]
          return (
            <div key={f.fund} className="min-w-0">
              <p className="font-semibold text-[14px]">{f.fund}</p>
              <div style={{ width: '100%', height: 240 }}>
                <ResponsiveContainer>
                  <ComposedChart data={rows} margin={{ top: 10, right: 12, left: 4, bottom: 4 }}>
                    <CartesianGrid stroke="var(--grid)" vertical={false} />
                    <XAxis dataKey="fy" tick={tick} />
                    <YAxis tickFormatter={usdk} width={56} tick={tick} />
                    <Tooltip content={(q: { active?: boolean; label?: string | number }) => (
                      <TextTip active={q.active} label={q.label === undefined ? undefined : String(q.label)}
                        rows={[...series, { name: t.on_lines, colour: 'transparent', text: (fy: string) => by.get(fy)?.t.total }]} />)} />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    {series.map(s => <Bar key={s.key} dataKey={s.key} name={s.name} stackId="s" fill={s.colour}
                      fillOpacity={s.key === 'rest' ? 0.35 : 0.85} isAnimationActive={false} />)}
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </div>)
        })}
      </div>
    </section>)
}

export type GroupShift = { fy: string; name: string; href: string; n: Record<string, number>; t: Record<string, string> }

/** OTHER MOVES THAT SHIFTED MONEY: the line table's own columns (frame.line.columns) and words,
 *  each line each year where budget or bills moved. */
export function GroupShifts({ rows, ix }: { rows: GroupShift[]; ix: ItemIndex }) {
  const t = ix.text
  if (!rows.length) return null
  const frame = (ix.frame.line as { columns: { id: string; key: string; label: string; means: string }[] }).columns
  const cols = (['transfers', 'carried', 'off', 'on', 'direct'] as const)
    .filter(k => rows.some(r => r.t[k])).map(k => frame.find(c => c.id === k)!).filter(Boolean)
  const link = { color: 'var(--link, var(--thread-2))' }
  return (
    <section className="mt-10">
      <H2>{t.shifts_h}</H2>
      <p className="text-[13px] mb-3 max-w-3xl" style={{ color: 'var(--text-secondary)' }}>{t.shifts_line}</p>
      <div className="overflow-x-auto">
        <table className="w-full text-[13px] tabular-nums">
          <thead><tr className="border-b" style={{ borderColor: 'var(--grid)' }}>
            <th className="text-left px-2 py-1.5">{t.year}</th><th className="text-left px-2 py-1.5" />
            {cols.map(c => <th key={c.id} title={c.means} className="text-right px-2 py-1.5 font-semibold underline decoration-dotted cursor-help">{c.label}</th>)}
          </tr></thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={`${r.fy}${r.href}`} className="border-b" style={{ borderColor: 'var(--grid)' }}>
                <td className="px-2 py-1.5 font-semibold">{i && rows[i - 1].fy === r.fy ? '' : r.fy}</td>
                <td className="px-2 py-1.5 text-left"><a href={`${r.href}?fy=${encodeURIComponent(r.fy)}`} className="underline" style={link}>{r.name}</a></td>
                {cols.map(c => <td key={c.id} className="px-2 py-1.5 text-right">{r.t[c.id] || <span style={muted}>—</span>}</td>)}
              </tr>))}
          </tbody>
        </table>
      </div>
    </section>)
}

export type Counts = { csv: string; missing: { fy: string; held: boolean }[]
  years: { fy: string; as_of: string; total: number; collaborative: number; day: number; residential: number; page: number; href?: string }[] }

/** CHILDREN PLACED OUT OF DISTRICT (TJ, 28 October 2026: "those placement counts would be VERY useful
 *  to undertand this shift"). The annual report's 1 March counts by kind, drawn in the colours of
 *  the tuition lines in GroupSplit so the two read across -- and that pairing is labelled ours. A
 *  count of children and a sum of dollars are never divided here. A year with no count is a gap on
 *  the axis, never a zero. */
export function GroupCounts({ c, years, ix, chart = true }: { c: Counts; years: string[]; ix: ItemIndex; chart?: boolean }) {
  const t = ix.text
  if (!c.years.length) return null
  const by = new Map(c.years.map(y => [y.fy, y]))
  const rows = years.map(fy => ({ fy, ...(by.get(fy) ?? {}) }))
  const n = (k: 'collaborative' | 'day' | 'residential' | 'total') => (fy: string) => { const y = by.get(fy); return y ? `${y[k]} ${t.counts_unit}` : undefined }
  const series = [
    { key: 'collaborative', name: t.c_collab, colour: MEMBER_COLOURS[0], opacity: 0.85, text: n('collaborative') },
    { key: 'day', name: t.c_day, colour: MEMBER_COLOURS[1], opacity: 0.85, text: n('day') },
    { key: 'residential', name: t.c_res, colour: MEMBER_COLOURS[1], opacity: 0.45, text: n('residential') }]
  const link = { color: 'var(--link, var(--thread-2))' }
  return (
    <section className="mt-10">
      <H2>{t.counts_h}</H2>
      <p className="text-[13px] mb-3 max-w-3xl" style={{ color: 'var(--text-secondary)' }}>{t.counts_line}</p>
      <p className="text-[13px] mb-3 max-w-3xl" style={{ color: 'var(--text-secondary)' }}>{t.counts_def}</p>
      <div className={chart ? 'grid gap-6 md:grid-cols-2 items-start' : ''}>
        {chart ? <div style={{ width: '100%', height: 240 }}>
          <ResponsiveContainer>
            <ComposedChart data={rows} margin={{ top: 10, right: 12, left: 4, bottom: 4 }}>
              <CartesianGrid stroke="var(--grid)" vertical={false} />
              <XAxis dataKey="fy" tick={tick} />
              <YAxis allowDecimals={false} width={40} tick={tick} />
              <Tooltip content={(q: { active?: boolean; label?: string | number }) => (
                <TextTip active={q.active} label={q.label === undefined ? undefined : String(q.label)}
                  rows={[...series, { name: t.c_total, colour: 'transparent', text: n('total') }]} />)} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              {series.map(s => <Bar key={s.key} dataKey={s.key} name={s.name} stackId="c" fill={s.colour} fillOpacity={s.opacity} isAnimationActive={false} />)}
            </ComposedChart>
          </ResponsiveContainer>
        </div> : null}
        <div className="text-[12.5px] space-y-1">
          {years.map(fy => {
            const y = by.get(fy), miss = c.missing.find(m => m.fy === fy)
            return (
              <p key={fy}><span className="font-semibold">{fy}</span>{' · '}
                {y ? <>{y.total} {t.counts_unit} <span style={muted}>({t.c_collab.toLowerCase()} {y.collaborative}, {t.c_day.toLowerCase()} {y.day}, {t.c_res.toLowerCase()} {y.residential}; {y.as_of})</span>{' · '}
                  {y.href ? <a href={`${y.href}#page=${y.page}`} className="underline" style={link}>{t.counts_src} {fy}, {t.counts_page} {y.page}</a> : `${t.counts_src} ${fy}, ${t.counts_page} ${y.page}`}</>
                  : <span style={muted}>{miss && !miss.held ? t.counts_unheld : t.counts_missing}</span>}
              </p>)
          })}
          <p className="pt-2" style={muted}>{t.counts_ours}</p>
          <p style={muted}><a href={c.csv} className="underline" style={link}>placement-counts.csv</a></p>
        </div>
      </div>
    </section>)
}

export type GroupMember = { name: string; account: string; href: string; history: LineHist[]; rates?: PayeeRates[]; counts: ('collaborative' | 'day' | 'residential')[] }

/** EACH LINE, SIDE BY SIDE (TJ, 28 October 2026: "the placements changing i want to see next to it
 *  how the spend changed and how the budget changed..... its not easy to compare those"). Small
 *  multiples: a column per line, a row per question -- children placed, budget, cost by who paid --
 *  every row on ONE y-scale across its columns, so a taller bar is more, whichever column it is in. */
export function GroupCompare({ members, counts, years, ix }: { members: GroupMember[]; counts: Counts | null; years: string[]; ix: ItemIndex }) {
  const t = ix.text
  const cb = new Map((counts?.years ?? []).map(y => [y.fy, y]))
  const kindName = { collaborative: t.c_collab, day: t.c_day, residential: t.c_res }
  const kindFill = { collaborative: [MEMBER_COLOURS[0], 0.85], day: [MEMBER_COLOURS[1], 0.85], residential: [MEMBER_COLOURS[1], 0.45] } as const
  // one scale per row, across the columns
  const maxCount = Math.max(1, ...members.flatMap(m => years.map(fy => m.counts.reduce((s, k) => s + (cb.get(fy)?.[k] ?? 0), 0))))
  // the budget row carries the all-in cost too, so the scale has to hold it
  const maxBudget = Math.max(1, ...members.flatMap(m => m.history.flatMap(h => [h.voted, h.budget, h.gross ?? 0, h.all_in])))
  const maxSpend = Math.max(1, ...members.flatMap(m => m.history.flatMap(h => [h.all_in, h.budget])))
  // every payer in either column, in one order and one colour, so a fund looks the same on both sides
  const funds = [...new Set(members.flatMap(m => m.history.flatMap(h => h.paid.map(p => p.fund))))].sort((a, b) => a.localeCompare(b))
  const fundColour = (f: string) => FUND_COLOURS[funds.indexOf(f) % FUND_COLOURS.length]
  const axes = (max: number, money = true) => <>
    <CartesianGrid stroke="var(--grid)" vertical={false} />
    <XAxis dataKey="fy" tick={tick} />
    <YAxis domain={[0, max]} allowDecimals={!money ? false : undefined} tickFormatter={money ? usdk : undefined} width={money ? 56 : 32} tick={tick} />
  </>
  const tipOf = (rows: { name: string; colour: string; text: (fy: string) => string | undefined }[]) =>
    (q: { active?: boolean; label?: string | number }) => <TextTip active={q.active} label={q.label === undefined ? undefined : String(q.label)} rows={rows} />
  const cell = (key: string, chart: React.ReactElement) => (
    <div key={key} className="min-w-0" style={{ width: '100%', height: 220 }}><ResponsiveContainer>{chart}</ResponsiveContainer></div>)

  const countChart = (m: GroupMember) => {
    const rows = years.map(fy => ({ fy, ...Object.fromEntries(m.counts.map(k => [k, cb.get(fy)?.[k]])) }))
    const tip = m.counts.map(k => ({ name: kindName[k], colour: kindFill[k][0], text: (fy: string) => cb.has(fy) ? `${cb.get(fy)![k]} ${t.counts_unit}` : undefined }))
    return cell(`c${m.account}`, (
      <ComposedChart data={rows} margin={{ top: 10, right: 12, left: 4, bottom: 4 }}>
        {axes(maxCount, false)}
        <Tooltip content={tipOf(tip)} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        {m.counts.map(k => <Bar key={k} dataKey={k} name={kindName[k]} stackId="c" fill={kindFill[k][0]} fillOpacity={kindFill[k][1]} isAnimationActive={false} />)}
      </ComposedChart>))
  }
  const budgetChart = (m: GroupMember) => {
    const by = new Map(m.history.map(h => [h.fy, h]))
    const net = m.history.some(h => h.t.net)
    const tip = [{ name: t.voted, colour: 'var(--thread-2)', text: (fy: string) => by.get(fy)?.t.voted },
      { name: t.budget, colour: 'var(--thread-1)', text: (fy: string) => by.get(fy)?.t.budget },
      ...(net ? [{ name: t.gross, colour: 'var(--thread-4)', text: (fy: string) => by.get(fy)?.t.gross }] : []),
      { name: t.all_in, colour: 'var(--text-primary)', text: (fy: string) => by.get(fy)?.t.all_in }]
    return cell(`b${m.account}`, (
      <LineChart data={m.history} margin={{ top: 10, right: 12, left: 4, bottom: 4 }}>
        {axes(maxBudget)}
        <Tooltip content={tipOf(tip)} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Line dataKey="voted" name={t.voted} stroke="var(--thread-2)" strokeDasharray="5 4" strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} />
        <Line dataKey="budget" name={t.budget} stroke="var(--thread-1)" strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} />
        {net ? <Line dataKey="gross" name={t.gross} stroke="var(--thread-4)" strokeDasharray="2 3" strokeWidth={2} dot={{ r: 3 }} connectNulls={false} isAnimationActive={false} /> : null}
        {/* what it actually cost, every fund -- the yardstick a net vote is read against */}
        <Line dataKey="all_in" name={t.all_in} stroke="var(--text-primary)" strokeWidth={3} dot={{ r: 3.5 }} isAnimationActive={false} />
      </LineChart>))
  }
  const spendChart = (m: GroupMember) => {
    const by = new Map(m.history.map(h => [h.fy, h]))
    const mine = funds.filter(f => m.history.some(h => h.paid.some(p => p.fund === f)))
    const rows = m.history.map(h => ({ ...h, ...Object.fromEntries(h.paid.map(p => [`f${funds.indexOf(p.fund)}`, p.v])) }))
    const tip = [{ name: t.spent, colour: 'var(--thread-1)', text: (fy: string) => by.get(fy)?.t.spent },
      ...mine.map(f => ({ name: f, colour: fundColour(f), text: (fy: string) => by.get(fy)?.paid.find(p => p.fund === f)?.t })),
      { name: t.all_in, colour: 'var(--text-primary)', text: (fy: string) => by.get(fy)?.t.all_in },
      { name: t.budget, colour: 'var(--thread-1)', text: (fy: string) => by.get(fy)?.t.budget }]
    return cell(`s${m.account}`, (
      <ComposedChart data={rows} margin={{ top: 10, right: 12, left: 4, bottom: 4 }}>
        {axes(maxSpend)}
        <Tooltip content={tipOf(tip)} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Bar dataKey="spent" name={t.spent} stackId="s" fill="var(--thread-1)" fillOpacity={0.75} isAnimationActive={false} />
        {mine.map(f => <Bar key={f} dataKey={`f${funds.indexOf(f)}`} name={f} stackId="s" fill={fundColour(f)} fillOpacity={0.75} isAnimationActive={false} />)}
        <Line dataKey="all_in" name={t.all_in} stroke="var(--text-primary)" strokeWidth={3} dot={{ r: 3.5 }} isAnimationActive={false} />
        <Line dataKey="budget" name={t.budget} stroke="var(--thread-1)" strokeDasharray="5 4" strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} />
      </ComposedChart>))
  }
  const link = { color: 'var(--link, var(--thread-2))' }
  const row = (title: string, draw: (m: GroupMember) => React.ReactElement) => (
    <div className="mt-5">
      <p className="font-semibold text-[14px] mb-1">{title}</p>
      <div className="grid gap-6 md:grid-cols-2">{members.map(draw)}</div>
    </div>)
  return (
    <section className="mt-8">
      <H2>{t.compare_h}</H2>
      <p className="text-[13px] max-w-3xl" style={{ color: 'var(--text-secondary)' }}>{t.compare_line}</p>
      {/* the column heads, once, above every row */}
      <div className="grid gap-6 md:grid-cols-2 mt-4 sticky top-0 z-[1] py-1" style={{ background: 'var(--bg, var(--surface-1))' }}>
        {members.map(m => <a key={m.account} href={m.href} className="text-[16px] font-semibold underline" style={link}>{m.name}</a>)}
      </div>
      {counts && members.some(m => m.counts.length) ? row(t.r_counts, countChart) : null}
      {row(t.r_budget, budgetChart)}
      {row(t.r_spend, spendChart)}
    </section>)
}

export type LinePayees = { top: string[]; rest: Record<string, { v: number; t: string }>
  years: Record<string, Record<string, { v: number; t: string; n: number; med: number | null; t_med: string }>> }
export type BillKinds = Record<string, Record<string, { v: number; t: string }>>

const BILL_KINDS = [['invoice', 'var(--thread-1)'], ['early', 'var(--thread-3)'], ['owed', 'var(--thread-5)'], ['other', 'var(--text-muted)']] as const

/** WHO IT PAID, WHAT KIND OF BILL, HOW MANY AND HOW BIG (TJ, 28 October 2026: "we need to find an
 *  answer to this.... breakdowns and charts per payee maybe to see what increased over time"). Three
 *  views of the line's own rows, every fund: payees by year; this year's bills against next year's
 *  paid early and orders owed; and per payee, the count of invoices beside the median invoice --
 *  more bills and bigger bills are different causes, and neither is a count of children. */
export function LineBills({ payees: P, kinds, years, ix }: { payees: LinePayees; kinds: BillKinds; years: string[]; ix: ItemIndex }) {
  const t = ix.text
  // the generator picked the biggest payees across the years and put them in name order (fy_items.payees_out)
  const top = P.top, payees = P.years
  if (!top.length) return null
  const rest = Object.keys(P.rest).length > 0
  const prow = years.map(fy => ({ fy, rest: P.rest[fy]?.v, ...Object.fromEntries(top.map((p, i) => [`p${i}`, payees[fy]?.[p]?.v])) }))
  const pser = [...top.map((p, i) => ({ key: `p${i}`, name: p, colour: FUND_COLOURS[i % FUND_COLOURS.length], text: (fy: string) => payees[fy]?.[p]?.t })),
    ...(rest ? [{ key: 'rest', name: t.payees_rest, colour: 'var(--text-muted)', text: (fy: string) => P.rest[fy]?.t }] : [])]
  const krow = years.map(fy => ({ fy, ...Object.fromEntries(BILL_KINDS.map(([k]) => [k, kinds[fy]?.[k]?.v])) }))
  const kname: Record<string, string> = { invoice: t.k_invoice, early: t.k_early, owed: t.k_owed, other: t.k_other }
  const kser = BILL_KINDS.filter(([k]) => years.some(fy => kinds[fy]?.[k])).map(([k, c]) => ({ key: k, name: kname[k], colour: c, text: (fy: string) => kinds[fy]?.[k]?.t }))
  const stack = (title: string, line: string, data: object[], series: { key: string; name: string; colour: string; text: (fy: string) => string | undefined }[]) => (
    <div className="min-w-0">
      <p className="font-semibold text-[14px]">{title}</p>
      <p className="text-[12.5px] mb-1" style={muted}>{line}</p>
      <div style={{ width: '100%', height: 250 }}>
        <ResponsiveContainer>
          <ComposedChart data={data} stackOffset="sign" margin={{ top: 10, right: 12, left: 4, bottom: 4 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tick={tick} />
            <YAxis tickFormatter={usdk} width={56} tick={tick} />
            <ReferenceLine y={0} stroke="var(--grid)" />
            <Tooltip content={(q: { active?: boolean; label?: string | number }) => (
              <TextTip active={q.active} label={q.label === undefined ? undefined : String(q.label)} rows={series} />)} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            {series.map(s => <Bar key={s.key} dataKey={s.key} name={s.name} stackId="s" fill={s.colour} fillOpacity={0.8} isAnimationActive={false} />)}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>)
  return (
    <section className="mt-10">
      <div className="grid gap-6 md:grid-cols-2">
        {stack(t.payees_h, t.payees_line, prow, pser)}
        {stack(t.kinds_h, t.kinds_line, krow, kser)}
      </div>
      <p className="font-semibold text-[14px] mt-6">{t.bills_h}</p>
      <p className="text-[12.5px] mb-2 max-w-3xl" style={muted}>{t.bills_line}</p>
      <div className="overflow-x-auto">
        <table className="w-full text-[13px] tabular-nums">
          <thead><tr className="border-b" style={{ borderColor: 'var(--grid)' }}>
            <th className="text-left px-2 py-1.5" />{years.map(fy => <th key={fy} className="text-right px-2 py-1.5 font-semibold">{fy}</th>)}</tr></thead>
          <tbody>
            {top.map(p => (
              <tr key={p} className="border-b" style={{ borderColor: 'var(--grid)' }}>
                <td className="px-2 py-1.5 text-left">{p}</td>
                {years.map(fy => {
                  const x = payees[fy]?.[p]
                  return <td key={fy} className="px-2 py-1.5 text-right">{x && x.n ? <>{x.n} {t.n_bills}<span className="block text-[11.5px]" style={muted}>{t.med_bill} {x.t_med}</span></>
                    : <span style={muted}>—</span>}</td>
                })}
              </tr>))}
          </tbody>
        </table>
      </div>
    </section>)
}

export type LineMemos = { shown: boolean; last: string; prev: string | null
  cats: { id: string; label: string; words: string }[]
  by_cat: Record<string, Record<string, { v: number; t: string }>>
  rows: { payee: string; cat: string; n: Record<string, number>; t: Record<string, string>; change: number; t_change: string }[]
  other: { memo: string; t: string }[] }

const CAT_COLOURS = ['var(--thread-3)', 'var(--thread-2)', 'var(--thread-5)', 'var(--thread-1)', 'var(--thread-4)', 'var(--thread-6, var(--text-secondary))', 'var(--axis)']

/** WHAT THE BILLS WERE FOR (TJ, 28 October 2026: "analze the MEMOS now per payee... to see what memo
 *  'category' has seen the most change"). The generator's keyword groups (fy_items.MEMO_CATS, ours,
 *  printed here with their words) by year, then each payee and group with its change into the last
 *  year, largest first. Left out where the keywords sorted less than half the money. */
export function LineMemoCats({ m, years, ix }: { m: LineMemos | undefined; years: string[]; ix: ItemIndex }) {
  const t = ix.text
  if (!m || !m.shown) return null
  const label: Record<string, string> = { ...Object.fromEntries(m.cats.map(c => [c.id, c.label])), other: t.c_other }
  const ids = [...m.cats.map(c => c.id), 'other'].filter(c => years.some(fy => m.by_cat[fy]?.[c]))
  const colour = (c: string) => c === 'other' ? 'var(--text-muted)' : CAT_COLOURS[m.cats.findIndex(x => x.id === c) % CAT_COLOURS.length]
  const rows = years.map(fy => ({ fy, ...Object.fromEntries(ids.map(c => [c, m.by_cat[fy]?.[c]?.v])) }))
  const series = ids.map(c => ({ key: c, name: label[c], colour: colour(c), text: (fy: string) => m.by_cat[fy]?.[c]?.t }))
  return (
    <section className="mt-10">
      <H2>{t.memos_h}</H2>
      <p className="text-[13px] mb-3 max-w-3xl" style={{ color: 'var(--text-secondary)' }}>{t.memos_line}</p>
      {/* stacked, not side by side (TJ, 29 October 2026): the table is a long list, so the chart
          takes the full width and the table sits under it */}
      <div className="space-y-6">
        <div style={{ width: '100%', height: 260 }}>
          <ResponsiveContainer>
            <ComposedChart data={rows} stackOffset="sign" margin={{ top: 10, right: 12, left: 4, bottom: 4 }}>
              <CartesianGrid stroke="var(--grid)" vertical={false} />
              <XAxis dataKey="fy" tick={tick} />
              <YAxis tickFormatter={usdk} width={56} tick={tick} />
              <ReferenceLine y={0} stroke="var(--grid)" />
              <Tooltip content={(q: { active?: boolean; label?: string | number }) => (
                <TextTip active={q.active} label={q.label === undefined ? undefined : String(q.label)} rows={series} />)} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              {series.map(s => <Bar key={s.key} dataKey={s.key} name={s.name} stackId="s" fill={s.colour} fillOpacity={0.8} isAnimationActive={false} />)}
            </ComposedChart>
          </ResponsiveContainer>
        </div>
        <div className="min-w-0">
          <p className="font-semibold text-[13.5px] mb-1">{t.memos_change}</p>
          <div className="overflow-x-auto">
            <table className="w-full text-[12.5px] tabular-nums">
              <thead><tr className="border-b" style={{ borderColor: 'var(--grid)' }}>
                <th className="text-left px-1.5 py-1" />{years.map(fy => <th key={fy} className="text-right px-1.5 py-1 font-semibold">{fy}</th>)}
                <th className="text-right px-1.5 py-1 font-semibold">{t.change_col}{m.prev ? ` ${m.prev.slice(2)}→${m.last.slice(2)}` : ''}</th></tr></thead>
              <tbody>
                {m.rows.map(r => (
                  <tr key={`${r.payee}${r.cat}`} className="border-b" style={{ borderColor: 'var(--grid)' }}>
                    <td className="px-1.5 py-1 text-left"><span className="inline-block w-2 h-2 rounded-sm mr-1.5" style={{ background: colour(r.cat) }} />
                      {label[r.cat]}<span className="block text-[11px] pl-3.5" style={muted}>{r.payee}</span></td>
                    {years.map(fy => <td key={fy} className="px-1.5 py-1 text-right">{r.t[fy] || <span style={muted}>—</span>}</td>)}
                    <td className="px-1.5 py-1 text-right font-semibold">{r.t_change || <span style={muted}>—</span>}</td>
                  </tr>))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
      <details className="mt-3 text-[12.5px] max-w-3xl">
        <summary className="cursor-pointer" style={{ color: 'var(--text-secondary)' }}>{t.memos_words}</summary>
        <ul className="mt-1 space-y-0.5">{m.cats.map(c => <li key={c.id}><span className="font-semibold">{c.label}</span> <span style={muted}>· {c.words}</span></li>)}</ul>
        {m.other.length ? <>
          <p className="mt-2 font-semibold">{t.memos_unsorted}</p>
          <ul className="space-y-0.5">{m.other.map(o => <li key={o.memo} className="flex justify-between gap-3"><span className="font-mono text-[11.5px]">{o.memo}</span><span className="tabular-nums">{o.t}</span></li>)}</ul>
        </> : null}
      </details>
    </section>)
}

export type PayeeRates = { payee: string; publisher: string; program: string; tier: string; csv: string
  years: { fy: string; href: string | null; page: number | null; t: Record<string, string>; ext_label: string; t_med: string; t_billed: string; years: number | null }[] }

/** THE PUBLISHED PRICE (TJ, 28 October 2026: "we can show the rates directly on this page for
 *  comparison"). The collaborative's own rate sheet, each year, beside what the line was billed --
 *  the pairing ours, and the bills-at-the-rate a conversion, labelled as both. */
export function RatesTable({ rates, ix }: { rates: PayeeRates[] | undefined; ix: ItemIndex }) {
  const t = ix.text
  if (!rates?.length) return null
  const link = { color: 'var(--link, var(--thread-2))' }
  return (
    <section className="mt-10">
      <H2>{t.rates_h}</H2>
      <p className="text-[13px] mb-3 max-w-3xl" style={{ color: 'var(--text-secondary)' }}>{t.rates_line}</p>
      {rates.map(r => (
        <div key={r.payee} className="mb-4">
          <p className="font-semibold text-[14px]">{r.publisher} · {r.program} · {r.tier} <span className="font-normal text-[12.5px]" style={muted}>({r.payee})</span></p>
          <div className="overflow-x-auto">
            <table className="w-full text-[13px] tabular-nums mt-1">
              <thead><tr className="border-b" style={{ borderColor: 'var(--grid)' }}>
                <th className="text-left px-2 py-1.5">{t.year}</th>
                {[t.r_sy, t.r_day, t.r_ext, t.r_45, t.r_med, t.r_billed, t.r_years].map(h => <th key={h} className="text-right px-2 py-1.5 font-semibold">{h}</th>)}
              </tr></thead>
              <tbody>
                {r.years.map(y => (
                  <tr key={y.fy} className="border-b" style={{ borderColor: 'var(--grid)' }}>
                    <td className="px-2 py-1.5 font-semibold">{y.fy}{y.href ? <a href={`${y.href}#page=${y.page}`} className="block text-[11px] font-normal underline" style={link}>{t.r_sheet}</a> : null}</td>
                    <td className="px-2 py-1.5 text-right">{y.t.school_year ?? '—'}</td>
                    <td className="px-2 py-1.5 text-right">{y.t.day ?? '—'}</td>
                    <td className="px-2 py-1.5 text-right">{y.t.extended_year ?? '—'}<span className="block text-[11px]" style={muted}>{y.ext_label}</span></td>
                    <td className="px-2 py-1.5 text-right">{y.t.initial_45_day ?? '—'}</td>
                    <td className="px-2 py-1.5 text-right font-semibold">{y.t_med || <span style={muted}>—</span>}</td>
                    <td className="px-2 py-1.5 text-right">{y.t_billed || <span style={muted}>—</span>}</td>
                    <td className="px-2 py-1.5 text-right">{y.years != null ? <>{y.years} <span className="text-[11px]" style={muted}>{t.r_years_unit}</span></> : <span style={muted}>—</span>}</td>
                  </tr>))}
              </tbody>
            </table>
          </div>
          <p className="text-[12px] mt-1 max-w-3xl" style={muted}>{t.r_years_note} <a href={r.csv} className="underline" style={link}>{r.csv.split('/').pop()}</a></p>
        </div>))}
    </section>)
}

/** WHAT EACH YEAR LEFT IN THE BUDGET, under the budget-against-spending chart (TJ, 28 October 2026:
 *  "it shows private tuition had a surplus (unspent money) of $522k ... on the 'budget against
 *  spending' chart ... it doesnt appear that way at all"). Left is budget less the school budget's
 *  own spending; the chart's bars are every fund's -- so the two differ by what other funds paid. */
function LeftRow({ h, ix }: { h: LineHist[]; ix: ItemIndex }) {
  const t = ix.text
  if (!h.some(x => x.t.left)) return null
  return (
    <div className="mt-1">
      <div className="grid text-[12.5px] tabular-nums" style={{ gridTemplateColumns: `auto repeat(${h.length}, minmax(0, 1fr))` }}>
        <span className="pr-3 font-semibold" style={{ color: 'var(--text-secondary)' }}>{t.left_row}</span>
        {h.map(x => <span key={x.fy} className="text-center"><span className="block text-[11px]" style={muted}>{x.fy}</span>
          <span className="font-semibold" style={{ color: (x.left ?? 0) < 0 ? 'var(--thread-3)' : 'var(--thread-5)' }}>{x.t.left}</span></span>)}
      </div>
      <p className="text-[12px] mt-1 max-w-3xl" style={muted}>{t.left_note}</p>
    </div>)
}
