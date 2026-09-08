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
  | 'dataroom' | 'reports' | 'agents' | 'ask' | 'database' | 'gaps' | 'variance'
  | 'askus'
  | 'funds'
  | 'staffing'
  | 'insurance'
  | 'sportsmoney'
  | 'stateaid'
  | 'stopped'
  | 'leaving'
  | 'families'

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
  // Budgets against what the district LATER REPORTED it spent. The label says "reported"
  // and not "actuals" on purpose: before FY2026 both columns come out of a district budget
  // book, and a budget book restating itself is not an accounting record. The SLUG does
  // not move -- it is published and cited, people say "budget versus actual" out loud, and
  // an address is an interface. `variance` is an alias for anybody arriving with the
  // accounting word instead.
  variance: 'budget-vs-actual',
  // The special revenue funds — grants, revolving funds, gifts, and the enterprise
  // funds — read out of thirteen annual town reports. The slug is the QUESTION rather
  // than the accounting term: a resident says "money outside the budget", and
  // `special-revenue` is an alias for anybody who arrives with the words the town uses.
  funds: 'money-outside-the-budget',
  // Every machine-readable address on the site, as LINKS. `llms.txt` names all of these
  // already, but it is text/plain, and assistants that only fetch URLs seen in a prior
  // page could read the name of a file and not be allowed to request it. See
  // components/AgentsIndex.tsx -- this page exists to put them in the link graph.
  agents: 'agents',
  // How to point an assistant at this archive, with the prompt to paste. Short address
  // on purpose: it gets read aloud and typed on a phone, which is the same reason
  // lburg.org exists. See components/AskAnAssistant.tsx.
  ask: 'ask',
  // A RESIDENT asks us a question, in their own words. Distinct from `ask`, which is the
  // agent-facing page about querying the data and has meant that for far longer. The slug
  // is the sentence somebody would say -- "ask a question" -- not "contact" or "feedback",
  // both of which promise something else: contact is about reaching a person, feedback is
  // about the site. This is about the BUDGET.
  askus: 'ask-a-question',
  // THE DATABASE area's front door. NOT `data` -- `/data` is a live Function prefix
  // serving real files, and an app route there would shadow the archive. The area is
  // `data` and the tab is `database`; an area and a page may share a name, they may not
  // share an address.
  database: 'database',
  // The gaps, in one place. NOT `gaps` as the address: what a resident types or reads
  // aloud is the question, and "what we cannot answer" is the question. `gaps` is an
  // alias, because it is what anybody working on the site calls it.
  gaps: 'what-we-cannot-answer',
  // The people the budget buys, in the three quantities the archive actually holds --
  // names the town printed, FTE the state published, and dollars. NOT `staff`: the page
  // is about the SCHOOLS' staffing and a bare `staff` would read as the town's. The word
  // people say out loud is "school staffing", so that is the address; `staffing` and the
  // rest are aliases.
  staffing: 'school-staffing',
  // The largest school cost that is not in the school budget. The slug is the THING, not
  // the finding — `health-insurance` is what a resident types and what gets read aloud at
  // a meeting. NOT `insurance` on its own: the town's ledger has a liability-insurance
  // department too, and a bare `insurance` would promise both.
  insurance: 'health-insurance',
  // Athletics drilled in: both sides of the money, charted. NOT `athletics` -- that tab
  // has meant the DECISION BOARD since long before this page existed, it is cited off
  // this site, and `sports`/`athletic` are already aliases for it. The slug is the
  // QUESTION a resident asks out loud -- "what do sports actually cost?" -- rather than
  // the accounting shape of the answer.
  sportsmoney: 'what-sports-cost',
  // The share of the school budget nobody in Lunenburg votes on. The slug is the THING a
  // resident says out loud -- "state aid" -- rather than `chapter-70`, which is the
  // accounting name for only the largest part of it and would promise less than the page
  // holds. NOT `aid` on its own: that reads as assistance to residents, which is a
  // different department in a different part of the budget.
  stateaid: 'state-aid',
  // Every school line the district's own book took to zero, and when. The slug is the
  // QUESTION as it was asked out loud -- "what wasn't paid for that previously was
  // paid?" -- rather than `defunded` or `cuts`, both of which state a conclusion this
  // page is careful not to draw: a line ending is not a service ending. NOT `zeros` or
  // `zeroed`, which name our instrument instead of the reader's question.
  stopped: 'what-stopped-being-funded',
  // What school choice would cost the town if students transferred out. The slug is the
  // sentence a resident says -- "if students leave" -- rather than `school-choice`, which
  // names a programme and would promise the whole of it, including the seats Lunenburg
  // OPENS, which is a different page's worth of material and the opposite direction of
  // money. NOT `enrollment-decline`: the page is about a decision families make, not
  // about a birth cohort, and those have different remedies.
  leaving: 'if-students-leave',
  // What a HOUSEHOLD pays, as against what the town raises. The slug is the sentence a
  // resident says out loud at a meeting -- "what do families actually pay?" -- rather than
  // `fees`, which is already an alias for the rate register and promises the schedule
  // instead of the bill. NOT `what-parents-pay`: the argument this page answers is about
  // families, and a household with no child in the schools is the other half of it.
  families: 'what-families-pay',
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
  // NOT 'actuals' alone as the slug: the page is a COMPARISON, and a reader who lands on
  // something called "actuals" reasonably expects a spending ledger, which is a different
  // page in a different area.
  'budget-vs-actual': 'variance', variance: 'variance', 'budgets-vs-actuals': 'variance',
  'budget-versus-actual': 'variance', actuals: 'variance', underspend: 'variance',
  // NOT 'api' or 'data' -- both are live Function prefixes serving real files, and an
  // alias would shadow the archive with an app route.
  agents: 'agents', 'for-agents': 'agents', ai: 'agents', llms: 'agents',
  'machine-readable': 'agents', downloads: 'agents',
  // NOT 'data', 'api' or 'schema' -- the first two are Function prefixes and the third is
  // a published reference document at /reference/schema.html.
  database: 'database', 'the-database': 'database', db: 'database',
  'the-data': 'database',
  // NOT 'missing' or 'unknown' -- both would read as a page about the archive being
  // broken. The page is about what the TOWN'S RECORDS do not say.
  gaps: 'gaps', 'what-we-cannot-answer': 'gaps', 'data-gaps': 'gaps',
  'what-is-not-in-here': 'gaps', gap: 'gaps',
  // NOT 'funds' on its own -- what a reader means by that word here is free cash, and
  // `freecash` already answers to `reserves`. This page is specifically the money that
  // is NOT appropriated.
  'money-outside-the-budget': 'funds', 'special-revenue': 'funds',
  'special-revenue-funds': 'funds', 'revolving-funds': 'funds', grants: 'funds',
  'outside-the-budget': 'funds',
  // NOT 'teachers' alone as the slug -- the page is about paraprofessionals at least as
  // much, and naming it for one role would tell a reader what the finding is before they
  // have seen it.
  'school-staffing': 'staffing', staffing: 'staffing', staff: 'staffing',
  teachers: 'staffing', headcount: 'staffing', paraprofessionals: 'staffing',
  paras: 'staffing', 'staff-rosters': 'staffing', rosters: 'staffing',
  // NOT 'retirees' or 'benefits' alone -- the first names only half the page and the
  // second would promise pensions, which are a different assessment in a different
  // department and are NOT established here.
  'health-insurance': 'insurance', insurance: 'insurance', health: 'insurance',
  'retiree-health': 'insurance', 'chapter-32b': 'insurance', 'schrethlth': 'insurance',
  // NOT 'athletics', 'sports' or 'athletic' -- all three already land on the decision
  // board, and a link that has been shared once must keep landing where it landed.
  'ask-a-question': 'askus', 'ask-us': 'askus', 'question': 'askus',
  'ask-a-budget-question': 'askus', 'submit-a-question': 'askus',
  'what-sports-cost': 'sportsmoney', 'athletics-money': 'sportsmoney',
  'sports-money': 'sportsmoney', 'athletics-cost': 'sportsmoney',
  'who-pays-for-sports': 'sportsmoney', 'athletics-both-sides': 'sportsmoney',
  // NOT 'aid' alone -- see the slug note. `chapter-70` and `cherry-sheet` are the two
  // names the documents use, and somebody arriving with either should land here.
  'state-aid': 'stateaid', 'chapter-70': 'stateaid', ch70: 'stateaid',
  'cherry-sheet': 'stateaid', 'local-aid': 'stateaid', 'school-aid': 'stateaid',
  // NOT 'cuts' -- a cut is a decision somebody made, and what this page measures is a
  // line going to zero in a document. The two are not the same claim, and the address
  // should not promise the stronger one. `defunded` and `zeroed-out` are what people
  // type looking for it, so both land here.
  'what-stopped-being-funded': 'stopped', 'stopped-being-funded': 'stopped',
  defunded: 'stopped', 'zeroed-out': 'stopped', 'what-stopped': 'stopped',
  'lines-that-stopped': 'stopped',
  // `school-choice` lands here because it is what somebody types, even though the page is
  // only one direction of it -- and the page says in its first screen which direction.
  // NOT 'choice' alone: it reads as the budget choices boards make, which is most of this
  // site. NOT 'enrollment', which is a count and not a scenario.
  // NOT 'fees' or 'fee-schedule' -- both have meant the rate register since before this
  // page existed, and a shared link must not change where it lands.
  'what-families-pay': 'families', 'family-fees': 'families',
  'what-parents-pay': 'families', 'school-fees': 'families',
  'student-fees': 'families', 'user-fees': 'families',
  'if-students-leave': 'leaving', 'school-choice': 'leaving', 'choicing-out': 'leaving',
  'students-leaving': 'leaving', 'school-choice-scenario': 'leaving',
  'what-if-students-leave': 'leaving', 'transfers-out': 'leaving',
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
  database: 'The database',
  gaps: 'What we cannot answer',
  variance: 'Budgets against what was later reported',
  funds: 'The money outside the budget',
  staffing: 'School staffing — names, FTE and dollars',
  insurance: 'Health insurance — the cost outside the school budget',
  sportsmoney: 'What sports cost, and who pays',
  stateaid: 'State aid — the part nobody here votes on',
  stopped: 'What stopped being funded',
  leaving: 'If students leave — what school choice would cost',
  families: 'What a family actually pays',
  askus: 'Ask us a question',
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
  gaps: 'themoney',
  variance: 'themoney',
  funds: 'themoney',
  staffing: 'themoney',
  insurance: 'themoney',
  sportsmoney: 'themoney',
  askus: 'themoney',
  stateaid: 'themoney',
  stopped: 'themoney',
  leaving: 'themoney',
  families: 'themoney',
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
export type Area = 'crisis' | 'money' | 'analyses' | 'data' | 'agents'

