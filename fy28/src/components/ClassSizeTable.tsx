import { Fragment } from 'react'

/** The class-size rule, drawn: the tiers it sets, and a room read against them.
 *
 *  WHY THIS IS ITS OWN COMPONENT AND NOT A GENERIC TABLE. Every other table on this site
 *  is a series -- years down the side, figures across. This one is a RULE, and the two
 *  things a reader has to see at a glance are the column that never changes (one educator,
 *  in every tier, in both age bands) and the fact that the numbers are a ceiling on
 *  CHILDREN rather than a description of staffing.
 *
 *  RULE 2 ABSOLUTELY. Nothing here holds, computes or rounds a figure. Every count, every
 *  citation and every quoted phrase arrives from `sped-regulation.json`, which parsed each
 *  one out of the sentence in 603 CMR 28.00 that states it. A number typed into this file
 *  would be a class-size rule nothing recomputes, which is exactly the defect rule 2
 *  exists for -- and this is a page people will quote at meetings. */

export type Tier = {
  setting: string; short: string; cite: string
  band: string; ages: string; role: string
  separateness: string; separateness_rank: number
  /** What distinguishes this row from another under the SAME citation. The two integrated
   *  preschool rows differ only by how many of the class have disabilities, and one
   *  citation against two different maximums reads as a bug without this. */
  condition: string
  students: number; educators: number; aides: number; staff: string
  swd_min?: number | null
  swd_cap?: number | null
}

export type Band = {
  band: string; ages: string; role: string; rows: number
  top: number; sub: number; drop: number
}

/** One worked room: how many children, how many adults, and what the rule says about it. */
export type Room = {
  key: string; students: number; educators: number; aides: number
  iep_aides: number; cite: string
  headline: string; verdict: string; why: string
  minimum: boolean
}

const EDU = 'var(--fund-school)'
const AIDE = 'var(--series-cost)'
const IEP = 'var(--status-warning)'

/** One adult, as a mark. Filled for the educator, hollow for the aide the rule names,
 *  dashed for an aide the rule does not count -- because the whole point of the second
 *  table is that the third kind exists and the regulation is silent about it. */
function Mark({ kind }: { kind: 'educator' | 'aide' | 'iep' }) {
  const c = kind === 'educator' ? EDU : kind === 'aide' ? AIDE : IEP
  return (
    <span aria-hidden="true" className="inline-block align-middle mr-1"
      style={{
        width: 11, height: 11, borderRadius: 11,
        background: kind === 'educator' ? c : 'transparent',
        border: `2px ${kind === 'iep' ? 'dashed' : 'solid'} ${c}`,
      }} />
  )
}

function Staff({ educators, aides, iep, role }: {
  educators: number; aides: number; iep?: number; role: string
}) {
  const counted = aides - (iep ?? 0)
  return (
    <span className="whitespace-nowrap">
      {Array.from({ length: educators }, (_, i) => <Mark key={`e${i}`} kind="educator" />)}
      {Array.from({ length: counted }, (_, i) => <Mark key={`a${i}`} kind="aide" />)}
      {Array.from({ length: iep ?? 0 }, (_, i) => <Mark key={`i${i}`} kind="iep" />)}
      <span className="sr-only">
        {educators} {role}{educators === 1 ? '' : 's'}
        {aides ? ` and ${aides} aide${aides === 1 ? '' : 's'}` : ' and no aide'}
        {iep ? `, ${iep} of them assigned to an individual child by an IEP` : ''}
      </span>
    </span>
  )
}

export function StaffKey({ iep }: { iep?: boolean }) {
  return (
    <p className="text-[12.5px] mt-3 flex flex-wrap gap-x-5 gap-y-1"
      style={{ color: 'var(--text-secondary)' }}>
      <span><Mark kind="educator" />the one educator each clause names</span>
      <span><Mark kind="aide" />aide</span>
      {iep && (
        <span><Mark kind="iep" />an aide an IEP assigns to one child</span>
      )}
    </p>
  )
}

