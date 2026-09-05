import MANIFEST from '../data/agent-manifest.json'
import { MODEL } from '../model/engine'
import { pathFor } from '../routes'
import sources from '../data/sources.json'

/** Numbered citations, tied to the figures they belong to.
 *
 *  "Our sources are public" is a claim. A number under the number, pointing at a file you
 *  can download, is a check somebody can run — which is the only version of this that is
 *  worth anything on a page asking a resident to accept arithmetic about their own tax
 *  bill.
 *
 *  Each entry records the document AND the basis: which column, and whether that column
 *  is a budget or actual spending. That distinction is not pedantry. A budget is what
 *  somebody voted; an actual is what got spent, and for some lines they differ by 7%. A
 *  growth rate computed across the two is partly growth and partly the step between them.
 *  Every projection here is computed from budget columns only, and the basis line is how a
 *  reader confirms it instead of trusting us. */

type Item = {
  id: string; n: number; metric: string; value: string
  kind: string; basis: string; doc: string; source: string
}

const C = MODEL.citations
const BY_ID = Object.fromEntries(C.items.map(i => [i.id, i])) as Record<string, Item>

/** Where each document is actually served from, taken from the source index rather than
 *  assumed. One file — the teachers' agreement, a 53MB scan — is hosted off-site because
 *  it exceeds the host's per-file limit, and a citation that guessed /docs/ for it would
 *  link to a 404. Reading the index means the two cannot drift apart. */
const DOC_URL: Record<string, string> = Object.fromEntries(
  (sources as { groups: { items: { path: string; url: string }[] }[] }).groups
    .flatMap(g => g.items).map(i => [i.path, i.url]))

/* Absolute. A citation exists so somebody can go and check the document, and for a
 * program "somebody" means a fetcher that will not follow a bare path. */
const SITE = MANIFEST.site
const urlFor = (doc: string) => {
  const u = DOC_URL[doc] ?? `/docs/${doc}`
  return u.startsWith('http') ? u : SITE + u
}

/** The marker that sits against a figure. Small, and a real link. */
export function Cite({ id }: { id: string }) {
  const c = BY_ID[id]
  if (!c) return null
  return (
    <a href={`#cite-${c.n}`}
      title={`${c.source} — ${c.basis}`}
      aria-label={`Citation ${c.n}: ${c.source}`}
      className="align-super text-[10px] font-bold ml-0.5 no-underline hover:underline"
      style={{ color: 'var(--series-cost)' }}>
      [{c.n}]
    </a>
  )
}

const KIND_COLOR: Record<string, string> = {
  ours: 'var(--status-warning)',
  statute: 'var(--text-muted)',
  contract: 'var(--text-muted)',
}

/** The list itself. Sits at the foot of a page, once. */
export function CitationList() {
  return (
    <section id="citations" className="scroll-mt-32 lg:scroll-mt-16 py-12 border-t"
      style={{ borderColor: 'var(--grid)' }}>
      <div className="mx-auto max-w-6xl px-5">
        <p className="text-xs font-semibold uppercase tracking-widest mb-2"
          style={{ color: 'var(--text-muted)' }}>Citations</p>
        <h2 className="text-2xl font-bold tracking-tight mb-3">Where every figure comes from</h2>
        <p className="text-[15px] leading-relaxed max-w-3xl mb-2"
          style={{ color: 'var(--text-secondary)' }}>
          Each number on this page carries a marker. Every document below can be downloaded
          in full &mdash; not a summary of it, the file itself.
        </p>
        <p className="text-[13px] leading-relaxed max-w-3xl mb-7"
          style={{ color: 'var(--text-secondary)' }}>
          <strong style={{ color: 'var(--text-primary)' }}>On budgets versus actuals.</strong>{' '}
          {C.note}
        </p>

        <ol className="flex flex-col gap-3.5">
          {C.items.map((c: Item) => (
            <li key={c.id} id={`cite-${c.n}`} className="scroll-mt-32 flex gap-3">
              <span className="text-[12px] font-bold tnum shrink-0 pt-0.5 w-6 text-right"
                style={{ color: 'var(--series-cost)' }}>{c.n}</span>
              <div className="min-w-0">
                <p className="text-[14px] font-semibold leading-snug">{c.metric}</p>
                <p className="text-[13px] leading-relaxed mt-0.5"
                  style={{ color: 'var(--text-secondary)' }}>
                  {c.basis}
                </p>
                <p className="text-[12px] mt-1 flex flex-wrap items-center gap-x-2 gap-y-0.5">
                  <span className="font-semibold"
                    style={{ color: KIND_COLOR[c.kind] ?? 'var(--text-muted)' }}>
                    {C.kindLabels[c.kind]}
                  </span>
                  <span aria-hidden="true" style={{ color: 'var(--text-muted)' }}>&middot;</span>
                  <a href={urlFor(c.doc)} download
                    className="underline" style={{ color: 'var(--series-cost)' }}>
                    {c.source}
                  </a>
                  <span aria-hidden="true" style={{ color: 'var(--text-muted)' }}>&middot;</span>
                  <code className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
                    sources/{c.doc}
                  </code>
                </p>
              </div>
            </li>
          ))}
        </ol>

        {/* A real link rather than a tab callback: the walkthrough deliberately narrows
            which tabs it can jump to, and the archive is not one of them. */}
        <a href={pathFor('sources')}
          className="inline-block mt-7 text-xs font-semibold px-3 py-2 rounded-md no-underline"
          style={{ background: 'var(--surface-3)', color: 'var(--text-primary)' }}>
          The full archive &mdash; every document, not just these &rarr;
        </a>
      </div>
    </section>
  )
}
