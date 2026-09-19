/** HOW ALIVE A MATTER IS — and why we say so.
 *
 *  TJ: "I want to see if something is HOT, COLD, just getting started, [a can of worms]".
 *
 *  COLOUR IS ALREADY SPOKEN FOR. The five group hues carry WHAT a thread is about, and a
 *  second hue scale competing with them would make the page a colour puzzle. So heat is
 *  drawn as FILL — three bars, filled by level — which reads at a glance, survives
 *  greyscale and colour-blindness, and takes its ink from the group's own colour instead
 *  of introducing another.
 *
 *  AND THE WORD IS NEVER ALONE. The counts that produced it sit beside it in the card, so
 *  "picking up" is a summary a reader can check rather than a verdict they must accept. */

export type Heat = 'picking up' | 'moving' | 'just started' | 'raised once' | 'slowing' | 'stale' | 'gone quiet' | 'settled'

const BARS: Record<Heat, number> = {
  'picking up': 3, moving: 2, slowing: 1, 'just started': 1, 'raised once': 1,
  stale: 0, 'gone quiet': 0, settled: 0,
}
const WHY: Record<Heat, string> = {
  'picking up': 'more meetings in the last three months than its own average',
  moving: 'discussed recently, at a steady pace',
  'just started': 'one meeting so far, and it was recent',
  'raised once': 'raised at one meeting and not returned to since — somebody put it on a future agenda and it did not come back',
  slowing: 'the pace has dropped',
  stale: 'an open question that is not being answered — real time has passed and its boards have sat repeatedly without returning to it',
  'gone quiet': 'nothing for over a year — which may be the record going quiet rather than the matter',
  settled: 'decided',
}

export function ThreadHeat({ heat, tone, momentum }: {
  heat: Heat; tone: string
  momentum: { meetings: number; boards: number; votes: number; days_since_last: number; meetings_last_90: number; board_meetings_since: number }
}) {
  const n = BARS[heat] ?? 0
  const title = `${heat} — ${WHY[heat]} (${momentum.meetings} meetings, `
    + `${momentum.meetings_last_90} in the last 90 days, last ${momentum.days_since_last} days ago; `
    + `its boards have met ${momentum.board_meetings_since} times since, in the record we can read)`
  return (
    <span className="inline-flex items-center gap-1 shrink-0" title={title}>
      <svg width="13" height="11" aria-hidden="true">
        {[0, 1, 2].map(i => (
          <rect key={i} x={i * 4.5} y={8 - i * 3.2} width="3" height={3 + i * 3.2} rx="1"
            fill={i < n ? tone : 'transparent'} stroke={tone}
            strokeWidth="1" opacity={i < n ? 1 : .35} />
        ))}
        {heat === 'stale' ? (
          <line x1="0.5" y1="10.5" x2="12.5" y2="1.5" stroke={tone} strokeWidth="1.4" />
        ) : null}
      </svg>
      <span className="text-[11px] font-semibold uppercase tracking-wide whitespace-nowrap"
        style={{ color: 'var(--text-secondary)' }}>{heat}</span>
    </span>
  )
}

/** "MANY BOARDS DISCUSSED IT WITH NO RESOLUTION" — said as the fact it is, not as a
 *  dramatic label. A matter that has spread across the town's tables and been settled by
 *  none of them is an ordinary and very common state, and naming it luridly would make a
 *  reader distrust the page. */
export function Tangled({ boards, meetings }: { boards: number; meetings: number }) {
  return (
    <span className="text-[12px]" style={{ color: 'var(--text-secondary)' }}>
      discussed by {boards} boards over {meetings} meetings and settled by none
    </span>
  )
}
