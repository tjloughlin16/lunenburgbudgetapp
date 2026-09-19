/** THE BANNER — an illustration, not a chart. TJ: "I meant..... just an interesting image."
 *
 *  It encodes nothing and should not be read for information: no axis, no scale, no datum.
 *  It is a picture of the word. Threads enter at the left edge, drift and cross the way
 *  matters cross boards, and then do one of two things — a few tie off in a knot, most run
 *  off the right edge still going. That is the whole of what this page is about, said
 *  without a sentence.
 *
 *  Drawn rather than photographed because the archive has no photograph it owns, and a
 *  stock picture of a town hall would be a decorative claim about a real place. Drawn
 *  DETERMINISTICALLY — every curve below is a fixed number, so it renders identically on
 *  every load and in the prerenderer, and a designer can move one and see exactly what
 *  moved. Colours come from the site's tokens, so it follows the theme rather than fighting
 *  it, and it sits at low opacity because a banner that competes with the page has stopped
 *  being a banner. `aria-hidden`: there is nothing here for a screen reader to gain. */

const W = 1000, H = 150

type T = { y: number; drift: number; tone: string; op: number; w: number; knot: number | null }

// Nine threads. `knot` is where one ties off, or null to run off the edge.
const THREADS: T[] = [
  { y: 22,  drift: 34,  tone: 'var(--series-cost)',    op: .55, w: 2.2, knot: null },
  { y: 40,  drift: -18, tone: 'var(--series-revenue)', op: .50, w: 1.8, knot: 742 },
  { y: 55,  drift: 26,  tone: 'var(--series-cost)',    op: .38, w: 1.6, knot: null },
  { y: 74,  drift: -30, tone: 'var(--brand)',          op: .55, w: 2.6, knot: null },
  { y: 88,  drift: 20,  tone: 'var(--series-revenue)', op: .42, w: 1.8, knot: 508 },
  { y: 103, drift: -14, tone: 'var(--series-cost)',    op: .48, w: 2.0, knot: null },
  { y: 118, drift: 30,  tone: 'var(--brand)',          op: .34, w: 1.5, knot: null },
  { y: 131, drift: -22, tone: 'var(--series-revenue)', op: .38, w: 1.7, knot: 884 },
  { y: 144, drift: 16,  tone: 'var(--series-cost)',    op: .30, w: 1.4, knot: null },
]

/** One thread: a long shallow S that drifts across its neighbours and keeps going. */
function path(t: T, end: number) {
  const { y, drift } = t
  return [
    `M -20 ${y}`,
    `C ${end * 0.18} ${y + drift * 0.9}, ${end * 0.30} ${y - drift * 0.7}, ${end * 0.46} ${y + drift * 0.25}`,
    `S ${end * 0.76} ${y - drift * 0.85}, ${end} ${y + drift * 0.15}`,
  ].join(' ')
}

export function ThreadsHero() {
  return (
    <div aria-hidden="true" className="mb-5 -mt-1" style={{ lineHeight: 0 }}>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" height="auto"
        preserveAspectRatio="none"
        style={{ display: 'block', maxHeight: 150, minHeight: 78 }}>
        <defs>
          {/* the running threads fade out as they leave, so the edge is not a cut */}
          <linearGradient id="th-fade" x1="0" x2="1">
            <stop offset="0" stopColor="white" stopOpacity="1" />
            <stop offset="0.72" stopColor="white" stopOpacity="1" />
            <stop offset="1" stopColor="white" stopOpacity="0" />
          </linearGradient>
          <mask id="th-mask">
            <rect x="-20" y="0" width={W + 20} height={H} fill="url(#th-fade)" />
          </mask>
        </defs>

        <g mask="url(#th-mask)" fill="none" strokeLinecap="round">
          {THREADS.map((t, i) => (
            <path key={i} d={path(t, t.knot ?? W + 20)} stroke={t.tone}
              strokeWidth={t.w} opacity={t.op} />
          ))}
        </g>

        {/* the ones that tie off — a small knot, drawn over the mask so it stays crisp */}
        {THREADS.filter(t => t.knot).map((t, i) => {
          const end = t.knot as number
          const ey = t.y + t.drift * 0.15
          return (
            <g key={`k${i}`} opacity={Math.min(t.op + 0.25, 1)}>
              <circle cx={end} cy={ey} r={t.w * 1.9} fill="var(--surface-1)" />
              <circle cx={end} cy={ey} r={t.w * 1.9} fill="none" stroke={t.tone} strokeWidth={t.w} />
            </g>
          )
        })}
      </svg>
    </div>
  )
}
