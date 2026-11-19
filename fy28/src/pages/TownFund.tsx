import { useEffect, useMemo, useState } from 'react'
import { ReportShell, H2 } from '../components/report'
import { Chip } from '../components/blocks/custom/fy-shared'
import { useFyYear } from '../components/blocks/custom/fy-year'

/* ONE TOWN FUND OR ONE TOWN LINE, at its own address: /town-funds/<slug>, /town-lines/<slug>.
 *
 * TJ, 19 November 2026: *"for the school accounts, i can drop in and see the actual ledger. i cant
 * figure out how to do that here"* and *"i thought we have a rule that every fund/account gets its
 * detailed page for navigation? ... this needs to be a pattern for ALL funds"*. So this renders ANY
 * town fund's payload, /data/town-funds/<slug>.json; nothing in it is about parks. The parks funds
 * (scripts/build_parks_ledger.py) are the first three; another fund is another payload.
 *
 * THE PAYLOAD. Every figure and string is formatted by the generator; this formats nothing.
 *   name, kicker, about, owner {name, href}, as_of
 *   years ['FY2023', ...], spans {fy: '1 July 2022 to 30 June 2023'}
 *   stats {fy: [{value, label}]}                       the year's headline figures
 *   accounts {columns [{id, label, means}], years {fy: {rows [{key, code, name, side, zero?, t {col: text}}],
 *             total {name, t}}}}                      the year, account by account
 *   across {label, columns [fy], rows [{name, side, cells [text]}], note}   every year side by side
 *   postings {kinds [{id, label, means}], shown [kind], years {fy: [{d, acct, kind, how, who, what, ref,
 *             amt, n}]}, masked} | null               every line of the journal
 *   postings_none                                       why there are no postings, when there are none
 *   read [{h, p}], related [{label, href}], sources [{label, href}], gaps? [{label, href}]
 */

type Col = { id: string; label: string; means: string }
type AcctRow = { key: string; code: string; name: string; side: 'in' | 'out'; zero?: boolean; t: Record<string, string> }
type Posting = { d: string; acct: string; kind: string; how: string; who: string; what: string; ref: string; amt: string; n: number; masked?: boolean }
type Item = {
  slug: string; path: string; code: string; name: string; kicker: string; about: string; as_of: string
  owner: { name: string; href: string }
  years: string[]; spans: Record<string, string>
  stats: Record<string, { value: string; label: string }[]>
  accounts: { columns: Col[]; years: Record<string, { rows: AcctRow[]; total: { name: string; t: Record<string, string> } }> }
  across?: { label: string; columns: string[]; rows: { name: string; side: string; cells: string[] }[]; note: string }
  postings: { kinds: Col[]; shown: string[]; years: Record<string, Posting[]>; masked?: string } | null
  postings_none: string | null
  read: { h: string; p: string }[]; related: { label: string; href: string }[]
  sources: { label: string; href: string }[]; gaps?: { label: string; href: string }[]
}

const muted = { color: 'var(--text-muted)' }, secondary = { color: 'var(--text-secondary)' }
const link = { color: 'var(--link, var(--thread-2))' }
const IN = 'var(--thread-1)', OUT = 'var(--thread-3)'
const th = 'px-2 py-1 font-semibold text-[12px]'

/** /town-funds/<slug> or /town-lines/<slug> -> the slug, or null. A slug ends in the fund's or the
 *  department's number (park-revolving-1500), so /town-funds/general-fund -- an older alias of the
 *  town-general-fund topic (routes.ts TOPIC_ALIASES) -- is not one. */
export function townFundFromPath(path: string): string | null {
  const m = path.replace(/\/+$/, '').match(/^\/town-(?:funds|lines)\/([a-z0-9-]+-\d+)$/)
  return m ? m[1] : null
}

/** The account table for one year. A row opens that account's postings below. Divs, not a
 *  <table>: the site adds download links to every table, and the JSON is the download. */
