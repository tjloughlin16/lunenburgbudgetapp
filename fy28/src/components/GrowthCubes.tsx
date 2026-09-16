import { usdShort } from '../model/engine'
import { DEVELOPMENT } from '../model/answers'

/** THE REQUIRED GROWTH, AS A TOWN YOU CAN SEE. Concept art, not a chart.
 *
 *  TJ, 16 September 2026: "I imagine it as modern looking cubes. The current
 *  development scale are something like white cubes. the required growth is in relation
 *  to the current development size, but in a new color, and each year gets a slightly
 *  different distinct color ... mostly concept art. not a CHART. So people 'feel' it ...
 *  scattered, like its showing business spread throughout a town (but obviously with not
 *  a TON of whitespace between) ... the 'cubes' represent buildings."
 *
 *  So: one isometric ground, a town's worth of blocks. Each block is one typical
 *  Lunenburg development -- the model's own mix of a shop, a restaurant, a plaza, a
 *  warehouse, storage and a solar array, at its assessed value. The grey blocks are
 *  everything commercial, industrial and personal the town has today, scattered across
 *  the ground the way businesses are. Each year's required additions arrive in a deeper
 *  blue and fill in around them, from the middle outward, until the town is mostly new.
 *  Nothing is typed: the counts are the model's (rule 2), and they are what the page's
 *  first finding says in words.
 *
 *  The scatter is seeded, so the picture is the same on every build and in print.
 *  Deliberately no axis, no gridlines, no tooltip: the numbers are under it. */

const MIX = DEVELOPMENT.mixValue
const BASE = Math.max(1, Math.round(DEVELOPMENT.existingBase / MIX))
const PER_YEAR = Math.max(1, Math.round(DEVELOPMENT.fiveYear.developments))
const YEARS = 5
/** Five steps of one hue, deepening: the years read as one thing growing. Fixed colours
 *  on purpose -- the same picture in both themes and on paper. */
const YEAR_HUES = ['#a5c8fa', '#6ea8f5', '#3b82f6', '#2563eb', '#1e3a8a']
const TODAY = { top: '#eceef1', edge: '#9ca3af' }

