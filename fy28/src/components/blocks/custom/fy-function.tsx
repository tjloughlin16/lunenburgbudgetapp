/* ONE FUNCTION CODE, at its own address: /school-functions/<code> (TJ, 2 November 2026: "i have no
 * idea what these are, but i want to see everything associated to them. if they are expensed, type
 * of accounts, just memos, etc").
 *
 * A function code is the fourth segment of every school account number -- what the money is FOR --
 * so one code collects general fund lines, grants, fee funds and lunch. Everything here is from
 * /data/fy-breakdown/function/<code>.json (scripts/build_function_pages.py), formatted there; this
 * file computes nothing but which rows to show. */
import { useMemo, useState } from 'react'
import { ReportShell, H2 } from '../../report'
import { Chip } from './fy-shared'
import { useFyYear } from './fy-year'

type Money = string | null
export type FunctionItem = {
  code: string; name: string; name_by: string; cls: string; cls_short: string; cls_text: string
  years: string[]; four_years: string
  totals: { fy: string; spent: string; budget: Money; kinds: Record<string, string>; counts: Record<string, number> }[]
  kinds: { id: string; label: string }[]
  groups: { name: string; spent: Money[] }[]
  accounts: { account: string; desc: string; group: string; program: string; href: string | null; lines: number; spent: Money[]; budget: Money[]; total: string }[]
  payees: { name: string; lines: number; spent: Money[]; total: string }[]
  memos: { fy: string; date: string; account: string; desc: string; memo: string; amount: string; journal: string }[]
  sources: { href: string; label: string }[]
}

const muted = { color: 'var(--text-muted)' }, secondary = { color: 'var(--text-secondary)' }
const link = { color: 'var(--link, var(--thread-2))' }
const neg = (t: Money) => (t ?? '').startsWith('-')
const PAYEES = 15

/** A year-by-year table: a label column, one column per year, and a total. Wraps the label. */
function YearTable({ head, years, rows, fy }: {
  head: string; years: string[]; fy: string
  rows: { key: string; label: React.ReactNode; sub?: React.ReactNode; cells: Money[]; total?: string }[]
}) {
  return (
    <div className="overflow-x-auto rounded-md border" style={{ borderColor: 'var(--grid)' }}>
      <table className="w-full text-[13px] tabular-nums border-collapse min-w-[560px]">
        <thead>
          <tr style={{ background: 'var(--surface-1)', color: 'var(--text-secondary)' }}>
            <th className="text-left font-semibold px-2.5 py-2 min-w-[12rem]" style={{ borderBottom: '2px solid var(--axis)' }}>{head}</th>
            {years.map(y => (
              <th key={y} className="text-right font-semibold px-2.5 py-2"
                style={{ borderBottom: '2px solid var(--axis)', color: y === fy ? 'var(--text-primary)' : undefined }}>{y}</th>))}
            {rows.some(r => r.total) ? (
              <th className="text-right font-semibold px-2.5 py-2" style={{ borderBottom: '2px solid var(--axis)', borderLeft: '1px solid var(--grid)' }}>
                All years</th>) : null}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, j) => (
            <tr key={r.key} style={{ background: j % 2 ? 'var(--surface-1)' : 'var(--surface-2)' }}>
              <th scope="row" className="text-left font-normal px-2.5 py-1.5 leading-snug">
                {r.label}{r.sub ? <span className="block text-[11px]" style={muted}>{r.sub}</span> : null}</th>
              {r.cells.map((c, i) => (
                <td key={i} className="text-right px-2.5 py-1.5 whitespace-nowrap"
                  style={{ color: c == null ? 'var(--text-muted)' : neg(c) ? 'var(--thread-3)' : 'var(--text-primary)',
                           fontWeight: years[i] === fy ? 600 : undefined }}>{c ?? '—'}</td>))}
              {r.total ? (
                <td className="text-right px-2.5 py-1.5 whitespace-nowrap font-semibold" style={{ borderLeft: '1px solid var(--grid)' }}>
                  {r.total}</td>) : null}
            </tr>))}
        </tbody>
      </table>
    </div>)
}

