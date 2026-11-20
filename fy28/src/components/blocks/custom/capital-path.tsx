/** ONE YEAR'S PATH: ranked -> the Town Manager's first plan -> funded (the capital-fy<YEAR> pages).
 *
 *  Each stage is a count and a dollar total, and a bar as long as its dollars against the ranked
 *  total, so the reader sees how much of the list survived each step and whether the final plan
 *  grew past the first one (it did in FY2024 and FY2027). Between stages, what moved: requests the
 *  final plan added that the first one left out, and the reverse. Stage names are the year's own
 *  documents' (a preliminary plan in one year, Option 1 in another); every figure is formatted by
 *  scripts/build_capital_rankings.py. */
import type { CustomProps } from './index'

type Stage = { label: string; doc: string; count_text: string; amount_text: string; amount: number; final?: boolean }
type Data = { stages: Stage[]; moves: (string | null)[]; note: string }

export default function CapitalPath({ data, alt }: CustomProps) {
  const d = data as Data
  const max = Math.max(1, ...d.stages.map(s => s.amount))
  return (
    <figure className="my-2 w-full max-w-3xl min-w-0" aria-label={alt}>
      <ol className="space-y-0">
        {d.stages.map((s, i) => (
          <li key={s.label}>
            <div className="flex items-baseline justify-between gap-3 flex-wrap">
              <p className="text-[14px] font-semibold" style={{ color: 'var(--text-primary)' }}>
                <span className="tabular-nums mr-1.5" style={{ color: 'var(--text-muted)' }}>{i + 1}</span>{s.label}</p>
              <p className="text-[14px] tabular-nums" style={{ color: 'var(--text-primary)' }}>
                <span className="font-semibold">{s.count_text}</span>
                <span style={{ color: 'var(--text-muted)' }}> · </span>{s.amount_text}</p>
            </div>
            <div className="mt-1 h-3 rounded-sm" style={{ width: `${Math.max(1.5, (100 * s.amount) / max)}%`,
              background: s.final ? 'var(--thread-1)' : 'var(--text-muted)', opacity: s.final ? 1 : 0.45 }} />
            <p className="text-[11.5px] mt-0.5" style={{ color: 'var(--text-muted)' }}>{s.doc}</p>
            {i < d.stages.length - 1 ? (
              <p className="text-[12.5px] my-1.5 pl-3 border-l-2" style={{ borderColor: 'var(--grid)', color: 'var(--text-secondary)' }}>
                {d.moves[i] ?? '↓'}</p>
            ) : null}
          </li>))}
      </ol>
      <figcaption className="mt-3 text-[12.5px]" style={{ color: 'var(--text-muted)' }}>{d.note}</figcaption>
    </figure>
  )
}
