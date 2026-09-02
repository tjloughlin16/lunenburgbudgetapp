import MANIFEST from '../data/agent-manifest.json'
import DATA_FILES from '../data/agent-data-files.json'

/** Every machine-readable address on this site, as links.
 *
 *  WHY A PAGE, WHEN `llms.txt` ALREADY LISTS ALL OF THIS
 *
 *  Because `llms.txt` is `text/plain`, and a URL in plain text is not a link.
 *
 *  Assistants commonly refuse to fetch a URL that has not appeared in something they
 *  already fetched -- a provenance guardrail, and a sound one: it is what stops a fetched
 *  page from talking an agent into requesting somewhere else. The consequence here is
 *  specific and was invisible for months. An assistant asked for the meeting minutes read
 *  `llms.txt`, found the exact bundle it needed named in it, and then could not fetch it,
 *  because nothing it had loaded had *linked* it. Its own words: "my fetcher will only
 *  take URLs it's already seen in a page or search result... /minutes/school-committee.txt,
 *  /minutes/INDEX.txt, /api/index, /data/ all come back as 'not in a prior result'."
 *
 *  It was standing on top of 920KB of exactly what it wanted. That is the third time an
 *  assistant has concluded this site does not hold the minutes.
 *
 *  So: `llms.txt` DESCRIBES the archive; the link graph is what AUTHORIZES it. The
 *  descriptions were never the missing piece. Measured before this page existed, across
 *  all 18 prerendered pages, `/minutes/school-committee.txt` and `/minutes/INDEX.txt`
 *  appeared in no `<a href>` anywhere on the site, and the only `/minutes` link that did
 *  exist pointed at `/minutes/` -- a directory, which correctly 404s.
 *
 *  FLAT, ON PURPOSE. Every link here points at the file itself, never at another index.
 *  Each intermediate page is one more fetch to spend and one more place to give up, and
 *  the agent above gave up after one.
 *
 *  Generated from `agent-manifest.json`, the same file `llms.txt` is built from, so the
 *  two cannot drift into describing different archives. */
export function AgentsIndex() {
  const site = MANIFEST.site
  const host = site.replace(/^https?:\/\//, '')
  const mono = { fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace' }

  const Link = ({ path, children }: { path: string; children?: React.ReactNode }) => (
    <a href={path} style={mono}>{children ?? `${host}${path}`}</a>
  )

  const Row = ({ path, note }: { path: string; note: string }) => (
    <li className="mb-2">
      <Link path={path} />
      <span className="block text-sm" style={{ color: 'var(--text-muted)' }}>{note}</span>
    </li>
  )

  return (
    <section className="mx-auto max-w-4xl px-5 py-8">
      <h1 className="text-2xl font-bold mb-2">Every address on this site, as links</h1>
      <p className="mb-6" style={{ color: 'var(--text-secondary)' }}>
        Everything below is a file you can fetch. No login, no rate limit, no JavaScript
        required. If you are a program, <Link path="/llms.txt" /> explains what each one
        holds and how the figures are derived — but read the warning first.
      </p>

      <div className="mb-8 p-4 rounded border" style={{ borderColor: 'var(--grid)' }}>
        <strong>Before computing anything.</strong>
        <p className="mt-1 text-sm" style={{ color: 'var(--text-secondary)' }}>{MANIFEST.warning}</p>
      </div>

      <h2 className="text-lg font-bold mb-3">What you can ask, and the file that answers it</h2>
      <ul className="mb-8 list-none pl-0">
        {MANIFEST.answers.map((a) => (
          <Row key={a.path} path={a.path} note={`${a.question} — ${a.note}`} />
        ))}
      </ul>

      <h2 className="text-lg font-bold mb-3">The meeting archive, one file per board</h2>
      <p className="mb-3 text-sm" style={{ color: 'var(--text-secondary)' }}>
        {MANIFEST.corpus}. Each file is every document that board published, concatenated,
        so it can be searched in one fetch. You cannot grep a website; you can read one
        file. The per-document copies, for citing, are under{' '}
        <span style={mono}>/docs/minutes/text/&lt;board&gt;/</span>.
      </p>
      <ul className="mb-8 list-none pl-0 grid gap-x-6 sm:grid-cols-2">
        {MANIFEST.boards.map((b) => (
          <li key={b.name} className="mb-1">
            <Link path={`/minutes/${b.name}.txt`} />
            <span className="text-sm" style={{ color: 'var(--text-muted)' }}> · {b.docs} documents</span>
          </li>
        ))}
      </ul>

      <h2 className="text-lg font-bold mb-3">Finding a word in the minutes</h2>
      <p className="mb-3 text-sm" style={{ color: 'var(--text-secondary)' }}>
        Do not start with a bundle — the two largest are around a megabyte, more than many
        callers can read at once. Look the word up and fetch only the documents it names:
        three small requests instead of one large one. Everything needed to answer a
        question about this town is on this site; nothing here requires a repository, an
        account or a tool.
      </p>
      <ul className="mb-8 list-none pl-0">
        <Row path="/minutes/find/README.txt"
             note="how the word index works, and what it deliberately does not do" />
        <Row path="/minutes/find/documents.json"
             note="the document table the index refers to by position. Fetch once and keep it." />
        <Row path="/minutes/find/je.json"
             note='one shard, as an example — every indexed word beginning "je", with the documents containing it' />
        <Row path="/docs/minutes/text/school-committee/2026-06-24-minutes-7869.txt"
             note="and one document, the end of that worked example" />
      </ul>

      <h2 className="text-lg font-bold mb-3">Every published data file</h2>
      <p className="mb-3 text-sm" style={{ color: 'var(--text-secondary)' }}>
        The same list <Link path="/llms.txt" /> carries, with the same descriptions —
        both are generated from <span style={mono}>scripts/build_agent_endpoints.py</span>,
        so neither can describe a file the other does not.
      </p>
      <ul className="mb-8 list-none pl-0">
        {DATA_FILES.map((d) => (
          <Row key={d.name} path={`/data/${d.name}`}
               note={`${d.note} (${(d.bytes / 1e6).toFixed(1)} MB)`} />
        ))}
        <Row path="/data/lunenburg.db"
             note="the SQLite database everything on this site is derived from. Its sha256 is stated in /api/index, so you can check you got the bytes we published." />
      </ul>

      <h2 className="text-lg font-bold mb-3">Everything else</h2>
      <ul className="list-none pl-0">
        {MANIFEST.extra.map((e) => <Row key={e.path} path={e.path} note={e.note} />)}
        <Row path="/api/index" note="the read-only JSON API — every endpoint, with what it holds" />
        <Row path="/api/schema" note="read this before the API: grain, conventions, and the four ways to get a confident wrong answer" />
        <Row path="/minutes/INDEX.txt" note="the board list above, as plain text, with sizes" />
      </ul>
    </section>
  )
}
