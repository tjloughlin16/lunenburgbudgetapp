import { useEffect, useState } from 'react'
import { Grain, ReportShell, Section, useReport } from '../components/report'

/** THE SCHOOL COMMITTEE'S LINE ITEM TRANSFERS, BY FISCAL YEAR, with a running tally.
 *
 *  TJ, 10 October 2026: *"build a page for the school committee that captures all the line
 *  item transfers that were voted in a meeting ... a running tally"* and *"this needs to be
 *  associated to each fiscal year so that I can look at all the line item transfers per
 *  fiscal year."*
 *
 *  MODEL-DRIVEN (rule 7d): `/data/school-committee-transfers.json`, written by
 *  scripts/build_school_transfers.py from the town's minutes as the meeting process reads
 *  them. This file lays out; it computes nothing but the year picked.
 *
 *  THREE KINDS OF THING, KEPT APART ON THE PAGE AS THEY ARE IN THE DATA (rule 3, 7):
 *    - counted: approved, in the TOWN'S MINUTES, totalled;
 *    - the district's own transfer SHEETS, where held: the line-level source;
 *    - awaiting: heard VOTED in a recording whose minutes are not read -- listed, never
 *      totalled, because caption figures are not figures.
 *  And a year we inferred from the meeting date is marked beside the row, not explained
 *  above the table (rule 7a). */

type Item = {
  meeting_date: string; description: string; from_line: string; to_line: string
  amount_as_printed: string; amount: string; amount_basis: string; outcome: string
  quote: string; minutes_url: string; our_copy: string; video_url: string
  fy_basis: string; fy_ours: boolean; why_not: string; running_total?: string
  /** The accounts, where a district sheet gives them -- never inferred. */
  accounts?: { from: Account[]; to: Account[] }
  sheet?: string; sheet_page?: string; form?: string; ties?: boolean
}
type Account = { org: string; object: string; description: string; amount_as_printed: string }
type Sheet = { fy: string; label: string; dated_as_printed: string; note: string; transfers_as_printed: string[]; reclassifications_as_printed: string[]; url: string; publisher_url: string }
type Year = {
  fy: number; n: number; total: string; n_no_amount: number; meetings: number; n_fy_ours: number
  tentative_total: string
  counted: Item[]; tentative: Item[]; awaiting: Item[]; not_counted: Item[]; sheets: Sheet[]
}
type Payload = {
  board: string; minutes_read: number; minutes_from: string; minutes_to: string
  years: Year[]; grain: string; sources: { label: string; url: string }[]
}

const FILE = 'school-committee-transfers.json'
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
const d = (iso: string) => { const [y, m, dd] = iso.split('-').map(Number); return `${dd} ${MONTHS[m - 1]} ${y}` }
const usd = (s: string) => s ? '$' + Number(s).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : ''

function fyFromUrl() {
  if (typeof window === 'undefined') return 0
  return Number(new URLSearchParams(window.location.search).get('fy') || 0)
}

