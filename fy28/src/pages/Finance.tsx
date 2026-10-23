import { JobsLink } from '../components/JobPostings'
import { BoardNav } from '../components/BoardNav'
import { useEffect, useRef, useState } from 'react'
import type { Tab } from '../routes'
import { boardFinanceSlugFromPath, departmentSlugFromPath } from '../routes'
import { usd } from '../model/engine'
import { Conclusions, Grain, H2, Body, NotEstablished, ReportShell, Stat, useReport, splitConclusions } from '../components/report'
import type { Conclusion } from '../components/report'

const TAB: Tab = 'schoolfinance'
const DATA = '/data/finance.json'

/** THE FINANCES, PER OWNER. TJ, 17 September 2026: "I want a report about school
 *  finances ... specifically that lists all the funds related to the school, some
 *  conclusions, the current balances, the trends over time, explanations of what each
 *  one is for ... Every board should have a 'Finance' tab ... we'll need a /departments
 *  page ... take every fund and account we know of, break it down into which 'department'
 *  owns them ... leaving none out from being listed somewhere ... all accounting measures
 *  should be trackable, and trendable."
 *
 *  One payload (scripts/build_finance.py, from the registry sources/data/fund-owners.csv
 *  that scripts/build_fund_owners.py keeps complete) and four doors onto it: the School
 *  Committee's page, which is a report with conclusions; every other board's
 *  /boards/<slug>/finance; /departments/<slug> for what the Town Manager runs; and
 *  /accounts, every measure once, including the ones nobody's page claims.
 *
 *  Three grades of figure, kept apart on the page (rule 13a): EVIDENCE is the accounting
 *  system's own FY26 printouts; READ is the annual reports' schedule FY2011-FY2023, read
 *  off the page and tied to its printed totals; TRANSCRIBED is OCR of the FY2023-FY2025
 *  balance tables, chained to the FY26 opening balance where it chains and flagged where
 *  it does not. Nothing here reconciles them. */
type Snap = { fy: number; period: number; original: number; revised: number; expended: number; encumbered: number; available: number; report: string; summed?: number }
type Current = Partial<Snap> & { grade: 'evidence' | 'transcribed'; as_of?: string; opening?: number; revenue?: number; spent?: number; salaries?: number; closing?: number; foots?: boolean
  estimate?: number; collected?: number; expense_budget?: number; revenue_estimate?: number; report?: string; reports?: string[] }
type Hist = { fy: number; grade: 'read' | 'transcribed'; opening?: number | null; revenue?: number | null; spent?: number | null; closing?: number | null; chains?: boolean; report: string }
type Measure = { id: string; kind: string; subkind: string; code: string; name: string; owner: string; owner_basis: string; relates_to: string
  purpose: string; authority: string; trend_label: string; report: string; current: Current | null; history: Hist[]; notes: string[]; snapshots?: Snap[]
  // DESE's own name for a school grant fund, from the allocation pages (dese-fund-codes.csv) --
  // the town's ledger name (`FY25 #240`) stays beside it, because that is what a resident asks for.
  dese?: { fund_code: string; name: string; fy: string; source_url: string; display: string } }
type Owner = { slug: string; name: string; kind: string; owns: string[]; relates: string[]; counts: Record<string, number>
  totals: { appropriation_revised: number | null; appropriation_spent: number | null; appropriation_period: number | null; special_revenue_held: number | null
    special_revenue_in: number | null; special_revenue_out: number | null; trust_held: number | null; agency_held: number | null; revenue_estimate: number | null }
  // WHO WORKS THERE, and the address of the chart that names them -- from
  // `body-crosswalk.csv`, which `build_org_charts.py` reads for the link the other way.
  // A LIST because one money page can have two charts behind it: the School Committee owns
  // the district's accounts, and this project draws both the committee's seats and the
  // district's staff against them.
  people?: { unit: string; chart_url: string; fy: string; named: number; years: number; basis: string }[] }
type Dept = { slug: string; name: string; kind: string; dept_codes: string; board: string; head: string }
type Payload = { about: string; grain: string; as_of: { ledger: string; special_revenue: string; trusts: string }; kinds: Record<string, string>
  measures: Record<string, Measure>; owners: Record<string, Owner>; departments: Dept[]; unresolved: string[]
  gaps: { side: string; what: string; why: string }[]; conclusions: Conclusion[]; conclusions_by_owner: Record<string, Conclusion[]> }

