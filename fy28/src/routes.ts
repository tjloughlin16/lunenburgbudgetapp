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

export type Tab = 'home' | 'walk' | 'deeper' | 'answers' | 'money' | 'themoney' | 'context' | 'why' | 'curve' | 'override'
  | 'priorities' | 'adjust' | 'development' | 'solved' | 'sources' | 'athletics' | 'rates' | 'freecash'
  | 'dataroom' | 'reports' | 'agents' | 'ask'

/** The canonical URL for each tab. The default tab lives at the root. */
export const SLUG: Record<Tab, string> = {
  // The root is a CHOOSER, not a chapter. It was the walkthrough, and before that Straight
  // answers, and each time the page at the root was one reading path presented as the whole
  // site. It is not: the argument, the documents, the data and the machine-readable
  // addresses are four different visits. See pages/Home.
  home: '',
  // The walkthrough gave up the root and kept every word. This is the one address on the
  // site that has ever moved, which is why `walkthrough` and `start-here` were already
  // aliases for it — anybody who typed one lands where they always did, and `/` now
  // answers with the door rather than with a 404 or a redirect.
  walk: 'walkthrough',
  deeper: 'go-deeper',
  answers: 'straight-answers',
  money: 'find-the-money',
  // THE MONEY area's front door. NOT `money` -- that tab id has meant `/find-the-money`
  // since long before the areas existed, and both the slug and the `money` alias are
  // cited off this site. An area and a page may share a name; they may not share a Tab.
  themoney: 'the-money',
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
  // A drill-in, not a chapter. Linked from the situation page and from Go deeper.
  athletics: 'athletics',
  // Reference, not argument. Every rate the model uses, with the year it applies to and
  // the document that set it — built after FY26 athletic fees were priced on FY25's
  // schedule for months because the source stated rates and never stated a year.
  rates: 'rate-register',
  // One-time money, and the page exists to show that it cannot bend the curve.
  freecash: 'free-cash',
  // What this project WROTE, as opposed to what it mirrors. Public and linked.
  reports: 'reports',
  // Every machine-readable address on the site, as LINKS. `llms.txt` names all of these
  // already, but it is text/plain, and assistants that only fetch URLs seen in a prior
  // page could read the name of a file and not be allowed to request it. See
  // components/AgentsIndex.tsx -- this page exists to put them in the link graph.
  agents: 'agents',
  // How to point an assistant at this archive, with the prompt to paste. Short address
  // on purpose: it gets read aloud and typed on a phone, which is the same reason
  // lburg.org exists. See components/AskAnAssistant.tsx.
  ask: 'ask',
  // UNLISTED. See UNLISTED below before adding a link to this anywhere.
  dataroom: 'data-room',
}

/** Pages that exist at an address and are reachable from nowhere.
 *
 *  Unlisted, NOT private, and the difference is the whole of it: there is no nav entry,
 *  no index entry, no sitemap entry and no prerendered file, so nothing links here and
 *  nothing crawls here. Anyone holding the address can read it, and if the address is
 *  ever posted anywhere it will be indexed like any other page. It is a page you hand to
 *  somebody, not a page behind a lock.
 *
 *  Deliberately NOT added to robots.txt. A Disallow line is served publicly to anybody
 *  who asks for it, so listing the path there would advertise the thing it is meant to
 *  keep quiet — the classic own-goal of that file.
 *
 *  Give an unlisted page NO alias. An alias is a second guessable address. */
export const UNLISTED: ReadonlySet<Tab> = new Set<Tab>(['dataroom'])

/** Forms somebody might type or that an older link might carry. Never generated, always
 *  accepted — a link that has been shared once is out of your hands forever. */
const ALIASES: Record<string, Tab> = {
  // The chooser answers to a name as well as to the root. `/` is what gets shared; `home`
  // is what somebody types when they have lost their place.
  home: 'home', doors: 'home',
  answers: 'answers',
  walk: 'walk', walkthrough: 'walk', start: 'walk', 'start-here': 'walk',
  deeper: 'deeper', more: 'deeper', everything: 'deeper',
  money: 'money', context: 'context', situation: 'context',
  why: 'why', rates: 'curve', curve: 'curve',
  override: 'override', 'the-override': 'override',
  adjust: 'adjust', budget: 'adjust', build: 'adjust',
  solved: 'solved', packages: 'solved', sustainable: 'solved', forever: 'solved',
  sources: 'sources', documents: 'sources', evidence: 'sources', citations: 'sources',
  athletics: 'athletics', sports: 'athletics', athletic: 'athletics',
  // NOT 'rates' -- that alias already means the curve page, and has since before this
  // page existed. A shared link must not change where it lands.
  'rate-register': 'rates', fees: 'rates', 'fee-schedule': 'rates', register: 'rates',
  // NOT 'money' -- taken, and by a page in a different area.
  'the-money': 'themoney', 'how-money-works': 'themoney', 'money-flow': 'themoney',
  'follow-the-money': 'themoney',
  'free-cash': 'freecash', freecash: 'freecash', reserves: 'freecash', 'certified-free-cash': 'freecash',
  reports: 'reports', analyses: 'reports', analysis: 'reports', 'our-analyses': 'reports',
  // NOT 'api' or 'data' -- both are live Function prefixes serving real files, and an
  // alias would shadow the archive with an app route.
  agents: 'agents', 'for-agents': 'agents', ai: 'agents', llms: 'agents',
  'machine-readable': 'agents', downloads: 'agents',
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
  home: 'Home',
  walk: 'Start here',
  deeper: 'Go deeper',
  answers: 'Straight answers',
  money: 'Find the money',
  themoney: 'How the money moves',
  context: 'The situation',
  why: 'Why it repeats',
  curve: 'Bend the curve',
  override: 'Overrides',
  priorities: 'Priorities',
  adjust: 'Build your own budget',
  development: 'Development',
  solved: 'What solved would require',
  sources: 'Sources',
  athletics: 'Athletics, both sides of the money',
  rates: 'Rates, fees and contracts — the register',
  freecash: 'Free cash — how much is actually spendable',
  reports: 'Reports and analyses',
  ask: 'How to query this data',
  agents: 'Every address on this site, as links',
  dataroom: 'The data room',
}

