import { Grain, ReportShell, Section, Stat, useReport } from '../components/report'

/** GRANTS OPEN TO LUNENBURG -- the DESE grant programs a school district can apply for now.
 *
 *  TJ, 22 October 2026: *"I want to create a fetcher and a page that lists available grants
 *  to Lunenburg. This page I hope to post the schools at to know they should be applying."*
 *  So it is a working list for the district (rule 8), soonest due first, and it says nothing
 *  about what anybody applied for before -- nothing here could know that.
 *
 *  MODEL-DRIVEN (rule 7d). Everything is `/data/grants-open-to-lunenburg.json`, written by
 *  scripts/build_grants_open.py from sources/data/dese-grant-opportunities.csv; this file lays
 *  out, it computes nothing. The grouping is OUR reading of DESE's eligibility text (rule 3),
 *  and every card carries that text verbatim beside the reading. */

type Grant = {
  fund_code: string; program: string; grant_type: string; funding: string
  posted: string; posted_text: string; due: string; due_text: string
  unit: string; contact: string; purpose: string; funding_text: string
  eligibility: string; reading: string; basis: string; url: string
}
type Group = { id: string; title: string; note: string; rows: Grant[] }
type Payload = {
  as_of: string; as_of_text: string; listed: number
  stats: { value: string; label: string }[]
  groups: Group[]
  reading_note: string
  grain: string
  sources: { label: string; url: string }[]
}

const FILE = 'grants-open-to-lunenburg.json'
const READING: Record<string, string> = {
  'districts eligible': 'school districts may apply',
  'not districts': 'not for school districts',
  unclear: 'limited or unclear',
}

export function GrantsOpenPage() {
  const { d: p, err } = useReport<Payload>(FILE)
  const lead = p?.groups[0]
  const rest = p?.groups.slice(1, 3) ?? []
  const formula = p?.groups.find(g => g.id === 'formula')
  const closed = p?.groups.find(g => g.id === 'closed')
  return (
    <ReportShell tab="grantsopen" title="Grants open to Lunenburg" err={err} loading={!p && !err}
      dataUrl={`/data/${FILE}`}
      standfirst={p
        ? <>State and federal grant programs a school district can apply for, soonest due first &mdash; as DESE listed them on {p.as_of_text}.</>
        : 'State and federal grant programs a school district can apply for, soonest due first.'}>
      {p && lead && <>
        <div className="flex flex-wrap gap-x-10 gap-y-5 mt-6">
          {p.stats.map(s => <Stat key={s.label} value={s.value}>{s.label}</Stat>)}
        </div>

        <Section kind="categorical" id={lead.id} title={lead.title}>
          <p className="text-[14px] max-w-2xl" style={{ color: 'var(--text-secondary)' }}>{lead.note}</p>
          <Cards rows={lead.rows} empty={`None on DESE’s list on ${p.as_of_text}.`} />
          <p className="text-xs mt-3 max-w-2xl" style={{ color: 'var(--text-muted)' }}>{p.reading_note}</p>
        </Section>

        {rest.map(g => (
          <Section key={g.id} kind="categorical" id={g.id} title={g.title}>
            <p className="text-[14px] max-w-2xl" style={{ color: 'var(--text-secondary)' }}>{g.note}</p>
            <Cards rows={g.rows} empty="None on the list that day." />
          </Section>
        ))}

        {formula && (
          <Section kind="categorical" id={formula.id} title={formula.title}>
            <p className="text-[14px] max-w-2xl" style={{ color: 'var(--text-secondary)' }}>{formula.note}</p>
            <Lines rows={formula.rows} asOf={p.as_of} />
          </Section>
        )}

        {closed && closed.rows.length > 0 && (
          <Section kind="raw" id={closed.id} title={closed.title}>
            <p className="text-[14px] max-w-2xl" style={{ color: 'var(--text-secondary)' }}>{closed.note}</p>
            <details className="mt-3 max-w-3xl">
              <summary className="cursor-pointer text-[13.5px] underline">
                {closed.rows.length} program{closed.rows.length === 1 ? '' : 's'}, most recently due first
              </summary>
              <Lines rows={closed.rows} asOf={p.as_of} />
            </details>
          </Section>
        )}

        <Section kind="raw" id="grants-about" title="What this lists">
          <Grain>{p.grain}</Grain>
          <p className="text-xs mt-3 max-w-2xl break-words" style={{ color: 'var(--text-muted)' }}>
            Sources: {p.sources.map((s, i) => (
              <span key={s.url}>{i ? ' · ' : ''}<a className="underline" href={s.url}>{s.label}</a></span>
            ))}.
          </p>
        </Section>
      </>}
    </ReportShell>
  )
}

function Cards({ rows, empty }: { rows: Grant[]; empty: string }) {
  if (!rows.length) return <p className="text-[14px] mt-3" style={{ color: 'var(--text-muted)' }}>{empty}</p>
  return (
    <div className="grid gap-3 mt-3 max-w-3xl">
      {rows.map(g => (
        <div key={g.url} id={`grant-${g.fund_code.replace(/[^A-Za-z0-9]+/g, '-')}`}
          className="card p-4 avoid-break min-w-0 scroll-mt-24">
          <p className="text-[13px] font-bold tnum" style={{ color: 'var(--series-cost)' }}>
            Due {g.due_text || 'date not printed'}
          </p>
          <a className="text-[15px] font-bold leading-snug break-words underline block mt-1" href={g.url}
            target="_blank" rel="noreferrer">{g.program}</a>
          <p className="text-[12.5px] mt-1" style={{ color: 'var(--text-secondary)' }}>
            {[`Fund code ${g.fund_code}`, g.grant_type, g.funding, g.posted_text && `posted ${g.posted_text}`].filter(Boolean).join(' · ')}
          </p>
          {g.purpose && <p className="text-[14px] mt-2 max-w-2xl">{g.purpose}</p>}
          {g.funding_text && <p className="text-[13px] mt-2" style={{ color: 'var(--text-secondary)' }}>{g.funding_text}</p>}
          <details className="mt-2">
            <summary className="cursor-pointer text-[12.5px] underline">
              Who may apply &mdash; our reading: {READING[g.reading] ?? g.reading}
            </summary>
            <p className="text-[13px] mt-2 whitespace-pre-line break-words max-w-2xl">{g.eligibility}</p>
            <p className="text-[11.5px] mt-2" style={{ color: 'var(--text-muted)' }}>
              DESE&rsquo;s eligibility text, quoted. Our reading: {g.basis}.
            </p>
          </details>
          <p className="text-[11.5px] mt-2 break-words" style={{ color: 'var(--text-muted)' }}>
            {g.unit}{g.contact ? <> · <a className="underline" href={`mailto:${g.contact}`}>{g.contact}</a></> : null}
          </p>
        </div>
      ))}
    </div>
  )
}

function Lines({ rows, asOf }: { rows: Grant[]; asOf: string }) {
  return (
    <ul className="mt-3 max-w-3xl">
      {rows.map(g => (
        <li key={g.url} className="text-[13.5px] py-1.5 border-b" style={{ borderColor: 'var(--border)' }}>
          <a className="underline break-words" href={g.url} target="_blank" rel="noreferrer">{g.program}</a>
          <span className="tnum" style={{ color: 'var(--text-muted)' }}>
            {' '}· {g.fund_code} · {g.grant_type} · {g.funding} · {g.due < asOf ? 'was due' : 'due'} {g.due_text || 'date not printed'}
          </span>
        </li>
      ))}
    </ul>
  )
}

export default GrantsOpenPage
