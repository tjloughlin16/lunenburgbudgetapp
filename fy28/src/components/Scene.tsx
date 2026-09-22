/* CONCEPT ART, NOT A CHART -- the same instrument as `GrowthCubes` on
 * /commercial-development, which says it best in its own header: so people FEEL it.
 *
 * TJ, 22 September 2026: *"not a 'chart' so much as chart-like. So a conceptual and
 * interesting image that shows the proportions, but not in a structured chart way...
 * meaning, there are a bunch of school buildings next to police cars, or something like
 * that."*
 *
 * The proportion is still exact -- one glyph is one unit and the counts are the data --
 * but the arrangement is a crowd rather than a table. No axis, no row labels, no tooltip:
 * the numbers are in the legend under it and in the table further down the page.
 *
 * THE SCATTER IS DETERMINISTIC, from a hash of the index rather than a running seed, so
 * the picture is identical on every render, in print, and between this and the SVG the
 * markdown carries for /docs and the PDF. The same arithmetic is in scripts/pictograms.py
 * -- `scene_layout` -- which is what keeps the two drawings the same town. */

export type SceneItem = { glyph: string; colour: string }
export type SceneKey = { label: string; note: string; colour: string }

export function Scene({
  items, keys, cols = 30, cell = 30, label,
}: {
  items: SceneItem[]
  keys: SceneKey[]
  cols?: number
  cell?: number
  label: string
}) {
  const rows = Math.ceil(items.length / cols)
  const W = cols * cell
  const H = rows * cell
  return (
    <div>
      {/* NO `vw` MATH. The first version broke out with `width: calc(100vw - 48px)` and
          `marginLeft: calc(50% - 50vw + 24px)`, which is the trick `GrowthCubes` uses --
          and here it produced a picture flush against the left edge with a gap on the
          right. Two reasons, both of which that page does not have: `100vw` INCLUDES the
          scrollbar, so the element is wider than what is visible, and this column is not
          centred in the viewport, so `50% - 50vw` does not resolve to the left edge.

          So the picture fills its container and the container is widened instead. The
          page's own padding then applies on both sides, which is what symmetric means. */}
      <div style={{ width: '100%' }}>
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full block" role="img"
          aria-label={label} preserveAspectRatio="xMidYMid meet"
          style={{ maxHeight: '50vh' }}>
          {items.map((it, i) => {
          // A grid with the corners knocked off: a plain grid reads as a table and a free
          // scatter reads as noise, so each glyph is displaced by up to a fifth of its
          // cell and varied slightly in size.
          const h = Math.imul(i, 2654435761) ^ 20260922
          const r1 = ((h >>> 8) & 0xffff) / 65535
          const r2 = ((h >>> 20) & 0xfff) / 4095
          const r3 = (h & 0xff) / 255
          const col = i % cols
          const row = Math.floor(i / cols)
          const jitter = 0.22
          const x = (col + 0.5 + (r1 - 0.5) * jitter * 2) * cell
          const y = (row + 0.5 + (r2 - 0.5) * jitter * 2) * cell
          const g = cell * (0.88 + r3 * 0.24)
          return (
            <g key={i} transform={`translate(${x - g / 2},${y - g / 2}) scale(${g / 24})`}
              fill={it.colour} opacity={0.92}>
              <path d={it.glyph} />
            </g>
          )
          })}
        </svg>
      </div>
      <ul className="mt-3 flex flex-wrap gap-x-5 gap-y-1.5 list-none p-0 m-0 text-[12px]">
        {keys.map(k => (
          <li key={k.label} className="flex items-baseline gap-2">
            <span aria-hidden className="inline-block rounded-[2px]"
              style={{ width: 10, height: 10, background: k.colour,
                       transform: 'translateY(1px)' }} />
            <span style={{ color: 'var(--text-primary)' }}>{k.label}</span>
            <span className="tnum" style={{ color: 'var(--text-muted)' }}>{k.note}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
