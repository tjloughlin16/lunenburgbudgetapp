import { ReportShell, useReport } from '../components/report'
import { NewBadge, NEW_DAYS } from '../components/SiteMenu'
import { todayIso } from '../lib/meetings'

/* NEW REPORTS, on a page of their own: /new-reports. TJ, 31 October 2026: "the 'new reports' at
 * the top of the reports page is too much. lets put new-reports as its own page. and we can link
 * to it somewhere and have it follow-able." So /reports keeps one line pointing here, and this page
 * carries the whole list, newest day first, with the feed that follows it.
 *
 * Every row is from /data/reports-recent.json (scripts/build_reports_index.py): each report's
 * birthday is the commit that added it. The feed, /feeds/new-reports.xml, is the same list
 * (scripts/build_feeds.py), so a feed reader and this page cannot disagree. */

type Recent = { reports: { title: string; url: string; first_published: string; about: string }[] }

const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September',
  'October', 'November', 'December']
const longDate = (iso: string) => {
  const [y, m, d] = iso.split('-').map(Number)
  return `${d} ${MONTHS[m - 1]} ${y}`
}
const link = { color: 'var(--series-cost)' }
/** A day with more than this many reports is folded: a conversion can publish hundreds at once. */
const FOLD = 8

export function NewReports() {
  const { d, err } = useReport<Recent>('reports-recent.json')
  const today = Date.parse(todayIso())
  const rows = (d?.reports ?? []).map(r => ({ ...r, age: Math.round((today - Date.parse(r.first_published)) / 864e5) }))
  const days = [...new Set(rows.map(r => r.first_published))]
  return (
    <ReportShell tab="newreports" title="New reports" err={err} loading={!d && !err}
      dataUrl="/data/reports-recent.json"
      standfirst="Every report and page this project publishes, by the day it first appeared.">
      <div className="card p-4 mt-5 max-w-3xl">
        <p className="text-[14px] font-semibold">Follow new reports</p>
        <p className="text-[13.5px] mt-1" style={{ color: 'var(--text-secondary)' }}>
          <a href="/feeds/new-reports.xml" className="underline font-semibold" style={link}>/feeds/new-reports.xml</a>
          {' '}is a feed of this list. Paste it into a feed reader, or into an RSS-to-email service
          to get each new report by email. This site keeps no list of who follows.</p>
      </div>
      {days.map(day => {
        const these = rows.filter(r => r.first_published === day)
        const list = (rs: typeof these) => (
          <ul className="m-0 p-0 list-none grid gap-3 sm:grid-cols-2 mt-3">
            {rs.map(r => (
              <li key={r.url}>
                <a href={r.url} className="card block p-4 h-full transition-opacity hover:opacity-90 no-underline">
                  <span className="flex items-baseline justify-between gap-3">
                    <span className="text-[15.5px] font-bold leading-tight" style={link}>{r.title} &rarr;</span>
                    {r.age >= 0 && r.age <= NEW_DAYS ? <NewBadge age={r.age} /> : null}
                  </span>
                  <span className="block text-[13.5px] mt-1 leading-snug" style={{ color: 'var(--text-secondary)' }}>{r.about}</span>
                </a>
              </li>))}
          </ul>)
        return (
          <section key={day} className="mt-8">
            <h2 className="text-[11px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
              {longDate(day)} <span className="font-normal normal-case tracking-normal">· {these.length} {these.length === 1 ? 'report' : 'reports'}</span>
            </h2>
            {list(these.slice(0, FOLD))}
            {these.length > FOLD ? (
              <details className="mt-3">
                <summary className="cursor-pointer text-[13.5px] font-semibold" style={link}>
                  Show all {these.length}</summary>
                {list(these.slice(FOLD))}
              </details>) : null}
          </section>)
      })}
    </ReportShell>)
}
