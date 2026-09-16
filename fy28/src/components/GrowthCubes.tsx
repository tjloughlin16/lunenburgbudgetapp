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

type Block = { u: number; v: number; h: number; w: number; d: number; tone: number; top: string; year: number }

/** LAY THE TOWN OUT WITHOUT A GRID, LEFT TO RIGHT. TJ: "We're a farmtown. It has to be
 *  scattered looking" -- and then: "starting with today on the left, and growing to the
 *  right will make the point more." It does: a reader's eye already reads left-to-right
 *  as time, and six clusters side by side let the size of five years' growth be seen
 *  against the size of the town that exists, which is the whole finding.
 *
 *  Each group is a loose blob whose radius comes from its count at one density, so
 *  today's 51 is visibly bigger than any one year's 28 and the five years together are
 *  visibly bigger than today. The blobs overlap a little at the edges, so it reads as
 *  one town spreading along a corridor rather than six piles. Buildings are dropped at
 *  random inside each blob and rejected if they would sit on another. */
const DENSITY = 0.42      // buildings per square unit of ground
const MIN_GAP = 1.15      // centre-to-centre, in ground units, before two overlap

function layout(): Block[] {
  const r = rng(20260916)
  const counts = [BASE, ...Array(YEARS).fill(PER_YEAR) as number[]]
  const radii = counts.map(n => Math.sqrt(n / (DENSITY * Math.PI)))
  // Centres along the ground's diagonal (u up, v down), which is screen-right in this
  // projection; each blob starts where the last one's edge is, less a little overlap.
  const centres: number[] = []
  let edge = 0
  radii.forEach((rad, k) => { const c = k === 0 ? 0 : edge + rad - 0.6; centres.push(c); edge = c + rad })
  const placed: Block[] = []
  // Less like cubes, more like buildings: long low ones, tall thin ones, and a little
  // tonal drift per building so no two are the same colour.
  const shape = () => {
    const long = r() < 0.3
    return { h: 0.55 + r() * (r() < 0.2 ? 2.2 : 1.1), w: long ? 0.9 + r() * 0.7 : 0.4 + r() * 0.5, d: long ? 0.4 + r() * 0.3 : 0.4 + r() * 0.5, tone: 0.93 + r() * 0.1 }
  }
  counts.forEach((n, k) => {
    let done = 0, tries = 0
    while (done < n && tries < n * 400) {
      tries++
      // Uniform in the disc by area, with a soft edge so neighbouring years mingle.
      const rr = Math.sqrt(r()) * radii[k] + (r() - 0.5) * 0.5
      const a = r() * Math.PI * 2
      // The corridor runs along (u, -v): a step of t along it is u += t/√2, v -= t/√2.
      const t = centres[k] + rr * Math.cos(a), n2 = rr * Math.sin(a) * 0.85
      const u = (t + n2) / Math.SQRT2, v = (-t + n2) / Math.SQRT2
      if (placed.every(p => Math.hypot(p.u - u, p.v - v) >= MIN_GAP)) {
        placed.push({ u, v, ...shape(), top: k === 0 ? TODAY.top : YEAR_HUES[k - 1], year: k })
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
  // Stretched sideways: the page is wide and the picture is allowed half a screen of
  // height, so the town is drawn long rather than letterboxed in a square.
  const px = (u: number, v: number) => ({ x: (u - v) * (W / 2) * 1.55, y: (u + v) * (W / 4) })
  const pts = BLOCKS.map(b => px(b.u, b.v))
  const minX = Math.min(...pts.map(p => p.x)) - W, maxX = Math.max(...pts.map(p => p.x)) + W
  const minY = Math.min(...pts.map(p => p.y)) - U * 3 - W / 2, maxY = Math.max(...pts.map(p => p.y)) + W
  const ordered = [...BLOCKS].sort((a, b) => (a.u + a.v) - (b.u + b.v))
  const legend = [{ label: 'Today', n: BASE, hue: TODAY.top },
    ...YEAR_HUES.map((h, y) => ({ label: `Year ${y + 1}`, n: PER_YEAR, hue: h }))]
  return (
    <figure className="mt-8 mb-2" aria-label="The required growth, as a town of buildings">
      {/* FULL BLEED. The report column is narrow for reading; a picture is not read, and
          TJ: "make sure it takes up the full width of the screen". The wrapper breaks
          out of the column to the viewport's edges; the caption stays in the column. */}
      <div className="overflow-x-auto" style={{ width: '100vw', marginLeft: 'calc(50% - 50vw)' }}>
        <svg viewBox={`${minX} ${minY} ${maxX - minX} ${maxY - minY}`} className="w-full block"
          style={{ maxHeight: '50vh' }} preserveAspectRatio="xMidYMid meet" role="img"
          aria-label={`Today's commercial base is about ${BASE} typical developments, the white cluster on the left; holding the gap adds about ${PER_YEAR} more a year for five years, each year a cluster further right.`}>
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
            const top = shade(b.top, Math.min(b.tone, b.year === 0 ? 1 : 1.04))
            // A soft shadow on the ground, cast to the lower right, is what makes a box
            // sit on a surface instead of float on the page.
            const shadow = [c(-w + 0.18, -d + 0.1), c(w + 0.45, -d + 0.1), c(w + 0.45, d + 0.35), c(-w + 0.18, d + 0.35)].join(' ')
            return (
              <g key={n}>
                <polygon points={shadow} fill="rgba(15, 23, 42, 0.10)" />
                <polygon points={left} fill={shade(top, k)} />
                <polygon points={right} fill={shade(top, k - 0.16)} />
                <polygon points={roof} fill={top} />
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
        Each building is one typical Lunenburg development, about {usdShort(MIX)} of assessed value in the model&rsquo;s own mix. The white cluster on the left is everything commercial, industrial and personal the town has today &mdash; about {BASE} of them. Each cluster to its right is one year of what would have to be added to hold the gap for five years: about {PER_YEAR} a year, {PER_YEAR * YEARS} in all. A projection, drawn to count; the layout is invented.
      </figcaption>
    </figure>
  )
}