export const AREA_LABEL: Record<Area, string> = {
  // TJ, 7 Sept: "Budget Crisis". Names the thing rather than the reader's posture
  // toward it — and it is what the town calls it, which is what a door has to match.
  crisis: 'Budget Crisis',
  money: 'The money',
  // TJ, 8 Sept: "Maybe we need another category, like 'School Detailed Analysis' next to
  // 'The Money'". He was right, and the count is the argument: `money` had reached
  // THIRTEEN tabs in one strip -- which the comment on AREA_TABS below already warned
  // against in the same file, and which is unusable on a phone.
  //
  // IT WAS `School analysis` FOR AN HOUR AND THAT WAS THE WRONG NAME. TJ, same day:
  // "Maybe we have just an Analyses section, not school specific, so we can also dump
  // town reports too." A name that says `school` is a promise about the contents, and
  // half the analyses this project will write are town-side -- free cash, the tax rate,
  // the ledger. Naming the area after the FORM (an analysis) rather than the SUBJECT
  // (schools) is what lets the town reports land here without a second rename.
  analyses: 'Analyses',
  data: 'The database',
  agents: 'For AI assistants',
}

/** The page each area opens at, and the tab that owns its bar. */
export const AREA_HOME: Record<Area, Tab> = {
  // `analyses` opens on /reports, which is the generated index of every analysis on
  // disk. An area whose front page is a list of what is in it needs no new hub page --
  // and build_reports_index.py already fails if an analysis is missing from it.
  crisis: 'walk', money: 'themoney', analyses: 'reports', data: 'database', agents: 'ask',
}

