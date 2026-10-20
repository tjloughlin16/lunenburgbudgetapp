/** THE DRILL-DOWN LEDGER: one leftover, account by account, each account a card whose evidence
 *  folds out. TJ, 20 October 2026: "if our page format doesnt work for this type of analysis
 *  you can explore other structures for the page" -- an investigation reads as a list of line
 *  items, each with its evidence, not as four claims.
 *
 *  Every word and figure arrives from the generator (scripts/topic.py, ledger()); nothing here
 *  computes or words a number (rule 2). Each card carries what it cannot show and the document
 *  that would settle it (rule 7c), and every quotation was checked verbatim against its source
 *  before the payload was written.
 *
 *  Native <details>, so a card folds on a phone and in the prerendered page with no script,
 *  and a screen reader announces it as expandable. */
import { abs } from '../lib/abs'

export type LedgerSection = {
  title: string; columns: string[]; rows: { label: string; cells: string[] }[]; note?: string
}
export type LedgerCard = {
  id: string; label: string; account: string; left: string; shape: string
  figures: { label: string; text: string }[]
  sections: LedgerSection[]
  quotes: { quote: string; label: string; href: string }[]
  unknown: string; closes: string; open: boolean
}
export type LedgerData = { caption: string; note: string; cards: LedgerCard[] }

function Section({ s }: { s: LedgerSection }) {
  return (
    <div className="mt-4">
      <p className="text-[12.5px] font-semibold uppercase tracking-wide" style={{ color: 'var(--text-secondary)' }}>
        {s.title}</p>
      <div className="overflow-x-auto mt-1.5">
        <table className="w-full text-[13px] tabular-nums border-collapse">
          <thead>
            <tr style={{ color: 'var(--text-muted)' }}>
              <th scope="col" className="text-left font-normal py-1 pr-3" />
              {s.columns.map((c, i) => <th key={c} scope="col" className={`font-normal py-1 pl-3 whitespace-nowrap ${
                s.rows.length && /^[-+]?\$|^\d{4}-\d\d-\d\d$/.test(s.rows[0].cells[i]) ? 'text-right' : 'text-left'}`}>{c}</th>)}
            </tr>
          </thead>
          <tbody>
            {s.rows.map(r => (
              <tr key={r.label} style={{ borderTop: '1px solid var(--grid)' }}>
                <th scope="row" className="text-left font-medium py-1.5 pr-3" style={{ color: 'var(--text-primary)' }}>{r.label}</th>
                {r.cells.map((c, i) => (
                  <td key={i} className={`py-1.5 pl-3 ${/^[-+]?\$|^\d{4}-\d\d-\d\d$/.test(c) ? 'text-right whitespace-nowrap' : 'text-left'}`}
                    style={{ color: 'var(--text-primary)' }}>{c}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {s.note ? <p className="text-[12px] leading-snug mt-1" style={{ color: 'var(--text-muted)' }}>{s.note}</p> : null}
    </div>
  )
}

export function AccountLedger({ l }: { l: LedgerData }) {
  return (
    <section className="mt-10 max-w-3xl" aria-label={l.caption}>
      <h2 className="text-[15px] font-semibold" style={{ color: 'var(--text-primary)' }}>{l.caption}</h2>
      <p className="text-[13px] leading-snug mt-1" style={{ color: 'var(--text-muted)' }}>{l.note}</p>
      <div className="mt-3 space-y-2">
        {l.cards.map(c => (
          <details key={c.id} open={c.open} className="card rounded-md"
            style={{ border: '1px solid var(--grid)', background: 'var(--surface-1)' }}>
            <summary className="cursor-pointer list-none px-3 py-2.5">
              <div className="flex items-baseline justify-between gap-3">
                <span className="min-w-0">
                  <span className="text-[14.5px] font-semibold" style={{ color: 'var(--text-primary)' }}>{c.label}</span>
                  <span className="block text-[11.5px] break-all" style={{ color: 'var(--text-muted)' }}>{c.account}</span>
                </span>
                <span className="shrink-0 text-right">
                  <span className="tnum text-[16px] font-semibold" style={{ color: 'var(--text-primary)' }}>{c.left}</span>
                  <span className="block text-[11.5px]" style={{ color: 'var(--text-muted)' }}>left</span>
                </span>
              </div>
              <p className="text-[13px] mt-1" style={{ color: 'var(--text-secondary)' }}>{c.shape}</p>
              <ul className="flex flex-wrap gap-x-4 gap-y-0.5 mt-1 text-[12.5px] tnum" style={{ color: 'var(--text-secondary)' }}>
                {c.figures.map(x => <li key={x.label}>{x.label} <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>{x.text}</span></li>)}
              </ul>
            </summary>
            <div className="px-3 pb-3">
              {c.sections.map(s => <Section key={s.title} s={s} />)}
              {c.quotes.map(q => (
                <figure key={q.href + q.quote.slice(0, 20)} className="mt-4 pl-3 border-l-2" style={{ borderColor: 'var(--grid)' }}>
                  <blockquote className="text-[13.5px] italic leading-relaxed" style={{ color: 'var(--text-primary)' }}>“{q.quote}”</blockquote>
                  <figcaption className="text-[12px] mt-0.5"><a href={abs(q.href)} className="underline"
                    style={{ color: 'var(--text-secondary)' }}>{q.label}</a></figcaption>
                </figure>
              ))}
              <p className="text-[12.5px] leading-snug mt-4" style={{ color: 'var(--text-muted)' }}>
                <span className="font-semibold">What this does not show:</span> {c.unknown}{' '}
                <span className="font-semibold">Would settle it:</span> {c.closes}.</p>
            </div>
          </details>
        ))}
      </div>
    </section>
  )
}
