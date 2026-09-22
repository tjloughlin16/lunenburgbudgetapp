/* AN ISOTYPE CHART: a quantity drawn as repeated glyphs rather than as a bar.
 *
 * TJ, 22 September 2026: *"show PEOPLE that represent each department as characters in
 * proportion to the amounts"*, and for the budget *"a conceptual image that shows some
 * stereotypical image that represents each department (a police car for police, fire
 * truck for fire, construction vehicle for DPW, etc) in size proportion to the dollar
 * amounts."* Rule 7f's signature note: the best opening image is drawn in the units the
 * subject is actually made of.
 *
 * REPEATED, NOT SCALED. A reader cannot judge area -- a police car drawn twice as tall is
 * four times the ink and reads as somewhere between two and four. Twenty-five school
 * figures beside four fire figures is a ratio anyone can count off the page.
 *
 * THE UNIT IS PRINTED, ALWAYS. `one figure = 10 people` is the whole contract between the
 * picture and the number; without it this is decoration.
 *
 * A PARTIAL UNIT IS DRAWN PARTIAL. Three people against a unit of ten is a third of a
 * figure: rounded up the Assessing office would be drawn the same as the Library, and
 * rounded down it would not appear at all.
 *
 * The paths come from the PAYLOAD (scripts/pictograms.py writes them), so this and the
 * generated SVG in the markdown draw the same glyph by construction. */

export type PictoRow = {
  key: string
  label: string
  value: number
  note: string
  glyph: string
  colour: string
}

export function Pictogram({
  rows, unit, unitLabel, unitText, size = 20, gap = 3, max = 26,
}: {
  rows: PictoRow[]
  unit: number
  unitLabel: string
  /** How to say the unit in words. `1,000,000 dollars` is arithmetic; `$1 million` is
   *  English, and this line is the contract between the picture and the number. */
  unitText?: string
  size?: number
  gap?: number
  max?: number
}) {
  return (
    <div>
      <ul className="list-none p-0 m-0 flex flex-col gap-2">
        {rows.map(r => {
          // AN ID WITH A SPACE IN IT IS NOT A REFERENCE. The key is a department name --
          // `Department of Public Works` -- and `url(#pc-Department of Public Works)`
          // silently resolves to nothing, so every part-figure rendered WHOLE and the
          // DPW's fourteen people were drawn as twenty.
          const cid = `pc-${r.key.replace(/[^a-zA-Z0-9]+/g, '-')}`
          const n = unit ? r.value / unit : 0
          const full = Math.min(Math.floor(n), max)
          const frac = n - Math.floor(n)
          return (
            <li key={r.key} className="flex items-center gap-3">
              <span className="text-[12px] shrink-0"
                style={{ color: 'var(--text-primary)', width: 172 }}>{r.label}</span>
              <span className="flex items-center" style={{ gap }}
                role="img"
                aria-label={`${r.label}: ${r.note}`}>
                {Array.from({ length: full }, (_, i) => (
                  <svg key={i} width={size} height={size} viewBox="0 0 24 24"
                    aria-hidden focusable="false">
                    <path d={r.glyph} fill={r.colour} />
                  </svg>
                ))}
                {frac > 0.04 && full < max ? (
                  <svg width={size} height={size} viewBox="0 0 24 24"
                    aria-hidden focusable="false" opacity={0.55}>
                    <defs>
                      <clipPath id={cid}>
                        {/* A VISIBLE MINIMUM, the same 2.4 the generated SVG uses.
                          Central Purchasing is 8% of an icon, which at 16px is barely
                          more than a pixel and reads as an empty row. */}
                      <rect x="0" y="0" width={Math.max(24 * frac, 2.4)} height="24" />
                      </clipPath>
                    </defs>
                    <path d={r.glyph} fill={r.colour} clipPath={`url(#${cid})`} />
                  </svg>
                ) : null}
              </span>
              <span className="text-[12px] tnum shrink-0"
                style={{ color: 'var(--text-muted)' }}>{r.note}</span>
            </li>
          )
        })}
      </ul>
      <p className="text-[12px] mt-3 mb-0" style={{ color: 'var(--text-muted)' }}>
        One figure is {unitText ?? `${unit.toLocaleString()} ${unitLabel}`}. A part-figure
        is a department that does not reach one whole unit.
      </p>
    </div>
  )
}
