/** Which tab a URL means, and which URL a tab has.
 *
 *  Split out of App so it can be tested without a browser: the whole point of shareable
 *  links is that somebody else follows one, and "it worked when I clicked it" is not
 *  evidence that /find-the-money resolves.
 *
 *  Paths rather than hashes. The situation page already uses `#anchor` for its own
 *  sections, and a hash router would fight it for the same slice of the URL — this way
 *  /bend-the-curve#leverage means what it looks like it means. Both hosts are configured
 *  to serve index.html for any path, so a cold load of a deep link works. */

export type Tab = 'answers' | 'money' | 'context' | 'why' | 'curve' | 'override'
  | 'priorities' | 'adjust' | 'development'

/** The canonical URL for each tab. The default tab lives at the root. */
export const SLUG: Record<Tab, string> = {
  answers: '',
  money: 'find-the-money',
  context: 'the-situation',
  why: 'why-it-repeats',
  curve: 'bend-the-curve',
  override: 'overrides',
  priorities: 'priorities',
  adjust: 'build-your-own-budget',
  development: 'development',
}

/** Forms somebody might type or that an older link might carry. Never generated, always
 *  accepted — a link that has been shared once is out of your hands forever. */
const ALIASES: Record<string, Tab> = {
  'straight-answers': 'answers', answers: 'answers',
  money: 'money', context: 'context', situation: 'context',
  why: 'why', rates: 'curve', curve: 'curve',
  override: 'override', 'the-override': 'override',
  adjust: 'adjust', budget: 'adjust', build: 'adjust',
}

const BY_SLUG: Record<string, Tab> = {
  ...ALIASES,
  ...Object.fromEntries(
    (Object.entries(SLUG) as [Tab, string][])
      .filter(([, v]) => v).map(([k, v]) => [v, k])),
}

export const pathFor = (tab: Tab): string => (SLUG[tab] ? `/${SLUG[tab]}` : '/')

/** Anything unrecognised falls back to the first tab rather than to an error page.
 *  A stale link should land somebody on the site, not on a 404 they will not report. */
export function tabFromPath(pathname: string): Tab {
  const seg = pathname.replace(/^\/+|\/+$/g, '').toLowerCase()
  return BY_SLUG[seg] ?? 'answers'
}