export function SchoolTransfers() {
  const { d: p, err } = useReport<Payload>(FILE)
  const [fy, setFy] = useState(fyFromUrl())
  // THE NEWEST YEAR IS THE DEFAULT, even when the town's minutes have not reached it yet --
  // TJ, 10 October 2026: *"are you sure there havent been any transfers for school committee
  // so far for FY27?!"* There had: voted 7 October 2026, in no minutes the town had posted.
  // Opening on the last complete year hid exactly the transfers a reader came for.
  const years = p?.years ?? []
  const pick = years.find(y => y.fy === fy) ?? years[0]
  useEffect(() => {
    if (!pick) return
    const u = new URL(window.location.href)
    u.searchParams.set('fy', String(pick.fy))
    window.history.replaceState(null, '', u)
  }, [pick])
  return (
    <ReportShell tab="sctransfers" title="School Committee line item transfers" err={err} loading={!p && !err}
      dataUrl={`/data/${FILE}`}
      standfirst={p && pick
        ? <>FY{pick.fy}: {pick.n} transfer{pick.n === 1 ? '' : 's'} approved at {pick.meetings} meeting{pick.meetings === 1 ? '' : 's'}, {usd(pick.total)} as the minutes print the amounts. Every School Committee vote to move money between budget lines, year by year.</>
        : 'Every School Committee vote to move money between budget lines, year by year.'}>
      {p && pick && <>
        <div className="flex flex-wrap gap-2 mt-6" role="group" aria-label="Fiscal year">
          {years.map(y => (
            <button key={y.fy} type="button" aria-pressed={y.fy === pick.fy} onClick={() => setFy(y.fy)}
              className="px-3 py-1.5 text-sm rounded-full border font-semibold tnum"
              style={y.fy === pick.fy
                ? { background: 'var(--text-primary)', color: 'var(--surface-1)', borderColor: 'var(--text-primary)' }
                : { borderColor: 'var(--grid)', color: 'var(--text-primary)' }}>
              FY{y.fy}<span className="font-normal opacity-70 ml-1.5">{y.n || (y.awaiting.length ? '·' : '')}</span>
            </button>
          ))}
        </div>

        <Section kind="categorical" id="year" title={`FY${pick.fy}: what was approved`}>
          <div className="flex flex-wrap gap-x-10 gap-y-3 mt-1 tnum">
            <Fig v={String(pick.n)} l={`transfer${pick.n === 1 ? '' : 's'} approved in the town’s minutes`} />
            <Fig v={usd(pick.total)} l={`printed in those minutes${pick.n_no_amount ? `; ${pick.n_no_amount} approved with no amount printed` : ''}`} />
            <Fig v={String(pick.meetings)} l={`meeting${pick.meetings === 1 ? '' : 's'} with a transfer vote`} />
            {Number(pick.tentative_total) > 0 && (
              <Fig v={usd(pick.tentative_total)} l="TENTATIVE: voted in a recording, not yet in the town’s minutes" tone="var(--status-warning)" />
            )}
          </div>
          {pick.counted.length === 0
            ? <p className="text-[14px] mt-4 max-w-2xl" style={{ color: 'var(--text-secondary)' }}>
                None in the town&rsquo;s minutes yet &mdash; the last School Committee minutes the town has posted are from {d(p.minutes_to)}.
                {pick.tentative.length > 0
                  ? <> The transfers voted since are below as <strong>tentative</strong>: heard in the recording, with the district&rsquo;s sheet for the amounts and accounts.</>
                  : (pick.awaiting.length > 0 || pick.sheets.length > 0) && <> What is known so far is below.</>}
              </p>
            : <div className="mt-4 overflow-x-auto">
              <table className="w-full text-[13.5px] border-collapse">
                <thead>
                  <tr className="text-left text-[11px] uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
                    <th className="py-1.5 pr-3 font-semibold">Meeting</th>
                    <th className="py-1.5 pr-3 font-semibold">What moved</th>
                    <th className="py-1.5 pr-3 font-semibold text-right">Amount</th>
                    <th className="py-1.5 font-semibold text-right hidden sm:table-cell">Year&rsquo;s total through then</th>
                  </tr>
                </thead>
                <tbody>
                  {pick.counted.map((it, i) => <Row key={i} it={it} />)}
                </tbody>
              </table>
            </div>}
          {pick.n_fy_ours > 0 && (
            <p className="text-xs mt-2 max-w-2xl" style={{ color: 'var(--text-muted)' }}>
              <sup>†</sup> {pick.n_fy_ours} of these carry no year in the minutes and are filed under the year the meeting fell in &mdash; ours. A vote in July to September can close the year before.
            </p>
          )}
        </Section>

        {pick.tentative.length > 0 && (
          <Section kind="categorical" id="tentative" title="Tentative: voted, awaiting the town’s minutes">
            <p className="text-[13.5px] max-w-2xl" style={{ color: 'var(--text-secondary)' }}>
              <strong>Interpreted, not yet the record.</strong> The vote is heard in the meeting&rsquo;s recording; the amounts and accounts are the district&rsquo;s own transfer sheet for that meeting. Each moves into the total above when the town posts the minutes.
            </p>
            <ul className="mt-3 space-y-3">
              {pick.tentative.map((it, i) => (
                <li key={i} className="card p-3" style={{ borderLeft: '4px solid var(--status-warning)' }}>
                  <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                    <span className="text-[10.5px] font-bold uppercase tracking-wider" style={{ color: 'var(--status-warning)' }}>
                      {it.form === 'reclassification' ? 'Reclassification · not in the motion' : 'Tentative'}
                    </span>
                    <span className="tnum font-semibold">{d(it.meeting_date)}</span>
                    <span className="tnum font-bold ml-auto">{it.amount_as_printed}</span>
                  </div>
                  {it.description && <p className="text-[13px] mt-1" style={{ color: 'var(--text-secondary)' }}>{it.description}</p>}
                  {it.accounts && <Accounts a={it.accounts} ties={it.ties} />}
                  <p className="text-[11.5px] mt-1.5" style={{ color: 'var(--text-muted)' }}>
                    {it.sheet && <><a className="underline" href={it.sheet}>the district&rsquo;s sheet{it.sheet_page ? `, page ${it.sheet_page}` : ''}</a> · </>}
                    {it.video_url && <a className="underline" href={it.video_url} target="_blank" rel="noreferrer">the vote, in the recording</a>}
                  </p>
                </li>
              ))}
            </ul>
          </Section>
        )}

        {pick.sheets.length > 0 && (
          <Section kind="raw" id="sheets" title="The district’s transfer sheets">
            <p className="text-[13.5px] max-w-2xl" style={{ color: 'var(--text-secondary)' }}>
              The form the committee is shown, with each line&rsquo;s account code and budget. The minutes keep the vote; this keeps the lines.
            </p>
            <ul className="mt-2 space-y-1.5">
              {pick.sheets.map(s => (
                <li key={s.url} className="text-[13.5px]">
                  <a className="underline" href={s.url} style={{ color: 'var(--series-cost)' }}>{s.label}</a>
                  {s.dated_as_printed && <span style={{ color: 'var(--text-muted)' }}> · dated {s.dated_as_printed}</span>}
                  {(s.transfers_as_printed.length > 0 || s.reclassifications_as_printed.length > 0) && (
                    <span className="block text-[12.5px] tnum" style={{ color: 'var(--text-secondary)' }}>
                      {s.transfers_as_printed.length > 0 && <>{s.transfers_as_printed.length} transfer{s.transfers_as_printed.length === 1 ? '' : 's'} on the sheet: {s.transfers_as_printed.join(' and ')}</>}
                      {s.transfers_as_printed.length > 0 && s.reclassifications_as_printed.length > 0 && '; '}
                      {s.reclassifications_as_printed.length > 0 && <>reclassification{s.reclassifications_as_printed.length === 1 ? '' : 's'} of {s.reclassifications_as_printed.join(' and ')} (moving a cost already booked to the right line)</>}
                    </span>
                  )}
                  {s.publisher_url && <> · <a className="underline text-[12px]" href={s.publisher_url} target="_blank" rel="noreferrer">district&rsquo;s copy</a></>}
                  {s.note && <span className="block text-[12px]" style={{ color: 'var(--status-warning)' }}>{s.note}.</span>}
                </li>
              ))}
            </ul>
          </Section>
        )}

        {pick.awaiting.length > 0 && (
          <Section kind="raw" id="awaiting" title="Heard voted, not yet in the town’s minutes">
            <p className="text-[13.5px] max-w-2xl" style={{ color: 'var(--text-secondary)' }}>
              From machine captions of the recording, for meetings whose minutes we do not hold. Not added to any total: a caption model mishears figures.
            </p>
            <ul className="mt-2 space-y-2">
              {pick.awaiting.map((it, i) => (
                <li key={i} className="text-[13.5px] pt-2" style={{ borderTop: '1px solid var(--grid)' }}>
                  <span className="tnum font-semibold">{d(it.meeting_date)}</span> · {it.description}
                  <span className="block text-[12px]" style={{ color: 'var(--text-muted)' }}>
                    heard as {it.amount_as_printed || 'no figure'} · {it.outcome} · <a className="underline" href={it.video_url} target="_blank" rel="noreferrer">the video, at that moment</a>
                  </span>
                </li>
              ))}
            </ul>
          </Section>
        )}

        <Section kind="raw" id="about" title="What this counts">
          <Grain>{p.grain}</Grain>
          <p className="text-xs mt-3 max-w-2xl" style={{ color: 'var(--text-muted)' }}>
            Read from every set of School Committee minutes the archive holds &mdash; {p.minutes_read}, {d(p.minutes_from)} to {d(p.minutes_to)} &mdash; as the meeting process reads each new one. &ldquo;From&rdquo; and &ldquo;to&rdquo; are read off the minutes&rsquo; wording by us; the description and the quoted words are the evidence.
          </p>
          {pick.not_counted.length > 0 && (
            <details className="mt-3">
              <summary className="cursor-pointer text-[13px]" style={{ color: 'var(--text-secondary)' }}>
                {pick.not_counted.length} item{pick.not_counted.length === 1 ? '' : 's'} in FY{pick.fy}&rsquo;s minutes not counted, and why
              </summary>
              <ul className="mt-2 space-y-1.5">
                {pick.not_counted.map((it, i) => (
                  <li key={i} className="text-[13px]">
                    <span className="tnum">{d(it.meeting_date)}</span> · {it.description}
                    <span style={{ color: 'var(--text-muted)' }}> &mdash; {it.why_not}</span>
                    {it.our_copy && <> · <a className="underline text-[12px]" href={it.our_copy}>minutes</a></>}
                  </li>
                ))}
              </ul>
            </details>
          )}
          <p className="text-xs mt-3 max-w-2xl break-words" style={{ color: 'var(--text-muted)' }}>
            Sources: {p.sources.map((s, i) => <span key={s.url}>{i ? ' · ' : ''}<a className="underline" href={s.url}>{s.label}</a></span>)}. <a className="underline" href="/boards/school-committee">The School Committee&rsquo;s page</a>.
          </p>
        </Section>
      </>}
    </ReportShell>
  )
}

