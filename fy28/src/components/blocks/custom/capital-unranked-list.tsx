/** ASKED FOR, NEVER RANKED (each capital year page).
 *
 *  TJ, 20 November 2026: "we need to show requests made that werent ranked FOR SURE. and if we
 *  can, figure out why (minutes?! transcripts?!)". One row per request a department made for the
 *  year that the Capital Planning Committee's list does not hold: what happened to it, the reason
 *  where a document or a recording states one, and every year it WAS ranked. A reason heard only
 *  in a recording is marked as captions, a finding aid; where nothing states a reason the row says
 *  so instead of supplying one. Requests folded into ranked ones are listed apart, below.
 *  Every string is formatted by scripts/build_capital_rankings.py from
 *  sources/data/capital-requests-unranked.csv. */
import type { CustomProps } from './index'

type Row = {
  project: string; dept: string; amount_text: string; what: string; reason: string
  basis: 'document' | 'captions' | 'none' | 'ours'; basis_text: string; href: string | null
  ranked_text: string
}
type Data = { rows: Row[]; merged: Row[]; text: { merged: string; reason: string; ranked: string }; note: string }

const TONE: Record<Row['basis'], string> = {
  document: 'var(--text-secondary)', ours: 'var(--status-warning)', captions: 'var(--status-warning)', none: 'var(--text-muted)',
}

function Item({ r, t }: { r: Row; t: Data['text'] }) {
  return (
    <li className="py-2.5 border-t" style={{ borderColor: 'var(--grid)' }}>
      <div className="flex flex-wrap items-baseline gap-x-2">
        <span className="text-[14px] font-semibold" style={{ color: 'var(--text-primary)' }}>{r.project}</span>
        <span className="text-[12.5px] tabular-nums" style={{ color: 'var(--text-muted)' }}>{r.dept} · {r.amount_text}</span>
        <span className="text-[11.5px] uppercase tracking-wide rounded-sm px-1.5"
          style={{ border: '1px solid var(--grid)', color: 'var(--text-secondary)' }}>{r.what}</span>
      </div>
      <p className="text-[13px] mt-1" style={{ color: r.basis === 'none' ? 'var(--text-muted)' : 'var(--text-primary)' }}>
        <span style={{ color: 'var(--text-muted)' }}>{t.reason} </span>{r.reason}
        {' '}<span className="text-[11.5px]" style={{ color: TONE[r.basis] }}>
          ({r.href ? <a href={r.href} className="underline">{r.basis_text}</a> : r.basis_text})</span>
      </p>
      <p className="text-[12px] mt-0.5" style={{ color: 'var(--text-muted)' }}>{t.ranked} {r.ranked_text}</p>
    </li>
  )
}

export default function CapitalUnrankedList({ data, alt }: CustomProps) {
  const d = data as Data
  return (
    <figure className="my-2 w-full max-w-full min-w-0" aria-label={alt}>
      <ul className="list-none p-0 m-0">{d.rows.map((r, i) => <Item key={i} r={r} t={d.text} />)}</ul>
      {d.merged.length ? (
        <>
          <p className="text-[12.5px] font-semibold mt-4 mb-1" style={{ color: 'var(--text-secondary)' }}>{d.text.merged}</p>
          <ul className="list-none p-0 m-0">{d.merged.map((r, i) => <Item key={i} r={r} t={d.text} />)}</ul>
        </>
      ) : null}
      <figcaption className="mt-2 text-[12.5px]" style={{ color: 'var(--text-muted)' }}>{d.note}</figcaption>
    </figure>
  )
}
