import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Go } from '../lib/nav'
import type { Tab } from '../routes'

/** THE SITE MENU -- every hub on the site, one button away, from every page.
 *
 *  TJ, 11 October 2026: *"There are many big hubs and some concepts that are somewhat
 *  buried. Threads. Jobs. Boards. Week digest. Reports, by area. I think we need a global
 *  nav that exposes all the contents in an easy to find way."*
 *
 *  It is a MENU and not more header links on purpose. TJ, 16 September 2026, on the strip
 *  that had grown to nine items: *"there are a LOT of links on the header. its
 *  overwhelming."* A strip has to fit a 400px phone, so it can carry four or five things
 *  and hides the rest. A panel opened on request can carry all of them, grouped, with room
 *  to say what each is -- the pattern is a MEGA MENU on a laptop and a full-screen sheet
 *  on a phone, and it is one component here at two widths.
 *
 *  Grouped by what a resident COMES FOR, not by how the site was built: what happened
 *  lately, who is deciding what, what the reports establish, the budget argument, and how
 *  to check any of it. The areas in routes.ts are the build's grouping and are not
 *  repeated here. */
type Item = { label: string; sub: string } & ({ to: Tab; anchor?: string; href?: never } | { href: string; to?: never; anchor?: never })
type Group = { title: string; items: Item[] }

/* EIGHT GROUPS, AND THE FIRST CUT HAD FIVE. TJ, same day: *"I likely missed full
 * categories (which really is the reason I asked for this)."* He had: the first version
 * reached 25 of the site's ~70 routes, and the misses were whole subjects -- the money,
 * the schools, the town, the tools, past budget seasons -- because it was written from
 * memory of the header rather than from the route table. This list was rebuilt by
 * diffing SLUG in routes.ts against it. Deliberately absent: the unlisted pages
 * (sources/analyses/UNLISTED and routes.UNLISTED), and the single reports, which /reports
 * indexes and which each subject group below links into. */