function Accounts({ it, fy, pick, picked }: { it: Item; fy: string; pick: (k: string | null) => void; picked: string | null }) {
  const y = it.accounts.years[fy]
  const [zeros, setZeros] = useState(false)
  if (!y) return null
  const cols = it.accounts.columns
  const rows = y.rows.filter(r => zeros || !r.zero)
  const hidden = y.rows.length - rows.length
  const grid = { gridTemplateColumns: `minmax(10rem, 1.6fr) repeat(${cols.length}, minmax(5.5rem, 1fr))` }
  return (
    <div className="overflow-x-auto">
      <div className="grid text-[13px] tabular-nums min-w-[560px]" style={grid}>
        <span className={th} />
        {cols.map(c => <span key={c.id} className={`${th} text-right`} title={c.means} style={secondary}>{c.label}</span>)}
        {rows.map(r => {
          const on = picked === r.key
          const can = !!it.postings
          return [
            <button key={r.key + 'n'} type="button" disabled={!can} onClick={() => pick(on ? null : r.key)}
              className="text-left px-2 py-1.5 border-t" aria-pressed={on}
              style={{ borderColor: 'var(--grid)', background: on ? 'var(--surface-2)' : undefined, cursor: can ? 'pointer' : 'default' }}>
              <span className="inline-block w-2 h-2 rounded-full mr-1.5 align-middle" style={{ background: r.side === 'in' ? IN : OUT }} />
              <span className={can ? 'underline decoration-dotted' : undefined}>{r.name}</span>
              <span className="block text-[11.5px]" style={muted}>{r.code}</span></button>,
            ...cols.map(c => <span key={r.key + c.id} className="px-2 py-1.5 text-right border-t"
              style={{ borderColor: 'var(--grid)', background: on ? 'var(--surface-2)' : undefined }}>{r.t[c.id]}</span>),
          ]
        })}
        <span className="px-2 py-1.5 border-t-2 font-semibold" style={{ borderColor: 'var(--text-muted)' }}>{y.total.name}</span>
        {cols.map(c => <span key={'tot' + c.id} className="px-2 py-1.5 text-right border-t-2 font-semibold"
          style={{ borderColor: 'var(--text-muted)' }}>{y.total.t[c.id]}</span>)}
      </div>
      {hidden ? <button type="button" className="text-[12.5px] underline mt-1" style={link} onClick={() => setZeros(true)}>
        Show {hidden} accounts with nothing in them</button> : null}
    </div>)
}

function Across({ a }: { a: NonNullable<Item['across']> }) {
  const grid = { gridTemplateColumns: `minmax(10rem, 1.6fr) repeat(${a.columns.length}, minmax(5.5rem, 1fr))` }
  return (
    <section className="mt-10">
      <H2>{a.label}</H2>
      <div className="overflow-x-auto">
        <div className="grid text-[13px] tabular-nums min-w-[560px]" style={grid}>
          <span className={th} />
          {a.columns.map(c => <span key={c} className={`${th} text-right`} style={secondary}>{c}</span>)}
          {a.rows.map(r => [
            <span key={r.name} className="px-2 py-1.5 border-t" style={{ borderColor: 'var(--grid)' }}>
              <span className="inline-block w-2 h-2 rounded-full mr-1.5 align-middle" style={{ background: r.side === 'in' ? IN : OUT }} />{r.name}</span>,
            ...r.cells.map((v, i) => <span key={r.name + i} className="px-2 py-1.5 text-right border-t" style={{ borderColor: 'var(--grid)' }}>{v}</span>),
          ])}
        </div>
      </div>
      <p className="text-[12.5px] mt-2" style={muted}>{a.note}</p>
    </section>)
}

function Postings({ it, fy, acct, setAcct }: { it: Item; fy: string; acct: string | null; setAcct: (k: string | null) => void }) {
  const P = it.postings!
  const [kinds, setKinds] = useState<string[]>(P.shown)
  const [q, setQ] = useState('')
  const all = P.years[fy] ?? []
  const names = useMemo(() => Object.fromEntries((it.accounts.years[fy]?.rows ?? []).map(r => [r.key, r.name])), [it, fy])
  const rows = all.filter(p => kinds.includes(p.kind) && (!acct || p.acct === acct)
    && (!q || `${p.who} ${p.what} ${p.ref}`.toLowerCase().includes(q.toLowerCase())))
  const toggle = (k: string) => setKinds(ks => ks.includes(k) ? ks.filter(x => x !== k) : [...ks, k])
  return (
    <section className="mt-10" id="postings">
      <H2>Every posting, {fy}</H2>
      <div className="flex flex-wrap gap-1.5 items-center">
        {P.kinds.map(k => <span key={k.id} title={k.means}><Chip on={kinds.includes(k.id)} onClick={() => toggle(k.id)}>{k.label}</Chip></span>)}
        {acct ? <Chip on onClick={() => setAcct(null)}>{names[acct] ?? acct} ×</Chip> : null}
        <input type="search" value={q} onChange={e => setQ(e.target.value)} placeholder="Find a payee or memo"
          className="ml-auto px-2 py-1 text-[13px] rounded border w-full sm:w-56"
          style={{ borderColor: 'var(--grid)', background: 'var(--surface-1)', color: 'var(--text-primary)' }} />
      </div>
      <p className="text-[12.5px] mt-2" style={muted}>{rows.length} of {all.length} postings shown. {P.masked}</p>
      <ul className="mt-1 divide-y text-[13.5px]" style={{ borderColor: 'var(--grid)' }}>
        {rows.map((p, i) => (
          <li key={i} className="py-1.5 grid grid-cols-[1fr_auto] gap-x-3" style={{ borderColor: 'var(--grid)' }}>
            <span className="min-w-0">
              <span>{p.who}</span> <span style={muted}>· {p.how} · {names[p.acct] ?? ''}</span>
              <span className="block text-[12.5px] break-words" style={muted}>{p.d} · {p.what} · {p.ref}</span>
            </span>
            <span className="tabular-nums text-right" style={{ color: p.kind === 'in' ? IN : p.kind === 'out' ? 'var(--text-primary)' : 'var(--text-secondary)' }}>{p.amt}</span>
          </li>))}
      </ul>
    </section>)
}

