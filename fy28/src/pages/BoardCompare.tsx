import { FullVersion } from '../components/FullVersion'
import type { Tab } from '../routes'
import { Conclusions, Grain, H2, NotEstablished, Provenance, ReportShell, Stat, useReport, splitConclusions } from '../components/report'
import type { Conclusion, Source } from '../components/report'
import { BoardBars } from '../components/BoardBars'

const TAB: Tab = 'boardcompare'
const DATA = '/data/board-posting.json'

/** THE BOARDS, COMPARED. TJ, 17 September 2026: "do we have a breakdown of the boards
 *  who post minutes? I want to show the school committee what percent of minutes they
 *  have missed compared to other boards" -- then "a sort of 'board analysis' page" --
 *  then "more of a general board comparison, not specific about the minutes. we will
 *  analyze a lot more than that." So this is the page every board is set beside the
 *  others on, one MEASURE per section, and the first measure is minutes posted. Each
 *  measure a report-style block: what it counts, the three budget boards, every board.
 *
 *  Built by scripts/build_board_posting.py from the town's own Agenda Center: a meeting
 *  is a date a board posted an agenda for; it has minutes if the Agenda Center lists
 *  minutes for that date. By fiscal year, because the lifetime number hides the story
 *  (the School Committee's is mostly one blank year; the Select Board's fall is recent),
 *  and with the last sixty days left out, because minutes lag. Rule 8: the best board is
 *  named as the standard; nobody is called out for a reason the data cannot see. */
type Year = { fy: number; meetings: number; with_minutes: number; recorded: number }
type Row = { slug: string; name: string; the_three: boolean; years: Year[]; meetings: number; with_minutes: number; share: number
             recorded: number; recorded_share: number; captions_disabled: number; ranked: boolean; rank?: number }
type Payload = {
  about: string; grain: string; as_of: string; lag_days: number; fys: number[]; min_meetings: number
  totals: { meetings: number; with_minutes: number; share: number; boards_ranked: number }
  boards: Row[]; unmatched: { board: string; documents: number }[]
  not_established: string[]; conclusions: Conclusion[]; sources?: Source[]
}
const n0 = (n: number) => n.toLocaleString('en-US')
const pct = (k: number, n: number) => (n ? `${Math.round(100 * k / n)}%` : '—')

export function BoardCompare() {
  const { d, err } = useReport<Payload>('board-posting.json')
  return (
    <ReportShell tab={TAB}
      title="The boards, compared"
      standfirst={d ? <>Every board the town posts for, set beside the others on what the record measures. One measure so far &mdash; which meetings got minutes, FY{d.fys[0]} to FY{d.fys[d.fys.length - 1]} &mdash; and more to come. <a className="underline" href="/boards">Each board&rsquo;s own page</a>.</> : undefined}
      err={err} loading={!d && !err} dataUrl={DATA}>
      {d && <Report d={d} />}
    </ReportShell>
  )
}

function Cell({ y }: { y: Year }) {
  const s = y.meetings ? Math.round(100 * y.with_minutes / y.meetings) : null
  const tone = s === null ? 'var(--text-muted)' : s >= 90 ? 'var(--status-good)' : s >= 60 ? 'var(--text-primary)' : 'var(--status-critical)'
  return (
    <td className="py-1.5 pr-3 text-right tnum whitespace-nowrap" style={{ color: tone }}>
      {y.meetings ? <>{y.with_minutes} of {y.meetings} <span className="text-[11px]" style={{ color: 'var(--text-muted)' }}>({pct(y.with_minutes, y.meetings)})</span></> : '—'}
    </td>
  )
}

