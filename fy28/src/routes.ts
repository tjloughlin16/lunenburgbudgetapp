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
  | 'schoolstaff'
  | 'parastaff'
  | 'insurance'
  | 'sportsmoney'
  | 'stateaid'
  | 'stopped'
  | 'cuts'
  | 'leaving'
  | 'families'
  | 'unwind'
  | 'minaid'
  | 'formula'
  | 'sped'
  | 'spedcount'
  | 'outflow'
  | 'spedcost'
  | 'spedroute'
  | 'classsize'
  | 'courses'
  | 'attrition'
  | 'enrollment'
  | 'circuitbreaker'
  | 'ap'
  | 'bythenumbers'
  // The middle of three lengths. One tab for all the posts: the slug is the second path
  // segment, `/blog/why-a-school-with-fewer-children-is-not-a-cheaper-school`, and
  // `blogSlugFromPath` below reads it. The bare `/blog` is the archive. See pages/Blog.
  | 'blog'
  | 'peers'
  | 'montytech'
  | 'required'
  | 'addsup'
  // Every analysis written as a MARKDOWN document rather than as a React page. One tab
  // for seventeen documents: the id is the second path segment, `/analysis/free-cash`,
  // and `analysisIdFromPath` below reads it. See pages/Analysis.tsx for why the documents
  // are rendered rather than transcribed.
  | 'analysis'
  | 'search'
  | 'recorded'
  | 'thisweek'

