/** SCHOOL LINES OTHER FUNDS PAID (fy-breakdown). TJ, 27 October 2026: "which of the school budget
 *  lines were paid by non general fund money ... athletics lines XYZ - paid by FUND X - an amount",
 *  then "group lines together ... that are the same school line, aggregates, but listing the funds
 *  paying it, with details available by clicking".
 *
 *  The sister of "What other funds paid for": the same placements, read by school line. One row
 *  per line for the page's year -- what other funds paid toward it in all, the line's budget and
 *  the share of its cost, and the funds as chips; a click opens each fund's amount and how we know.
 *  Every figure is formatted by scripts/build_fy_breakdown.py (line_funds_data), which ties the
 *  lines to the table of funds. */
import { Fragment, useMemo, useState } from 'react'
import { useFyYear } from './fy-year'
import { HeadTip, PAYER, WideScroll } from './fy-shared'
import type { CustomProps } from './index'

type Fund = { fund: string; group: string; how: string; n: number; t: string; share: string }
type Line = { cat: string; line: string; acct: string; n: number; t: string; budget: string; share: string
  groups: string[]; funds: Fund[] }
type Year = { fy: string; lines: Line[]; total: string; n_rows: number }
type Data = { years: Year[]; how: { id: string; label: string; means: string }[]
  groups: { id: string; label: string }[]; text: Record<string, string> }
type Key = 'cat' | 'line' | 'n' | 'funds'

const muted = { color: 'var(--text-muted)' }, secondary = { color: 'var(--text-secondary)' }

function Chip({ on, onClick, children }: { on: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button type="button" onClick={onClick} className="px-2.5 py-1 rounded-full text-[12.5px]"
      style={{ border: '1px solid var(--grid)', background: on ? 'var(--text-primary)' : 'transparent',
        color: on ? 'var(--surface-1, #fff)' : 'var(--text-secondary)' }}>{children}</button>)
}

