import MANIFEST from '../data/agent-manifest.json'

/** The site's inventory, in visible text, at the foot of every page.
 *
 *  There is an identical manifest in an HTML comment at the top of every page, and testing
 *  showed it reaches nobody: a readability pass, `html.parser` and a naive tag strip all
 *  discard comments before a model sees the text. So the comment is belt, and this is
 *  braces — the copy that actually survives being read.
 *
 *  It is deliberately visible rather than hidden. A resident who wants the spreadsheet, a
 *  journalist who wants the minutes, and an assistant asked "does this site have X" all
 *  need the same list, and hiding it from one of them to tidy the page for the others
 *  would be the wrong trade. Full URLs are written out as TEXT and not only as hrefs,
 *  because an extractor keeps the text and throws the attribute away.
 *
 *  Rendered from `agent-manifest.json`, which `scripts/build_agent_manifest.py` generates
 *  and refuses to populate with a path that is not in the build. */
export function DataFooter() {
  const host = MANIFEST.site.replace(/^https?:\/\//, '')
  return (
    <section
      aria-label="Data and sources"
      style={{
        marginTop: '1.5rem', paddingTop: '1.5rem',
        borderTop: '1px solid var(--border, rgba(128,128,128,.25))',
        fontSize: '.88rem', color: 'var(--text-secondary)',
      }}>
      <h2 style={{ fontSize: '1rem', margin: '0 0 .4rem', color: 'var(--text-primary)' }}>
        Ask an AI about this budget — it has everything it needs here
      </h2>
      <p style={{ margin: '0 0 .9rem', maxWidth: '48rem' }}>
        {MANIFEST.promise} Point an assistant at <strong>{host}</strong> and ask it
        anything below; every file is plain text or CSV and needs no login.
      </p>

      <p style={{ margin: '0 0 1rem', maxWidth: '48rem' }}>
        <strong>One rule before computing anything.</strong> {MANIFEST.warning}
      </p>

      <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 1rem',
                   display: 'grid', gap: '.55rem' }}>
        {MANIFEST.answers.map(a => (
          <li key={a.path}>
            <span style={{ color: 'var(--text-primary)' }}>{a.question}</span>
            <br />
            <a href={a.path} style={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace' }}>
              {host}{a.path}
            </a>
            {a.note ? <span> — {a.note}</span> : null}
          </li>
        ))}
      </ul>

      <p style={{ margin: '0 0 1rem', maxWidth: '48rem' }}>
        {MANIFEST.extra.map((e, i) => (
          <span key={e.path}>
            {i > 0 ? ' · ' : ''}
            <a href={e.path} style={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace' }}>
              {host}{e.path}
            </a> — {e.note}
          </span>
        ))}
      </p>

      {MANIFEST.corpus && (
        <p style={{ margin: 0, maxWidth: '48rem' }}>
          <strong>The meeting archive</strong> is {MANIFEST.corpus} — published as full
          text, not as an index. This is where the town argues about fees, contracts,
          staffing and overrides, and none of that appears in a budget document. Fetch one
          bundle per board to search it; each document inside carries its own permanent
          address so a finding can be cited to the document rather than the bundle.
        </p>
      )}
    </section>
  )
}