export function FunctionPage({ item, parent }: { item: FunctionItem; parent: { href: string; label: string } }) {
  const years = item.years
  const [fy, setFy] = useFyYear(years)
  const yi = Math.max(0, years.indexOf(fy))
  const t = item.totals[yi]
  const [allPayees, setAllPayees] = useState(false)
  const memos = useMemo(() => item.memos.filter(m => m.fy === years[yi]), [item, years, yi])
  const payees = allPayees ? item.payees : item.payees.slice(0, PAYEES)
  const COUNT_WORD: Record<string, string> = { payroll: 'pay runs', invoice: 'invoices', 'journal entry': 'entries',
    receipt: 'receipts', owed: 'purchase order lines' }
  return (
    <ReportShell title={`${item.code} ${item.name}`} kicker={`Function code · ${item.cls_short}`}
      dataUrl={`/data/fy-breakdown/function/${item.code}.json`}
      standfirst={item.cls_text}
      meta={<p className="mt-3 text-[13px]" style={secondary}>
        What the money is FOR: the fourth part of every school account number
        (0100-3-300-<b>{item.code}</b>-…), across every fund. Name from {item.name_by}.</p>}>
      <div className="flex flex-wrap gap-1.5 mt-5">
        {years.map(y => <Chip key={y} on={y === years[yi]} onClick={() => setFy(y)}>{y}</Chip>)}
      </div>

      {/* the year, in one row of figures: what was budgeted, what was spent, and what kind of entry spent it */}
      <section className="mt-6">
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          <div className="rounded-md border p-3" style={{ borderColor: 'var(--grid)' }}>
            <p className="text-[12px]" style={muted}>Spent, {years[yi]}</p>
            <p className="text-[20px] font-semibold tabular-nums">{t.spent}</p>
            <p className="text-[12px]" style={muted}>payments plus what is still owed, every fund</p>
          </div>
          <div className="rounded-md border p-3" style={{ borderColor: 'var(--grid)' }}>
            <p className="text-[12px]" style={muted}>Budgeted, {years[yi]}</p>
            <p className="text-[20px] font-semibold tabular-nums">{t.budget ?? '—'}</p>
            <p className="text-[12px]" style={muted}>original budget plus transfers{t.budget ? '' : '; none on this code'}</p>
          </div>
          {item.kinds.filter(k => t.kinds[k.id]).map(k => (
            <div key={k.id} className="rounded-md border p-3" style={{ borderColor: 'var(--grid)' }}>
              <p className="text-[12px]" style={muted}>{k.label}</p>
              <p className="text-[20px] font-semibold tabular-nums" style={neg(t.kinds[k.id]) ? { color: 'var(--thread-3)' } : undefined}>
                {t.kinds[k.id]}</p>
              <p className="text-[12px]" style={muted}>{t.counts[k.id]} {COUNT_WORD[k.id] ?? 'lines'}</p>
            </div>))}
        </div>
        <p className="text-[12px] mt-2 max-w-3xl" style={muted}>
          A payroll line is what one pay run cost one account; the books record no person. A negative
          figure is money moved off this code, or a purchase order closed.</p>
      </section>

      <section className="mt-10">
        <H2>Which funds paid</H2>
        <YearTable head="Fund group" years={years} fy={years[yi]}
          rows={item.groups.map(g => ({ key: g.name, label: g.name, cells: g.spent }))} />
      </section>

      <section className="mt-10">
        <H2>Every account on this code</H2>
        <p className="text-[13px] mb-2 max-w-3xl" style={secondary}>
          Spent per year. A linked account has its own page: a school budget line, or the grant or fee fund that paid it.</p>
        <YearTable head="Account" years={years} fy={years[yi]}
          rows={item.accounts.map(a => ({
            key: a.account,
            label: a.href ? <a href={`${a.href}?fy=${encodeURIComponent(years[yi])}`} className="underline" style={link}>{a.desc}</a> : a.desc,
            sub: <>{a.program === 'General fund' ? 'General fund' : `${a.group} · ${a.program}`} · {a.account}</>,
            cells: a.spent, total: a.total }))} />
      </section>

      {item.payees.length ? (
        <section className="mt-10">
          <H2>Who was paid</H2>
          <p className="text-[13px] mb-2 max-w-3xl" style={secondary}>
            From invoices only: a pay run names no person. A family receiving services is masked, never named.</p>
          <YearTable head="Payee" years={years} fy={years[yi]}
            rows={payees.map(p => ({ key: p.name, label: p.name, sub: `${p.lines} invoice lines`, cells: p.spent, total: p.total }))} />
          {item.payees.length > PAYEES ? (
            <button type="button" className="mt-2 text-[13px] underline cursor-pointer" style={link} onClick={() => setAllPayees(v => !v)}>
              {allPayees ? `Show the top ${PAYEES}` : `Show all ${item.payees.length} payees`}</button>) : null}
        </section>) : null}

      <section className="mt-10">
        <H2>Journal entries, {years[yi]}</H2>
        <p className="text-[13px] mb-2 max-w-3xl" style={secondary}>
          Money moved by hand rather than paid: re-charges between accounts, year-end entries and their
          reversals, with the memo as the books print it (cut at about eighteen characters).</p>
        {memos.length ? (
          <div className="overflow-x-auto rounded-md border" style={{ borderColor: 'var(--grid)' }}>
            <table className="w-full text-[13px] tabular-nums border-collapse min-w-[560px]">
              <thead><tr style={{ background: 'var(--surface-1)', color: 'var(--text-secondary)' }}>
                {['Date', 'Account', 'Memo', 'Amount'].map((h, i) => (
                  <th key={h} className={`${i === 3 ? 'text-right' : 'text-left'} font-semibold px-2.5 py-2`} style={{ borderBottom: '2px solid var(--axis)' }}>{h}</th>))}
              </tr></thead>
              <tbody>
                {memos.map((m, j) => (
                  <tr key={`${m.journal}${m.account}${j}`} style={{ background: j % 2 ? 'var(--surface-1)' : 'var(--surface-2)' }}>
                    <td className="px-2.5 py-1.5 whitespace-nowrap">{m.date}</td>
                    <td className="px-2.5 py-1.5 leading-snug">{m.desc}<span className="block text-[11px]" style={muted}>{m.account}</span></td>
                    <td className="px-2.5 py-1.5 leading-snug">{m.memo || <span style={muted}>no memo</span>}<span className="block text-[11px]" style={muted}>entry {m.journal}</span></td>
                    <td className="px-2.5 py-1.5 text-right whitespace-nowrap" style={neg(m.amount) ? { color: 'var(--thread-3)' } : undefined}>{m.amount}</td>
                  </tr>))}
              </tbody>
            </table>
          </div>) : <p className="text-[13px]" style={muted}>No journal entries on this code in {years[yi]}.</p>}
      </section>

      <section className="mt-10">
        <H2>Sources</H2>
        <ul className="text-[13px] space-y-1 list-disc pl-5">
          {item.sources.map(s => <li key={s.href}><a className="underline" style={link} href={s.href}>{s.label}</a></li>)}
        </ul>
        <p className="text-[13px] mt-3"><a className="underline" style={link} href={parent.href}>← {parent.label}</a></p>
      </section>
    </ReportShell>)
}