export const GROUPS: Group[] = [
  { title: 'Lately', items: [
    { to: 'thisweek', label: 'This week in town', sub: 'Meetings ahead and what just happened' },
    { to: 'budgetfeed', label: 'Budget feed', sub: 'This season, every board, as it happens' },
    { href: '/budget-feed/fy27', label: 'Past budget seasons', sub: 'FY27 and FY26, replayed' },
    { to: 'recorded', label: 'Meeting minutes', sub: 'What was said, meeting by meeting' },
    { to: 'blog', label: 'Articles', sub: 'Written up, one question at a time' },
    { href: '/feeds/all.xml', label: 'Subscribe (feeds)', sub: 'Atom feeds: every board, or all' },
  ] },
  { title: 'Who decides', items: [
    { to: 'threads', label: 'Threads', sub: 'Each matter, followed across boards' },
    { to: 'boards', label: 'Boards & committees', sub: 'Meetings, votes, finance, per board' },
    { to: 'boardcompare', label: 'The boards, compared', sub: 'Who posts minutes, and how fast' },
    { to: 'orgcharts', label: 'Org charts', sub: 'Who works where, by year' },
    { to: 'jobs', label: 'Job postings', sub: 'Open positions, town and schools' },
  ] },
  { title: 'The budget gap', items: [
    { to: 'walk', label: 'The walk-through', sub: 'Why the budget keeps breaking' },
    { to: 'answers', label: 'Straight answers', sub: 'The questions people actually ask' },
    { to: 'why', label: 'Why it repeats', sub: 'The gap returns each year' },
    { to: 'solutions', label: 'Solutions', sub: 'Every option, and who it costs' },
    { to: 'reports', anchor: 'levers', label: 'Solution options, in depth', sub: 'One report per lever' },
    { to: 'solved', label: 'The cost of closing it', sub: 'What “solved” requires' },
    { to: 'deeper', label: 'Go deeper', sub: 'Every chapter of the argument' },
  ] },
  { title: 'Try it yourself', items: [
    { to: 'adjust', label: 'Build your own budget', sub: 'Move the levers, see the gap' },
    { to: 'priorities', label: 'Set priorities', sub: 'Rank what to protect' },
    { to: 'development', label: 'Commercial growth', sub: 'What new building would bring in' },
    { to: 'money', label: 'Find the money', sub: 'Where the money could come from' },
    { to: 'curve', label: 'Bend the curve', sub: 'Slow the growth, not just this year' },
  ] },
  { title: 'The money', items: [
    { to: 'themoney', label: 'Where it comes from and goes', sub: 'In, out, and who decides' },
    { to: 'stateaid', label: 'State aid', sub: 'The part nobody here votes on' },
    { to: 'funds', label: 'Outside the budget', sub: 'Grants, revolving funds, gifts' },
    { to: 'accounts', label: 'Every account', sub: 'Each fund and line, once' },
    { to: 'departments', label: 'Departments', sub: 'Every department’s accounts' },
    { to: 'reports', anchor: 'townbudgets', label: 'Department budgets', sub: 'As Town Meeting voted them' },
    { to: 'rates', label: 'Rates, fees and contracts', sub: 'The register' },
  ] },
  { title: 'The schools', items: [
    { to: 'reports', anchor: 'school', label: 'All school reports', sub: 'Staff, students, money' },
    { to: 'sped', label: 'Special education', sub: 'Counts, costs, placements' },
    { to: 'staffing', label: 'Staffing', sub: 'Who works in each school' },
    { to: 'enrollment', label: 'Enrolment', sub: 'Who is in the schools, FY1994 on' },
    { to: 'athletics', label: 'Athletics and fees', sub: 'Both sides of the money' },
    { to: 'minaid', label: 'Chapter 70', sub: 'Why we get the minimum' },
    { to: 'cuts', label: 'The cut register', sub: 'What was announced, what shows' },
  ] },
  { title: 'The town', items: [
    { to: 'reports', anchor: 'town', label: 'All town reports', sub: 'People, the ledger, the votes' },
    { to: 'bythenumbers', label: 'By the numbers', sub: 'Who lives here' },
    { to: 'owners', label: 'Homes and taxes', sub: 'Who owns, and the tax bill' },
    { to: 'growth', label: 'Commercial development', sub: 'The base, and what was built' },
    { to: 'freecash', label: 'Free cash', sub: 'How much is actually spendable' },
    { to: 'parks', label: 'Parks & Recreation', sub: 'A department, whole' },
    { to: 'youthsports', label: 'Youth sports and fields', sub: 'What the leagues pay' },
  ] },
  { title: 'Check it', items: [
    { to: 'sources', label: 'Sources', sub: 'Every document this rests on' },
    { to: 'search', label: 'Search', sub: 'Pages, documents, minutes, video' },
    { to: 'gaps', label: 'What we cannot answer', sub: 'And what would settle it' },
    { to: 'askus', label: 'Ask us a question', sub: 'If it is not here' },
    { to: 'database', label: 'The database', sub: 'Query it yourself' },
    { to: 'ask', label: 'For AI assistants', sub: 'Point an assistant at this' },
    { to: 'about', label: 'About', sub: 'Who runs this, and how' },
  ] },
]

function ItemLink({ it, tab, onPick, compact }: { it: Item; tab: Tab; onPick?: () => void; compact?: boolean }) {
  const here = it.to !== undefined && tab === it.to && !it.anchor
  const cls = 'block rounded px-2 -mx-2 no-underline hover:bg-[var(--surface-3)] ' + (compact ? 'py-0.5' : 'py-1')
  const body = (
    <>
      <span className={'block font-semibold ' + (compact ? 'text-[13px]' : 'text-[14px]')}
        style={{ color: here ? 'var(--series-cost)' : 'var(--text-primary)' }}>{it.label}</span>
      {!compact && <span className="hidden sm:block text-[12px] leading-snug" style={{ color: 'var(--text-secondary)' }}>{it.sub}</span>}
    </>
  )
  return it.href
    ? <a href={it.href} onClick={onPick} className={cls} title={it.sub}>{body}</a>
    : <Go to={it.to!} anchor={it.anchor} onClick={onPick} title={it.sub}
        aria-current={here ? 'page' : undefined} className={cls}>{body}</Go>
}

