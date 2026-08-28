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

export type Tab = 'walk' | 'deeper' | 'answers' | 'money' | 'context' | 'why' | 'curve' | 'override'
  | 'priorities' | 'adjust' | 'development' | 'solved' | 'sources'

/** The canonical URL for each tab. The default tab lives at the root. */
export const SLUG: Record<Tab, string> = {
  // The walkthrough is the front door now, so it takes the root. Straight answers keeps
  // an address of its own rather than losing one — nothing here has been retired.
  walk: '',
  deeper: 'go-deeper',
  answers: 'straight-answers',
  money: 'find-the-money',
  context: 'the-situation',
  why: 'why-it-repeats',
  curve: 'bend-the-curve',
  override: 'overrides',
  priorities: 'priorities',
  adjust: 'build-your-own-budget',
  development: 'development',
  solved: 'what-solved-requires',
  // Top level, and a short address. This is the page somebody is sent to when they say
  // they do not believe a number, and the link has to survive being read aloud.
  sources: 'sources',
}

/** Forms somebody might type or that an older link might carry. Never generated, always
 *  accepted — a link that has been shared once is out of your hands forever. */
const ALIASES: Record<string, Tab> = {
  answers: 'answers',
  walk: 'walk', walkthrough: 'walk', start: 'walk', 'start-here': 'walk',
  deeper: 'deeper', more: 'deeper', everything: 'deeper',
  money: 'money', context: 'context', situation: 'context',
  why: 'why', rates: 'curve', curve: 'curve',
  override: 'override', 'the-override': 'override',
  adjust: 'adjust', budget: 'adjust', build: 'adjust',
  solved: 'solved', packages: 'solved', sustainable: 'solved', forever: 'solved',
  sources: 'sources', documents: 'sources', evidence: 'sources', citations: 'sources',
}

const BY_SLUG: Record<string, Tab> = {
  ...ALIASES,
  ...Object.fromEntries(
    (Object.entries(SLUG) as [Tab, string][])
      .filter(([, v]) => v).map(([k, v]) => [v, k])),
}

/** What each page is called, in one place.
 *
 *  Was duplicated between the nav, the Go deeper index and the breadcrumb, which is three
 *  chances for a page to be called two things. */
export const LABEL: Record<Tab, string> = {
  walk: 'Start here',
  deeper: 'Go deeper',
  answers: 'Straight answers',
  money: 'Find the money',
  context: 'The situation',
  why: 'Why it repeats',
  curve: 'Bend the curve',
  override: 'Overrides',
  priorities: 'Priorities',
  adjust: 'Build your own budget',
  development: 'Development',
  solved: 'What solved would require',
  sources: 'Sources',
}

/** Which page a drill-in sits under, for the trail back when somebody arrives by link
 *  rather than by clicking. The two boards hang off the walkthrough because they are in
 *  its header; everything else is behind the one door. */
export const PARENT: Partial<Record<Tab, Tab>> = {
  answers: 'deeper', money: 'deeper', context: 'deeper', why: 'deeper',
  override: 'deeper', priorities: 'deeper', development: 'deeper', solved: 'deeper',
}

export const pathFor = (tab: Tab): string => (SLUG[tab] ? `/${SLUG[tab]}` : '/')

/** Whichever tab owns the root, derived rather than named.
 *
 *  This was hardcoded to 'answers', and moving the front door to the walkthrough left it
 *  quietly pointing at the old one — so the root and every unrecognised path still resolved
 *  to Straight answers while every test of the nav said otherwise. Derived, it cannot
 *  drift the next time the front door moves. */
const ROOT: Tab = (Object.entries(SLUG) as [Tab, string][]).find(([, v]) => v === '')![0]

/** Anything unrecognised falls back to the first tab rather than to an error page.
 *  A stale link should land somebody on the site, not on a 404 they will not report. */
export function tabFromPath(pathname: string): Tab {
  const seg = pathname.replace(/^\/+|\/+$/g, '').toLowerCase()
  return BY_SLUG[seg] ?? ROOT
}
