import MANIFEST from '../data/agent-manifest.json'

/** The machine-readable addresses, at the TOP of the document.
 *
 *  WHY THE TOP, WHEN THE FOOTER ALREADY HAS THEM
 *
 *  Because the footer is not delivered. Measured on the production front page: it is
 *  255,823 bytes, and `href="/api/index"` sits at byte 243,571 -- **95.2% of the way
 *  through**. A reader that converts a page and caps the result never reaches it. That is
 *  not a guess: `/api/lines`, 121KB of JSON, comes back from a fetch tool truncated
 *  mid-record, so the ceiling is well under this page's size.
 *
 *  So an assistant read this site, was told by `llms.txt` that `/api/index` exists, and
 *  could not fetch it -- its own words: *"the fetch tool is refusing every URL on the site
 *  except the two I already pulled... it isn't registering the ones inside llms.txt."*
 *  Both halves were true at once. The links were live and unreachable.
 *
 *  `llms.txt` cannot fix this, ever. It is `text/plain`, so the addresses in it are text
 *  rather than links, and a reader that only fetches URLs it has seen linked is not
 *  authorised by it. **The only route into the link graph is an HTML page, and the links
 *  have to be early enough in one to survive the cut.** This line lands inside the first
 *  couple of KB of converted text on every route.
 *
 *  It is small, visible and honest -- not hidden, for the reasons in DataFooter.tsx: text
 *  served only to machines is cloaking, and it would not work anyway, because the readers
 *  that matter drop hidden nodes exactly as they drop comments.
 *
 *  ONE LINK, NOT FIVE -- changed 6 September 2026
 *
 *  It listed five addresses, and a resident opening the front page met a row of file paths
 *  before a word about the budget. TJ: "it's just too overwhelming." That is a real cost
 *  and it was being paid by every human visitor to buy something for a minority of
 *  machine ones.
 *
 *  What matters is not that the addresses are HERE. It is that a machine-readable entry
 *  point is EARLY -- above the truncation cut -- and that following it reaches everything.
 *  So the strip is one link to /ask, which carries the prompt, every endpoint as a real
 *  anchor, and the MCP server. One hop, and the hop is complete.
 *
 *  That is the condition to preserve if this is ever edited again: /ask must keep real
 *  anchors to the endpoints. If it degrades into prose about them, this line becomes a
 *  dead end that looks like an index, which is worse than the row of paths it replaced.
 *  `check-agents.mjs` fetches every advertised URL, and DataFooter still lists them all.
 *
 *  `scripts/agent-view.mjs --links` fails the build if any of these drifts past 50,000
 *  characters of converted text, so this cannot quietly slide down the page again. */
/* Absolute. This line is the first machine-readable address on the page, put there
 * because /api/index used to sit 95% of the way down the homepage; a relative href
 * makes it unusable to the caller it was moved up for. */
/* The host appears ONCE, on the first link. Repeating it five times is ink that
 * carries no information -- a human reads the same 27 characters over and over to
 * find the four that differ. The hrefs stay absolute either way, which is the part
 * a fetcher uses. */
const ABS = (p: string) => `${MANIFEST.site}${p}`

export function DataTopLine() {
  const host = MANIFEST.site.replace(/^https?:\/\//, '')
  return (
    <div className="border-b" style={{ borderColor: 'var(--grid)' }}>
      <p className="mx-auto max-w-6xl px-5 py-1.5 text-[12px]">
        {/* The link text is the DESCRIPTION, not "click here". A screen reader can list a
          * page's links out of context, and "click here" nine times is a list of nine
          * identical entries -- WCAG 2.4.4. It also means the words a person scans are the
          * words that say what happens, which is the same reason it reads better. */}
        <a href={ABS('/ask')} className="font-semibold underline underline-offset-2"
          style={{ color: 'var(--series-cost)' }}>
          Analyse this budget with AI
        </a>
        <span className="ml-2" style={{ color: 'var(--text-muted)' }}>
          {host}/ask
        </span>
      </p>
    </div>
  )
}
