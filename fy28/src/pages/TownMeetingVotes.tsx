import { ReportShell, useReport } from '../components/report'
import { VoteList, type VotePayload } from '../components/VoteList'

/** EVERY TOWN MEETING VOTE -- every warrant article of every Town Meeting the archive finds,
 *  searchable and filed by fiscal year. TJ, 23 October 2026: *"a single page that lists all town
 *  meeting votes, ever. and easily searchable and findable by FY."*
 *
 *  MODEL-DRIVEN (rule 7d): `/data/town-meeting-votes.json`, written by
 *  scripts/build_vote_lists.py from the Town Meeting register (build_town_meetings.py) and the
 *  Clerk's record. "Ever" is stated, not implied: the payload's coverage lines say which meetings
 *  are held and from what record, and the page prints them. */

const FILE = 'town-meeting-votes.json'

export function TownMeetingVotesPage() {
  const { d: p, err } = useReport<VotePayload>(FILE)
  return (
    <ReportShell tab="tmvotes" title="Every Town Meeting vote" err={err} loading={!p && !err} noPrint
      dataUrl={`/data/${FILE}`}
      standfirst={p ? p.standfirst : 'Every warrant article Town Meeting has voted, with what was decided and where it is recorded.'}>
      {p && <VoteList p={p} />}
    </ReportShell>
  )
}

export default TownMeetingVotesPage
