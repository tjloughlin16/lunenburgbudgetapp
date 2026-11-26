/** BIG FIGURES (the FY2026 closeout hub, 25 November 2026).
 *
 *  TJ: "on the hub, i need to see 2 numbers i think: the official surplus in a big number, and
 *  the upper-end surplus number if you count the prepay". Two or three figures, large, side by
 *  side, each with one line saying what it is. A figure that is OUR arithmetic carries the amber
 *  rule and the "our estimate" tag every other estimate on the site carries (rule 3), so the
 *  official figure and ours can never read as two readings of equal standing. Every string is
 *  formatted and checked by the generator; this prints the text. */
import type { CustomProps } from './index'

type Fig = { value: string; label: string; kind: 'published' | 'estimate'; tag: string }
type Data = { figures: Fig[] }

export default function BigFigures({ data, alt }: CustomProps) {
  const d = data as Data
  return (
    <div aria-label={alt} className="max-w-3xl grid grid-cols-1 sm:grid-cols-2 gap-4">
      {d.figures.map((f, i) => {
        const est = f.kind === 'estimate'
        return (
          <div key={i} className="py-1 pl-4"
            style={{ borderLeft: `4px solid ${est ? 'var(--status-warning)' : 'var(--text-primary)'}` }}>
            <p className="text-[40px] sm:text-[44px] leading-none font-bold tabular-nums"
              style={{ color: est ? 'var(--text-secondary)' : 'var(--text-primary)' }}>{f.value}</p>
            <p className="text-[14.5px] leading-snug mt-2" style={{ color: 'var(--text-secondary)' }}>{f.label}</p>
            <p className="text-[10.5px] font-semibold uppercase tracking-widest mt-1.5"
              style={{ color: est ? 'var(--status-warning)' : 'var(--text-muted)' }}>{f.tag}</p>
          </div>
        )
      })}
    </div>
  )
}
