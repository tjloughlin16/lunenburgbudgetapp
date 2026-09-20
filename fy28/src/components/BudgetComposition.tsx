import { useState } from 'react'
import { usd, usdShort } from '../model/engine'
import { RATE_LINES, type Bucket } from '../model/rates'

/** The whole school budget, before anything is done to it.
 *
 *  Kristina Skrehot, 19 September 2026, having read the rate sliders: "It would help to
 *  also show the overall budget with these categories as a pie chart at the start of the
 *  information somewhere to ground people's understanding of the budget."
 *
 *  She is right, and the mistake is rule 7a's: the walkthrough showed the parts moving
 *  two rooms before it showed what the whole was. A reader who has not seen the
 *  denominator cannot read a share.
 *
 *  A BAR RATHER THAN A PIE, and the reason is measured rather than stylistic. The sliders
 *  carry seven buckets; seven categorical hues do not survive the palette validator here
 *  (two below the chroma floor, CVD separation ΔE 5.4, normal-vision floor ΔE 12.8). Four
 *  grouped segments do, and a horizontal bar is the form for part-to-whole with long
 *  category names. The seven are not lost — they are the table underneath, under the
 *  sliders' own labels, which is also the relief the amber's 2.36:1 contrast requires.
 *
 *  EVERY FIGURE COMES FROM RATE_LINES, which is what the sliders themselves are drawn
 *  from. That is deliberate: a composition chart that could disagree with the controls
 *  below it would be worse than no chart. There is no second derivation here to drift. */

type Group = { id: string; label: string; hue: string; parts: Bucket[]; gloss: string }

/** Four groups, and the grouping is an argument rather than a convenience: it is the
 *  shape room 5 is about to make — most of the budget is people, a fifth is special
 *  education, insurance is the third thing, and what the Committee controls is the rest. */
const GROUPS: Group[] = [
  { id: 'pay', label: 'Staff pay', hue: 'var(--bud-pay)', parts: ['salaries'],
    gloss: 'Teachers, administrators, custodians, nurses — every position except special education' },
  { id: 'sped', label: 'Special education', hue: 'var(--bud-sped)',
    parts: ['sped', 'sped_tuition'],
    gloss: 'Staff here, and tuition where a child’s plan requires another school' },
  { id: 'health', label: 'Health insurance', hue: 'var(--bud-health)', parts: ['health'],
    gloss: 'Bought by the Town, not by the school district' },
  { id: 'else', label: 'Everything else', hue: 'var(--bud-else)',
    parts: ['other', 'transport', 'utilities'],
    gloss: 'Supplies, technology, athletics, clubs, buses, heat and light' },
]

const LINE = Object.fromEntries(RATE_LINES.map(l => [l.key, l])) as
  Record<Bucket, typeof RATE_LINES[number]>

const TOTAL = RATE_LINES.reduce((s, l) => s + l.amount, 0)

const rows = GROUPS.map(g => {
  const amount = g.parts.reduce((s, k) => s + LINE[k].amount, 0)
  return { ...g, amount, share: amount / TOTAL }
})

const pct = (x: number, d = 1) => `${(x * 100).toFixed(d)}%`