/** Which page a drill-in sits under, for the trail back when somebody arrives by link
 *  rather than by clicking. The two boards hang off the walkthrough because they are in
 *  its header; everything else is behind the one door. */
export const PARENT: Partial<Record<Tab, Tab>> = {
  answers: 'deeper', money: 'deeper', context: 'deeper', why: 'deeper',
  override: 'deeper', priorities: 'deeper', development: 'deeper', solved: 'deeper',
  athletics: 'context',
  rates: 'deeper',
  reports: 'themoney',
  agents: 'sources',
  freecash: 'money',
}

export const pathFor = (tab: Tab): string => (SLUG[tab] ? `/${SLUG[tab]}` : '/')

/** Whichever tab owns the root, derived rather than named.
 *
 *  This was hardcoded to 'answers', and moving the front door to the walkthrough left it
 *  quietly pointing at the old one — so the root and every unrecognized path still resolved
 *  to Straight answers while every test of the nav said otherwise. Derived, it cannot
 *  drift the next time the front door moves. */
export const ROOT: Tab = (Object.entries(SLUG) as [Tab, string][]).find(([, v]) => v === '')![0]

/** Anything unrecognized falls back to the first tab rather than to an error page.
 *  A stale link should land somebody on the site, not on a 404 they will not report. */
export function tabFromPath(pathname: string): Tab {
  const seg = pathname.replace(/^\/+|\/+$/g, '').toLowerCase()
  return BY_SLUG[seg] ?? ROOT
}

/** WHICH AREA A PAGE BELONGS TO — the nav is scoped, the URLs are not.
 *
 *  The header used to show one flat bar on every page: the walkthrough, Go deeper,
 *  Sources and the two boards. That bar is the CRISIS ANALYSIS chapter list, and showing
 *  it on the front page re-presented the corridor the chooser exists to escape. TJ:
 *  "those tabs and pages should only show when going into that subpage."
 *
 *  So navigation is scoped by area and **the addresses are not touched**. `/bend-the-curve`
 *  does not become `/crisis/bend-the-curve`: those slugs are cited off this site and a URL
 *  is an interface. Navigation scope does not have to equal URL nesting, which is what
 *  makes this a nav change rather than a migration — and why check_moved_docs.py has
 *  nothing new to check.
 *
 *  `sources` is deliberately in NO area. It backs all four, and putting it inside one
 *  would say it belongs to that one. It stays in the header everywhere, as a utility
 *  link rather than a peer tab — the claim this site rests on is that a resident can
 *  check it, and evidence reachable only from inside one area is a weaker claim than it
 *  sounds.
 */
export type Area = 'crisis' | 'money' | 'data' | 'agents'

export const AREA_LABEL: Record<Area, string> = {
  // TJ, 7 Sept: "Budget Crisis". Names the thing rather than the reader's posture
  // toward it — and it is what the town calls it, which is what a door has to match.
  crisis: 'Budget Crisis',
  money: 'The money',
  data: 'The database',
  agents: 'For AI assistants',
}

/** The page each area opens at, and the tab that owns its bar. */
export const AREA_HOME: Record<Area, Tab> = {
  crisis: 'walk', money: 'themoney', data: 'rates', agents: 'ask',
}

const AREA_OF: Partial<Record<Tab, Area>> = {
  walk: 'crisis', deeper: 'crisis', answers: 'crisis', money: 'crisis', context: 'crisis',
  why: 'crisis', curve: 'crisis', override: 'crisis', priorities: 'crisis',
  adjust: 'crisis', development: 'crisis', solved: 'crisis', athletics: 'crisis',
  freecash: 'crisis',
  themoney: 'money', reports: 'money',
  rates: 'data', dataroom: 'data',
  ask: 'agents', agents: 'agents',
}

export function areaOf(t: Tab): Area | null {
  return AREA_OF[t] ?? null
}

/** The tabs shown in an area's own bar, in order. Drill-ins are reachable from the pages
 *  that link them rather than from the bar — a bar with fourteen entries is a sitemap. */
export const AREA_TABS: Record<Area, Tab[]> = {
  crisis: ['walk', 'solved', 'curve', 'adjust', 'answers', 'deeper'],
  money: ['themoney', 'reports'],
  data: ['rates'],
  agents: ['ask', 'agents'],
}
