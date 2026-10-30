import { useEffect, useMemo, useState } from 'react'
import { ReportShell, H2 } from '../components/report'
import { Chip } from '../components/blocks/custom/fy-shared'
import { useFyYear } from '../components/blocks/custom/fy-year'

/* ONE TOWN FUND, at its own address: /town-funds/<slug>. The school funds' pages
 * (/school-funds/<slug>, pages/FyItem.tsx) for a fund the TOWN holds -- so far the Town general
 * fund, and on it what the schools bring in (preschool tuition, student parking, a school medical
 * reimbursement), year by year, received against the Town's estimate.
 *
 * TJ, 29 October 2026: "a fund page slug for the town general fund ... it should work the same as
 * the schools." Client-rendered only, as the school fund pages. Every figure and string is from
 * /data/town-funds/<slug>.json and index.json, written by scripts/build_town_funds.py. */

type Txt = Record<string, string>
type Acct = { id: string; account: string; name: string; what: string; printed: string }
type Cell = { id: string; received: number | null; estimate: number | null; t: { received: string; estimate: string }; src: string; href: string; check: string }
type Year = { fy: string; rows: Cell[]; why: string; total: { v: number; t: string } | null
  together: { received: number | null; estimate: number | null; t: { received: string; estimate: string }; src: string; href: string } | null }
type Fund = { slug: string; name: string; fund: string; what: string; accounts: Acct[]; years: Year[]
  links: { label: string; href: string }[]; sources: { label: string; href: string }[] }
type Index = { funds: { slug: string; name: string; what: string }[]; base: string; text: Txt }

const muted = { color: 'var(--text-muted)' }, secondary = { color: 'var(--text-secondary)' }
const link = { color: 'var(--link, var(--thread-2))' }
const COLOURS = ['var(--thread-1)', 'var(--thread-2)', 'var(--thread-5)']

export function townFundFromPath(pathname: string): string | null {
  const m = /^\/town-funds\/([a-z0-9-]+)\/?$/.exec(pathname.toLowerCase())
  return m ? m[1] : null
}

/** Each account's years as bars on one scale, the estimate as a tick. */
function History({ f, t }: { f: Fund; t: Txt }) {
  const max = Math.max(1, ...f.years.flatMap(y => y.rows.flatMap(r => [r.received ?? 0, r.estimate ?? 0])))
  return (
    <section className="mt-10">
      <H2>{t.history_h}</H2>
      <p className="text-[13px] mb-3 max-w-3xl" style={secondary}>{t.history_note}</p>
      <div className="space-y-6">
        {f.accounts.map((a, i) => (
          <div key={a.id}>
            <p className="font-semibold text-[14px]">{a.name} <span className="font-normal text-[12px]" style={muted}>· {a.account}</span></p>
            <div className="mt-1 space-y-0.5">
              {f.years.map(y => {
                const c = y.rows.find(r => r.id === a.id)!
                return (
                  <div key={y.fy} className="flex items-center gap-2 text-[12px]">
                    <span className="w-14 shrink-0 tabular-nums" style={muted}>{y.fy}</span>
                    <div className="relative flex-1 h-3.5" style={{ background: 'var(--grid)', opacity: c.received == null ? 0.35 : 1 }}>
                      {c.received != null ? <div className="absolute inset-y-0 left-0" style={{ width: `${(c.received / max) * 100}%`, background: COLOURS[i % COLOURS.length] }} /> : null}
                      {c.estimate != null ? <div className="absolute -inset-y-0.5 w-0.5" style={{ left: `${(c.estimate / max) * 100}%`, background: 'var(--text-primary, currentColor)' }} title={`${t.estimate} ${c.t.estimate}`} /> : null}
                    </div>
                    <span className="w-40 shrink-0 text-right tabular-nums">{c.received != null ? c.t.received : <span style={muted}>{t.none}</span>}
                      {c.estimate != null ? <span style={muted}> / {c.t.estimate}</span> : null}</span>
                  </div>)
              })}
            </div>
          </div>))}
      </div>
    </section>)
}

