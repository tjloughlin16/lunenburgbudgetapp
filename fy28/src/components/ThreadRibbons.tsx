import { useState } from 'react'
import { ThreadKind } from './ThreadKind'

/** THE THREADS, AS THREADS — one line per matter, running left to right through time.
 *
 *  TJ asked for something at the top of the page "just to make it interesting", and then,
 *  when I hesitated over rule 7a: "images dont need to follow our preface rule.... its not
 *  a block of text to read." Correct — 7a is about blocks of prose a reader has to get
 *  past. So this could have been decoration. It is the data instead, because a picture of
 *  the thing beats a picture near the thing, and because a literal ribbon per thread is
 *  the clearest statement of what the word means on this site.
 *
 *  WHAT IT ENCODES, and nothing else: when each matter first appears in the readable
 *  record, when it last moved, every meeting that touched it, and whether it ended.
 *
 *  COLOUR, computed rather than chosen. `--series-cost` and `--series-revenue` are the
 *  site's own pair, and they were run through the palette validator rather than eyeballed:
 *  light (#2a78d6/#eb6834 on #fcfcfb) and dark (#3987e5/#d95926 on #1a1a19) each pass the
 *  lightness band, the chroma floor, CVD separation (protan ΔE 24.7 / 26.8, tritan 32.7 /
 *  32.4), the normal-vision floor and contrast. The first draft used muted grey for
 *  settled, which FAILED the chroma floor — it reads as gray, and a reader would have been
 *  told "finished" by a colour that says "absent".
 *
 *  AND IDENTITY IS NEVER COLOUR ALONE: every row is labelled, a settled row ends in a
 *  filled dot and an open row in a hollow one, and the legend names both states. */

type Row = { id: string; label: string; status: string; kind: string; first: string; last: string; dates: string[]; tone: string }

const day = (iso: string) => Date.parse(iso + 'T12:00:00Z') / 86400000

export function ThreadRibbons({ rows, onGo }: { rows: Row[]; onGo: (id: string) => void }) {
  const [hover, setHover] = useState<string | null>(null)
  const live = rows.filter(r => r.first && r.last)
  if (live.length < 2) return null

  const lo = Math.min(...live.map(r => day(r.first)))
  const hi = Math.max(...live.map(r => day(r.last)))
  const span = Math.max(hi - lo, 1)

  const ROW = 15, PAD_T = 22, PAD_B = 20, LABEL = 132, RIGHT = 8
  const W = 660, H = PAD_T + live.length * ROW + PAD_B
  const x = (iso: string) => LABEL + ((day(iso) - lo) / span) * (W - LABEL - RIGHT)

  // Year ticks across the span, so the axis says WHEN without a label on every point.
  const years: number[] = []
  for (let y = new Date(lo * 86400000).getUTCFullYear(); y <= new Date(hi * 86400000).getUTCFullYear(); y++) years.push(y)

  return (
    <figure className="m-0 mb-5">
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} role="img"
        aria-label={`${live.length} threads over time, each a line from when it first appears in the record to when it last moved`}
        style={{ display: 'block', maxWidth: '100%', overflow: 'visible' }}>
        {years.map(y => {
          const px = x(`${y}-01-01`)
          if (px < LABEL || px > W - RIGHT) return null
          return (
            <g key={y}>
              <line x1={px} x2={px} y1={PAD_T - 8} y2={H - PAD_B + 4}
                stroke="var(--grid)" strokeWidth="1" />
              <text x={px} y={H - PAD_B + 15} textAnchor="middle" fontSize="10"
                fill="var(--text-muted)">{y}</text>
            </g>
          )
        })}

        {live.map((r, i) => {
          const y = PAD_T + i * ROW + ROW / 2
          const done = r.status === 'resolved'
          const tone = r.tone
          const on = hover === r.id
          const x1 = x(r.first), x2 = x(r.last)
          return (
            <g key={r.id} style={{ cursor: 'pointer' }}
              onMouseEnter={() => setHover(r.id)} onMouseLeave={() => setHover(null)}
              onClick={() => onGo(r.id)}>
              {/* the row's hit area is the whole row, not the 2px line */}
              <rect x="0" y={y - ROW / 2} width={W} height={ROW} fill="transparent" />
              <g transform={`translate(0 ${y - 5.5})`} opacity={on ? 1 : .8}>
                <ThreadKind kind={r.kind} tone={tone} size={11} />
              </g>
              <text x="15" y={y + 3} fontSize="10.5" fill={on ? 'var(--text-primary)' : 'var(--text-secondary)'}
                style={{ fontWeight: on ? 600 : 400 }}>
                {r.label.length > 24 ? r.label.slice(0, 23) + '…' : r.label}
              </text>
              <line x1={x1} x2={x2} y1={y} y2={y} stroke={tone}
                strokeWidth={on ? 3.5 : 2} strokeLinecap="round" opacity={on ? 1 : .85} />
              {r.dates.map(d => (
                <circle key={d} cx={x(d)} cy={y} r={on ? 2.6 : 2} fill={tone} opacity=".9" />
              ))}
              {/* SHAPE, not colour, says whether it ended: filled = settled, hollow = open */}
              <circle cx={x2} cy={y} r={done ? 4 : 3.6} fill={done ? tone : 'var(--surface-1)'}
                stroke={tone} strokeWidth="2" />
            </g>
          )
        })}
      </svg>
      {/* COLOUR IS THE GROUP; SHAPE IS THE STATE. Two encodings on one mark, neither
          standing in for the other — a hollow end is open and a filled end is settled
          whatever colour the line is, which is what keeps this readable in greyscale. */}
      <figcaption className="text-[11.5px] mt-1 flex flex-wrap gap-x-4 gap-y-1"
        style={{ color: 'var(--text-muted)' }}>
        <span><svg width="22" height="8" className="inline align-middle mr-1">
          <line x1="1" y1="4" x2="14" y2="4" stroke="var(--text-muted)" strokeWidth="2" strokeLinecap="round" />
          <circle cx="17" cy="4" r="3.2" fill="var(--surface-1)" stroke="var(--text-muted)" strokeWidth="2" />
        </svg>still open</span>
        <span><svg width="22" height="8" className="inline align-middle mr-1">
          <line x1="1" y1="4" x2="14" y2="4" stroke="var(--text-muted)" strokeWidth="2" strokeLinecap="round" />
          <circle cx="17" cy="4" r="3.6" fill="var(--text-muted)" stroke="var(--text-muted)" strokeWidth="2" />
        </svg>settled</span>
        <span>colour is the group · each dot is a meeting that discussed it</span>
      </figcaption>
    </figure>
  )
}