const AREA_OF: Partial<Record<Tab, Area>> = {
  walk: 'crisis', deeper: 'crisis', answers: 'crisis', money: 'crisis', context: 'crisis',
  why: 'crisis', curve: 'crisis', override: 'crisis', priorities: 'crisis',
  adjust: 'crisis', development: 'crisis', solved: 'crisis', athletics: 'crisis',
  freecash: 'crisis',
  // `money` is now WHERE THE MONEY COMES FROM AND GOES, plus the limits of the record:
  // the flow hub, the two revenue-side pages, what we cannot answer, and the question box.
  themoney: 'money', stateaid: 'money', funds: 'money', gaps: 'money', askus: 'money',
  // `analyses` is every drill-in REPORT, school or town. Health insurance and budget-vs-
  // actual moved here from the money side: both are analyses of spending rather than
  // accounts of where money originates, and filing them by subject was what produced a
  // thirteen-tab strip in the first place.
  reports: 'analyses', staffing: 'analyses', stopped: 'analyses', leaving: 'analyses',
  families: 'analyses', sportsmoney: 'analyses', insurance: 'analyses',
  variance: 'analyses',
  database: 'data', rates: 'data', dataroom: 'data',
  ask: 'agents', agents: 'agents',
}

export function areaOf(t: Tab): Area | null {
  return AREA_OF[t] ?? null
}