/** A small seeded PRNG (mulberry32) so the scatter never changes between builds. */
function rng(seed: number) {
  return () => {
    seed |= 0; seed = (seed + 0x6D2B79F5) | 0
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

function shade(hex: string, f: number): string {
  const n = parseInt(hex.slice(1), 16)
  const ch = (x: number) => Math.max(0, Math.min(255, Math.round(x * f)))
  return `#${((ch((n >> 16) & 255) << 16) | (ch((n >> 8) & 255) << 8) | ch(n & 255)).toString(16).padStart(6, '0')}`
}

type Block = { i: number; j: number; h: number; w: number; d: number; top: string; edge: string; year: number }

/** Lay the town out: a jittered grid big enough for every block with a few streets
 *  left empty, today's businesses spread evenly across it, each year's additions
 *  taking the nearest empty lots to the centre. */
function layout(): Block[] {
  const total = BASE + PER_YEAR * YEARS
  const cols = Math.ceil(Math.sqrt(total * 1.55 * 1.6))
  const rows = Math.ceil((total * 1.55) / cols)
  const r = rng(20260916)
  // Streets: every sixth column and fifth row stay empty, so the ground reads as a map
  // with blocks on it rather than as a solid mass -- the way a map shows a town.
  const cells: { i: number; j: number }[] = []
  for (let j = 0; j < rows; j++) for (let i = 0; i < cols; i++) if (i % 6 !== 3 && j % 5 !== 2) cells.push({ i, j })
  // Shuffle, then take today's blocks from across the whole ground -- scattered.
  for (let n = cells.length - 1; n > 0; n--) { const m = Math.floor(r() * (n + 1)); [cells[n], cells[m]] = [cells[m], cells[n]] }
  const today = cells.slice(0, BASE)
  // The rest, by distance from the centre with a little noise, so each year's colour
  // grows outward from the middle of town rather than appearing at random.
  const ci = (cols - 1) / 2, cj = (rows - 1) / 2
  const rest = cells.slice(BASE)
    .map(c => ({ c, d: Math.hypot((c.i - ci) / cols, (c.j - cj) / rows) + (r() - 0.5) * 0.12 }))
    .sort((a, b) => a.d - b.d).map(x => x.c)
  // A building on a map is a low box with its own outline: mostly one storey, a few
  // taller, and a footprint that is not the whole lot and not square.
  const shape = () => ({ h: [1, 1, 1, 1.6, 1.6, 2.4][Math.floor(r() * 6)], w: 0.55 + r() * 0.4, d: 0.55 + r() * 0.4 })
  const blocks: Block[] = today.map(c => ({ ...c, ...shape(), top: TODAY.top, edge: TODAY.edge, year: 0 }))
  let k = 0
  for (let y = 0; y < YEARS; y++) {
    for (let n = 0; n < PER_YEAR && k < rest.length; n++, k++) {
      blocks.push({ ...rest[k], ...shape(), top: YEAR_HUES[y], edge: shade(YEAR_HUES[y], 0.72), year: y + 1 })
    }
  }
  return blocks
}

const BLOCKS = layout()
const W = 18          // a lot's width on the ground, in px
const U = 6           // one storey, in px -- low, the way a map draws them
const GROUND = '#f3f4f6'
const GROUND_EDGE = '#e5e7eb'
const TODAY_SIDE = 0.9

export function GrowthCubes() {
  const px = (i: number, j: number) => ({ x: (i - j) * (W / 2), y: (i + j) * (W / 4) })
  const pts = BLOCKS.map(b => px(b.i, b.j))
  const minX = Math.min(...pts.map(p => p.x)) - W, maxX = Math.max(...pts.map(p => p.x)) + W
  const minY = Math.min(...pts.map(p => p.y)) - U * 4 - W / 2, maxY = Math.max(...pts.map(p => p.y)) + W
  const ordered = [...BLOCKS].sort((a, b) => (a.i + a.j) - (b.i + b.j))
  // The ground: the diamond the grid sits on, drawn first.
  const maxI = Math.max(...BLOCKS.map(b => b.i)) + 1, maxJ = Math.max(...BLOCKS.map(b => b.j)) + 1
  const g = [px(-0.5, -0.5), px(maxI - 0.5, -0.5), px(maxI - 0.5, maxJ - 0.5), px(-0.5, maxJ - 0.5)]
  const ground = g.map(p => `${p.x},${p.y}`).join(' ')
  const legend = [{ label: 'Today', n: BASE, hue: TODAY.top, edge: TODAY.edge },
    ...YEAR_HUES.map((h, y) => ({ label: `Year ${y + 1}`, n: PER_YEAR, hue: h, edge: shade(h, 0.6) }))]
  return (
    <figure className="mt-8 mb-2" aria-label="The required growth, as a town of buildings">
      <div className="overflow-x-auto">
        <svg viewBox={`${minX} ${minY} ${maxX - minX} ${maxY - minY}`} className="w-full"
          style={{ minWidth: 560, maxHeight: 460 }} role="img"
          aria-label={`Today's commercial base is about ${BASE} typical developments, scattered across town; holding the gap adds about ${PER_YEAR} more a year for five years, ${PER_YEAR * YEARS} in all.`}>
          <polygon points={ground} fill={GROUND} stroke={GROUND_EDGE} strokeWidth={1} />
          {ordered.map((b, n) => {
            // A box of footprint w x d lots, h storeys, at lot (i, j): its four ground
            // corners in iso, lifted by the height for the roof.
            const hh = b.h * U
            const c = (di: number, dj: number, up = 0) => { const p = px(b.i + di, b.j + dj); return `${p.x},${p.y - up}` }
            const w = b.w / 2, d = b.d / 2
            const roof = [c(-w, -d, hh), c(w, -d, hh), c(w, d, hh), c(-w, d, hh)].join(' ')
            const left = [c(-w, d, hh), c(w, d, hh), c(w, d), c(-w, d)].join(' ')   // the face toward the viewer's left
            const right = [c(w, -d, hh), c(w, d, hh), c(w, d), c(w, -d)].join(' ')  // ... and right
            const side = b.year === 0 ? TODAY_SIDE : 0.84
            return (
              <g key={n}>
                <polygon points={left} fill={shade(b.top, side)} stroke={b.edge} strokeWidth={0.4} strokeLinejoin="round" />
                <polygon points={right} fill={shade(b.top, side - 0.14)} stroke={b.edge} strokeWidth={0.4} strokeLinejoin="round" />
                <polygon points={roof} fill={b.top} stroke={b.edge} strokeWidth={0.4} strokeLinejoin="round" />
              </g>
            )
          })}
        </svg>
      </div>
      <div className="flex flex-wrap gap-x-5 gap-y-1.5 mt-3 text-[12px]" aria-label="Key">
        {legend.map(l => (
          <span key={l.label} className="inline-flex items-center gap-1.5">
            <span aria-hidden="true" style={{ width: 12, height: 12, background: l.hue, border: `1px solid ${l.edge}`, display: 'inline-block', borderRadius: 2 }} />
            <span className="font-semibold">{l.label}</span>
            <span className="tnum" style={{ color: 'var(--text-muted)' }}>{l.label === 'Today' ? `${l.n} buildings’ worth` : `+${l.n}`}</span>
          </span>
        ))}
      </div>
      <figcaption className="text-[12.5px] mt-2 max-w-3xl leading-snug" style={{ color: 'var(--text-muted)' }}>
        Each building is one typical Lunenburg development, about {usdShort(MIX)} of assessed value in the model&rsquo;s own mix. Grey is everything commercial, industrial and personal the town has today &mdash; about {BASE} of them. Each year&rsquo;s blue is what would have to be added to hold the gap for five years: about {PER_YEAR} a year, {PER_YEAR * YEARS} in all, until most of the town is new. A projection, drawn to count; the streets are invented.
      </figcaption>
    </figure>
  )
}
