/** SCHOOL LINES OTHER FUNDS PAID (fy-breakdown). TJ, 27 October 2026: "which of the school budget
 *  lines were paid by non general fund money ... athletics lines XYZ - paid by FUND X - an amount".
 *
 *  The sister of "What other funds paid for": the same placements, read by school line. One row
 *  per line and fund, for the page's year, sortable and filterable. Every figure is formatted by
 *  scripts/build_fy_breakdown.py (line_funds_data), which ties these rows to the table of funds. */
import { useMemo, useState } from 'react'
import { useFyYear } from './fy-year'
import { HeadTip, PAYER, WideScroll } from './fy-shared'
import type { CustomProps } from './index'

type Row = { cat: string; line: string; acct: string; fund: string; group: string; how: string
  n: number; t: string; budget: string; share: string }
type Year = { fy: string; rows: Row[]; total: string; n_lines: number }
type Data = { years: Year[]; how: { id: string; label: string; means: string }[]
  groups: { id: string; label: string }[]; text: Record<string, string> }
type Key = 'cat' | 'line' | 'fund' | 'kind' | 'how' | 'n'

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
  const [sort, setSort] = useState<{ k: Key; dir: 1 | -1 }>({ k: 'cat', dir: 1 })
  const rows = useMemo(() => {
    const ql = q.trim().toLowerCase()
    const out = y.rows.filter(r => (!grp || r.group === grp)
      && (!ql || `${r.line} ${r.cat} ${r.fund} ${r.acct}`.toLowerCase().includes(ql)))
    const val = (r: Row) => sort.k === 'kind' ? kind[r.group] : sort.k === 'how' ? how[r.how].label : sort.k === 'n' ? '' : r[sort.k]
    return out.sort((a, b) => sort.k === 'n' ? sort.dir * (a.n - b.n)
      : sort.dir * val(a).localeCompare(val(b)) || b.n - a.n)
  }, [y, grp, q, sort, kind, how])
  const sum = rows.reduce((s, r) => s + r.n, 0)
  const head = (k: Key, label: string, right = false) => (
    <th className={`px-2 py-1.5 font-semibold whitespace-nowrap cursor-pointer select-none ${right ? 'text-right' : 'text-left'}`}
      onClick={() => setSort(s => ({ k, dir: s.k === k ? (s.dir === 1 ? -1 : 1) : (k === 'n' ? -1 : 1) }))}>
      {label}{sort.k === k ? (sort.dir < 0 ? ' ↓' : ' ↑') : ''}</th>)
  return (
    <figure aria-label={alt}>
      <div className="flex flex-wrap gap-1.5">
        <Chip on={!grp} onClick={() => setGrp('')}>{t.all_kinds}</Chip>
        {d.groups.filter(g => y.rows.some(r => r.group === g.id)).map(g => (
          <Chip key={g.id} on={grp === g.id} onClick={() => setGrp(grp === g.id ? '' : g.id)}>
            <span className="inline-block w-2 h-2 rounded-[1px] mr-1.5 align-middle" style={{ background: PAYER[g.id] }} />{g.label}</Chip>))}
      </div>
      <input value={q} onChange={e => setQ(e.target.value)} placeholder={t.filter} aria-label={t.filter}
        className="mt-2 w-full max-w-md px-2.5 py-1.5 rounded text-[13px]"
        style={{ border: '1px solid var(--grid)', background: 'transparent' }} />
      <WideScroll cue={t.scroll}>
        <table className="w-full min-w-[1180px] text-[13px] tabular-nums border-collapse">
          <thead>
            <tr className="border-b" style={{ borderColor: 'var(--grid)' }}>
              {head('cat', t.cat)}{head('line', t.line)}{head('fund', t.fund)}{head('kind', t.kind)}
              <th className="px-2 py-1.5 text-left font-semibold whitespace-nowrap cursor-pointer select-none"
                onClick={() => setSort(s => ({ k: 'how', dir: s.k === 'how' ? (s.dir === 1 ? -1 : 1) : 1 }))}>
                {t.how}{sort.k === 'how' ? (sort.dir < 0 ? ' ↓' : ' ↑') : ''}</th>
              {head('n', t.paid, true)}
              <th className="px-2 py-1.5 text-right font-semibold whitespace-nowrap"><HeadTip label={t.budget} means={t.budget_means}>{t.budget}</HeadTip></th>
              <th className="px-2 py-1.5 text-right font-semibold whitespace-nowrap"><HeadTip label={t.share} means={t.share_means}>{t.share}</HeadTip></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i} className="border-b align-top" style={{ borderColor: 'var(--grid)' }}>
                <td className="px-2 py-1" style={secondary}>{r.cat}</td>
                <td className="px-2 py-1">{r.line}{r.acct ? <span className="block text-[11px]" style={muted}>{r.acct}</span> : null}</td>
                <td className="px-2 py-1">{r.fund}</td>
                <td className="px-2 py-1 whitespace-nowrap" style={secondary}>
                  <span className="inline-block w-2 h-2 rounded-[1px] mr-1.5 align-middle" style={{ background: PAYER[r.group] }} />{kind[r.group]}</td>
                <td className="px-2 py-1 whitespace-nowrap" style={secondary}><HeadTip label={how[r.how].label} means={how[r.how].means}>{how[r.how].label}</HeadTip></td>
                <td className="px-2 py-1 text-right whitespace-nowrap font-semibold">{r.t}</td>
                <td className="px-2 py-1 text-right whitespace-nowrap" style={secondary}>{r.budget}</td>
                <td className="px-2 py-1 text-right whitespace-nowrap" style={secondary}>{r.share}</td>
              </tr>))}
          </tbody>
          <tfoot>
            <tr>
              <td className="px-2 py-1.5 font-semibold" colSpan={5}>{t.sum} · {rows.length}</td>
              <td className="px-2 py-1.5 text-right font-semibold whitespace-nowrap">
                {rows.length === y.rows.length ? y.total : `$${Math.round(sum).toLocaleString('en-US')}`}</td>
              <td colSpan={2} />
            </tr>
          </tfoot>
        </table>
      </WideScroll>
    </figure>)
}