/** The same eight groups, drawn as a SITE MAP -- the panel's body, and the FAT FOOTER on
 *  every page. A menu behind a button is found only by people who think to press it; a
 *  footer map is where a reader who has scrolled to the end looks for "what else is here". */
export function SiteMap({ tab, onPick, compact }: { tab: Tab; onPick?: () => void; compact?: boolean }) {
  return (
    <div className={'grid gap-x-6 grid-cols-2 lg:grid-cols-4 ' + (compact ? 'gap-y-5' : 'gap-y-6')}>
      {GROUPS.map(g => (
        <section key={g.title}>
          <h2 className="text-[11px] font-bold uppercase tracking-widest mb-1"
            style={{ color: 'var(--text-muted)' }}>{g.title}</h2>
          <ul className="m-0 p-0 list-none">
            {g.items.map(it => <li key={it.label}><ItemLink it={it} tab={tab} onPick={onPick} compact={compact} /></li>)}
          </ul>
        </section>
      ))}
    </div>
  )
}

export function SiteMenu({ tab }: { tab: Tab }) {
  const [open, setOpen] = useState(false)
  const btn = useRef<HTMLButtonElement>(null)
  const panel = useRef<HTMLDivElement>(null)

  // Closes on Escape, on a click outside, and on any navigation (the tab changing).
  useEffect(() => { setOpen(false) }, [tab])
  useEffect(() => {
    if (!open) return
    const k = (e: KeyboardEvent) => { if (e.key === 'Escape') { setOpen(false); btn.current?.focus() } }
    const c = (e: MouseEvent) => {
      const t = e.target as Node
      if (!panel.current?.contains(t) && !btn.current?.contains(t)) setOpen(false)
    }
    document.addEventListener('keydown', k)
    document.addEventListener('mousedown', c)
    return () => { document.removeEventListener('keydown', k); document.removeEventListener('mousedown', c) }
  }, [open])

  return (
    <>
      {/* A LABELLED hamburger. The three lines alone are the most-missed icon on the web;
          the word beside them is what makes it findable, and it costs ~40px. */}
      <button ref={btn} type="button" onClick={() => setOpen(o => !o)}
        aria-expanded={open} aria-controls="site-menu"
        className="inline-flex items-center gap-1.5 text-xs font-bold px-2.5 py-1 rounded-full whitespace-nowrap shrink-0"
        // OUTLINED, in the link colour, so it reads as a CONTROL and not as one more word in
        // the strip. TJ: "make sure we expose enough in the menu that they know it's there."
        style={{ background: open ? 'var(--series-cost)' : 'transparent',
                 color: open ? 'var(--surface-2)' : 'var(--series-cost)',
                 border: '1.5px solid var(--series-cost)' }}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
          strokeWidth="2.5" strokeLinecap="round" aria-hidden="true">
          {open ? <path d="M6 6l12 12M18 6L6 18" /> : <path d="M4 7h16M4 12h16M4 17h16" />}
        </svg>
        Menu
      </button>
      {/* PORTALLED to <body>. The header has `backdrop-blur`, and a backdrop-filter makes
          an element the CONTAINING BLOCK for its `position: fixed` descendants -- so inside
          it, `bottom: 0` meant the bottom of a 40px bar and the phone sheet had no height. */}
      {open && createPortal(
        <div ref={panel} id="site-menu" role="dialog" aria-label="Everything on this site"
          className="fixed left-0 right-0 top-10 bottom-0 sm:bottom-auto z-40 overflow-y-auto border-b shadow-lg"
          style={{ background: 'var(--surface-2)', borderColor: 'var(--grid)', maxHeight: 'calc(100vh - 2.5rem)' }}>
          <div className="mx-auto max-w-6xl px-4 py-5">
            <SiteMap tab={tab} onPick={() => setOpen(false)} />
          </div>
        </div>,
        document.body,
      )}
    </>
  )
}