const KIND_ORDER = ['appropriation', 'debt', 'special-revenue', 'enterprise', 'trust', 'stabilization', 'agency', 'capital', 'revenue']
const KIND_TITLE: Record<string, string> = {
  appropriation: 'What Town Meeting votes for it', debt: 'Debt service', 'special-revenue': 'Its own funds — revolving, grants, gifts',
  enterprise: 'Enterprise funds', trust: 'Trusts', stabilization: 'Stabilization funds', agency: 'Held for somebody else', capital: 'Capital project funds', revenue: 'Revenue it raises',
}
const n0 = (n: number) => n.toLocaleString('en-US')
const money = (n: number | null | undefined) => (n === null || n === undefined ? '—' : n < 0 ? `(${usd(-n)})` : usd(n))
const short = (n: number) => Math.abs(n) >= 1e6 ? `$${(n / 1e6).toFixed(2)}M` : Math.abs(n) >= 1e3 ? `$${Math.round(n / 1e3)}k` : usd(n)
const title = (s: string) => s.replace(/\s+/g, ' ').trim().toLowerCase().replace(/(^|[\s(/-])([a-z])/g, (_m, p, c) => p + c.toUpperCase())
  .replace(/\bFy(\d)/g, 'FY$1').replace(/\bCoa\b/g, 'COA').replace(/\bDpw\b/g, 'DPW').replace(/\bIt\b/g, 'IT').replace(/\bPeg\b/g, 'PEG').replace(/\bMart\b/g, 'MART').replace(/\bOpeb\b/g, 'OPEB')
// A grant fund reads by DESE's name; everything else by the ledger's, re-cased.
const label = (m: Measure) => m.dese ? m.dese.display : title(m.name)
const ledgerName = (m: Measure) => m.name.replace(/\s+/g, ' ').trim()
// Where there is no second line to carry it, the ledger's name rides along in the label.
const labelInline = (m: Measure) => m.dese ? `${m.dese.display} — the ledger’s “${ledgerName(m)}”` : title(m.name)
const ownerHref = (d: Payload, slug: string) => {
  const o = d.owners[slug]
  if (!o) return '/accounts'
  if (o.kind === 'board') return slug === 'school-committee' ? '/boards/school-committee/finance' : `/boards/${slug}/finance`
  return `/departments/${slug}`
}
const gradeTone = (g: string) => g === 'evidence' ? 'var(--status-good)' : g === 'read' ? 'var(--text-primary)' : 'var(--status-warn, #b45309)'

/* ---- the four doors ------------------------------------------------------------- */

export function SchoolFinance() {
  const { d, err } = useReport<Payload>('finance.json')
  return (
    <ReportShell tab={TAB} title="The School Committee’s finances"
      standfirst={d ? <Standfirst d={d} slug="school-committee" /> : undefined}
      err={err} loading={!d && !err} dataUrl={DATA}>
      <BoardNav slug="school-committee" current="finance" />
      {d && <OwnerPage d={d} slug="school-committee" conclusions={d.conclusions} />}
    </ReportShell>
  )
}

export function BoardFinance() {
  const BTAB: Tab = 'boards'
  const slug = boardFinanceSlugFromPath(window.location.pathname) ?? ''
  const { d, err } = useReport<Payload>('finance.json')
  const o = d?.owners[slug]
  return (
    <ReportShell tab={BTAB} title={o ? `${o.name} — finances` : 'A board’s finances'}
      standfirst={d && o ? <Standfirst d={d} slug={slug} /> : d ? <>No account in any report we hold is owned by this board. <a className="underline" href="/accounts">Every account, once</a> lists who owns what.</> : undefined}
      err={err} loading={!d && !err} dataUrl={DATA}>
      <BoardNav slug={slug} current="finance" />
      {d && o && <OwnerPage d={d} slug={slug} />}
    </ReportShell>
  )
}

export function Departments() {
  const DTAB: Tab = 'departments'
  const slug = departmentSlugFromPath(window.location.pathname)
  const { d, err } = useReport<Payload>('finance.json')
  if (slug) {
    const o = d?.owners[slug]
    return (
      <ReportShell tab={DTAB} title={o ? o.name : 'A department'}
        standfirst={d && o ? <Standfirst d={d} slug={slug} /> : undefined}
        err={err} loading={!d && !err} dataUrl={DATA}>
        {d && o && <OwnerPage d={d} slug={slug} />}
        {d && !o && <p className="mt-6 text-sm">No department by that name. <a className="underline" href="/departments">The departments</a>.</p>}
      </ReportShell>
    )
  }
  return (
    <ReportShell tab={DTAB} title="The departments"
      standfirst={d ? <>What the Town Manager runs, and what each department is voted, holds and raises &mdash; FY{2026} as the accounting system printed it. Boards that run a department (the schools, the library, the parks) are on <a className="underline" href="/boards">their own pages</a>; every account in one list is at <a className="underline" href="/accounts">/accounts</a>.</> : undefined}
      err={err} loading={!d && !err} dataUrl={DATA}>
      {d && <DeptIndex d={d} />}
    </ReportShell>
  )
}

export function Accounts() {
  const ATAB: Tab = 'accounts'
  const { d, err } = useReport<Payload>('finance.json')
  const n = d ? Object.keys(d.measures).length : 0
  return (
    <ReportShell tab={ATAB} title="Every account, once"
      standfirst={d ? <>{n0(n)} accounting measures the town&rsquo;s reports print &mdash; department lines, revenue estimates, funds, trusts, capital accounts &mdash; each listed once, under the board or department that owns it. {d.unresolved.length ? <>{d.unresolved.length} have no owner yet and are listed at the end.</> : null}</> : undefined}
      err={err} loading={!d && !err} dataUrl={DATA}>
      {d && <AccountsIndex d={d} />}
    </ReportShell>
  )
}

/* ---- one owner's page ----------------------------------------------------------- */

function Standfirst({ d, slug }: { d: Payload; slug: string }) {
  const o = d.owners[slug]; const t = o.totals
  const parts: React.ReactNode[] = []
  if (t.appropriation_revised !== null) parts.push(<>voted {short(t.appropriation_revised)} for FY2026{t.appropriation_period === 12 ? ' and spent ' + short(t.appropriation_spent ?? 0) + ' of it through June (period 12), counting what was still owed' : ''}</>)
  if (t.special_revenue_held !== null) parts.push(<>holds {short(t.special_revenue_held)} in {o.counts['special-revenue']} funds outside the budget</>)
  if (t.trust_held !== null) parts.push(<>{short(t.trust_held)} in {(o.counts.trust ?? 0) + (o.counts.stabilization ?? 0)} trust and stabilization funds</>)
  if (t.revenue_estimate !== null && o.counts.revenue) parts.push(<>raises an estimated {short(t.revenue_estimate)} in {o.counts.revenue} revenue lines</>)
  return <>The {o.name} {parts.length ? <>{parts.map((p, i) => <span key={i}>{i ? (i === parts.length - 1 ? ', and ' : ', ') : ''}{p}</span>)}.</> : <>owns {o.owns.length} accounts.</>} <a className="underline" href="#accounts">{o.owns.length} accounts in all</a>, each with what it is for and what it has done.{slug !== 'school-committee' ? <> <a className="underline" href="/accounts">Every account, once</a>.</> : null}</>
}

function OwnerPage({ d, slug, conclusions }: { d: Payload; slug: string; conclusions?: Conclusion[] }) {
  const o = d.owners[slug]; const t = o.totals
  const owns = o.owns.map(i => d.measures[i])
  const byKind = KIND_ORDER.map(k => [k, owns.filter(m => m.kind === k)] as const).filter(([, ms]) => ms.length)
  const related = o.relates.map(i => d.measures[i])
  const [top, rest] = splitConclusions(conclusions)
  const isBoard = o.kind === 'board'
  const tab = useFinanceTab()
  const nAccounts = owns.length
  return (
    <>
      <FinanceTabs tab={tab} nAccounts={nAccounts} />
      <div hidden={tab !== 'overview'} role="tabpanel" id="panel-overview" aria-labelledby="tab-overview">
      <Grain>{d.grain}</Grain>
      {isBoard && <p className="text-[13px] mt-3"><a className="underline" href={`/boards/${slug}`}>&larr; the {o.name}&rsquo;s board page</a> · <a className="underline" href="/accounts">every account, once</a></p>}
      {/* JOB POSTINGS this body owns, if any -- the same block the board pages carry. */}
      <JobsLink slug={slug} />
      {/* THE PEOPLE BEHIND THE MONEY. TJ, 25 September 2026: *"i would like to cross link the
          org chart and the personell pages for each department, so we can see the trends over
          time when needed, or directly se the people when needed."*
          The count and the YEAR travel together on purpose: the rosters run to FY2025 for
          most bodies and FY2027 for the ones read off the officials listing, so a headcount
          with no year attached would read as a claim about today. And it is NAMES the town
          printed, not full-time equivalents -- a roster carries no FTE, which is why this
          links to the chart rather than reprinting a figure as though it were a staffing
          level. */}
      {o.people?.length ? (
        <p className="text-[13px] mt-3">
          {/* "Org chart" FIRST, as the words a reader looks for -- TJ could not find this line
              when it opened with a headcount. */}
          <strong>Org chart:</strong>{' '}
          {o.people.map((p, i) => (
            <span key={p.unit}>
              {i > 0 ? ' · ' : ''}
              <a className="underline" href={p.chart_url}>
                the {p.named} people named in {p.unit} in FY{p.fy}
              </a>
            </span>
          ))}
          {' '}&mdash; names the town printed, across {o.people[0].years} years of charts; no FTE.
        </p>
      ) : null}
      <div className="mt-8 flex flex-wrap gap-x-12 gap-y-6">
        {t.appropriation_revised !== null && <Stat value={short(t.appropriation_revised)}>voted for FY2026 across {(o.counts.appropriation ?? 0) + (o.counts.debt ?? 0)} line{(o.counts.appropriation ?? 0) + (o.counts.debt ?? 0) === 1 ? '' : 's'}, as revised{t.appropriation_period === 12 ? '; ' + short(t.appropriation_spent ?? 0) + ' spent or still owed through June (period 12)' : ''}</Stat>}
        {t.special_revenue_held !== null && <Stat value={short(t.special_revenue_held)} tone="var(--series-revenue)">held in {o.counts['special-revenue']} funds outside the budget at {d.as_of.special_revenue}</Stat>}
        {t.special_revenue_in !== null && <Stat value={short(t.special_revenue_in)}>into those funds in nine months of FY2026; {short(t.special_revenue_out ?? 0)} out</Stat>}
        {t.trust_held !== null && <Stat value={short(t.trust_held)}>in {(o.counts.trust ?? 0) + (o.counts.stabilization ?? 0)} trust and stabilization funds at {d.as_of.trusts}</Stat>}
        {t.revenue_estimate !== null && (o.counts.revenue ?? 0) > 0 && <Stat value={short(t.revenue_estimate)}>estimated FY2026 revenue across {o.counts.revenue} lines it raises</Stat>}
      </div>

      {conclusions && conclusions.length > 0 && (
        <>
          <H2 id="conclusions">If you read nothing else</H2>
          <Conclusions rows={top} reportUrl={DATA} />
          {rest.length > 0 && <Conclusions rows={rest} reportUrl={DATA} noAsk short={false} />}
        </>
      )}

      <p className="text-[14px] mt-8"><a className="underline font-semibold" href="#accounts"
        style={{ color: 'var(--series-cost)' }}>Every account, with its history &rarr;</a></p>
      </div>
      <div hidden={tab !== 'accounts'} role="tabpanel" id="panel-accounts" aria-labelledby="tab-accounts">
        {byKind.map(([k, ms]) => (
          <section key={k}>
            <H2 id={k}>{KIND_TITLE[k]}</H2>
            <Body>{d.kinds[k]}. {ms.length} {ms.length === 1 ? 'line' : 'lines'}.</Body>
            {k === 'appropriation' || k === 'debt' ? <ApproTable ms={ms} /> :
             k === 'revenue' ? <RevenueTable ms={ms} /> :
             k === 'enterprise' ? <EnterpriseTable ms={ms} /> :
             <FundTable ms={ms} />}
          </section>
        ))}
        {related.length > 0 && (
          <section>
            <H2 id="related">Money on other pages that is also the {o.name}&rsquo;s</H2>
            <Body>Owned elsewhere in the ledger, spent on or received for this body.</Body>
            <ul className="mt-3 space-y-1.5 text-sm">
              {related.map(m => <li key={m.id}><span className="tnum" style={{ color: 'var(--text-muted)' }}>{m.code}</span> {labelInline(m)}{m.purpose ? <span style={{ color: 'var(--text-secondary)' }}> — {m.purpose}</span> : null} · <a className="underline" href={ownerHref(d, m.owner)}>{d.owners[m.owner]?.name ?? m.owner}</a>{m.current && m.kind === 'appropriation' ? <span className="tnum" style={{ color: 'var(--text-secondary)' }}> · {money(m.current.revised)} voted</span> : m.current && m.kind === 'revenue' ? <span className="tnum" style={{ color: 'var(--text-secondary)' }}> · {money(m.current.estimate)} estimated</span> : m.current && m.current.closing !== undefined ? <span className="tnum" style={{ color: 'var(--text-secondary)' }}> · {money(m.current.closing)} held</span> : null}</li>)}
            </ul>
          </section>
        )}
        <Legend d={d} />
        <H2 id="gaps">What this page cannot say</H2>
        <NotEstablished rows={[
          'What any fund balance is committed to. The reports are balances, not obligations.',
          'FY2024 and FY2025 activity for every fund: the annual reports print year-end balances only, and two of them do not chain to the FY26 opening balance (flagged in the tables).',
          'A trend for the appropriation lines. The annual reports print them, but the extract cannot yet say which printed column is which for most years (rule 13), so none is shown until it can.',
          ...d.gaps.map(g => g.what),
        ]} closes="The FY2025 special-revenue and trust reports, and the year-to-date budget reports for FY2023–FY2025, from the Town Accountant — the same printouts the FY26 ones are." />
      </div>
    </>
  )
}

/* ---- the two tabs ----------------------------------------------------------------
 * ACCOUNTS IS A TAB WITH AN ADDRESS. TJ, 14 October 2026: "i need the 'funds/accounts' to
 * be a tab in the /finance page for the boards. its buried in an expansion section and i
 * cant share that with people directly." The accounts sat behind the "full version" fold,
 * which has no address of its own, so a link could only ever land on the overview.
 * `#accounts` now opens the Accounts tab, so /boards/<slug>/finance#accounts is a link a
 * person can send. BOTH panels stay in the DOM and one is `hidden`, so the prerendered
 * page and the search index still carry every account. */
type FinanceTab = 'overview' | 'accounts'   // 'overview' is labelled Summary: the board's own tab row already has an Overview
const tabFromHash = (): FinanceTab => (window.location.hash === '#accounts' || window.location.hash.startsWith(ACCT) ? 'accounts' : 'overview')

function useFinanceTab(): FinanceTab {
  const [tab, setTab] = useState<FinanceTab>(tabFromHash)
  useEffect(() => {
    const on = () => setTab(tabFromHash())
    window.addEventListener('hashchange', on)
    return () => window.removeEventListener('hashchange', on)
  }, [])
  return tab
}

function FinanceTabs({ tab, nAccounts }: { tab: FinanceTab; nAccounts: number }) {
  const item = (id: FinanceTab, label: string) => {
    const on = tab === id
    return (
      <a role="tab" id={`tab-${id}`} aria-selected={on} aria-controls={`panel-${id}`}
        href={id === 'accounts' ? '#accounts' : '#overview'}
        onClick={e => {
          // Overview drops the hash rather than leaving "#overview" on a shared link.
          if (id === 'overview') { e.preventDefault(); history.pushState(null, '', window.location.pathname + window.location.search); window.dispatchEvent(new HashChangeEvent('hashchange')) }
        }}
        className="px-1 pb-2 -mb-px text-[15px] font-semibold border-b-2 no-underline"
        style={on ? { borderColor: 'var(--series-cost)', color: 'var(--text-primary)' }
                  : { borderColor: 'transparent', color: 'var(--text-muted)' }}>{label}</a>
    )
  }
  return (
    <div role="tablist" aria-label="Finances" className="mt-6 flex gap-6 border-b" style={{ borderColor: 'var(--grid)' }}>
      {item('overview', 'Summary')}
      {item('accounts', `Accounts (${nAccounts})`)}
    </div>
  )
}

/* ---- the tables ----------------------------------------------------------------- */

const th = 'text-[10px] font-bold uppercase tracking-widest'
const Th = ({ children, right }: { children: React.ReactNode; right?: boolean }) => <th className={`${th} py-1.5 pr-3 ${right ? 'text-right' : 'text-left'}`} style={{ color: 'var(--text-muted)' }}>{children}</th>
const Td = ({ children, right, tone }: { children: React.ReactNode; right?: boolean; tone?: string }) => <td className={`py-1.5 pr-3 align-top ${right ? 'text-right tnum whitespace-nowrap' : ''}`} style={tone ? { color: tone } : undefined}>{children}</td>

/* ---- the drill-in: every account row opens its history --------------------------
 * TJ, 22 October 2026: "finances section for boards should have each fund be clickable, to
 * drill-in to the history." ONE drill-in, used by every table on all three doors (the board
 * pages, /departments/<slug>, and /accounts through the owner pages it links to) -- rule 7d's
 * one renderer, many payloads.
 *
 * AN OPEN ACCOUNT HAS AN ADDRESS: `#acct-<id>` opens the Accounts tab with that row open and
 * scrolled to, so a single fund's history is a link a person can send. /accounts links every
 * account it lists to that address on its owner's page. No new route and no new payload: the
 * history is already in finance.json (`history`, `snapshots`, `current`). */
const ACCT = '#acct-'
const openFromHash = () => (window.location.hash.startsWith(ACCT) ? decodeURIComponent(window.location.hash.slice(ACCT.length)) : null)

function useOpenAccount(): [string | null, (id: string) => void] {
  const [open, setOpen] = useState<string | null>(openFromHash)
  useEffect(() => {
    const on = () => setOpen(openFromHash())
    window.addEventListener('hashchange', on)
    return () => window.removeEventListener('hashchange', on)
  }, [])
  const toggle = (id: string) => {
    const next = openFromHash() === id ? '#accounts' : ACCT + encodeURIComponent(id)
    history.replaceState(null, '', window.location.pathname + window.location.search + next)
    window.dispatchEvent(new HashChangeEvent('hashchange'))
  }
  return [open, toggle]
}
const acctHref = (d: Payload, m: Measure) => `${ownerHref(d, m.owner)}${ACCT}${encodeURIComponent(m.id)}`

/** The account's name, as the control that opens its history. Sub-lines stay outside the
 *  button: one of them is a link, and a link inside a button is not a link. */
function NameToggle({ m, open, onToggle }: { m: Measure; open: boolean; onToggle: () => void }) {
  return (
    <>
      <button type="button" onClick={onToggle} aria-expanded={open} aria-controls={`hist-${m.id}`}
        className="text-left font-semibold underline decoration-dotted underline-offset-2">
        <span aria-hidden="true" className="inline-block w-3 text-[10px]" style={{ color: 'var(--text-muted)' }}>{open ? '\u25BE' : '\u25B8'}</span>{label(m)}
      </button>
      {m.dese && <span className="block text-[11.5px]" style={{ color: 'var(--text-muted)' }}>the town’s ledger calls it “{ledgerName(m)}” · <a className="underline" href={m.dese.source_url}>DESE allocation page</a></span>}
      {(m.purpose || m.authority) && <span className="block text-[11.5px]" style={{ color: 'var(--text-muted)' }}>{m.purpose}{m.purpose && m.authority ? ' · ' : ''}{m.authority}</span>}
    </>
  )
}

/** One table row and, when open, the row beneath it holding the account's history. */
function DrillRow({ m, open, onToggle, cols, children }: { m: Measure; open: boolean; onToggle: () => void; cols: number; children: (name: React.ReactNode) => React.ReactNode }) {
  const ref = useRef<HTMLTableRowElement>(null)
  // Arriving on `#acct-<id>`: bring the open row into view once the table has drawn.
  useEffect(() => { if (open && openFromHash() === m.id) ref.current?.scrollIntoView({ block: 'start' }) }, [open, m.id])
  return (
    <>
      <tr ref={ref} id={`acct-${m.id}`} style={{ borderTop: '1px solid var(--grid)', scrollMarginTop: 80 }}>
        {children(<NameToggle m={m} open={open} onToggle={onToggle} />)}
      </tr>
      {open && <tr><td colSpan={cols} className="pb-3" id={`hist-${m.id}`}><AccountHistory m={m} /></td></tr>}
    </>
  )
}

function ApproTable({ ms }: { ms: Measure[] }) {
  const [openId, toggle] = useOpenAccount()
  return (
    <div className="overflow-x-auto mt-4">
      <table className="text-sm" style={{ minWidth: 760 }}>
        <thead><tr><Th>code</Th><Th>line</Th><Th right>voted</Th><Th right>revised</Th><Th right>paid</Th><Th right>encumbered</Th><Th right>left</Th><Th right>as of</Th></tr></thead>
        <tbody>{ms.map(m => { const c = m.current; return (
          <DrillRow key={m.id} m={m} open={openId === m.id} onToggle={() => toggle(m.id)} cols={8}>{name => <>
            <Td tone="var(--text-muted)">{m.code}</Td><Td>{name}</Td>
            <Td right>{money(c?.original)}</Td><Td right>{money(c?.revised)}</Td><Td right>{money(c?.expended)}</Td><Td right>{money(c?.encumbered)}</Td>
            <Td right tone={(c?.available ?? 0) < 0 ? 'var(--status-critical)' : undefined}>{money(c?.available)}</Td>
            <Td right tone="var(--text-muted)">{c ? `FY${String(c.fy).slice(2)} p${c.period}` : '—'}</Td>
          </>}</DrillRow>) })}</tbody>
      </table>
      <p className="text-[12px] mt-2" style={{ color: 'var(--text-muted)' }}>The FY26 year-to-date budget reports (evidence). Period 12 runs through June, unaudited, summed from the line&rsquo;s accounts; period 9 is 31 March. A line is net of whatever else pays for the thing &mdash; rule 11. Click a line for every figure held for it.</p>
    </div>
  )
}

function RevenueTable({ ms }: { ms: Measure[] }) {
  const [openId, toggle] = useOpenAccount()
  return (
    <div className="overflow-x-auto mt-4">
      <table className="text-sm" style={{ minWidth: 560 }}>
        <thead><tr><Th>object</Th><Th>line</Th><Th>kind</Th><Th right>estimated</Th><Th right>collected by March</Th></tr></thead>
        <tbody>{ms.map(m => { const c = m.current; return (
          <DrillRow key={m.id} m={m} open={openId === m.id} onToggle={() => toggle(m.id)} cols={5}>{name => <>
            <Td tone="var(--text-muted)">{m.code}</Td><Td>{name}</Td><Td tone="var(--text-muted)">{m.subkind}</Td>
            <Td right>{money(c?.estimate)}</Td><Td right>{money(c?.collected)}</Td>
          </>}</DrillRow>) })}</tbody>
      </table>
      <p className="text-[12px] mt-2" style={{ color: 'var(--text-muted)' }}>The FY26 revenue report, period 9 (evidence). Lines estimated at zero are kept: a code the town carries is a thing it can receive.</p>
    </div>
  )
}

function EnterpriseTable({ ms }: { ms: Measure[] }) {
  const [openId, toggle] = useOpenAccount()
  return (
    <div className="overflow-x-auto mt-4">
      <table className="text-sm" style={{ minWidth: 640 }}>
        <thead><tr><Th>fund</Th><Th>name</Th><Th right>expense budget</Th><Th right>spent or owed</Th><Th right>revenue estimate</Th><Th right>collected</Th></tr></thead>
        <tbody>{ms.map(m => { const c = m.current; return (
          <DrillRow key={m.id} m={m} open={openId === m.id} onToggle={() => toggle(m.id)} cols={6}>{name => <>
            <Td tone="var(--text-muted)">{m.code}</Td><Td>{name}</Td>
            <Td right>{money(c?.expense_budget)}</Td><Td right>{money(c?.spent)}</Td><Td right>{money(c?.revenue_estimate)}</Td><Td right>{money(c?.collected)}</Td>
          </>}</DrillRow>) })}</tbody>
      </table>
      <p className="text-[12px] mt-2" style={{ color: 'var(--text-muted)' }}>The FY26 enterprise-fund reports, period 9 (evidence), summed from their accounts.</p>
    </div>
  )
}

function FundTable({ ms }: { ms: Measure[] }) {
  const [openId, toggle] = useOpenAccount()
  const anyHist = ms.some(m => m.history.length)
  const cols = anyHist ? 7 : 6
  return (
    <div className="overflow-x-auto mt-4">
      <table className="text-sm" style={{ minWidth: anyHist ? 820 : 640 }}>
        <thead><tr><Th>fund</Th><Th>name</Th><Th right>opening</Th><Th right>in</Th><Th right>out</Th><Th right>held</Th>{anyHist && <Th>held, by year</Th>}</tr></thead>
        <tbody>{ms.map(m => { const c = m.current; const open = openId === m.id; return (
          <DrillRow key={m.id} m={m} open={open} onToggle={() => toggle(m.id)} cols={cols}>{name => <>
              <Td tone="var(--text-muted)">{m.code}{m.subkind && m.subkind !== 'other' && <span className="block text-[10px]">{m.subkind}</span>}</Td>
              <Td>{name}</Td>
              <Td right>{money(c?.opening)}</Td><Td right>{money(c?.revenue)}</Td><Td right>{money(c?.spent)}</Td>
              <Td right tone={(c?.closing ?? 0) < -0.005 ? 'var(--status-critical)' : undefined}><strong>{money(c?.closing)}</strong>{c && c.grade === 'transcribed' && <span className="block text-[10px] font-normal" style={{ color: gradeTone('transcribed') }}>transcribed, FY{c.fy}</span>}{c && c.foots === false && <span className="block text-[10px] font-normal" style={{ color: 'var(--status-critical)' }}>row does not foot</span>}</Td>
              {anyHist && <Td>{m.history.length ? <button type="button" className="underline text-[12px]" onClick={() => toggle(m.id)} aria-expanded={open}><Spark m={m} /> {open ? 'hide' : `${m.history.length + (c ? 1 : 0)} years`}</button> : <span className="text-[11px]" style={{ color: 'var(--text-muted)' }}>FY26 only</span>}</Td>}
          </>}</DrillRow>) })}</tbody>
      </table>
      <p className="text-[12px] mt-2" style={{ color: 'var(--text-muted)' }}>Opening, in, out and held from the FY26 fund reports as of 31 March 2026 (evidence), read by the identity opening + in − out = held, which every row here satisfies unless flagged. A balance in parentheses is overdrawn. Click a fund for its history.</p>
    </div>
  )
}

function Spark({ m }: { m: Measure }) {
  const pts = [...m.history.filter(h => h.closing !== null && h.closing !== undefined).map(h => ({ fy: h.fy, v: h.closing as number, g: h.grade })),
    ...(m.current && m.current.closing !== undefined ? [{ fy: m.current.fy as number, v: m.current.closing, g: m.current.grade }] : [])].sort((a, b) => a.fy - b.fy)
  if (pts.length < 2) return null
  const w = 96, h = 22
  const min = Math.min(0, ...pts.map(p => p.v)), max = Math.max(0, ...pts.map(p => p.v))
  const x = (fy: number) => ((fy - pts[0].fy) / Math.max(1, pts[pts.length - 1].fy - pts[0].fy)) * (w - 4) + 2
  const y = (v: number) => max === min ? h / 2 : h - 2 - ((v - min) / (max - min)) * (h - 4)
  return (
    <svg width={w} height={h} className="inline-block align-middle mr-1" aria-hidden="true">
      <line x1={0} x2={w} y1={y(0)} y2={y(0)} stroke="var(--grid)" strokeWidth={1} />
      <polyline fill="none" stroke="var(--text-secondary)" strokeWidth={1.25} points={pts.map(p => `${x(p.fy)},${y(p.v)}`).join(' ')} />
      {pts.map(p => <circle key={p.fy} cx={x(p.fy)} cy={y(p.v)} r={1.8} fill={gradeTone(p.g)} />)}
    </svg>
  )
}

/* ---- one account's history -------------------------------------------------------
 * EVERY YEAR HELD, EACH FIGURE WITH ITS GRADE, AND THE YEARS NOT HELD SHOWN AS GAPS. The span
 * runs from the first year any report gives a figure to FY2026; a year inside it with no row
 * is drawn and listed as a gap, never bridged (the three grades are never averaged or joined
 * into one line, rule 13a). FY2024 and FY2025 are the case that matters: the annual reports
 * print a year-end balance and nothing else, so what came in and went out is NOT PRINTED --
 * a records request, not a zero. */
type HRow = { fy: number; grade: string; opening?: number | null; revenue?: number | null; spent?: number | null; closing?: number | null; chains?: boolean; report?: string; gap?: boolean; period?: number }
const FUND_KINDS = ['special-revenue', 'trust', 'stabilization', 'agency', 'capital']
const LAST_FY = 2026
const BALANCE_ONLY = [2024, 2025]   // the annual reports' balance tables: closing balance only

function fundRows(m: Measure): HRow[] {
  const held: HRow[] = [...m.history.map(h => ({ ...h })),
    ...(m.current && m.current.fy !== undefined ? [{ fy: m.current.fy, grade: m.current.grade, opening: m.current.opening, revenue: m.current.revenue, spent: m.current.spent, closing: m.current.closing, report: m.current.report ?? '' }] : [])]
  if (!held.length) return []
  const first = Math.min(...held.map(r => r.fy))
  const out: HRow[] = []
  for (let fy = first; fy <= LAST_FY; fy++) {
    const rs = held.filter(r => r.fy === fy)
    out.push(...(rs.length ? rs : [{ fy, grade: 'gap', gap: true }]))
  }
  return out
}

const docHref = (report?: string) => !report ? undefined : report.startsWith('sources/') ? '/docs/' + report.slice('sources/'.length) : undefined
const NotPrinted = () => <span className="italic text-[11px]" style={{ color: 'var(--text-muted)' }}>not printed</span>

function AccountHistory({ m }: { m: Measure }) {
  const isFund = FUND_KINDS.includes(m.kind)
  const rows = isFund ? fundRows(m) : []
  const gaps = rows.filter(r => r.gap).length
  const balanceOnly = rows.some(r => !r.gap && BALANCE_ONLY.includes(r.fy) && r.grade === 'transcribed')
  return (
    // STICKY TO THE LEFT, AS WIDE AS THE SCREEN: the card sits in a table that scrolls
    // sideways on a phone, and a history card as wide as that table runs its notes off-screen.
    <div className="card p-3 mt-1 text-[12.5px]" style={{ position: 'sticky', left: 0, maxWidth: 'min(100%, calc(100vw - 32px))' }}>
      <p className="text-[11px] font-semibold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>{labelInline(m)}, year by year{m.trend_label ? ` — the annual reports call it “${m.trend_label}”` : ''}</p>
      {isFund && rows.length > 0 && <>
        {rows.filter(r => !r.gap && r.closing !== null && r.closing !== undefined).length >= 3 && <HistoryChart rows={rows} />}
        <div className="overflow-x-auto">
        <table className="mt-2">
          <thead><tr><Th>year</Th><Th right>opening</Th><Th right>in</Th><Th right>out</Th><Th right>held at year end</Th><Th>grade</Th><Th>source</Th></tr></thead>
          <tbody>{rows.map(r => r.gap ? (
            <tr key={r.fy + 'gap'} style={{ borderTop: '1px solid var(--grid)' }}>
              <Td>FY{r.fy}</Td><td colSpan={4} className="py-1.5 pr-3 italic text-[11.5px]" style={{ color: 'var(--text-muted)' }}>no figure held for this year</td><Td tone="var(--text-muted)">gap</Td><Td>{''}</Td>
            </tr>) : (
            <tr key={r.fy + r.grade} style={{ borderTop: '1px solid var(--grid)' }}>
              <Td>FY{r.fy}{r.fy === LAST_FY && r.grade === 'evidence' ? ' (to March)' : ''}</Td>
              {BALANCE_ONLY.includes(r.fy) && r.grade === 'transcribed'
                ? <><Td right><NotPrinted /></Td><Td right><NotPrinted /></Td><Td right><NotPrinted /></Td></>
                : <><Td right>{money(r.opening)}</Td><Td right>{money(r.revenue)}</Td><Td right>{money(r.spent)}</Td></>}
              <Td right><strong>{money(r.closing)}</strong></Td>
              <Td tone={gradeTone(r.grade)}>{r.grade}{r.chains === false ? <span style={{ color: 'var(--status-critical)' }}> · does not chain to the FY26 opening balance</span> : r.chains === true ? ' · chains to FY26' : ''}</Td>
              <Td>{docHref(r.report) ? <a className="underline text-[11.5px]" href={docHref(r.report)}>the report</a> : null}</Td>
            </tr>))}</tbody>
        </table>
        </div>
        <p className="text-[11.5px] mt-2" style={{ color: 'var(--text-muted)' }}>
          {balanceOnly ? <>FY2024 and FY2025: the annual reports print the year-end balance only, so what came in and went out those years is not printed &mdash; a gap, <a className="underline" href="/what-we-cannot-answer">registered</a>; the town&rsquo;s FY2024 and FY2025 special-revenue and trust reports would close it. </> : null}
          {gaps ? <>{gaps} year{gaps === 1 ? '' : 's'} in the span ha{gaps === 1 ? 's' : 've'} no figure in any report we hold, and {gaps === 1 ? 'is' : 'are'} shown as {gaps === 1 ? 'a gap' : 'gaps'}, not joined across. </> : null}
          A dash is a column that report left blank. The grades are never mixed: see the key below the tables.
        </p>
      </>}
      {isFund && rows.length === 0 && <p className="mt-2">No figure for this fund in any report we hold.</p>}
      {!isFund && <LineHistory m={m} />}
    </div>
  )
}

/** A general-fund line, revenue estimate or enterprise fund: what is held is FY2026. */
function LineHistory({ m }: { m: Measure }) {
  const snaps = m.snapshots ?? []
  const c = m.current
  return (
    <>
      {snaps.length > 0 && (
        <div className="overflow-x-auto">
        <table className="mt-2">
          <thead><tr><Th>report</Th><Th right>voted</Th><Th right>revised</Th><Th right>paid</Th><Th right>encumbered</Th><Th right>left</Th><Th>grade</Th></tr></thead>
          <tbody>{snaps.map(s => (
            <tr key={s.period} style={{ borderTop: '1px solid var(--grid)' }}>
              <Td>FY{s.fy}, period {s.period}{s.period === 12 ? ' (through June, unaudited)' : s.period === 9 ? ' (31 March)' : ''}</Td>
              <Td right>{money(s.original)}</Td><Td right>{money(s.revised)}</Td><Td right>{money(s.expended)}</Td><Td right>{money(s.encumbered)}</Td><Td right>{money(s.available)}</Td>
              <Td tone={gradeTone('evidence')}>evidence</Td>
            </tr>))}</tbody>
        </table>
        </div>
      )}
      {!snaps.length && c && <p className="mt-2">FY{c.fy}{c.period ? `, period ${c.period}` : ''}: {m.kind === 'revenue' ? <>estimated {money(c.estimate)}, collected {money(c.collected)}</> : m.kind === 'enterprise' ? <>expense budget {money(c.expense_budget)}, spent or owed {money(c.spent)}; revenue estimate {money(c.revenue_estimate)}, collected {money(c.collected)}</> : <>{money(c.revised)} revised</>} <span style={{ color: gradeTone(c.grade) }}>({c.grade})</span>.</p>}
      {!c && <p className="mt-2">No figure for this line in any report we hold.</p>}
      <p className="text-[11.5px] mt-2" style={{ color: 'var(--text-muted)' }}>
        {m.kind === 'appropriation' || m.kind === 'debt'
          ? <>FY2011&ndash;FY2025 are a gap here, not a zero: the annual reports print these lines, but which printed column is which is not yet established for most years (rule 13), so none is shown until it can be. The town&rsquo;s year-to-date budget reports for those years would close it.</>
          : <>Only FY2026 is held for this line; earlier years are a gap until the same report for those years is in hand.</>}
      </p>
    </>
  )
}

/** Held at year end, one slot per year: a bar where a figure is held, coloured by its grade,
 *  and an empty dashed slot where none is. A component drawn from the payload (rule 7f). */
function HistoryChart({ rows }: { rows: HRow[] }) {
  const years = Array.from(new Set(rows.map(r => r.fy))).sort((a, b) => a - b)
  // One figure per year for the bar: the evidence row if there is one, else the first held.
  const pick = (fy: number) => {
    const rs = rows.filter(r => r.fy === fy && !r.gap && r.closing !== null && r.closing !== undefined)
    return rs.find(r => r.grade === 'evidence') ?? rs[0]
  }
  const vals = years.map(pick)
  const nums = vals.filter(Boolean).map(r => r!.closing as number)
  const max = Math.max(0, ...nums), min = Math.min(0, ...nums)
  const W = 640, H = 150, top = 12, bottom = 22, left = 4
  const slot = (W - left) / years.length
  const y = (v: number) => max === min ? H - bottom : top + ((max - v) / (max - min)) * (H - top - bottom)
  return (
    <figure className="mt-3" style={{ maxWidth: W }}>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label={`Held at year end, FY${years[0]} to FY${years[years.length - 1]}`}>
        <line x1={0} x2={W} y1={y(0)} y2={y(0)} stroke="var(--grid)" />
        {years.map((fy, i) => {
          const r = vals[i]; const x = left + i * slot + slot * 0.15; const w = slot * 0.7
          if (!r) return (
            <g key={fy}>
              <rect x={x} y={top} width={w} height={H - top - bottom} fill="none" stroke="var(--text-muted)" strokeDasharray="3 3" strokeOpacity={0.6} />
              <title>FY{fy}: no figure held</title>
            </g>)
          const v = r.closing as number
          return (
            <g key={fy}>
              <rect x={x} y={Math.min(y(v), y(0))} width={w} height={Math.max(1, Math.abs(y(v) - y(0)))} fill={gradeTone(r.grade)} fillOpacity={r.grade === 'transcribed' ? 0.75 : 0.9} />
              <title>FY{fy}: {money(v)} ({r.grade})</title>
            </g>)
        })}
        {years.map((fy, i) => (i === 0 || i === years.length - 1 || fy % 5 === 0) && (
          <text key={'l' + fy} x={left + i * slot + slot / 2} y={H - 6} textAnchor="middle" fontSize={11} fill="var(--text-muted)">FY{String(fy).slice(2)}</text>))}
      </svg>
      <figcaption className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
        Held at year end{years.includes(LAST_FY) ? ' (FY26 at 31 March)' : ''}; highest {money(max)}{min < 0 ? `, lowest ${money(min)}` : ''}. Bars coloured by grade: <span style={{ color: gradeTone('evidence') }}>evidence</span>, <span style={{ color: gradeTone('read') }}>read</span>, <span style={{ color: gradeTone('transcribed') }}>transcribed</span>; a dashed slot is a year with no figure.
      </figcaption>
    </figure>
  )
}

function Legend({ d }: { d: Payload }) {
  return (
    <div className="card p-4 mt-8 max-w-3xl text-[13px]" style={{ color: 'var(--text-secondary)' }}>
      <p className="text-[11px] font-semibold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>Three grades of figure, never mixed</p>
      <p className="mt-1.5"><strong style={{ color: gradeTone('evidence') }}>evidence</strong> — the accounting system&rsquo;s own printouts: the FY26 budget reports ({d.as_of.ledger}), the special-revenue report as of {d.as_of.special_revenue}, the trust report as of {d.as_of.trusts}.</p>
      <p className="mt-1"><strong style={{ color: gradeTone('read') }}>read</strong> — the annual reports&rsquo; special-revenue schedule, FY2011&ndash;FY2023, read off the page and tied to the report&rsquo;s own printed totals on all four columns.</p>
      <p className="mt-1"><strong style={{ color: gradeTone('transcribed') }}>transcribed</strong> — OCR of the FY2023&ndash;FY2025 balance tables, columns read by position; checked against the FY26 opening balance where the years meet, and flagged where it does not chain. Rule 13: a reading is not the record.</p>
      <p className="mt-2">Who owns what is our reading of the town&rsquo;s books, and each row&rsquo;s basis is in <a className="underline" href="/docs/data/fund-owners.csv">the registry</a>: the department code the town itself puts on a fund, the department a line is filed under, or the fund&rsquo;s name.</p>
    </div>
  )
}

/* ---- the indexes ----------------------------------------------------------------- */

function DeptIndex({ d }: { d: Payload }) {
  const depts = d.departments.filter(x => x.kind === 'department').map(x => d.owners[x.slug]).filter(Boolean)
  const external = d.departments.filter(x => x.kind === 'external').map(x => d.owners[x.slug]).filter(Boolean)
  const boardsRunning = Object.values(d.owners).filter(o => o.kind === 'board' && (o.totals.appropriation_revised ?? 0) > 0).sort((a, b) => (b.totals.appropriation_revised ?? 0) - (a.totals.appropriation_revised ?? 0))
  const Row = ({ o }: { o: Owner }) => (
    <tr style={{ borderTop: '1px solid var(--grid)' }}>
      <Td><a className="underline font-semibold" href={ownerHref(d, o.slug)}>{o.name}</a></Td>
      <Td right>{money(o.totals.appropriation_revised)}</Td><Td right>{money(o.totals.special_revenue_held)}</Td><Td right>{money(o.totals.trust_held)}</Td><Td right>{o.owns.length}</Td>
    </tr>
  )
  const Head = () => <thead><tr><Th>who</Th><Th right>voted FY26</Th><Th right>in its own funds</Th><Th right>in trusts</Th><Th right>accounts</Th></tr></thead>
  return (
    <>
      <Grain>{d.grain}</Grain>
      <H2 id="departments">The Town Manager&rsquo;s departments</H2>
      <div className="overflow-x-auto mt-4"><table className="text-sm" style={{ minWidth: 640 }}><Head /><tbody>{depts.sort((a, b) => (b.totals.appropriation_revised ?? 0) - (a.totals.appropriation_revised ?? 0)).map(o => <Row key={o.slug} o={o} />)}</tbody></table></div>
      <H2 id="boards">Boards that run a department</H2>
      <Body>Voted a line of their own; their pages are under <a className="underline" href="/boards">the boards</a>.</Body>
      <div className="overflow-x-auto mt-4"><table className="text-sm" style={{ minWidth: 640 }}><Head /><tbody>{boardsRunning.map(o => <Row key={o.slug} o={o} />)}</tbody></table></div>
      <H2 id="external">Assessed from outside the town</H2>
      <Body>Lines Town Meeting votes and cannot change: the regional school, the retirement system, the state&rsquo;s cherry-sheet charges.</Body>
      <div className="overflow-x-auto mt-4"><table className="text-sm" style={{ minWidth: 640 }}><Head /><tbody>{external.map(o => <Row key={o.slug} o={o} />)}</tbody></table></div>
      <Legend d={d} />
    </>
  )
}

function AccountsIndex({ d }: { d: Payload }) {
  const groups: [string, Owner[]][] = [
    ['Boards', Object.values(d.owners).filter(o => o.kind === 'board')],
    ['Departments', Object.values(d.owners).filter(o => o.kind === 'department')],
    ['Assessed from outside', Object.values(d.owners).filter(o => o.kind === 'external')],
  ]
  const kinds = Object.entries(d.kinds)
  const counts: Record<string, number> = {}
  for (const m of Object.values(d.measures)) counts[m.kind] = (counts[m.kind] ?? 0) + 1
  return (
    <>
      <Grain>{d.grain}</Grain>
      <div className="mt-8 flex flex-wrap gap-x-10 gap-y-4">
        {kinds.map(([k, what]) => <Stat key={k} value={n0(counts[k] ?? 0)}>{k.replace('-', ' ')} — {what}</Stat>)}
      </div>
      {groups.map(([label, os]) => (
        <section key={label}>
          <H2 id={label.toLowerCase().replace(/\s+/g, '-')}>{label}</H2>
          {os.sort((a, b) => b.owns.length - a.owns.length).map(o => (
            <details key={o.slug} className="mt-3 card p-3">
              <summary className="cursor-pointer text-sm"><a className="underline font-semibold" href={ownerHref(d, o.slug)}>{o.name}</a> <span style={{ color: 'var(--text-muted)' }}>· {o.owns.length} account{o.owns.length === 1 ? '' : 's'}{o.totals.appropriation_revised !== null ? ` · ${short(o.totals.appropriation_revised)} voted` : ''}{o.totals.special_revenue_held !== null ? ` · ${short(o.totals.special_revenue_held)} in its funds` : ''}</span></summary>
              <ul className="mt-2 text-[12.5px] columns-1 md:columns-2 gap-6">
                {o.owns.map(i => { const m = d.measures[i]; return <li key={i} className="break-inside-avoid"><span className="tnum" style={{ color: 'var(--text-muted)' }}>{m.code}</span> <a className="underline" href={acctHref(d, m)}>{labelInline(m)}</a> <span style={{ color: 'var(--text-muted)' }}>· {m.kind}</span></li> })}
              </ul>
            </details>
          ))}
        </section>
      ))}
      <H2 id="unresolved">Funds nobody&rsquo;s page claims</H2>
      <Body>{d.unresolved.length ? <>{d.unresolved.length} measures no document we hold assigns to a board or department. They are listed rather than guessed at.</> : <>Every measure has an owner.</>}</Body>
      {d.unresolved.length > 0 && <FundTable ms={d.unresolved.map(i => d.measures[i])} />}
      <Legend d={d} />
    </>
  )
}