/** The canonical URL for each tab. The default tab lives at the root. */
export const SLUG: Record<Tab, string> = {
  // The root is a CHOOSER, not a chapter. It was the walkthrough, and before that Straight
  // answers, and each time the page at the root was one reading path presented as the whole
  // site. It is not: the argument, the documents, the data and the machine-readable
  // addresses are four different visits. See pages/Home.
  home: '',
  // The walkthrough gave up the root and kept every word, and on 12 September 2026 it
  // gave up its name too. TJ: "rename the url for budget crisis to just /crisis vs
  // /walkthrough" -- the section is called Budget Crisis everywhere a reader sees it,
  // and an address should say what the page is, not how it was written. `walkthrough`
  // and `start-here` stay as aliases; nothing anybody typed or shared stops working.
  walk: 'crisis',
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
  // WHY /school-staffing IS THIS PAGE AND NOT ONE OF THE OTHER TWO.
  //
  // The address was published, linked from other reports, listed in the sitemap and in
  // llms.txt, and is cited off this site. It has always led with the window argument --
  // the h1 a reader met was about the years somebody picks -- so the reader arriving on
  // an old link lands on the finding they were sent for. Splitting a page is not a reason
  // to move an address, and every alias below stays exactly where it was pointing.
  //
  // The two pages carved out of it take NEW addresses, and take only forms nobody has
  // been given before.
  //
  // Who is in the building, which is the question a parent actually arrives with. NOT
  // `staff-by-school` or `rosters` as the slug: `rosters` and `staff-rosters` have meant
  // /school-staffing since long before this page existed and keep meaning it. The slug is
  // the sentence somebody says out loud.
  schoolstaff: 'who-works-in-each-school',
  // The biggest single change in who the schools employ. NOT `paras` or
  // `paraprofessionals` as the slug OR as an alias -- both have pointed at
  // /school-staffing for months and a link that has been shared once keeps landing where
  // it landed. The definite article is deliberate: it is the name of a group of people,
  // not a topic heading.
  parastaff: 'the-paraprofessionals',
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
  // The register of what the district SAID it was cutting, cycle by cycle, and what an
  // independent series shows afterwards. `cut-register` rather than `cuts`: the page is
  // not a list of cuts that happened, and an address should not promise the stronger
  // claim -- the same reasoning that keeps /what-stopped-being-funded off `cuts`. The
  // aliases below are what somebody actually types looking for this.
  cuts: 'cut-register',
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
  // What happened in each part of the budget when a grant stopped paying for it. The slug
  // is the CONDITION a resident names -- "when grants end" -- and stops there, because the
  // answer is two answers: in half the affected functions the town's money rose and in the
  // other half nothing replaced it. NOT `grant-unwinding`, which is our word for the
  // mechanism and nobody's word for the question. NOT `esser`, which names one federal
  // programme when the source publishes a fund total that cannot be split by grant --
  // an address that promises more than the page can deliver. NOT `grants`, `funds` or
  // `special-revenue`: all three have meant /money-outside-the-budget since long before
  // this page existed, and a shared link must keep landing where it landed.
  unwind: 'when-grants-end',
  // Chapter 70's FORMULA, as against state aid as a whole. The slug is the sentence a
  // resident says out loud at a meeting -- "why do we only get minimum aid?" -- rather
  // than `chapter-70`, which is already an alias for /state-aid and has been since long
  // before this page existed, and which names an accounting programme instead of the
  // question about it. NOT `minimum-aid` alone: that reads as a description of a benefit
  // somebody receives rather than as the complaint the town has actually been making to
  // the Legislature. NOT `the-formula`, which promises every formula in the budget.
  minaid: 'why-we-only-get-minimum-aid',
  // HOW Chapter 70 works, as against WHERE Lunenburg sits in it. Two pages because they
  // are two questions: /why-we-only-get-minimum-aid establishes the town's position and
  // this one explains the mechanism, in eight plain steps. The slug is what somebody types
  // when they want the thing explained -- "how does Chapter 70 work" -- rather than
  // `chapter-70`, which is an alias for /state-aid, or `ch70-formula` and `the-formula`,
  // which have meant /why-we-only-get-minimum-aid since before this page existed. A link
  // that has been shared once keeps landing where it landed, even when a newer page is a
  // better answer to the word.
  formula: 'how-chapter-70-works',
  // Special education, as FOUR reports behind one door. The door's slug is the words a
  // resident says -- "special education" -- and nothing more, because the page is a
  // chooser rather than an argument and a slug that named a finding would preload one.
  //
  // THE FOUR ARE FOUR ADDRESSES ON PURPOSE. notes/QUEUE.md item 10: "Four reports, not
  // one. Keep them apart. Merging them into one narrative is how a proxy becomes a fact."
  // Separate addresses are the structural form of that: a resident can be sent to the one
  // that answers their question, and a link that has been shared cannot drift into
  // carrying the other three.
  sped: 'special-education',
  // The question as it gets asked out loud -- "how many kids are on an IEP" -- rather
  // than `sped-enrollment`, which names our instrument, or `students-with-disabilities`,
  // which is DESE's phrase and not the town's. NOT `how-many-students`, which promises
  // enrollment as a whole.
  spedcount: 'how-many-students-are-on-an-iep',
  // NOT `school-choice`, `students-leaving` or `transfers-out` -- all three have meant
  // /if-students-leave since before this page existed, and that page is a SCENARIO with
  // dials while this one is a measurement with none. A shared link must keep landing
  // where it landed. The slug is where the children actually are, which is what this
  // report counts and what /if-students-leave does not.
  outflow: 'where-students-go-instead',
  // The sentence a resident says at a meeting. NOT `sped-cost` and NOT
  // `out-of-district-tuition`, which name the accounting shape of the answer rather than
  // the question -- and NOT `circuit-breaker`, which promises only the reimbursement half.
  spedcost: 'what-special-education-costs',
  // The question underneath the tuition line, phrased as the route rather than as the
  // outcome. NOT `out-of-district`, which reads as a page about the placements
  // themselves, and NOT `placement-counts`, which names a CSV.
  spedroute: 'who-ends-up-out-of-district',
  // THE RULE, at the address a resident would type. NOT `603-cmr-28`, which is the
  // citation and not the question, and NOT `special-education-regulation`, which is what
  // the regulation is CALLED rather than what anybody wants from it -- both are aliases.
  // Nobody in the whole meeting archive has ever said "substantially separate" or "603
  // CMR"; 21 documents say "class size". The address is the town's own word for it.
  classsize: 'special-education-class-size',
  // What every OTHER district spends, and Lunenburg inside that. The slug is the sentence
  // a resident says at a meeting -- "what do other districts spend?" -- rather than
  // `per-pupil-spending`, which names the statistic instead of the question, or
  // `peer-districts`, which is what this project calls the set and is also the name of an
  // older analysis about what neighbours CUT rather than what they spend. NOT `spending`
  // or `comparison` on their own: the first promises the whole budget and the second
  // promises nothing at all. NOT `how-we-compare`, which reads as a verdict.
  // WHAT RAN, as against who was employed to run it. The slug is the question a parent
  // asks at a meeting -- "did the cuts change what my kid can take?" -- narrowed to the
  // half this page can answer, and the verb is the grain: a section is what RAN, which is
  // what the schedule offered and what students chose, together. NOT `course-offerings`,
  // which is the district's phrase for the catalogue and promises a list of courses this
  // file does not hold -- DESE publishes sections by SUBJECT AREA and never by course, so
  // an address naming courses in the plural would over-promise on the first click. NOT
  // `electives`, which is one part of what is counted here and the loudest part, so it
  // would preload the finding. NOT `class-size` or anything near it: those have meant
  // /special-education-class-size since before this page existed, they are cited off this
  // site, and that page quotes a STATUTE while this one counts sections. Both are
  // accepted as aliases below, because they are what somebody types.
  courses: 'what-courses-actually-ran',
  // WHICH GRADES CHILDREN LEAVE IN. The slug is the question residents ask out loud --
  // TJ, relaying it: "people are asking me to show which grades students are leaving
  // over time." NOT `attrition`, which is DESE's word and, in this town's own meeting
  // record, means STAFF attrition both times anybody has ever said it. NOT
  // `declining-enrollment` or `enrollment-decline`: no document in the whole readable
  // archive uses either phrase, and the page's third finding is that the leaving is nine
  // times the size of the enrolment change, so an address naming a decline would preload
  // the opposite of what the page establishes. NOT `where-students-go`, which is
  // /where-students-go-instead and answers a question this file explicitly cannot -- the
  // attrition rate names no destination at all. Both are accepted as aliases below,
  // because they are what somebody types.
  attrition: 'which-grades-students-leave',
  // THE DENOMINATOR every other page divides by, on its own. `enrollment` had been kept
  // free on purpose ("nothing has meant either before") -- it now means this, and only
  // this. American spelling in the address because that is what a resident types.
  enrollment: 'who-is-in-the-schools',
  // The name everybody in the school-budget argument uses, and nothing else means it.
  circuitbreaker: 'circuit-breaker',
  // The two letters everybody says. `advanced-placement` is the alias.
  ap: 'ap-exams',
  peers: 'what-other-districts-spend',
  // WHO LIVES HERE, before any argument about what the town should spend. The slug is
  // the phrase people already use for a page of facts about a place -- "Lunenburg by the
  // numbers" -- and it is the one address here that promises no finding at all, which is
  // right for a page whose whole job is to hand both sides of the override argument the
  // same figures. NOT `demographics`, which is the word of the person who fetched the
  // data rather than of anybody reading it. NOT `census`: the town runs its own annual
  // census and a resident typing that means the Town Clerk's, not the Census Bureau's --
  // it is accepted as an alias because it is what people type, and the page says in its
  // first screen which census it is. NOT `who-lives-here` as the canonical form, because
  // the page is also households, income and tenure; it is an alias.
  bythenumbers: 'lunenburg-by-the-numbers',
  // THE WORD EVERYBODY ALREADY HAS. Not `posts`, which names the container rather than
  // the thing; not `updates`, which promises news about this project rather than about
  // the town's money. A post is shared into a Facebook group and the address travels with
  // it, so it has to read as an address somebody would click from a feed.
  blog: 'blog',
  // THE ONE WORD. A search box is the most-understood affordance on the web and it is
  // reached by typing the word; `find` is what the /minutes/find/ endpoint for callers
  // uses and is accepted as an alias.
  search: 'search',
  // WHAT WAS SAID. Our minutes of recorded meetings -- 231 meetings have no record but
  // the video. Not `minutes`: the town's minutes live at /minutes and these are not
  // those. Not `transcripts`: a transcript is the captions, and this is a reading of
  // them. "What was said" is the question a resident arrives with and it carries its
  // own caveat, because what was said is on the recording and this points at it.
  recorded: 'what-was-said',
  // What is coming and what just appeared, as our watchers saw it. The phrase a
  // resident says; `feed` and `updates` are accepted.
  thisweek: 'this-week',
  // The name everybody in town says out loud, and nothing else. NOT
  // `regional-vocational-assessment`, which is the accounting shape of the thing and what
  // nobody calls it; NOT `montachusett`, which is also a planning commission, a transit
  // authority and a home-care agency, all of which appear in these minutes; and NOT
  // `vocational-school`, which promises a page about the school rather than about the
  // bill. `monty-tech` WAS AN ALIAS FOR /where-students-go-instead and is now this page's
  // own address -- the one alias move made deliberately here, because a reader typing it
  // wanted the assessment and was being handed a headcount. The old page is linked from
  // the first screen of this one.
  montytech: 'monty-tech',
  // What the state ENFORCES, as against every other spending page here, which measures a
  // budget somebody chose. The slug is the sentence a resident says when they hear the
  // town is barely above the state minimum -- NOT `net-school-spending`, which is DESE's
  // term of art and nobody's sentence, and NOT `spending-vs-required`, which names the
  // payload. NOT `are-we-meeting-the-minimum` either: the answer is yes in every measured
  // year, and a slug that promises a yes/no buries the finding, which is about position.
  required: 'what-the-state-requires-us-to-spend',
  // EVERY REPORT'S CONCLUSIONS, IN ONE PLACE. The slug is the sentence a resident says
  // when they have read three of these and want the point -- "what does it all add up
  // to?" NOT `summary` or `key-findings`, which are the words of the person who wrote the
  // reports rather than of anybody reading them, and NOT `conclusions`, which names our
  // instrument: the payload field, the Python module and the component are all called
  // that, and an address should name the reader's question. NOT `the-big-picture`, which
  // promises a view of the whole budget and this is a synthesis of the ANALYSES.
  addsup: 'what-it-all-adds-up-to',
  // UNLISTED. See UNLISTED below before adding a link to this anywhere.
  // The bare address is the fallback index only. Every markdown analysis lives one
  // segment down -- /analysis/free-cash -- and those are the addresses that are
  // published, prerendered and in the sitemap. `analysis` itself is UNLISTED because
  // /reports is the canonical index of every analysis and a second one would compete
  // with it.
  analysis: 'analysis',
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
export const UNLISTED: ReadonlySet<Tab> = new Set<Tab>(['dataroom', 'analysis'])

/** Forms somebody might type or that an older link might carry. Never generated, always
 *  accepted — a link that has been shared once is out of your hands forever. */
const ALIASES: Record<string, Tab> = {
  // The chooser answers to a name as well as to the root. `/` is what gets shared; `home`
  // is what somebody types when they have lost their place.
  home: 'home', doors: 'home',
  answers: 'answers',
  walk: 'walk', crisis: 'walk', 'budget-crisis': 'walk', walkthrough: 'walk', start: 'walk', 'start-here': 'walk',
  deeper: 'deeper', more: 'deeper', everything: 'deeper',
  money: 'money', context: 'context', situation: 'context',
  why: 'why', rates: 'curve', curve: 'curve',
  override: 'override', 'the-override': 'override',
  adjust: 'adjust', budget: 'adjust', build: 'adjust',
  solved: 'solved', packages: 'solved', sustainable: 'solved', forever: 'solved',
  sources: 'sources', documents: 'sources', evidence: 'sources', citations: 'sources',
  // The words somebody types looking for the synthesis. `conclusions` and `findings` are
  // what this project calls the thing internally and are exactly the forms a reader who
  // has heard about it second-hand will try; they are accepted and never generated.
  addsup: 'addsup', conclusions: 'addsup', 'key-findings': 'addsup',
  findings: 'addsup', summary: 'addsup', takeaways: 'addsup',
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
  // NOTHING ABOVE MOVES. These are forms nobody has been handed before, for the two pages
  // carved out of /school-staffing -- `staff-by-school` and `who-works-here` for the
  // building question, and the paraprofessional forms that are NOT already spoken for.
  // `paras`, `paraprofessionals`, `teachers`, `headcount`, `rosters` and `staff-rosters`
  // are deliberately absent: every one of them has meant /school-staffing since long
  // before these pages existed.
  'who-works-in-each-school': 'schoolstaff', 'staff-by-school': 'schoolstaff',
  'who-works-here': 'schoolstaff', 'school-by-school-staffing': 'schoolstaff',
  'who-works-in-the-schools': 'schoolstaff', 'staff-per-school': 'schoolstaff',
  'the-paraprofessionals': 'parastaff', 'paraprofessional-staffing': 'parastaff',
  'para-staffing': 'parastaff', 'teaching-assistants': 'parastaff',
  'classroom-aides': 'parastaff', 'paraprofessionals-and-teachers': 'parastaff',
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
  // NOT 'cuts' bare -- see the slug note. These are the phrasings a resident types.
  'cut-register': 'cuts', 'the-cut-register': 'cuts', 'announced-cuts': 'cuts',
  'what-was-cut': 'cuts', 'did-the-cuts-happen': 'cuts', 'reduction-lists': 'cuts',
  'personnel-cuts': 'cuts', 'staff-cuts': 'cuts',
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
  // NOT 'grants' or 'grant-funding' -- both already land on /money-outside-the-budget.
  // These are the forms somebody types looking for what happened when the federal money
  // ran out.
  'when-grants-end': 'unwind', 'grants-ending': 'unwind', 'grant-unwinding': 'unwind',
  'esser': 'unwind', 'esser-cliff': 'unwind', 'when-the-grants-ended': 'unwind',
  'grant-funded-positions': 'unwind', 'fund-split': 'unwind',
  // NOT 'chapter-70', 'ch70' or 'school-aid' -- all three have meant /state-aid since
  // long before this page existed and are cited off this site. A link that has been
  // shared once must keep landing where it landed, even when a newer page is arguably a
  // better answer to the word. These are the forms somebody types looking for the FLOOR.
  'why-we-only-get-minimum-aid': 'minaid', 'minimum-aid': 'minaid',
  'min-aid': 'minaid', 'ch70-formula': 'minaid', 'chapter-70-formula': 'minaid',
  'foundation-budget': 'minaid', 'the-formula': 'minaid',
  // The forms somebody types wanting the formula EXPLAINED rather than applied to this
  // town. NOT 'chapter-70', 'ch70-formula', 'the-formula' or 'foundation-budget': all
  // four already land elsewhere and are cited off this site.
  'how-chapter-70-works': 'formula', 'how-the-formula-works': 'formula',
  'how-chapter-70-is-calculated': 'formula', 'chapter-70-explained': 'formula',
  'how-school-aid-is-calculated': 'formula', 'minimum-aid-explained': 'formula',
  'if-students-leave': 'leaving', 'school-choice': 'leaving', 'choicing-out': 'leaving',
  'students-leaving': 'leaving', 'school-choice-scenario': 'leaving',
  'what-if-students-leave': 'leaving', 'transfers-out': 'leaving',
  // NOT 'sped' alone as the slug -- it is jargon nobody says out loud -- but it is
  // exactly what somebody working on the site types, so it lands here.
  'special-education': 'sped', sped: 'sped', 'special-ed': 'sped',
  'special-education-reports': 'sped', 'iep': 'sped',
  'how-many-students-are-on-an-iep': 'spedcount', 'iep-count': 'spedcount',
  'students-with-disabilities': 'spedcount', 'sped-enrollment': 'spedcount',
  'how-many-on-an-iep': 'spedcount',
  // NOT 'school-choice' or 'students-leaving': both already land on /if-students-leave.
  'where-students-go-instead': 'outflow', 'where-our-students-go': 'outflow',
  'who-leaves': 'outflow', 'residents-by-district': 'outflow',
  'where-students-go': 'outflow',
  'what-special-education-costs': 'spedcost', 'sped-cost': 'spedcost',
  'out-of-district-tuition': 'spedcost',
  'sped-money': 'spedcost',
  // NOT 'peers' meaning the older sources/analyses/peer-districts.md -- that document is
  // about what comparable districts CUT, it is reachable from /reports, and it is a
  // different question from what they SPEND. These are the forms somebody types looking
  // for the spending comparison.
  'what-other-districts-spend': 'peers', 'per-pupil': 'peers',
  'per-pupil-spending': 'peers', peers: 'peers', 'peer-districts': 'peers',
  'comparison-districts': 'peers', 'how-we-compare': 'peers',
  'what-other-towns-spend': 'peers', 'spending-per-pupil': 'peers',
  // The forms somebody types looking for the ENFORCED floor. NOT 'minimum-aid' or
  // 'ch70-formula', which have meant /why-we-only-get-minimum-aid since before this page
  // existed, and NOT 'per-pupil', which is /what-other-districts-spend.
  'what-the-state-requires-us-to-spend': 'required',
  'net-school-spending': 'required', 'required-net-school-spending': 'required',
  nss: 'required', 'spending-vs-required': 'required', 'the-state-minimum': 'required',
  'minimum-spending': 'required', 'required-spending': 'required',
  'are-we-meeting-the-minimum': 'required',
  // NOT 'vocational' or 'regional' on their own: the first promises the school and the
  // second is a word this town uses for a planning commission and a transit authority.
  'monty-tech': 'montytech', montytech: 'montytech', 'monty': 'montytech',
  montachusett: 'montytech', 'regional-assessment': 'montytech',
  'monty-tech-assessment': 'montytech', 'vocational-school': 'montytech',
  'who-ends-up-out-of-district': 'spedroute', 'out-of-district': 'spedroute',
  'placement-counts': 'spedroute', 'placements': 'spedroute',
  'the-route-out-of-district': 'spedroute',
  // NOT `class-size` bare pointing anywhere else: this is the only page about it. The
  // citation forms are here because an official arriving from a DESE document has the
  // number and not the question, and `paras`/`paraprofessionals` are deliberately NOT
  // here -- both have meant /school-staffing since long before this page existed, and a
  // link that has been shared once must keep landing where it landed.
  'special-education-class-size': 'classsize', 'class-size': 'classsize',
  'class-sizes': 'classsize', 'class-size-rules': 'classsize',
  'special-education-regulation': 'classsize', '603-cmr-28': 'classsize',
  '603cmr28': 'classsize', 'the-ratio-rule': 'classsize',
  'students-per-teacher': 'classsize', 'how-many-students-per-teacher': 'classsize',
  'instructional-grouping': 'classsize',
  // NOT 'class-size', 'class-sizes' or 'students-per-teacher' -- all three have meant
  // /special-education-class-size since before this page existed and are cited off this
  // site. A link that has been shared once keeps landing where it landed. These are the
  // forms somebody types looking for WHAT RAN.
  'what-courses-actually-ran': 'courses', 'course-offerings': 'courses',
  courses: 'courses', electives: 'courses', 'course-catalog': 'courses',
  'program-of-studies': 'courses', 'what-gets-taught': 'courses',
  'what-is-taught': 'courses', 'course-sections': 'courses', sections: 'courses',
  curriculum: 'courses', 'master-schedule': 'courses',
  'did-the-cuts-cut-courses': 'courses', 'what-classes-run': 'courses',
  // NOT 'students-leaving', 'school-choice' or 'transfers-out' -- all three have meant
  // /if-students-leave since before this page existed. These are the forms somebody
  // types looking for WHICH GRADE.
  // NOT 'population' or 'enrollment' pointing anywhere else: nothing has meant either
  // before. `census` lands here deliberately -- see the slug note -- and so does
  // `seniors`, which nothing else answers to.
  'lunenburg-by-the-numbers': 'bythenumbers', 'by-the-numbers': 'bythenumbers',
  'who-lives-here': 'bythenumbers', 'who-lives-in-lunenburg': 'bythenumbers',
  demographics: 'bythenumbers', census: 'bythenumbers', acs: 'bythenumbers',
  blog: 'blog', posts: 'blog', 'the-blog': 'blog', updates: 'blog',
  'this-week': 'thisweek', 'this-week-in-town': 'thisweek', feed: 'thisweek', 'meeting-feed': 'thisweek',
  'what-was-said': 'recorded', 'recording-minutes': 'recorded', 'our-minutes': 'recorded',
  search: 'search', find: 'search', 'search-minutes': 'search', 'search-everything': 'search',
  // /worth-knowing WAS A PAGE AND IS NOW THE BLOG. It rendered all 48 items as cards from
  // a published payload, with the editorial apparatus on every one -- which put copy
  // nobody had decided to publish on the public site, and made a worklist into a product.
  // The address stays because it was published, linked and in the sitemap: a URL that has
  // been shared once is out of your hands forever, and /blog is where a reader arriving on
  // one wanted to be anyway.
  'worth-knowing': 'blog', 'did-you-know': 'blog', 'myth-vs-fact': 'blog', cards: 'blog',
  'one-fact-at-a-time': 'blog',
  population: 'bythenumbers', seniors: 'bythenumbers', 'town-profile': 'bythenumbers',
  households: 'bythenumbers', 'median-income': 'bythenumbers',
  'ap-exams': 'ap', ap: 'ap', 'advanced-placement': 'ap', 'ap-courses': 'ap', 'ap-coursework': 'ap', 'ap-scores': 'ap',
  'circuit-breaker': 'circuitbreaker', circuitbreaker: 'circuitbreaker', 'special-education-reimbursement': 'circuitbreaker', 'sped-reimbursement': 'circuitbreaker',
  'who-is-in-the-schools': 'enrollment', enrollment: 'enrollment', enrolment: 'enrollment',
  'student-count': 'enrollment', 'how-many-students': 'enrollment',
  'which-grades-students-leave': 'attrition', attrition: 'attrition',
  'student-attrition': 'attrition', 'which-grades-lose-students': 'attrition',
  'declining-enrollment': 'attrition', 'enrollment-decline': 'attrition',
  'when-students-leave': 'attrition', 'grade-8': 'attrition',
  'eighth-grade': 'attrition', 'who-leaves-and-when': 'attrition',
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
  search: 'Search — everything this project holds',
  recorded: 'What was said — minutes from the recordings',
  thisweek: 'This week in town — meetings coming up, minutes and recordings just posted',
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
  staffing: 'School staffing — did it go up, and over which years',
  schoolstaff: 'Who works in each school',
  parastaff: 'The paraprofessionals',
  insurance: 'Health insurance — the cost outside the school budget',
  sportsmoney: 'What sports cost, and who pays',
  stateaid: 'State aid — the part nobody here votes on',
  stopped: 'What stopped being funded',
  cuts: 'The cut register — what was announced, and what shows',
  leaving: 'If students leave — what school choice would cost',
  families: 'What a family actually pays',
  unwind: 'When a grant ends — who picks up the bill',
  minaid: 'Chapter 70 — the formula, and why it pays the floor',
  formula: 'How Chapter 70 actually works, in eight steps',
  askus: 'Ask us a question',
  sped: 'Special education — four reports',
  montytech: 'Monty Tech — the assessment, and what sets it',
  spedcount: 'How many Lunenburg children are on an IEP',
  outflow: 'Who leaves Lunenburg schools, and where they go',
  spedcost: 'What out-of-district special education costs, and what comes back',
  spedroute: 'Who ends up out of district',
  classsize: 'How many students one special education group may have',
  courses: 'What courses actually ran, subject by subject',
  attrition: 'Which grades students leave in',
  enrollment: 'Who is in the schools — enrolment, FY1994 to today',
  circuitbreaker: 'The circuit breaker — what the state reimburses for the costliest placements',
  ap: 'AP exams — who sits them, in what, and how they score',
  peers: 'What other districts spend, for each pupil',
  bythenumbers: 'Lunenburg by the numbers — who lives here',
  blog: 'The blog — one finding at a time, in two minutes',
  required: 'What the state requires us to spend — and where that puts us',
  addsup: 'The One Big Report',
  analysis: 'An analysis',
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
  schoolstaff: 'themoney',
  parastaff: 'themoney',
  insurance: 'themoney',
  sportsmoney: 'themoney',
  askus: 'themoney',
  stateaid: 'themoney',
  stopped: 'themoney',
  cuts: 'themoney',
  leaving: 'themoney',
  families: 'themoney',
  unwind: 'themoney',
  minaid: 'themoney',
  formula: 'minaid',
  sped: 'reports',
  spedcount: 'sped', spedcost: 'sped', spedroute: 'sped',
  // NOT under `sped`, and that is the whole structural point of this page. It counts
  // EVERY resident child educated somewhere else, and its headline negative is that the
  // file carries no disability flag -- so a general measurement filed under Special
  // education would contradict its own first sentence by its location. The special
  // education hub still reaches it, as the question it cannot answer.
  outflow: 'reports',
  peers: 'reports',
  bythenumbers: 'reports',
  blog: 'reports',
  recorded: 'reports',
  thisweek: 'reports',
  courses: 'reports',
  attrition: 'reports',
  enrollment: 'reports',
  circuitbreaker: 'reports',
  ap: 'reports',
  analysis: 'reports',
  required: 'reports',
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
  // The one two-segment address on the site. Seventeen markdown analyses share a single
  // page component, so the document id travels in the path rather than in a Tab of its
  // own -- see `analysis` in the union above.
  if (seg.startsWith('analysis/')) return 'analysis'
  // The second. Forty-eight posts share one page component; the slug is in the path.
  if (seg.startsWith('blog/')) return 'blog'
  if (seg.startsWith('what-was-said/')) return 'recorded'
  return BY_SLUG[seg] ?? ROOT
}

/** The document a `/analysis/<id>` address names, or null for the bare index.
 *
 *  Restricted to the shape an analysis id actually has, so the path cannot be used to
 *  reach for anything else: this value becomes part of a fetch URL. */
export function analysisIdFromPath(pathname: string): string | null {
  const m = /^\/analysis\/([a-z0-9-]+)\/?$/.exec(pathname.toLowerCase())
  return m ? m[1] : null
}

/** The post a `/blog/<slug>` address names, or null for the archive at `/blog`.
 *
 *  Restricted to the shape a slug actually has, for the same reason `analysisIdFromPath`
 *  is: this value is compared against a generated payload and rendered into the page, and
 *  an address is not a place to accept arbitrary text. */
/** The meeting a `/what-was-said/<board>/<date>-<video>` address names, or null. */
export function recordedSlugFromPath(pathname: string): string | null {
  const m = /^\/what-was-said\/([a-z0-9-]+\/[0-9]{4}-[0-9]{2}-[0-9]{2}-[A-Za-z0-9_-]+)\/?$/.exec(pathname)
  return m ? m[1] : null
}

export function blogSlugFromPath(pathname: string): string | null {
  const m = /^\/blog\/([a-z0-9-]+)\/?$/.exec(pathname.toLowerCase())
  return m ? m[1] : null
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
  // `analyses` opens on /reports, the generated index of every analysis this project
  // has written -- BOTH KINDS. An area whose front page is a list of what is in it needs
  // no new hub page.
  //
  // THIS COMMENT WAS FALSE FOR A DAY AND NOTHING FAILED. It said the index covered every
  // analysis on disk and that build_reports_index.py fails if one is missing, and both
  // were true while every analysis was a Markdown document in sources/analyses/. Eight
  // reports were then built as React PAGES, the generator could not see them, and the
  // front door of this whole area listed the documents and none of the pages -- an
  // omission, which is the one defect shape nothing here catches by re-reading.
  //
  // It is true again, and by construction rather than by care: the generator reads
  // AREA_TABS.analyses below, joins each tab to the page component that declares
  // `const TAB: Tab = ...`, and REFUSES TO WRITE if a routed report has no owner. Adding a
  // report to that list without a page, or a page without adding it to that list, fails.
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
  schoolstaff: 'analyses', parastaff: 'analyses',
  cuts: 'analyses',
  families: 'analyses', sportsmoney: 'analyses', insurance: 'analyses',
  variance: 'analyses', unwind: 'analyses', minaid: 'analyses', formula: 'analyses',
  sped: 'analyses', spedcount: 'analyses', outflow: 'analyses', spedcost: 'analyses',
  spedroute: 'analyses', peers: 'analyses', montytech: 'analyses', required: 'analyses',
  classsize: 'analyses', courses: 'analyses', attrition: 'analyses', enrollment: 'analyses', circuitbreaker: 'analyses', ap: 'analyses',
  // AN ANALYSIS OF THE TOWN RATHER THAN OF ITS BUDGET, and this area is named for the
  // FORM rather than for the subject precisely so that it can land here -- see the note
  // on AREA_LABEL.analyses. It is not `crisis`: a page of facts about who lives in
  // Lunenburg is not a chapter of an argument, and filing it inside one would make it
  // read as evidence for a conclusion it does not draw. It is not `data` either: that
  // area is the database and the register, which are instruments, and this is a report
  // with conclusions of its own.
  bythenumbers: 'analyses',
  blog: 'analyses',
  recorded: 'analyses',
  thisweek: 'analyses',
  addsup: 'analyses',
  analysis: 'analyses',
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
  // `sped` is ONE entry for FOUR reports, and that is deliberate twice over. The comment
  // above warns that a bar with fourteen entries is a sitemap; adding the four reports
  // individually would have made it exactly that. And the four belong behind one door
  // anyway: /special-education is a chooser whose whole job is to say, before a reader
  // opens any of them, that these four do not combine.
  // `outflow` and `leaving` are ADJACENT ON PURPOSE. One is a measurement of where the
  // town's children actually are and the other is a scenario of what it would cost if
  // more of them left; they are the two halves a resident conflates, and side by side in
  // the bar is where the difference is cheapest to see. Splitting them across the strip
  // would leave the scenario findable and the measurement not, which is the wrong way
  // round -- the measurement is the thing that happened.
  // `required` sits next to `peers` and `minaid` on purpose: the three are the same
  // question asked of three different documents, and a reader who opens one should meet
  // the other two immediately rather than discover later that they exist.
  // `montytech` sits next to `outflow` and `leaving`, because those three are the pages
  // about children who are not in a Lunenburg classroom and they answer three different
  // questions: how many there are, what it would cost if more left, and what the town is
  // already assessed for the largest group of them.
  // `addsup` is FIRST, ahead of the index. A reader arriving in this area has a question,
  // not a filing need, and the one page that answers a question rather than listing
  // pages should be the one they meet -- rule 7a applied to a nav bar. /reports stays
  // second because it is the area's home and every report is reachable from it.
  // `cuts` sits beside `staffing` and `stopped` on purpose: the three are the same
  // question asked of three records -- who is employed, which lines ended, and what the
  // district said it was removing -- and a reader who opens one wants the other two.
  // `courses` sits INSIDE that run, immediately after `staffing`, because it is the
  // fourth record of the same question and the only one that counts what was TAUGHT
  // rather than what was employed or appropriated. A reader who has just been told
  // teacher FTE fell in a subject arrives at the next question -- did a class stop
  // running -- and that is the page next to it.
  // `classsize` sits immediately after `sped` because it is the question a reader who
  // opened special education came with -- how many children to a teacher -- and it is
  // the only page in the area that quotes a STATUTE rather than measuring this town.
  // `formula` sits immediately after `minaid` because it is the question a reader who
  // opened that page arrives with -- HOW does this work -- and the two are deliberately
  // separate addresses: one establishes where the town sits in the formula and the other
  // explains the formula. Adjacent in the bar is where the difference is cheapest to see.
  // `bythenumbers` is third, immediately after the index, because it is the only page in
  // the area that needs no budget knowledge to read -- a resident can start there and
  // arrive at everything else knowing who the town is. Every other entry assumes the
  // argument; this one is the denominator under it.
  // `blog` is second, immediately after the synthesis and before the index, because it is
  // the only entry here that asks nothing of a reader. /reports is a filing system and
  // every other entry assumes you know which report you want; a post hands over one
  // finding in two minutes and then hands the reader on. Somebody who does not yet have a
  // question should meet it before the shelf -- rule 7a applied to a nav bar, the same
  // argument that put `addsup` first.
  analyses: ['addsup', 'blog', 'thisweek', 'recorded', 'reports', 'bythenumbers', 'sped', 'classsize', 'circuitbreaker',
             'peers',
             'required', 'minaid',
             'formula',
             'staffing', 'schoolstaff', 'parastaff', 'courses', 'ap', 'cuts',
             'stopped',
             'unwind', 'enrollment', 'attrition', 'outflow', 'montytech', 'leaving', 'families',
             'sportsmoney',
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