export function TownFund() {
  const slug = townFundFromPath(window.location.pathname)
  const [it, setIt] = useState<Item | null>(null)
  const [err, setErr] = useState<string | null>(null)
  useEffect(() => {
    if (!slug) { setErr('No fund at this address.'); return }
    fetch(`/data/town-funds/${slug}.json`).then(r => { if (!r.ok) throw new Error(String(r.status)); return r.json() })
      .then(setIt, () => setErr('No fund at this address.'))
  }, [slug])
  return (
    <ReportShell title={it?.name ?? 'Town fund'} kicker={it?.kicker} err={err} loading={!it && !err}
      dataUrl={slug ? `/data/town-funds/${slug}.json` : undefined}
      standfirst={it?.about}
      meta={it ? <p className="mt-3 text-[13px]"><span style={muted}>Owned by</span> <a className="underline" style={link} href={it.owner.href}>{it.owner.name}</a> <span style={muted}>· {it.as_of}</span></p> : undefined}>
      {it && <Body it={it} />}
    </ReportShell>)
}

/** The page once its payload is in: the year hook is created with the fund's own years, so a
 *  `?fy=` in the address is honoured and the latest year opens by default. */
function Body({ it }: { it: Item }) {
  const [fy, setFy] = useFyYear(it.years)
  const [acct, setAcct] = useState<string | null>(null)
  useEffect(() => { setAcct(null) }, [fy])
  const pick = (k: string | null) => {
    setAcct(k)
    if (k) window.setTimeout(() => document.getElementById('postings')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 0)
  }
  return (<>
        <div className="flex flex-wrap items-end justify-between gap-3 pb-3 border-b" style={{ borderColor: 'var(--grid)' }}>
          <div>
            <span className="block text-[36px] font-bold leading-none tabular-nums">{fy}</span>
            <span className="block text-[13.5px] mt-1" style={secondary}>{it.spans[fy]}</span>
          </div>
          <div className="flex flex-wrap gap-1.5">{it.years.map(y => <Chip key={y} on={y === fy} onClick={() => setFy(y)}>{y}</Chip>)}</div>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-x-6 gap-y-3 mt-4">
          {(it.stats[fy] ?? []).map((s, i) => (
            <div key={i}><span className="block text-[20px] font-semibold tabular-nums">{s.value}</span>
              <span className="block text-[12.5px] leading-snug" style={secondary}>{s.label}</span></div>))}
        </div>
        <section className="mt-8">
          <H2>Account by account, {fy}</H2>
          <Accounts it={it} fy={fy} pick={pick} picked={acct} />
          {it.postings ? <p className="text-[12.5px] mt-2" style={muted}>Tap an account for its postings.</p> : null}
        </section>
        {it.postings ? <Postings it={it} fy={fy} acct={acct} setAcct={setAcct} /> : (
          <section className="mt-8">
            <H2>Postings</H2>
            <p className="text-[13.5px] max-w-3xl" style={secondary}>{it.postings_none}
              {it.gaps?.map(g => <> <a key={g.href} className="underline" style={link} href={g.href}>{g.label}</a>.</>)}</p>
          </section>)}
        {it.across ? <Across a={it.across} /> : null}
        <section className="mt-10 max-w-3xl">
          <H2>How to read this ledger</H2>
          <dl className="text-[13.5px] space-y-2">
            {it.read.map(r => <div key={r.h}><dt className="font-semibold">{r.h}</dt><dd style={secondary}>{r.p}</dd></div>)}
          </dl>
        </section>
        <section className="mt-10">
          <H2>Related</H2>
          <ul className="text-[13.5px] flex flex-wrap gap-x-5 gap-y-1">
            {it.related.map(r => <li key={r.href}><a className="underline" style={link} href={r.href}>{r.label}</a></li>)}
          </ul>
        </section>
        <section className="mt-10">
          <H2>Sources</H2>
          <ol className="text-[13px] space-y-1 list-decimal pl-5">
            {it.sources.map(s => <li key={s.href}><a className="underline" style={link} href={s.href}>{s.label}</a></li>)}
          </ol>
        </section>
      </>)
}