/** THE ACCOUNTS ON THE DISTRICT'S SHEET: org and object codes as printed, from -> to. A side
 *  that does not add up to the sheet's own printed total says so -- the transcription keeps
 *  what is printed rather than correcting it. */
function Accounts({ a, ties }: { a: { from: Account[]; to: Account[] }; ties?: boolean }) {
  const col = (label: string, xs: Account[]) => (
    <div className="min-w-0">
      <p className="text-[10.5px] font-bold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>{label}</p>
      <ul className="mt-0.5">
        {xs.map((x, i) => (
          <li key={i} className="text-[12.5px] flex justify-between gap-3 tnum">
            <span className="min-w-0 break-words">{x.description} <span style={{ color: 'var(--text-muted)' }}>{x.org}-{x.object}</span></span>
            <span className="shrink-0">{x.amount_as_printed}</span>
          </li>
        ))}
      </ul>
    </div>
  )
  return (
    <div className="mt-2">
      <div className="grid gap-3 sm:grid-cols-2">{col('From', a.from)}{col('To', a.to)}</div>
      {ties === false && <p className="text-[11.5px] mt-1" style={{ color: 'var(--status-warning)' }}>The lines as printed do not add up to the sheet&rsquo;s own total.</p>}
    </div>
  )
}

function Fig({ v, l, tone }: { v: string; l: string; tone?: string }) {
  return (
    <div className="min-w-0">
      <p className="text-2xl font-bold" style={tone ? { color: tone } : undefined}>{v}</p>
      <p className="text-[12.5px] max-w-[16rem]" style={{ color: 'var(--text-secondary)' }}>{l}</p>
    </div>
  )
}