function YearTable({ f, y, t }: { f: Fund; y: Year; t: Txt }) {
  return (
    <section className="mt-6">
      <H2>{y.fy}</H2>
      <div className="overflow-x-auto">
        <table className="w-full text-[13px]">
          <thead><tr className="border-b" style={{ borderColor: 'var(--grid)' }}>
            <th className="text-left px-2 py-1.5">{t.account}</th>
            <th className="text-right px-2 py-1.5">{t.received}</th>
            <th className="text-right px-2 py-1.5">{t.estimate}</th>
            <th className="text-left px-2 py-1.5">{t.source}</th></tr></thead>
          <tbody>
            {y.rows.map(r => {
              const a = f.accounts.find(x => x.id === r.id)!
              return (
                <tr key={r.id} className="border-b align-top" style={{ borderColor: 'var(--grid)' }}>
                  <td className="px-2 py-1.5"><span className="font-semibold">{a.name}</span>
                    <div className="text-[12px]" style={muted}>{a.what}</div></td>
                  <td className="px-2 py-1.5 text-right tabular-nums">{r.received != null ? r.t.received : <span style={muted}>{t.none}</span>}</td>
                  <td className="px-2 py-1.5 text-right tabular-nums">{r.estimate != null ? r.t.estimate : <span style={muted}>—</span>}</td>
                  <td className="px-2 py-1.5 text-[12px]">{r.href ? <a className="underline" style={link} href={r.href}>{r.src}</a> : null}
                    {r.check ? <div style={muted}>{t.check}: {r.check}</div> : null}</td>
                </tr>)
            })}
            {y.total ? (
              <tr><td className="px-2 py-1.5 font-semibold">{t.total}</td><td className="px-2 py-1.5 text-right tabular-nums font-semibold">{y.total.t}</td><td /><td /></tr>) : null}
            {y.together ? (
              <tr className="align-top"><td className="px-2 py-1.5 font-semibold">{t.together}</td>
                <td className="px-2 py-1.5 text-right tabular-nums font-semibold">{y.together.received != null ? y.together.t.received : <span style={muted}>{t.none}</span>}</td>
                <td className="px-2 py-1.5 text-right tabular-nums">{y.together.estimate != null ? y.together.t.estimate : '—'}</td>
                <td className="px-2 py-1.5 text-[12px]"><a className="underline" style={link} href={y.together.href}>{y.together.src}</a></td></tr>) : null}
          </tbody>
        </table>
      </div>
      {y.why ? <p className="text-[13px] mt-2" style={secondary}>{y.why}</p> : null}
    </section>)
}

export function TownFund() {
  const slug = townFundFromPath(window.location.pathname)
  const [ix, setIx] = useState<Index | null>(null)
  const [f, setF] = useState<Fund | null>(null)
  const [err, setErr] = useState(false)
  useEffect(() => {
    if (!slug) return
    let live = true
    const get = (u: string) => fetch(u).then(r => { if (!r.ok) throw new Error(String(r.status)); return r.json() })
    get('/data/town-funds/index.json').then(i => { if (live) setIx(i) }, () => {})
    get(`/data/town-funds/${slug}.json`).then(v => { if (live) setF(v) }, () => { if (live) setErr(true) })
    return () => { live = false }
  }, [slug])
  if (!slug || err) return (
    <ReportShell title={ix?.text.not_found ?? ''} noPrint>
      {ix ? <p className="mt-4 text-[14px]"><a className="underline" style={link} href={ix.text.parent_href}>← {ix.text.parent}</a></p> : null}
    </ReportShell>)
  if (!ix || !f) return <ReportShell title="" loading />
  return <FundView f={f} ix={ix} />
}

function FundView({ f, ix }: { f: Fund; ix: Index }) {
  const years = useMemo(() => f.years.map(y => y.fy), [f])
  const [fy, setFy] = useFyYear(years)
  const t = ix.text
  const y = f.years.find(v => v.fy === fy) ?? f.years[f.years.length - 1]
  return (
    <ReportShell title={f.name} kicker={`${t.k_fund} · ${f.fund}`} dataUrl={`/data/town-funds/${f.slug}.json`}
      standfirst={f.what}
      meta={<div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[13px]"><span style={muted}>{t.see}:</span>
        {f.links.map(l => <a key={l.href} href={l.href} className="underline" style={link}>{l.label} →</a>)}</div>}>
      <p className="text-[13px] mt-4 max-w-3xl" style={secondary}>{t.not_school}</p>
      <div className="flex flex-wrap gap-1.5 mt-5">
        {years.map(v => <Chip key={v} on={v === y.fy} onClick={() => setFy(v)}>{v}</Chip>)}
      </div>
      <YearTable f={f} y={y} t={t} />
      <History f={f} t={t} />
      <section className="mt-10">
        <H2>{t.sources}</H2>
        <ul className="text-[13px] space-y-1 list-disc pl-5">
          {f.sources.map(s => <li key={s.href}><a className="underline" style={link} href={s.href}>{s.label}</a></li>)}
        </ul>
        <p className="text-[13px] mt-3"><a className="underline" style={link} href={t.parent_href}>← {t.parent}</a></p>
      </section>
    </ReportShell>)
}