/** The tabs shown in an area's own bar, in order. Drill-ins are reachable from the pages
 *  that link them rather than from the bar — a bar with fourteen entries is a sitemap. */
export const AREA_TABS: Record<Area, Tab[]> = {
  // The three BOARDS — what would fix it, bend the curve, build your own budget — are
  // not here. They are `CTAS` in App.tsx and render as buttons at the right of the same
  // bar, so listing them here drew each of them twice. Chapters and tools are different
  // things sharing one strip; the lists must stay disjoint, and `assertNoDuplicateNav`
  // below fails loudly if they stop being.
  crisis: ['walk', 'answers', 'deeper'],
  money: ['themoney', 'stateaid', 'funds', 'gaps', 'askus'],
  analyses: ['reports', 'staffing', 'stopped', 'leaving', 'families', 'sportsmoney',
             'insurance', 'variance'],
  data: ['database', 'rates'],
  agents: ['ask', 'agents'],
}

/** The area bar and the boards must not draw the same page twice.
 *
 *  They did: `solved`, `curve` and `adjust` were in AREA_TABS.crisis AND in CTAS, so the
 *  crisis header showed each of them as a tab and again as a button. Nothing failed,
 *  because a nav that renders something twice is still a valid nav — which is exactly why
 *  this needs an assertion rather than care.
 *
 *  Called from App at module load. In a dev build it throws; in production it warns and
 *  the page still renders, because a duplicated button is ugly and a blank site is worse.
 */
export function assertNoDuplicateNav(ctaIds: Tab[]): void {
  const dupes = (Object.keys(AREA_TABS) as Area[]).flatMap(a =>
    AREA_TABS[a].filter(t => ctaIds.includes(t)).map(t => `${a}:${t}`))
  if (!dupes.length) return
  const msg = `nav draws these twice — in AREA_TABS and in CTAS: ${dupes.join(', ')}`
  if (import.meta.env.DEV) throw new Error(msg)
  console.warn(msg)
}