export default function FyLineFunds({ data, alt }: CustomProps) {
  const d = data as Data
  const t = d.text
  const fys = useMemo(() => d.years.map(v => v.fy), [d])
  const [fy] = useFyYear(fys)
  const y = d.years[Math.max(0, fys.indexOf(fy))]
  const kind = Object.fromEntries(d.groups.map(g => [g.id, g.label]))
  const how = Object.fromEntries(d.how.map(h => [h.id, h]))
  const [grp, setGrp] = useState('')
  const [q, setQ] = useState('')
  const [open, setOpen] = useState<Set<string>>(new Set())
  const [sort, setSort] = useState<{ k: Key; dir: 1 | -1 }>({ k: 'cat', dir: 1 })
  const id = (l: Line) => `${l.acct}|${l.line}`
  // a kind of fund picked shows the lines it paid toward, and only its funds under them
  const lines = useMemo(() => {
    const ql = q.trim().toLowerCase()
    const out = y.lines
      .filter(l => !grp || l.groups.includes(grp))
      .filter(l => !ql || `${l.line} ${l.cat} ${l.acct} ${l.funds.map(f => f.fund).join(' ')}`.toLowerCase().includes(ql))
    return out.sort((a, b) => sort.k === 'n' ? sort.dir * (a.n - b.n)
      : sort.k === 'funds' ? sort.dir * (a.funds.length - b.funds.length) || b.n - a.n
      : sort.dir * a[sort.k].localeCompare(b[sort.k]) || b.n - a.n)
  }, [y, grp, q, sort])
  const toggle = (k: string) => setOpen(s => { const n = new Set(s); if (n.has(k)) n.delete(k); else n.add(k); return n })
  const allOpen = lines.length > 0 && lines.every(l => open.has(id(l)))
  const head = (k: Key, label: string, right = false) => (
    <th className={`px-2 py-1.5 font-semibold whitespace-nowrap cursor-pointer select-none ${right ? 'text-right' : 'text-left'}`}
      onClick={() => setSort(s => ({ k, dir: s.k === k ? (s.dir === 1 ? -1 : 1) : (k === 'n' || k === 'funds' ? -1 : 1) }))}>
      {label}{sort.k === k ? (sort.dir < 0 ? ' ↓' : ' ↑') : ''}</th>)
  return (
    <figure aria-label={alt}>
      <div className="flex flex-wrap gap-1.5">
        <Chip on={!grp} onClick={() => setGrp('')}>{t.all_kinds}</Chip>
        {d.groups.filter(g => y.lines.some(l => l.groups.includes(g.id))).map(g => (
          <Chip key={g.id} on={grp === g.id} onClick={() => setGrp(grp === g.id ? '' : g.id)}>
            <span className="inline-block w-2 h-2 rounded-[1px] mr-1.5 align-middle" style={{ background: PAYER[g.id] }} />{g.label}</Chip>))}
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-3">
        <input value={q} onChange={e => setQ(e.target.value)} placeholder={t.filter} aria-label={t.filter}
          className="w-full max-w-md px-2.5 py-1.5 rounded text-[13px]"
          style={{ border: '1px solid var(--grid)', background: 'transparent' }} />
        <button type="button" className="text-[12.5px] underline" style={secondary}
          onClick={() => setOpen(allOpen ? new Set() : new Set(lines.map(id)))}>{allOpen ? t.collapse : t.expand}</button>
      </div>
      <WideScroll cue={t.scroll}>
        <table className="w-full min-w-[960px] text-[13px] tabular-nums border-collapse">
          <thead>
            <tr className="border-b" style={{ borderColor: 'var(--grid)' }}>
              {head('cat', t.cat)}{head('line', t.line)}{head('funds', t.fund)}{head('n', t.paid, true)}
              <th className="px-2 py-1.5 text-right font-semibold whitespace-nowrap"><HeadTip label={t.budget} means={t.budget_means}>{t.budget}</HeadTip></th>
              <th className="px-2 py-1.5 text-right font-semibold whitespace-nowrap"><HeadTip label={t.share} means={t.share_means}>{t.share}</HeadTip></th>
            </tr>
          </thead>
          <tbody>
            {lines.map(l => {
              const k = id(l), on = open.has(k)
              const funds = grp ? l.funds.filter(f => f.group === grp) : l.funds
              return (
                <Fragment key={k}>
                  <tr className="border-b align-top cursor-pointer" style={{ borderColor: 'var(--grid)' }}
                    onClick={() => toggle(k)} aria-expanded={on}>
                    <td className="px-2 py-1.5" style={secondary}>{l.cat}</td>
                    <td className="px-2 py-1.5">
                      <span className="inline-block w-3.5 text-[12px]" style={muted} aria-hidden>{on ? '▾' : '▸'}</span>{l.line}
                      {l.acct ? <span className="block pl-3.5 text-[11px]" style={muted}>{l.acct}</span> : null}</td>
                    <td className="px-2 py-1.5">
                      <span className="inline-flex flex-wrap gap-1 items-center">
                        {l.groups.map(g => <span key={g} title={kind[g]} className="inline-block w-2 h-2 rounded-[1px]" style={{ background: PAYER[g] }} />)}
                        <span style={secondary}>{funds.length} {funds.length === 1 ? t.fund_one : t.funds}</span></span></td>
                    <td className="px-2 py-1.5 text-right whitespace-nowrap font-semibold">{l.t}</td>
                    <td className="px-2 py-1.5 text-right whitespace-nowrap" style={secondary}>{l.budget}</td>
                    <td className="px-2 py-1.5 text-right whitespace-nowrap" style={secondary}>{l.share}</td>
                  </tr>
                  {on ? funds.map((f, i) => (
                    <tr key={i} className="text-[12.5px]" style={{ background: 'var(--surface-2, transparent)' }}>
                      <td />
                      <td className="px-2 py-1 pl-5" colSpan={1}>
                        <span className="inline-block w-2 h-2 rounded-[1px] mr-1.5 align-middle" style={{ background: PAYER[f.group] }} />{f.fund}
                        <span className="block pl-3.5 text-[11.5px]" style={muted}>{kind[f.group]}</span></td>
                      <td className="px-2 py-1" style={secondary}><HeadTip label={how[f.how].label} means={how[f.how].means}>{how[f.how].label}</HeadTip></td>
                      <td className="px-2 py-1 text-right whitespace-nowrap">{f.t}</td>
                      <td />
                      <td className="px-2 py-1 text-right whitespace-nowrap" style={secondary}>{f.share}</td>
                    </tr>)) : null}
                </Fragment>)
            })}
          </tbody>
          <tfoot>
            <tr>
              <td className="px-2 py-1.5 font-semibold" colSpan={3}>{t.sum} · {lines.length} {t.lines}</td>
              <td className="px-2 py-1.5 text-right font-semibold whitespace-nowrap">{!grp && !q.trim() ? y.total : ''}</td>
              <td colSpan={2} />
            </tr>
          </tfoot>
        </table>
      </WideScroll>
    </figure>)
}
