/** The scenario table: what the regulation permits for a group of N, and nothing else.
 *
 *  WHY IT IS ITS OWN COMPONENT AND NOT A GENERIC TABLE. Every other table on this site is
 *  a series -- years down the side, figures across. This one is a RULE, and the thing a
 *  reader has to be able to see at a glance is the column that never changes: one
 *  certified special educator in every tier, in both settings, at every group size. A
 *  generic three-column table draws `1` five times and says nothing; this draws the
 *  staffing as marks, so the constant and the thing that scales are visible before any
 *  number is read.
 *
 *  RULE 2 ABSOLUTELY. Nothing here holds, computes or rounds a figure. Every count, every
 *  citation and every quoted phrase arrives from `sped-regulation.json`, which parsed each
 *  one out of the sentence in 603 CMR 28.00 that states it. A number typed into this file
 *  would be a class-size rule nothing recomputes, which is the exact defect rule 2 exists
 *  for -- and this page is one people will quote at meetings. */

export type Tier = {
  setting: string; short: string; cite: string
  students: number; educators: number; aides: number; staff: string
  swd_cap?: number | null
}

const EDU = 'var(--fund-school)'
const AIDE = 'var(--series-cost)'

/** One staff member, as a mark. Filled for the certified special educator, hollow for an
 *  aide -- the regulation draws exactly this distinction (28.02(3) defines one and never
 *  defines the other) and the table should not flatten it into two identical dots. */
function Mark({ kind }: { kind: 'educator' | 'aide' }) {
  const c = kind === 'educator' ? EDU : AIDE
  return (
    <span aria-hidden="true" className="inline-block align-middle mr-1"
      style={{
        width: 11, height: 11, borderRadius: 11,
        background: kind === 'educator' ? c : 'transparent',
        border: `2px solid ${c}`,
      }} />
  )
}

function Staff({ educators, aides }: { educators: number; aides: number }) {
  return (
    <span className="whitespace-nowrap">
      {Array.from({ length: educators }, (_, i) => <Mark key={`e${i}`} kind="educator" />)}
      {Array.from({ length: aides }, (_, i) => <Mark key={`a${i}`} kind="aide" />)}
      <span className="sr-only">
        {educators} certified special educator{educators === 1 ? '' : 's'}
        {aides ? ` and ${aides} aide${aides === 1 ? '' : 's'}` : ' and no aide'}
      </span>
    </span>
  )
}

export function StaffKey() {
  return (
    <p className="text-[12.5px] mt-3 flex flex-wrap gap-x-5 gap-y-1"
      style={{ color: 'var(--text-secondary)' }}>
      <span><Mark kind="educator" />certified special educator</span>
      <span><Mark kind="aide" />aide</span>
    </p>
  )
}

export function ScenarioTable({ rows, caption }: { rows: Tier[]; caption?: string }) {
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
              {['the setting', 'students, at most', 'the staff that permits it',
                'certified special educators', 'aides', 'where it says so'].map((h, i) => (
                  <th key={h}
                    className="font-semibold py-1.5 pr-4 align-bottom border-b"
                    style={{
                      color: 'var(--text-secondary)', borderColor: 'var(--grid)',
                      textAlign: i === 0 || i === 2 || i === 5 ? 'left' : 'right',
                      whiteSpace: i === 0 || i === 2 ? 'normal' : 'nowrap',
                    }}>{h}</th>
                ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => {
              const first = i === 0 || rows[i - 1].setting !== r.setting
              return (
                <tr key={`${r.cite}-${r.students}-${r.aides}`}>
                  <td className="py-1.5 pr-4 border-b align-top"
                    style={{
                      borderColor: 'var(--grid)',
                      color: first ? 'var(--text-primary)' : 'var(--text-muted)',
                      fontWeight: first ? 600 : 400,
                      borderTop: first && i ? '1px solid var(--grid)' : undefined,
                    }}>{first ? r.setting : ' '}</td>
                  <td className="py-1.5 pr-4 border-b text-right font-bold text-[15px]"
                    style={{ borderColor: 'var(--grid)' }}>{r.students}</td>
                  <td className="py-1.5 pr-4 border-b"
                    style={{ borderColor: 'var(--grid)' }}>
                    <Staff educators={r.educators} aides={r.aides} />
                  </td>
                  <td className="py-1.5 pr-4 border-b text-right"
                    style={{ borderColor: 'var(--grid)', color: 'var(--text-secondary)' }}>
                    {r.educators}
                  </td>
                  <td className="py-1.5 pr-4 border-b text-right"
                    style={{ borderColor: 'var(--grid)', color: 'var(--text-secondary)' }}>
                    {r.aides}
                  </td>
                  <td className="py-1.5 pr-4 border-b whitespace-nowrap text-[12px]"
                    style={{ borderColor: 'var(--grid)', color: 'var(--text-muted)' }}>
                    {r.cite}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      <StaffKey />
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
