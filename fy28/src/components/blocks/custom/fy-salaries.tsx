/** SALARIES PAID FROM OUTSIDE THE GENERAL FUND (fy-breakdown). TJ, 28 October 2026: "we must now
 *  have the information if a non-general fund source paid some portion or all of a salary or
 *  salary LINE (school line)."
 *
 *  The page's year, two ways. By school salary line: pay a year-end journal entry moved off the
 *  line to another fund, or back onto it, both ends named in the books, and the share another
 *  fund carried in the end. By fund: all of a fund's pay, by where it lands -- moved to or from
 *  a school line, the same kind of work (our match), or no school line, which is where a grant's
 *  own payroll mostly sits because its accounts name a kind of work, never a post. A row opens
 *  its entries or its kinds of work. Every figure is formatted by scripts/fy_salaries.py. */
import { Fragment, useMemo, useState } from 'react'
import { useFyYear } from './fy-year'
import { Chip, HeadTip, WideScroll } from './fy-shared'
import type { CustomProps } from './index'

type LineT = { before: string; off: string; on: string; kept: string; share: string; dir: '' | 'off' | 'on' }
type Line = { line: string; cat: string; n: { before: number; off: number; on: number; kept: number; share: number | null }; t: LineT
  funds: { name: string; text: string; dir: 'off' | 'on' }[]; moves: { date: string; memo: string; dir: 'off' | 'on'; text: string; funds: string }[] }
type FK = 'run' | 'moved' | 'adj' | 'total'
type Fund = { name: string; n: Record<FK, number>; t: Record<FK, string>; kinds: { name: string; text: string }[] }
type RK = 'name' | 'steady' | 'typical' | 'steady_total' | 'other' | 'total'
type Reg = { name: string; account: string; n: Record<Exclude<RK, 'name'>, number>; t: Record<Exclude<RK, 'name'>, string>
  runs: [string, number][]; moves: { date: string; memo: string; line: string; dir: 'to' | 'from'; text: string }[] }
type Year = { regular: Reg[]; fy: string; lines: Line[]; funds: Fund[]; total: string; share: string; sums: Record<'run' | 'took' | 'gave' | 'between' | 'adj', string>; n_lines: number }
type Data = { years: Year[]; text: Record<string, string>; links: { href: string; label: string }[] }

const muted = { color: 'var(--text-muted)' }, secondary = { color: 'var(--text-secondary)' }
const OFF = 'var(--thread-3)', ON = 'var(--thread-1)'
const num = 'px-2 py-1.5 text-right whitespace-nowrap tabular-nums'

function useSort<K extends string>(first: K) {
  const [sort, setSort] = useState<{ key: K; dir: 1 | -1 }>({ key: first, dir: -1 })
  const head = (key: K, label: string, right = true, means?: string) => (
    <th className={`px-2 py-1.5 font-semibold cursor-pointer select-none align-bottom ${right ? 'text-right' : 'text-left'}`}
      aria-sort={sort.key === key ? (sort.dir < 0 ? 'descending' : 'ascending') : 'none'}
      onClick={() => setSort(s => ({ key, dir: s.key === key ? (s.dir === 1 ? -1 : 1) : (right ? -1 : 1) }))}>
      {means ? <HeadTip label={label} means={means}><span>{label}{sort.key === key ? (sort.dir < 0 ? ' ↓' : ' ↑') : ''}</span></HeadTip>
        : <>{label}{sort.key === key ? (sort.dir < 0 ? ' ↓' : ' ↑') : ''}</>}</th>)
  return { sort, head }
}
const order = <R,>(rows: R[], val: (r: R) => string | number, dir: 1 | -1) => [...rows].sort((a, b) => {
  const x = val(a), z = val(b)
  return dir * (typeof x === 'number' && typeof z === 'number' ? x - z : String(x).localeCompare(String(z)))
})