function Table({ rows, fys, caption }: { rows: Row[]; fys: number[]; caption: string }) {
  return (
    <div className="overflow-x-auto mt-4">
      <table className="text-sm" style={{ minWidth: 640 }}>
        <caption className="text-left text-[12px] pb-2" style={{ color: 'var(--text-muted)' }}>{caption}</caption>
        <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
          <th className="text-left py-1.5 pr-4">board</th>
          {fys.map(f => <th key={f} className="text-right py-1.5 pr-3">FY{f}</th>)}
          <th className="text-right py-1.5 pr-3">all {fys.length} years</th>
          <th className="text-right py-1.5">recorded</th>
        </tr></thead>
        <tbody>{rows.map(r => (
          <tr key={r.slug} style={{ borderTop: '1px solid var(--grid)' }} className={r.the_three ? 'font-semibold' : undefined}>
            <td className="py-1.5 pr-4"><a className="underline" href={`/boards/${r.slug}`}>{r.name}</a>{r.rank ? <span className="text-[11px] font-normal ml-1.5" style={{ color: 'var(--text-muted)' }}>#{r.rank}</span> : null}</td>
            {r.years.map(y => <Cell key={y.fy} y={y} />)}
            <td className="py-1.5 pr-3 text-right tnum whitespace-nowrap">{r.with_minutes} of {r.meetings} <span className="text-[11px]" style={{ color: 'var(--text-muted)' }}>({pct(r.with_minutes, r.meetings)})</span></td>
            <td className="py-1.5 text-right tnum whitespace-nowrap" style={{ color: 'var(--text-secondary)' }}>{pct(r.recorded, r.meetings)}</td>
          </tr>))}</tbody>
      </table>
    </div>
  )
}

function Report({ d }: { d: Payload }) {
  const three = d.boards.filter(r => r.the_three)
  const ranked = d.boards.filter(r => r.ranked)
  const rest = d.boards.filter(r => !r.ranked)
  const [shortRows, moreRows] = splitConclusions(d.conclusions, undefined)
  const sc = three.find(r => r.slug === 'school-committee')!
  const fc = three.find(r => r.slug === 'finance-committee')!
  const sb = three.find(r => r.slug === 'select-board')!
  const last = d.fys[d.fys.length - 1]
  const y = (r: Row) => r.years.find(x => x.fy === last)!
  return (
    <>
      {/* THE PICTURE FIRST: every ranked board, one bar each. */}
      <BoardBars rows={ranked} fys={d.fys} />

      <section data-section="conclusions" data-short="">
        <H2 id="minutes">Measure 1 &mdash; which meetings got minutes</H2>
        <p className="text-sm max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
          Across every board, FY{d.fys[0]} to FY{d.fys[d.fys.length - 1]}: {n0(d.totals.with_minutes)} of {n0(d.totals.meetings)} meetings with a posted agenda also have posted minutes, {d.totals.share.toFixed(0)}%. Board by board and year by year, on the town&rsquo;s own site.
        </p>
        <div className="flex flex-wrap gap-x-10 gap-y-5 mt-6">
          <Stat value={pct(y(fc).with_minutes, y(fc).meetings)}>of Finance Committee meetings in FY{last} have minutes posted &mdash; {y(fc).with_minutes} of {y(fc).meetings}</Stat>
          <Stat value={pct(y(sb).with_minutes, y(sb).meetings)} tone="var(--status-critical)">of Select Board meetings in FY{last} &mdash; {y(sb).with_minutes} of {y(sb).meetings}</Stat>
          <Stat value={pct(y(sc).with_minutes, y(sc).meetings)} tone="var(--series-cost)">of School Committee meetings in FY{last} &mdash; {y(sc).with_minutes} of {y(sc).meetings}</Stat>
          <Stat value={`${d.totals.share.toFixed(0)}%`}>of every board&rsquo;s meetings, all {d.fys.length} years &mdash; {n0(d.totals.with_minutes)} of {n0(d.totals.meetings)}</Stat>
        </div>
        <Grain>{d.grain} Meetings in the last {d.lag_days} days are left out, because minutes are approved at the next meeting and posted after it.</Grain>
        <Conclusions rows={shortRows} />
      </section>

      <FullVersion what="every board, every year">
        {moreRows.length > 0 && (
          <>
            <H2 id="more-findings">The other findings</H2>
            <Conclusions rows={moreRows} noAsk short={false} />
          </>
        )}

        <section data-section="categorical">
          <H2 id="the-three">The three budget boards</H2>
          <p className="text-sm max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
            Meetings with minutes posted, of meetings with a posted agenda, by fiscal year (July to June). The last column is the share of meetings the town&rsquo;s channel holds a recording for.
          </p>
          <Table rows={three} fys={d.fys} caption="The boards that build the budget." />

          <H2 id="every-board">Every board with {d.min_meetings} or more meetings</H2>
          <p className="text-sm max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
            Ranked by the {d.fys.length}-year share. Green is ninety per cent or better; red is under sixty.
          </p>
          <Table rows={ranked} fys={d.fys} caption={`${ranked.length} boards, ranked.`} />
          {rest.length > 0 && (
            <>
              <H2 id="smaller">Boards with fewer meetings</H2>
              <p className="text-sm max-w-3xl" style={{ color: 'var(--text-secondary)' }}>Listed, not ranked: too few meetings for a share to mean much.</p>
              <Table rows={rest} fys={d.fys} caption={`${rest.length} boards with fewer than ${d.min_meetings} meetings in the window.`} />
            </>
          )}
        </section>

        <section data-section="raw">
          <H2 id="how">How this is counted</H2>
          <p className="text-sm max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
            The town&rsquo;s Agenda Center lists every agenda and every set of minutes each board has posted; the refresh reads it daily. A <em>meeting</em> here is a date a board posted an agenda for, and it <em>has minutes</em> if the Agenda Center lists minutes for the same board and date. Nothing is inferred from a recording or from our own minutes. The School Committee is a district body with its own page, and that page sends readers to the town&rsquo;s Agenda Center for minutes &mdash; so it is counted on the same shelf as every other board (checked {d.as_of}).
          </p>
          <NotEstablished rows={d.not_established} closes="A year of the watcher’s posting dates (collected since 8 September 2026) would give how long each board takes to post; the town’s own record of cancelled meetings would separate a meeting that was not minuted from one that was not held." />
          {d.sources && <Provenance sources={d.sources} />}
        </section>
      </FullVersion>
    </>
  )
}
