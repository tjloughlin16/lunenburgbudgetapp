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
 *  just wants the spreadsheet all find the same thing. */
export function DataFooter() {
  const host = MANIFEST.site.replace(/^https?:\/\//, '')
  const corpus = MANIFEST.corpus || ''
  const link = (p: string) => (
    <a href={p} style={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace' }}>
      {host}{p}
    </a>
  )
  return (
    <p className="mb-2" style={{ color: 'var(--text-muted)' }}>
      <strong style={{ color: 'var(--text-secondary)' }}>Data.</strong>{' '}
      Every figure here is downloadable, and every source document with it.{' '}
      {link('/llms.txt')} · {link('/data/')} · {link('/minutes/')}
      {corpus ? ` — full text of ${corpus.split(' across ')[0]}, across every town board.` : '.'}
    </p>
  )
}
