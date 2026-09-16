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
const YEAR_HUES = ['#bfdbfe', '#7fb3f7', '#3b82f6', '#1d4ed8', '#172554']
const TODAY = { top: '#f4f5f7' }

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

type Block = { u: number; v: number; h: number; w: number; d: number; top: string; year: number }

/** LAY THE TOWN OUT WITHOUT A GRID. TJ: "We're a farmtown. It has to be scattered
 *  looking." Buildings are dropped at random on the ground, rejecting any that would sit
 *  on another, and the colours are kept apart by RADIUS: today's town is the white
 *  cluster in the middle, and each year's additions form the next ring out, so the eye
 *  reads the growth as growth -- the town getting bigger around what is already there.
 *  The ring radii come from the counts: each band has the area its buildings need at
 *  one density, so a ring of 28 is visibly the same size as the next ring of 28 and
 *  the centre of 51 is visibly bigger than either. */
const DENSITY = 0.42      // buildings per square unit of ground
const MIN_GAP = 1.05      // centre-to-centre, in ground units, before two overlap

function layout(): Block[] {
  const r = rng(20260916)
  const counts = [BASE, ...Array(YEARS).fill(PER_YEAR) as number[]]
  const radii: number[] = [0]
  let cum = 0
  for (const n of counts) { cum += n; radii.push(Math.sqrt(cum / (DENSITY * Math.PI))) }
  const placed: Block[] = []
  const shape = () => ({ h: [0.8, 1, 1, 1.3, 1.7][Math.floor(r() * 5)], w: 0.5 + r() * 0.4, d: 0.5 + r() * 0.4 })
  counts.forEach((n, band) => {
    const r0 = radii[band], r1 = radii[band + 1]
    let done = 0, tries = 0
    while (done < n && tries < n * 400) {
      tries++
      // Uniform in the annulus by area, with a soft edge so rings blend rather than snap.
      const rr = Math.sqrt(r0 * r0 + r() * (r1 * r1 - r0 * r0)) + (r() - 0.5) * 0.35
      const a = r() * Math.PI * 2
      const u = rr * Math.cos(a), v = rr * Math.sin(a)
      if (placed.every(p => Math.hypot(p.u - u, p.v - v) >= MIN_GAP)) {
        const top = band === 0 ? TODAY.top : YEAR_HUES[band - 1]
        placed.push({ u, v, ...shape(), top, year: band })
        done++
      }
    }
  })
  return placed
}

const BLOCKS = layout()
const W = 20          // one ground unit, in px
const U = 7           // one storey, in px

export function GrowthCubes() {
  const px = (u: number, v: number) => ({ x: (u - v) * (W / 2), y: (u + v) * (W / 4) })
  const pts = BLOCKS.map(b => px(b.u, b.v))
  const minX = Math.min(...pts.map(p => p.x)) - W, maxX = Math.max(...pts.map(p => p.x)) + W
  const minY = Math.min(...pts.map(p => p.y)) - U * 3 - W / 2, maxY = Math.max(...pts.map(p => p.y)) + W
  const ordered = [...BLOCKS].sort((a, b) => (a.u + a.v) - (b.u + b.v))
  const legend = [{ label: 'Today', n: BASE, hue: TODAY.top },
    ...YEAR_HUES.map((h, y) => ({ label: `Year ${y + 1}`, n: PER_YEAR, hue: h }))]
  return (
    <figure className="mt-8 mb-2" aria-label="The required growth, as a town of buildings">
      <div className="overflow-x-auto">
        <svg viewBox={`${minX} ${minY} ${maxX - minX} ${maxY - minY}`} className="w-full"
          style={{ minWidth: 560, maxHeight: '50vh' }} role="img"
          aria-label={`Today's commercial base is about ${BASE} typical developments, the white cluster in the middle; holding the gap adds about ${PER_YEAR} more a year for five years, each year a ring further out.`}>
          {ordered.map((b, n) => {
            // A box of footprint w x d, h storeys, centred at (u, v). No outlines: the
            // three faces at three shades are the silhouette, which is what a building
            // is from the air.
            const hh = b.h * U
            const c = (du: number, dv: number, up = 0) => { const p = px(b.u + du, b.v + dv); return `${p.x},${p.y - up}` }
            const w = b.w / 2, d = b.d / 2
            const roof = [c(-w, -d, hh), c(w, -d, hh), c(w, d, hh), c(-w, d, hh)].join(' ')
            const left = [c(-w, d, hh), c(w, d, hh), c(w, d), c(-w, d)].join(' ')
            const right = [c(w, -d, hh), c(w, d, hh), c(w, d), c(w, -d)].join(' ')
            const k = b.year === 0 ? 0.86 : 0.82
            return (
              <g key={n}>
                <polygon points={left} fill={shade(b.top, k)} />
                <polygon points={right} fill={shade(b.top, k - 0.16)} />
                <polygon points={roof} fill={b.top} />
              </g>
            )
          })}
        </svg>
      </div>
      <div className="flex flex-wrap gap-x-5 gap-y-1.5 mt-3 text-[12px]" aria-label="Key">
        {legend.map(l => (
          <span key={l.label} className="inline-flex items-center gap-1.5">
            <span aria-hidden="true" style={{ width: 12, height: 12, background: l.hue, boxShadow: `inset -3px -3px 0 ${shade(l.hue, 0.72)}`, display: 'inline-block', borderRadius: 2 }} />
            <span className="font-semibold">{l.label}</span>
            <span className="tnum" style={{ color: 'var(--text-muted)' }}>{l.label === 'Today' ? `${l.n} buildings’ worth` : `+${l.n}`}</span>
          </span>
        ))}
      </div>
      <figcaption className="text-[12.5px] mt-2 max-w-3xl leading-snug" style={{ color: 'var(--text-muted)' }}>
        Each building is one typical Lunenburg development, about {usdShort(MIX)} of assessed value in the model&rsquo;s own mix. The white cluster is everything commercial, industrial and personal the town has today &mdash; about {BASE} of them. Each ring out is one year of what would have to be added to hold the gap for five years: about {PER_YEAR} a year, {PER_YEAR * YEARS} in all. A projection, drawn to count; the layout is invented.
      </figcaption>
    </figure>
  )
}
