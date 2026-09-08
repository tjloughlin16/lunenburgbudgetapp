/** HOW CONFIRMED IS A FIGURE — the label that travels with one.
 *
 *  Every figure on this site sits at one of three levels, and the failure is never being
 *  at a low level. It is REPORTING a low level as though it were a high one:
 *
 *    stated              a document says so, and nothing independent checks it
 *    cross-checked       a second, independent document agrees — or visibly disagrees,
 *                        which is itself informative
 *    traced to a payment an invoice, warrant or payroll record; the transaction happened
 *
 *  Most of a public archive lives at the first two, and that is normal. So the label is
 *  never a gate that withholds an answer — a bounded answer with its basis attached is
 *  more useful than a refusal.
 *
 *  ONE FLAG SITS ABOVE ALL THREE, and it is not a fourth level: where the body that
 *  produced a figure has publicly declined to stand behind it, or the figure is contested
 *  on the public record, that is a different fact about the number and it is said beside
 *  it. `contested` renders it.
 *
 *  This lives in one file because two copies of a scale is two scales. */
export type Level = 'stated' | 'cross-checked' | 'traced to a payment' | 'contested'

export const LEVEL_TONE: Record<Level, string> = {
  'stated': 'var(--status-warning)',
  'cross-checked': 'var(--series-cost)',
  'traced to a payment': 'var(--status-good)',
  'contested': 'var(--status-bad)',
}

export function Basis({ level, children }: { level: Level; children?: React.ReactNode }) {
  return (
    <span className="inline-flex items-baseline gap-1.5 align-middle">
      <span className="text-[10px] font-bold uppercase tracking-widest px-1.5 py-0.5
                       rounded border whitespace-nowrap"
        style={{ color: LEVEL_TONE[level], borderColor: LEVEL_TONE[level] }}>{level}</span>
      {children ? (
        <span className="text-[12px]" style={{ color: 'var(--text-muted)' }}>{children}</span>
      ) : null}
    </span>
  )
}