export default function FySalaries({ data, alt }: CustomProps) {
  const d = data as Data
  const t = d.text
  const fys = useMemo(() => d.years.map(v => v.fy), [d])
  const [fy] = useFyYear(fys)
  const y = d.years[Math.max(0, fys.indexOf(fy))]
  const [tab, setTab] = useState<'lines' | 'funds' | 'regular'>('lines')
  const [open, setOpen] = useState<string | null>(null)
  const L = useSort<'line' | 'cat' | 'before' | 'off' | 'on' | 'kept' | 'share'>('share')
  const F = useSort<'name' | FK>('total')
  const R = useSort<RK>('steady_total')
  const regs = order(y.regular, r => R.sort.key === 'name' ? r.name : r.n[R.sort.key], R.sort.dir)
  const lines = order(y.lines, r => L.sort.key === 'line' ? r.line : L.sort.key === 'cat' ? r.cat
    : L.sort.key === 'share' ? (r.n.share ?? 0) : r.n[L.sort.key], L.sort.dir)
  const funds = order(y.funds, r => F.sort.key === 'name' ? r.name : r.n[F.sort.key], F.sort.dir)
  return (
    <figure aria-label={alt}>
      <p className="text-[13.5px]"><span className="font-semibold tabular-nums">{y.total}</span>{' '}
        <span style={secondary}>{t.lead} {y.fy}, {y.share} {t.of_all}</span></p>
      <p className="text-[12.5px] mt-1 font-semibold" style={secondary}>{t.how}</p>
      <ul className="text-[12.5px] mt-0.5 space-y-0.5" style={secondary}>
        <li><span className="tabular-nums font-semibold" style={{ color: 'var(--text-primary)' }}>{y.sums.run}</span> {t.s_run}</li>
        <li><span className="tabular-nums font-semibold" style={{ color: OFF }}>+{y.sums.took}</span> {t.s_took}</li>
        <li><span className="tabular-nums font-semibold" style={{ color: ON }}>−{y.sums.gave}</span> {t.s_gave}</li>
        <li><span className="tabular-nums">{y.sums.between}</span> {t.s_between}</li>
        <li><span className="tabular-nums">{y.sums.adj}</span> {t.s_adj}</li>
      </ul>
      <div className="flex gap-1.5 mt-3">
        <Chip on={tab === 'lines'} onClick={() => setTab('lines')}>{t.tab_lines} · {y.n_lines}</Chip>
        <Chip on={tab === 'funds'} onClick={() => setTab('funds')}>{t.tab_funds} · {y.funds.length}</Chip>
        <Chip on={tab === 'regular'} onClick={() => setTab('regular')}>{t.tab_regular} · {y.regular.length}</Chip>
      </div>
      {tab === 'regular' ? (
        <>
          <p className="text-[12.5px] mt-2" style={muted}>{t.regular_read}</p>
          <WideScroll cue={t.tab_regular}>
            <table className="w-full min-w-[860px] text-[13px] border-collapse">
              <thead><tr className="border-b" style={{ borderColor: 'var(--grid)' }}>
                {R.head('name', t.c_account, false)}{R.head('steady', t.c_steady, true, t.m_steady)}{R.head('typical', t.c_typical, true, t.m_typical)}
                {R.head('steady_total', t.c_steady_total, true, t.m_steady_total)}{R.head('other', t.c_rest, true, t.m_rest)}{R.head('total', t.c_total_pay)}
              </tr></thead>
              <tbody>
                {regs.map(r => {
                  const key = `${r.name}|${r.account}`
                  const max = Math.max(1, ...r.runs.map(x => x[1]))
                  return (
                    <Fragment key={key}>
                      <tr className="border-b align-top cursor-pointer hover:bg-[var(--surface-2)]" style={{ borderColor: 'var(--grid)' }}
                        onClick={() => setOpen(o => (o === key ? null : key))}>
                        <td className="px-2 py-1.5 min-w-[16rem]"><span className="underline decoration-dotted underline-offset-2">{r.name}</span>
                          <span className="block text-[11.5px]" style={muted}>{r.account}{r.moves.length ? ` · ${t.has_moves}` : ''}</span>
                          {/* the shape at a glance: one bar a pay run, the typical run dashed */}
                          <svg width={Math.max(60, r.runs.length * 5)} height={22} className="mt-1 block" aria-hidden>
                            {r.runs.map(([, v], i) => <rect key={i} x={i * 5} y={22 - Math.max(1, (Math.max(0, v) / max) * 20)} width={3.5}
                              height={Math.max(1, (Math.max(0, v) / max) * 20)} fill="var(--thread-2)" opacity={Math.abs(v - r.n.typical) <= 0.25 * r.n.typical ? 1 : 0.4} />)}
                            <line x1={0} x2={r.runs.length * 5} y1={22 - (r.n.typical / max) * 20} y2={22 - (r.n.typical / max) * 20}
                              stroke="var(--text-secondary)" strokeDasharray="2 2" strokeWidth={1} />
                          </svg></td>
                        <td className={num} style={secondary}>{r.t.steady}</td>
                        <td className={num}>{r.t.typical}</td>
                        <td className={num} style={{ fontWeight: 600 }}>{r.t.steady_total}</td>
                        <td className={num} style={muted}>{r.t.other}</td>
                        <td className={num} style={secondary}>{r.t.total}</td>
                      </tr>
                      {open === key ? (
                        <tr className="border-b" style={{ borderColor: 'var(--grid)' }}><td colSpan={6} className="px-3 py-2 text-[12.5px]" style={{ background: 'var(--surface-2)' }}>
                          <p style={muted}>{t.runs_note}</p>
                          <p className="tabular-nums mt-1" style={secondary}>{r.runs.map(([w, v]) => `${w} $${Math.round(v).toLocaleString('en-US')}`).join(' · ')}</p>
                          {r.moves.length ? <>
                            <p className="text-[12px] font-semibold uppercase tracking-wide mt-2" style={muted}>{t.moves_h}</p>
                            <ul className="mt-1 space-y-1">{r.moves.map((mv, i) => (
                              <li key={i} className="flex justify-between gap-3"><span>{mv.date} · <span style={secondary}>“{mv.memo}”</span> · {mv.dir === 'to' ? t.to : t.from} <span className="font-semibold">{mv.line}</span></span>
                                <span className="tabular-nums font-semibold whitespace-nowrap">{mv.text}</span></li>))}</ul>
                          </> : <p className="mt-1" style={muted}>{t.no_moves_r}</p>}
                        </td></tr>) : null}
                    </Fragment>)
                })}
              </tbody>
            </table>
          </WideScroll>
        </>
      ) : tab === 'lines' ? (
        <>
          <p className="text-[12.5px] mt-2" style={muted}>{t.lines_read}</p>
          {y.lines.length ? (
            <WideScroll cue={t.tab_lines}>
              <table className="w-full min-w-[860px] text-[13px] border-collapse">
                <thead><tr className="border-b" style={{ borderColor: 'var(--grid)' }}>
                  {L.head('line', t.c_line, false)}{L.head('cat', t.c_cat, false)}{L.head('before', t.c_before, true, t.m_before)}
                  {L.head('off', t.c_off, true, t.m_off)}{L.head('on', t.c_on, true, t.m_on)}{L.head('kept', t.c_kept, true, t.m_kept)}{L.head('share', t.c_share, true, t.m_share)}
                </tr></thead>
                <tbody>
                  {lines.map(r => (
                    <Fragment key={r.line}>
                      <tr className="border-b align-top cursor-pointer hover:bg-[var(--surface-2)]" style={{ borderColor: 'var(--grid)' }}
                        onClick={() => setOpen(o => (o === r.line ? null : r.line))}>
                        <td className="px-2 py-1.5 min-w-[14rem]"><span className="underline decoration-dotted underline-offset-2">{r.line}</span>
                          <span className="block text-[11.5px]" style={muted}>{r.funds.map(f => `${f.dir === 'off' ? '→' : '←'} ${f.name}`).join(' · ')}</span></td>
                        <td className="px-2 py-1.5" style={secondary}>{r.cat}</td>
                        <td className={num} style={secondary}>{r.t.before}</td>
                        <td className={num} style={{ color: OFF }}>{r.t.off}</td>
                        <td className={num} style={{ color: ON }}>{r.t.on}</td>
                        <td className={num}>{r.t.kept}</td>
                        <td className={num} style={{ fontWeight: 600, color: r.t.dir === 'on' ? ON : OFF }}>
                          {r.t.share ? <>{r.t.share}<span className="block text-[11px] font-normal" style={muted}>{r.t.dir === 'on' ? t.took_on : t.carried}</span></> : ''}</td>
                      </tr>
                      {open === r.line ? (
                        <tr className="border-b" style={{ borderColor: 'var(--grid)' }}><td colSpan={7} className="px-3 py-2" style={{ background: 'var(--surface-2)' }}>
                          <p className="text-[12px] font-semibold uppercase tracking-wide" style={muted}>{t.entries}</p>
                          <ul className="mt-1 space-y-1 text-[12.5px]">
                            {r.moves.map((mv, i) => (
                              <li key={i} className="flex justify-between gap-3">
                                <span>{mv.date} · <span style={secondary}>“{mv.memo}”</span> · <span style={muted}>{mv.dir === 'off' ? t.to : t.from} {mv.funds}</span></span>
                                <span className="tabular-nums font-semibold whitespace-nowrap" style={{ color: mv.dir === 'off' ? OFF : ON }}>{mv.dir === 'off' ? '−' : '+'}{mv.text}</span>
                              </li>))}
                          </ul>
                        </td></tr>) : null}
                    </Fragment>))}
                </tbody>
              </table>
            </WideScroll>) : <p className="text-[13px] mt-2" style={muted}>{t.no_lines}</p>}
        </>
      ) : (
        <>
          <p className="text-[12.5px] mt-2" style={muted}>{t.funds_read}</p>
          <WideScroll cue={t.tab_funds}>
            <table className="w-full min-w-[820px] text-[13px] border-collapse">
              <thead><tr className="border-b" style={{ borderColor: 'var(--grid)' }}>
                {F.head('name', t.c_fund, false)}{F.head('run', t.c_run, true, t.m_run)}{F.head('moved', t.c_moved, true, t.m_moved)}
                {F.head('adj', t.c_adj, true, t.m_adj)}{F.head('total', t.c_total, true, t.m_total)}
              </tr></thead>
              <tbody>
                {funds.map(r => (
                  <Fragment key={r.name}>
                    <tr className={`border-b align-top ${r.kinds.length ? 'cursor-pointer hover:bg-[var(--surface-2)]' : ''}`} style={{ borderColor: 'var(--grid)' }}
                      onClick={() => r.kinds.length && setOpen(o => (o === r.name ? null : r.name))}>
                      <td className="px-2 py-1.5 min-w-[14rem]">{r.kinds.length ? <span className="underline decoration-dotted underline-offset-2">{r.name}</span> : r.name}</td>
                      <td className={num} style={secondary}>{r.t.run}</td>
                      <td className={num} style={{ color: r.n.moved < 0 ? ON : OFF }}>{r.t.moved}</td>
                      <td className={num} style={muted}>{r.t.adj}</td>
                      <td className={num} style={{ fontWeight: 600 }}>{r.t.total}</td>
                    </tr>
                    {open === r.name ? (
                      <tr className="border-b" style={{ borderColor: 'var(--grid)' }}><td colSpan={5} className="px-3 py-2 text-[12.5px]" style={{ background: 'var(--surface-2)' }}>
                        <span style={muted}>{t.kinds}</span> {r.kinds.map(k => `${k.name} ${k.text}`).join(' · ')}</td></tr>) : null}
                  </Fragment>))}
              </tbody>
            </table>
          </WideScroll>
        </>)}
      <p className="text-[12px] mt-2" style={muted}>{t.limit} {d.links.map((l, i) => <Fragment key={l.href}>{i ? ' · ' : ''}<a className="underline" href={l.href}>{l.label}</a></Fragment>)}</p>
    </figure>)
}