export function BudgetComposition() {
  const [open, setOpen] = useState(false)
  const [hot, setHot] = useState<string | null>(null)

  return (
    <figure className="card p-4 sm:p-5 my-5">
      {/* The figure leads with the total, because the total IS the point of the figure.
          A reader who takes nothing else from it should leave knowing the size. */}
      <figcaption className="mb-3">
        <div className="text-[11px] uppercase tracking-wide font-semibold"
          style={{ color: 'var(--text-muted)' }}>The school budget, whole</div>
        <div className="text-[26px] sm:text-[32px] font-bold tnum leading-none mt-1">
          {usd(TOTAL)}
        </div>
        <p className="text-[12.5px] leading-relaxed mt-1.5"
          style={{ color: 'var(--text-secondary)' }}>
          FY27 as adopted, plus the programs restored since. This is the whole that every
          share below is a share <em>of</em> — and the same figure the rate controls act on.
        </p>
      </figcaption>

      {/* THE BAR. 2px surface gaps between fills, rounded outer ends only, so the bar
          reads as one quantity cut up rather than four bars pushed together. */}
      <div className="flex w-full h-11 sm:h-12" role="img"
        aria-label={rows.map(r => `${r.label} ${pct(r.share)}`).join('; ')}>
        {rows.map((r, i) => (
          <div key={r.id}
            onMouseEnter={() => setHot(r.id)} onMouseLeave={() => setHot(null)}
            className="relative h-full transition-[filter] duration-150"
            style={{
              width: `${r.share * 100}%`,
              background: r.hue,
              marginLeft: i === 0 ? 0 : 2,
              borderTopLeftRadius: i === 0 ? 4 : 0,
              borderBottomLeftRadius: i === 0 ? 4 : 0,
              borderTopRightRadius: i === rows.length - 1 ? 4 : 0,
              borderBottomRightRadius: i === rows.length - 1 ? 4 : 0,
              filter: hot && hot !== r.id ? 'saturate(0.45) opacity(0.55)' : 'none',
            }}>
            {/* Direct label INSIDE the segment where it fits. Four segments, four labels —
                the guidance allows direct labels up to four, and the two narrow ones fall
                back to the legend rather than colliding. */}
            {r.share > 0.13 && (
              <span className="absolute inset-0 flex items-center justify-center
                               text-[12px] sm:text-[13px] font-bold tnum"
                style={{ color: '#ffffff' }}>{pct(r.share, 0)}</span>
            )}
          </div>
        ))}
      </div>

      {/* THE LEGEND, always present, and carrying the share for the segments too narrow to
          label in place. Identity is never colour alone: every row has its name. */}
      <ul className="mt-3 grid gap-x-5 gap-y-2 sm:grid-cols-2">
        {rows.map(r => (
          <li key={r.id} className="flex items-baseline gap-2"
            onMouseEnter={() => setHot(r.id)} onMouseLeave={() => setHot(null)}>
            <span className="inline-block shrink-0 rounded-[2px]"
              style={{ width: 10, height: 10, background: r.hue, transform: 'translateY(1px)' }}
              aria-hidden="true" />
            <div className="min-w-0">
              <div className="text-[13px] leading-tight">
                <span className="font-semibold">{r.label}</span>{' '}
                <span className="tnum" style={{ color: 'var(--text-secondary)' }}>
                  {pct(r.share)} · {usdShort(r.amount)}
                </span>
              </div>
              <div className="text-[11.5px] leading-snug mt-0.5"
                style={{ color: 'var(--text-muted)' }}>{r.gloss}</div>
            </div>
          </li>
        ))}
      </ul>

      {/* THE TABLE TWIN. All seven buckets under the names the sliders use, so a reader can
          carry a row from here to a control two rooms down and know it is the same thing.
          Collapsed by default: rule 7b, the raw comes after the conclusion, not before. */}
      <div className="mt-3 pt-3" style={{ borderTop: '1px solid var(--grid)' }}>
        <button type="button" onClick={() => setOpen(o => !o)}
          aria-expanded={open}
          className="text-[12.5px] font-semibold"
          style={{ color: 'var(--series-cost)' }}>
          {open ? 'Hide' : 'Show'} all seven lines, as the controls name them
        </button>
        {open && (
          <div className="overflow-x-auto mt-2.5">
            <table className="w-full text-[12.5px]">
              <thead>
                <tr style={{ color: 'var(--text-muted)' }} className="text-left">
                  <th className="font-semibold py-1 pr-3">Line</th>
                  <th className="font-semibold py-1 pr-3 text-right">FY27</th>
                  <th className="font-semibold py-1 text-right">Share</th>
                </tr>
              </thead>
              <tbody>
                {rows.flatMap(g => g.parts.map(k => (
                  <tr key={k} style={{ borderTop: '1px solid var(--grid)' }}>
                    <td className="py-1.5 pr-3">
                      <span className="inline-block rounded-[2px] mr-2"
                        style={{ width: 8, height: 8, background: g.hue }} aria-hidden="true" />
                      {LINE[k].label}
                    </td>
                    <td className="py-1.5 pr-3 text-right tnum">{usd(LINE[k].amount)}</td>
                    <td className="py-1.5 text-right tnum">{pct(LINE[k].amount / TOTAL)}</td>
                  </tr>
                )))}
                <tr style={{ borderTop: '2px solid var(--axis)' }}>
                  <td className="py-1.5 pr-3 font-bold">Total</td>
                  <td className="py-1.5 pr-3 text-right tnum font-bold">{usd(TOTAL)}</td>
                  <td className="py-1.5 text-right tnum font-bold">100%</td>
                </tr>
              </tbody>
            </table>
            <p className="text-[11.5px] leading-snug mt-2" style={{ color: 'var(--text-muted)' }}>
              <strong>Salaries</strong> is every position except special education staff,
              which has its own line — about {usdShort(LINE.sped.amount)} of people the
              state&rsquo;s account codes file under salaries and this model does not, because
              the two grow for different reasons.
            </p>
          </div>
        )}
      </div>
    </figure>
  )
}