function Row({ it }: { it: Item }) {
  // Both ends or neither: half a split (`Building maintenance -> …`) says less than the sentence.
  const moved = it.from_line && it.to_line
  return (
    <tr className="align-top" style={{ borderTop: '1px solid var(--grid)' }}>
      <td className="py-2 pr-3 tnum whitespace-nowrap">
        {d(it.meeting_date)}{it.fy_ours && <sup title={it.fy_basis}>†</sup>}
      </td>
      <td className="py-2 pr-3 min-w-[12rem]">
        {moved
          ? <span className="font-semibold">{it.from_line} <span aria-label="to">&rarr;</span> {it.to_line}</span>
          : <span className="font-semibold">{it.description}</span>}
        {moved && <span className="block text-[12.5px]" style={{ color: 'var(--text-secondary)' }}>{it.description}</span>}
        {it.accounts && (
          <details className="mt-1">
            <summary className="cursor-pointer text-[12px]" style={{ color: 'var(--series-cost)' }}>Accounts, from the district&rsquo;s sheet</summary>
            <Accounts a={it.accounts} ties={it.ties} />
          </details>
        )}
        <span className="block text-[11.5px] mt-0.5" style={{ color: 'var(--text-muted)' }}>
          {it.quote && <>&ldquo;{it.quote.length > 140 ? it.quote.slice(0, 140) + '…' : it.quote}&rdquo; · </>}
          {it.our_copy && <a className="underline" href={it.our_copy}>minutes</a>}
          {it.minutes_url && <> · <a className="underline" href={it.minutes_url} target="_blank" rel="noreferrer">town&rsquo;s copy</a></>}
        </span>
      </td>
      <td className="py-2 pr-3 text-right tnum whitespace-nowrap">
        {it.amount ? usd(it.amount) : <span style={{ color: 'var(--text-muted)' }}>not printed</span>}
        {it.amount_basis.startsWith('sum') && <span className="block text-[11px]" style={{ color: 'var(--text-muted)' }}>{it.amount_basis}</span>}
      </td>
      <td className="py-2 text-right tnum whitespace-nowrap hidden sm:table-cell" style={{ color: 'var(--text-secondary)' }}>{usd(it.running_total || '')}</td>
    </tr>
  )
}
