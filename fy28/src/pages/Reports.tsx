import MANIFEST from '../data/agent-manifest.json'
import { useEffect, useState } from 'react'
import { Section, Note } from '../components/primitives'

/** Reports and analyses — what this project has written, as opposed to what it mirrors.
 *
 *  These lived as one group inside the source catalogue, on a shelf between the town's
 *  PDFs and the district's spreadsheets. That is the wrong shelf: everything else there
 *  was written by somebody else and republished unchanged, and these were written here.
 *  The distinction is the single most important thing a reader needs, so the caveat leads
 *  the page rather than footnoting it.
 *
 *  Every row carries the three things that make a claim checkable: the document, the
 *  script that recomputes every figure in it, and the data underneath. A reader should
 *  never have to take any of this on trust.
 */

type Report = {
  id: string; title: string; about: string; words: number; updated: string | null
  markdown: { url: string; bytes: number; sha256: string }
  pdf: { url: string; bytes: number } | null
  verifier: { path: string; command: string } | null
  charts: string[]
}
type Payload = {
  generated: string
  caveat: { headline: string; body: string; checkable: string; corrections: string }
  reports: Report[]
  data: Record<string, { url: string; about: string }>
}

const kb = (n: number) => n >= 1e6 ? `${(n / 1e6).toFixed(1)} MB` : `${Math.round(n / 1024)} KB`

/* Absolute. Every report on this page is a file, and a file linked relatively is
 * one an assistant that only follows URLs it has seen cannot open. */
const ABS = (u: string) => (u.startsWith('http') ? u : `${MANIFEST.site}${u}`)

export function Reports() {
  const [d, setD] = useState<Payload | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    let live = true
    fetch('/data/reports.json')
      .then(r => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(x => { if (live) setD(x) })
      .catch(e => { if (live) setErr(String(e)) })
    return () => { live = false }
  }, [])

  if (err) return (
    <div className="mx-auto max-w-6xl px-5 py-20">
      <h1 className="text-2xl font-bold mb-3">The report index could not load</h1>
      <p style={{ color: 'var(--text-secondary)' }}>
        <code>/data/reports.json</code> did not answer: {err}. The analyses themselves are
        still at <code>/docs/analyses/</code>.
      </p>
    </div>
  )
  if (!d) return (
    <div className="mx-auto max-w-6xl px-5 py-20">
      <p style={{ color: 'var(--text-muted)' }}>Loading…</p>
    </div>
  )

  return (
    <>
      <header className="mx-auto max-w-6xl px-5 pt-12 pb-2">
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mb-4">
          Reports and analyses
        </h1>
        <p className="max-w-3xl text-[15px] leading-relaxed"
          style={{ color: 'var(--text-secondary)' }}>
          {d.reports.length} documents written by this project, from records the town and
          district published and from documents obtained by request. Each one is published
          as a web page, a PDF and its source text, and most are checked by a script that
          recomputes every figure in them.
        </p>
      </header>

      {/* The caveat is the first thing on the page, at full weight, not a footnote. */}
      <div className="mx-auto max-w-6xl px-5 mt-6">
        <div className="card p-5" style={{ borderLeft: '4px solid var(--status-warning)' }}>
          <p className="text-[11px] font-semibold uppercase tracking-widest mb-2"
            style={{ color: 'var(--status-warning)' }}>Read this first</p>
          <p className="text-lg font-bold mb-3">{d.caveat.headline}</p>
          <div className="space-y-3 text-sm leading-relaxed max-w-3xl"
            style={{ color: 'var(--text-secondary)' }}>
            <p>{d.caveat.body}</p>
            <p>{d.caveat.checkable}</p>
            <p>{d.caveat.corrections}</p>
          </div>
        </div>
      </div>

      <Section id="reports" eyebrow="The documents" title="Every analysis"
        lede={<p>
          Newest first among the current work. Each row links the readable version, the
          printable one, the source text with its checksum, and — where one exists — the
          command that reproduces every figure in it from the database.
        </p>}>
        <ul className="space-y-5">
          {d.reports.map(r => (
            <li key={r.id} className="card p-4">
              <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 mb-1.5">
                <h3 className="text-lg font-bold leading-tight">{r.title}</h3>
                <span className="text-[11px] tnum" style={{ color: 'var(--text-muted)' }}>
                  {r.words.toLocaleString()} words
                  {r.updated ? ` · updated ${r.updated}` : ''}
                </span>
              </div>
              <p className="text-sm leading-relaxed mb-3 max-w-3xl"
                style={{ color: 'var(--text-secondary)' }}>{r.about}</p>

              <div className="flex flex-wrap gap-x-4 gap-y-1.5 text-[13px] items-center">
                <a href={ABS(r.markdown.url)} className="font-semibold underline"
                  style={{ color: 'var(--series-cost)' }}>Read it</a>
                {r.pdf && (
                  <a href={ABS(r.pdf.url)} className="font-semibold underline"
                    style={{ color: 'var(--series-cost)' }}>
                    PDF <span className="font-normal tnum"
                      style={{ color: 'var(--text-muted)' }}>{kb(r.pdf.bytes)}</span>
                  </a>
                )}
                <a href={ABS(r.markdown.url)} download className="underline"
                  style={{ color: 'var(--text-secondary)' }}>Source text</a>
                {r.verifier ? (
                  <span className="text-[12px]" style={{ color: 'var(--status-good)' }}>
                    ✓ every figure recomputed by{' '}
                    <code className="text-[11px]">{r.verifier.command}</code>
                  </span>
                ) : (
                  <span className="text-[12px]" style={{ color: 'var(--text-muted)' }}>
                    no verifier script — figures checked by hand
                  </span>
                )}
              </div>
              <p className="text-[11px] mt-2 break-all" style={{ color: 'var(--text-muted)' }}>
                sha256 {r.markdown.sha256}
              </p>
            </li>
          ))}
        </ul>
      </Section>

      <Section id="data" eyebrow="Underneath all of it" title="The data, linked directly"
        lede={<p>
          Nothing above has to be taken on trust. These are the same sources the analyses
          are computed from, published at stable addresses.
        </p>}>
        <div className="grid sm:grid-cols-2 gap-3">
          {Object.entries(d.data).map(([k, v]) => (
            <a key={k} href={ABS(v.url)} className="card p-4 block">
              <p className="font-semibold text-sm mb-1" style={{ color: 'var(--series-cost)' }}>
                <code>{v.url}</code>
              </p>
              <p className="text-[13px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                {v.about}
              </p>
            </a>
          ))}
        </div>
        <Note>
          Index generated {d.generated} by <code>scripts/build_reports_index.py</code>, so
          it cannot describe a document that is not there or omit one that is.
        </Note>
      </Section>
    </>
  )
}