/** EVERY TIER THE REGULATION SETS, IN ONE TABLE, BOTH AGE BANDS.
 *
 *  The preschool clauses used to sit below, in a section headed "a different rule again",
 *  and held out like that they read as an EXCEPTION. They are the same shape carried into
 *  the other age band, and merging them turns this page's strongest finding -- one
 *  educator in every tier, only the aides scale -- from a fact about one clause into a
 *  pattern holding across every age the regulation covers.
 *
 *  WHAT THE MERGE MUST NOT FLATTEN, and the columns are shaped by each of these:
 *
 *    - 28.06(7) says `teacher` where 28.06(6) says `certified special educator`. Nothing
 *      establishes those are the same qualification, so the band header prints each
 *      clause's own word and the column header is neutral.
 *    - The regulation splits at age five, so the band header states the ages. A reader who
 *      takes a preschool maximum for a school-age one has been misled by our layout rather
 *      than by the regulation.
 *    - `condition` says why one citation appears against two different maximums. */
export function ScenarioTable({ rows, bands, caption }: {
  rows: Tier[]; bands: Band[]; caption?: string
}) {
  const head = ['the setting', 'when', 'students, at most', 'the staff that permits it',
    'educators', 'aides', 'where it says so']
  const left = (i: number) => i === 0 || i === 1 || i === 3 || i === 6
  return (
    <div className="mt-4">
      {caption && (
        <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
          style={{ color: 'var(--text-muted)' }}>{caption}</p>
      )}
      <div className="overflow-x-auto -mx-1 px-1">
        <table className="text-[13px] tnum border-collapse min-w-full">
          <thead>
            <tr>
              {head.map((h, i) => (
                <th key={h} className="font-semibold py-1.5 pr-4 align-bottom border-b"
                  style={{
                    color: 'var(--text-secondary)', borderColor: 'var(--grid)',
                    textAlign: left(i) ? 'left' : 'right',
                    whiteSpace: left(i) ? 'normal' : 'nowrap',
                  }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {bands.map(b => (
              <Fragment key={b.band}>
                <tr>
                  <th colSpan={head.length} scope="colgroup"
                    className="text-left font-bold text-[12.5px] pt-5 pb-1.5"
                    style={{ color: 'var(--text-primary)' }}>
                    {b.band}
                    <span className="font-normal ml-2"
                      style={{ color: 'var(--text-muted)' }}>
                      {b.ages} &middot; the clause says &ldquo;{b.role}&rdquo;
                    </span>
                  </th>
                </tr>
                {rows.filter(r => r.band === b.band).map((r, i, band) => {
                  const first = i === 0 || band[i - 1].setting !== r.setting
                  return (
                    <tr key={`${r.cite}-${r.students}-${r.aides}`}>
                      <td className="py-1.5 pr-4 border-b align-top"
                        style={{
                          borderColor: 'var(--grid)',
                          color: first ? 'var(--text-primary)' : 'var(--text-muted)',
                          fontWeight: first ? 600 : 400,
                        }}>{first ? r.setting : ' '}</td>
                      <td className="py-1.5 pr-4 border-b align-top text-[12.5px]"
                        style={{
                          borderColor: 'var(--grid)', color: 'var(--text-secondary)',
                        }}>{r.condition || '—'}</td>
                      <td className="py-1.5 pr-4 border-b text-right font-bold text-[15px]"
                        style={{ borderColor: 'var(--grid)' }}>{r.students}</td>
                      <td className="py-1.5 pr-4 border-b"
                        style={{ borderColor: 'var(--grid)' }}>
                        <Staff educators={r.educators} aides={r.aides} role={r.role} />
                      </td>
                      <td className="py-1.5 pr-4 border-b text-right"
                        style={{
                          borderColor: 'var(--grid)', color: 'var(--text-secondary)',
                        }}>{r.educators}</td>
                      <td className="py-1.5 pr-4 border-b text-right"
                        style={{
                          borderColor: 'var(--grid)', color: 'var(--text-secondary)',
                        }}>{r.aides}</td>
                      <td className="py-1.5 pr-4 border-b whitespace-nowrap text-[12px]"
                        style={{ borderColor: 'var(--grid)', color: 'var(--text-muted)' }}>
                        {r.cite}
                      </td>
                    </tr>
                  )
                })}
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>
      <StaffKey />
    </div>
  )
}

/** THE SAME CHILDREN, STAFFED TWO WAYS.
 *
 *  TJ's question, and it is the one everybody actually has: "If we see 12 kids in a room,
 *  with 1 teacher and 3 paras, but each para is a 1:1, how does that work out?"
 *
 *  The tier table answers it only if you already know that the numbers are a ceiling on
 *  CHILDREN. Most readers do not, and read them as a description of staffing -- which is
 *  how "we have a lot of paras" gets treated as evidence about class sizes, in both
 *  directions. So the rooms are drawn: the same group size at the rule's minimum and at
 *  triple it, both lawful, indistinguishable from outside.
 *
 *  The rooms are BUILT IN THE GENERATOR, not here. Their student counts and minimum
 *  staffing are read off the regulation's own tiers; the extra IEP-assigned aides are the
 *  illustration's own number and the payload says so. */
export function RoomTable({ rooms, caption }: { rooms: Room[]; caption?: string }) {
  return (
    <div className="mt-4">
      {caption && (
        <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
          style={{ color: 'var(--text-muted)' }}>{caption}</p>
      )}
      <div className="grid gap-3 md:grid-cols-3">
        {rooms.map(r => (
          <div key={r.key} className="card p-4 avoid-break"
            style={{ borderTop: `3px solid ${r.minimum ? AIDE : IEP}` }}>
            <p className="text-2xl font-bold tracking-tight tnum">{r.headline}</p>
            <p className="mt-2">
              <Staff educators={r.educators} aides={r.aides} iep={r.iep_aides}
                role="educator" />
            </p>
            <p className="text-[13px] font-semibold mt-2.5">{r.verdict}</p>
            <p className="text-[13px] leading-relaxed mt-1.5"
              style={{ color: 'var(--text-secondary)' }}>{r.why}</p>
            <p className="text-[11.5px] mt-2.5" style={{ color: 'var(--text-muted)' }}>
              {r.cite}
            </p>
          </div>
        ))}
      </div>
      <StaffKey iep />
    </div>
  )
}

/** A plain table, for the rows that are counts rather than rules. */
export function TableTwin({ head, rows, caption }: {
  head: string[]; rows: (string | number)[][]; caption?: string
}) {
  return (
    <div className="mt-3">
      {caption && (
        <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
          style={{ color: 'var(--text-muted)' }}>{caption}</p>
      )}
      <div className="overflow-x-auto -mx-1 px-1">
        <table className="text-[12.5px] tnum border-collapse min-w-full">
          <thead>
            <tr>{head.map((h, i) => (
              <th key={h} className="font-semibold py-1.5 pr-4 whitespace-nowrap border-b"
                style={{
                  color: 'var(--text-secondary)', borderColor: 'var(--grid)',
                  textAlign: i === 0 ? 'left' : 'right',
                }}>{h}</th>
            ))}</tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i}>
                {r.map((c, j) => (
                  <td key={j} className="py-1 pr-4 whitespace-nowrap border-b"
                    style={{
                      borderColor: 'var(--grid)',
                      color: j === 0 ? 'var(--text-primary)' : 'var(--text-secondary)',
                      textAlign: j === 0 ? 'left' : 'right',
                    }}>{c}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

/** A clause of the regulation, printed as the regulation prints it.
 *
 *  The citation goes BELOW the quotation, not above it: rule 7a applied to a block quote.
 *  A reader wants the words; the number that lets them look it up is what they want next. */
export function Clause({ cite, title, text }: {
  cite: string; title?: string; text: string
}) {
  return (
    <blockquote className="mt-4 pl-4 border-l-2 max-w-2xl avoid-break"
      style={{ borderColor: 'var(--fund-school)' }}>
      {title && (
        <p className="text-[11px] font-semibold uppercase tracking-widest mb-1"
          style={{ color: 'var(--text-muted)' }}>{title}</p>
      )}
      <p className="text-[14.5px] leading-relaxed">{text}</p>
      <cite className="not-italic text-[12px] block mt-1.5"
        style={{ color: 'var(--text-muted)' }}>{cite}</cite>
    </blockquote>
  )
}
