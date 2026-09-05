import MANIFEST from '../data/agent-manifest.json'

/** One line in the footer saying what is downloadable.
 *
 *  Not a pitch. An earlier version of this was a headed block addressed to AI assistants,
 *  and it read like an advert on a site whose whole claim is that it is not selling
 *  anything. The links are the useful part; the framing was not.
 *
 *  It is VISIBLE rather than hidden, deliberately and for two reasons. Serving different
 *  content to people and machines is cloaking — against search engine guidelines, and
 *  indefensible for a site arguing for transparency. And it would not work: a headless
 *  browser reading innerText and a readability extractor both drop hidden nodes, as they
 *  both drop comments. Hidden text reaches the sloppiest readers and misses the careful
 *  ones.
 *
 *  So the paths sit in plain text, where an assistant, a journalist and a resident who
 *  just wants the spreadsheet all find the same thing.
 *
 *  THESE MUST BE FILES, NOT DIRECTORIES. This footer linked `/data/` and `/minutes/` for
 *  months. Both are directory paths, both correctly 404, and between them they were the
 *  only `/minutes` link anywhere on the site -- so the one site-wide pointer at the
 *  meeting archive led an assistant to a 404 whose body it then could not act on, because
 *  that body is text/plain and a URL in plain text is not a link. Every entry here now
 *  resolves to a real file, and `/agents` carries the long tail. See AgentsIndex.tsx. */
export function DataFooter() {
  const host = MANIFEST.site.replace(/^https?:\/\//, '')
  const corpus = MANIFEST.corpus || ''
  // Absolute: this footer is the one thing on every page that names a machine-readable
  // address, and a relative href is an address only to a caller that already knows where
  // it is standing.
  const link = (p: string) => (
    <a href={`https://${host}${p}`}
      style={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace' }}>
      {host}{p}
    </a>
  )
  return (
    <p className="mb-2" style={{ color: 'var(--text-muted)' }}>
      <strong style={{ color: 'var(--text-secondary)' }}>Data.</strong>{' '}
      Every figure here is downloadable, and every source document with it.{' '}
      {link('/llms.txt')} · {link('/minutes/INDEX.txt')} · {link('/data/minutes-index.csv')}
      {' · '}{link('/api/index')} · {link('/agents')}
      {corpus ? ` — full text of ${corpus.split(' across ')[0]}, across every town board.` : '.'}
    </p>
  )
}
