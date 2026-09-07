import { useCallback, useEffect, useRef, useState } from 'react'
import { MODEL, project, runCascade, newGrowthPerDollar } from './model/engine'
import { seedFromCuts, type CutState } from './model/cuts'
import { Context, CONTEXT_NAV } from './pages/Context'
import { Priorities } from './pages/Priorities'
import { Adjust } from './pages/Adjust'
import { Development } from './pages/Development'
import { WhyItRepeats } from './pages/WhyItRepeats'
import { Answers } from './pages/Answers'
import { FindTheMoney } from './pages/FindTheMoney'
import { BendTheCurve } from './pages/BendTheCurve'
import { Override } from './pages/Override'
import { Walkthrough } from './pages/Walkthrough'
import { Home } from './pages/Home'
import { Solved } from './pages/Solved'
import { GoDeeper } from './pages/GoDeeper'
import { Sources } from './pages/Sources'
import { Athletics } from './pages/Athletics'
import { Rates } from './pages/Rates'
import { DataFooter } from './components/DataFooter'
import { AgentsIndex } from './components/AgentsIndex'
import { AskAnAssistant } from './components/AskAnAssistant'
import { FreeCash } from './pages/FreeCash'
import { DataRoom } from './pages/DataRoom'
import { Reports } from './pages/Reports'
import { Money } from './pages/Money'
import { Database } from './pages/Database'
import { LABEL, PARENT, ROOT, pathFor, tabFromPath, type Tab, AREA_TABS, areaOf, assertNoDuplicateNav } from './routes'
import { type Package } from './model/rates'
import { UpdatedBar, ReleaseNotesDialog, VersionStamp } from './components/WhatChanged'


/** The three pages you use rather than read.
 *
 *  Kept out of the reading order on purpose, so they do not sit among the chapters
 *  pretending to be another chapter. Two of them are boards of controls with a result
 *  attached — one moves amounts, one moves rates — and between them they are what the
 *  rest of the site is written to prepare somebody for.
 *
 *  The third is the answer, and it goes first. It spent its life inside the walkthrough's
 *  last room and then behind the Go deeper door, which is where a site puts the things it
 *  is not sure anybody wants: a quiet index entry is the right shape for a derivation and
 *  the wrong shape for the conclusion. Somebody who arrives already knowing the problem —
 *  which by now is most of this town — should be one click from what would fix it. */
const CTAS: { id: Tab; label: string; short: string; glyph: string; sub: string }[] = [
  { id: 'solved', label: 'What would fix it', short: 'What fixes it', glyph: '\u2713',
    sub: 'Combinations that keep the gap shut — for five years, ten, a generation, or permanently' },
  { id: 'curve', label: 'Bend the curve', short: 'The curve', glyph: '\u2197',
    sub: 'Cut things and watch the rate not move; then change a rate and watch it bend' },
  { id: 'adjust', label: 'Build your own budget', short: 'Build a budget', glyph: '\u2699',
    sub: 'The interactive one — every dial that moves the gap, on one page' },
]

// Fails the dev build if a page is about to be drawn twice in one bar.
assertNoDuplicateNav(CTAS.map(c => c.id))

/** The chapter strip is gone.
 *
 *  Seven pills competing for a phone's width was the site telling a first-time reader that
 *  it had seven equally good beginnings, which was never true. The walkthrough is the way
 *  in, the two boards are the things you use, and everything else keeps its address and
 *  its content behind one quiet door. Nothing has been removed — see pages/GoDeeper. */
// `Go deeper` used to sit in the global bar; it is now a tab inside the crisis
// area's own list (AREA_TABS in routes.ts), so this constant has no reader.
// Deleted rather than left unused — an unused nav definition is the next
// person's evidence that the bar still works the old way.

/** Three pages, three jobs.
 *
 *  The two interactive pages are deliberately separate scenarios. Priorities asks what a
 *  ranking gives up on its own; Adjust asks what you would actually do. Letting a fee
 *  increase on one quietly rescue the other would hide the point of both. The only thing
 *  that crosses between them is a starting list of cuts, sent one way, on request. */
export default function App() {
  const [tab, setTab] = useState<Tab>(() => tabFromPath(window.location.pathname))
  /** Which area's bar to show. `null` on the chooser and on Sources, which is global. */
  const area = areaOf(tab)
  const [order, setOrder] = useState<string[]>(MODEL.presets.school_committee.order)
  const [preset, setPreset] = useState<string | null>('school_committee')
  const [seed, setSeed] = useState<{ state: CutState; nonce: number } | null>(null)
  /** One of the seven options, sent from the board that names them to a board that draws
   *  it. Lives here because the two destinations are different pages, and because an
   *  option loaded on the walkthrough has to survive the navigation to reach them. */
  const [option, setOption] = useState<
    { route: Package; nonce: number; to: Tab } | null>(null)
  /** The last page navigated from. Not for display — the breadcrumb is structural, and a
   *  crumb that changed depending on how you arrived would be a history trail wearing
   *  breadcrumb clothes. This exists only so that going up can pop the stack instead of
   *  growing it. */
  const [from, setFrom] = useState<Tab | null>(null)
  // The commercial build rate is the same decision on two pages, so it lives here rather
  // than being duplicated. Housing is modeled on Development only.
  const [newValue, setNewValue] = useState(MODEL.taxBase.currentNewGrowthValue)
  const [homes, setHomes] = useState(MODEL.taxBase.fy23NewValue)
  /** The release notes, over the page rather than instead of it. Held here because
   *  two things open it — the bar at the top and the footer stamp — and they are on
   *  opposite ends of every page. */
  const [notesOpen, setNotesOpen] = useState(false)
  const pending = useRef<string | null>(null)

  // The back button has to work, or a shared link is a trap: follow one, look around,
  // and there is no way back to where you came from.
  useEffect(() => {
    const onPop = () => { setFrom(null); setTab(tabFromPath(window.location.pathname)) }
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [])

  // A link may carry a section as well as a tab — /bend-the-curve#leverage. Tabs render
  // their own sections, so the element only exists after the tab has switched.
  useEffect(() => {
    const id = window.location.hash.slice(1)
    if (!id) return
    // Twice, because the first pass is often wrong. A room lands as soon as the tab has
    // rendered, and then the charts inside it measure themselves and push everything
    // below them down the page — so a link to a late section arrives at the right
    // element and the wrong place. The second pass corrects it once layout has settled.
    const scroll = () => document.getElementById(id)?.scrollIntoView()
    requestAnimationFrame(scroll)
    const settled = setTimeout(scroll, 400)
    return () => clearTimeout(settled)
  }, [tab])

  // Deep links into the context page work from any tab: switch first, scroll once the
  // section actually exists.
  useEffect(() => {
    if (tab !== 'context' || !pending.current) return
    const id = pending.current
    pending.current = null
    requestAnimationFrame(() =>
      document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' }))
  }, [tab])

  /** Push the URL for a tab, optionally with a section on it. Skipped when it would be
   *  a no-op, so the back button does not collect duplicate entries. */
  const navigate = (t: Tab, anchor?: string) => {
    const url = pathFor(t) + (anchor ? `#${anchor}` : '')
    if (url !== window.location.pathname + window.location.hash)
      window.history.pushState(null, '', url)
  }

  const jump = useCallback((anchor: string) => {
    navigate('context', anchor)
    if (tab === 'context') {
      document.getElementById(anchor)?.scrollIntoView({ behavior: 'smooth' })
      return
    }
    pending.current = anchor
    setTab('context')
  }, [tab])

  const go = (t: Tab, anchor?: string) => {
    if (t !== tab) setFrom(tab)
    setTab(t); navigate(t, anchor)
    // The hash effect above scrolls once the target tab has rendered. It only fires on a
    // tab change, so a jump inside the page you are already on has to scroll itself.
    if (!anchor) window.scrollTo({ top: 0 })
    else if (t === tab)
      requestAnimationFrame(() =>
        document.getElementById(anchor)?.scrollIntoView({ behavior: 'smooth' }))
  }

  /** Going up a level. Never grows the history stack.
   *
   *  A breadcrumb is a statement about where a page sits, not about how you got to it, so
   *  clicking one should feel like going back rather than like traveling somewhere new.
   *  Pushing an entry meant that after Start -> Go deeper -> Straight answers, clicking
   *  "Go deeper" left four entries and the back button walked forwards through them.
   *
   *  If the crumb is the page we just came from, actually go back and let popstate do the
   *  work. Otherwise replace the current entry rather than adding one. */
  const goUp = (t: Tab) => {
    if (from === t) { window.history.back(); return }
    setFrom(null)
    setTab(t)
    const url = pathFor(t)
    if (url !== window.location.pathname + window.location.hash)
      window.history.replaceState(null, '', url)
    window.scrollTo({ top: 0 })
  }

  /** Send an option to a board. The curve draws it; the builder prices it in things. */
  const loadOption = (route: Package, to: 'curve' | 'adjust') => {
    setOption({ route, nonce: Date.now(), to })
    go(to, to === 'curve' ? 'board' : undefined)
  }
  /* Only the board it was sent to picks it up. Otherwise walking onto the other board
   * later would silently rewrite a scenario the reader had been building by hand. */
  const optionFor = (t: Tab) => (option?.to === t ? option : null)

  const sendToAdjust = () => {
    const result = runCascade(order, MODEL.assumptions, 1)
    setSeed({ state: seedFromCuts(result[0].cuts), nonce: Date.now() })
    go('adjust')
  }

  return (
    <div>
      <header className="sticky top-0 z-30 backdrop-blur border-b"
        style={{ background: 'color-mix(in srgb, var(--surface-2) 92%, transparent)',
                 borderColor: 'var(--grid)' }}>
        <nav aria-label="Sections"
          className="mx-auto max-w-6xl px-4 h-10 flex items-center gap-2">
          {/* The site outgrew its name. It was "Lunenburg FY28" when it was a projection
              of one budget year; it is now an argument about why the year keeps
              recurring and what would stop it, and the address people will type is
              lunenburgbudgetproject.org. A brand that disagrees with the domain is a
              small tax on everybody who tries to tell somebody else about it.
              FY28 has not gone anywhere — it is all over the walkthrough, where it is a
              fact rather than a title. */}
          <button onClick={() => go('home')}
            className="font-bold shrink-0 mr-1 leading-none text-left"
            title="Back to the front page — the four ways into this site">
            {/* Two lines on a phone rather than a shorter name. "Budget Project" alone
                saved thirty pixels and dropped the only word that says which town this
                is about — which is the one word a link shared into a Lunenburg Facebook
                group cannot do without. */}
            {/* ONE LINE, always. The phone variant used to stack "Lunenburg" over
                "Budget Project", which on its own made the bar twice as tall as it
                needed to be — a two-line brand in a sticky header costs a row of the
                page on every screen, forever. The short form keeps the town's name,
                which is the one word a link shared into a Lunenburg group cannot do
                without. */}
            <span className="hidden sm:inline text-sm whitespace-nowrap">
              <span style={{ color: 'var(--brand)' }}>Lunenburg</span> Budget Project
            </span>
            <span className="sm:hidden text-[13px] whitespace-nowrap">
              <span style={{ color: 'var(--brand)' }}>Lunenburg</span> Budget
            </span>
          </button>

          {/* AREA NAV — scoped, and empty on the front page.
              This bar used to list the walkthrough, Go deeper and the two boards on EVERY
              page including the chooser, which re-presented the corridor the chooser
              exists to escape. Those are the CRISIS ANALYSIS chapters; they belong inside
              that area and nowhere else. The addresses did not move: scoping the nav is
              not the same as nesting the URLs. */}
          {area && (
            <>
              {/* The area's NAME is not drawn. The tabs beside it are the area, and a
                  label repeating them is a word that costs horizontal room on a phone
                  and tells a reader nothing they cannot see. */}
              <div className="no-scrollbar flex items-center gap-1 min-w-0
                              overflow-x-auto overscroll-x-contain">
                {AREA_TABS[area].map(id => (
                  <button key={id} onClick={() => go(id)}
                    aria-current={tab === id ? 'page' : undefined}
                    className="text-xs font-semibold px-2 py-1 rounded whitespace-nowrap shrink-0"
                    style={{ background: tab === id ? 'var(--surface-3)' : 'transparent',
                             color: tab === id ? 'var(--text-primary)'
                                               : 'var(--text-secondary)' }}>
                    {LABEL[id]}
                  </button>
                ))}
              </div>
            </>
          )}

          {/* Sources is in NO area on purpose and shows everywhere, pushed to the right so
              it reads as a utility rather than as a peer of the chapter tabs. It backs all
              four areas; putting it inside one would say it belongs to that one. Kept on a
              phone where other things are not: the claim this site rests on is that a
              resident can check it, and evidence reachable only on a desktop is a weaker
              claim than it sounds. */}
          <div className="flex items-center gap-1.5 ml-auto min-w-0 shrink-0">
            <button onClick={() => go('sources')} title="Every document this is built on"
              aria-current={tab === 'sources' ? 'page' : undefined}
              className="inline-flex text-xs font-semibold px-2 py-1 rounded
                         whitespace-nowrap shrink-0"
              style={{ background: tab === 'sources' ? 'var(--surface-3)' : 'transparent',
                       color: tab === 'sources' ? 'var(--text-primary)'
                                                : 'var(--text-secondary)' }}>
              Sources
            </button>

            {/* The two boards, only where they mean something. On the money, database and
                assistant areas they are an invitation to leave. */}
            {area === 'crisis' && CTAS.map(c => (
              <button key={c.id} onClick={() => go(c.id)} title={c.sub}
                aria-current={tab === c.id ? 'page' : undefined}
                className="cta flex items-center gap-1.5 text-xs font-bold
                           px-2.5 py-1.5 rounded whitespace-nowrap shrink-0
                           transition-opacity hover:opacity-90"
                style={tab === c.id
                  ? { background: 'var(--text-primary)', color: 'var(--surface-1)' }
                  : undefined}>
                <span aria-hidden="true">{c.glyph}</span>
                <span className="hidden sm:inline">{c.label}</span>
                <span className="sm:hidden">{c.short}</span>
              </button>
            ))}
          </div>
        </nav>
        {tab === 'context' && (
          <div className="border-t" style={{ borderColor: 'var(--grid)' }}>
            <div className="no-scrollbar mx-auto max-w-6xl px-5 h-9 flex items-center
                            gap-1 overflow-x-auto overscroll-x-contain">
              {CONTEXT_NAV.map(([id, label]) => (
                <a key={id} href={`#${id}`}
                  className="text-[11px] px-2 py-1 rounded whitespace-nowrap shrink-0 opacity-70 hover:opacity-100"
                  style={{ color: 'var(--text-secondary)' }}>{label}</a>
              ))}
            </div>
          </div>
        )}
      </header>

      {/* THE MACHINE-READABLE TOP LINE WAS REMOVED, 7 Sept 2026. TJ: "remove 'Analyse
          this budget with AI' now. we have a top level page that describes it."

          It is worth knowing what that gave up, because the component is still in the
          tree and somebody will wonder. It existed for BYTE POSITION: the same links in
          the footer sit at about 95% of a 250KB page, and agent fetch tools that truncate
          never reach them. A line under the header is read first.

          What replaces it is structural rather than textual — `For AI assistants` is now
          one of four doors on the front page, so /ask and /agents are in the link graph
          at the top level instead of being a banner on every page. That is a better
          answer for a human and a WEAKER one for a truncating fetcher, which only sees
          the page it asked for. If that turns out to matter, the fix is an early link in
          the head rather than a visible bar. See components/DataTopLine.tsx, which is
          left in place with its reasoning intact. */}

      {/* Under the header rather than inside it: the header is sticky and this is not
          worth the vertical space on every scroll, but it has to be seen on arrival.

          ARRIVAL is the operative word, and it was on every route. Four stacked bars ran
          before the first word of /ask on a phone -- nav, the AI link, this, and the
          breadcrumb -- which is most of a small screen spent on furniture. "The archive
          was updated" is context for somebody landing on the site, so it belongs on the
          page people land on. Somebody three pages deep has already arrived. */}
      {/* Both arrival pages, and only those. `/` is the door somebody lands on now, and
          the walkthrough is the page most bookmarks and shared links still point at. */}
      {(tab === 'home' || tab === 'walk')
        && <UpdatedBar onOpen={() => setNotesOpen(true)} />}

      {/* The root has no breadcrumb because there is nothing above it. Everything else
          does, including the walkthrough now that it sits one level down. */}
      {tab !== ROOT && <Breadcrumb tab={tab} goUp={goUp} />}

      {tab === 'home' && <Home onJump={go} />}

      {tab === 'walk' && <Walkthrough onJump={go} />}

      {tab === 'deeper' && <GoDeeper onJump={go} />}

      {tab === 'sources' && <Sources onJump={go} />}
      {tab === 'athletics' && <Athletics onJump={go} />}
      {tab === 'rates' && <Rates />}
      {tab === 'freecash' && <FreeCash />}
      {tab === 'themoney' && <Money onJump={go} />}
      {tab === 'database' && <Database onJump={go} />}
      {tab === 'reports' && <Reports />}
      {tab === 'agents' && <AgentsIndex />}
      {tab === 'ask' && <AskAnAssistant />}
      {/* Unlisted. Nothing on the site links here -- see UNLISTED in routes.ts. */}
      {tab === 'dataroom' && <DataRoom />}

      {tab === 'answers' && <Answers onJump={go} />}

      {tab === 'money' && <FindTheMoney onJump={go} />}

      {tab === 'context' && <Context onSources={() => go('sources')}
        onAthletics={() => go('athletics')} onRecommend={() => {
        setOrder(MODEL.presets.our_recommendation.order)
        setPreset('our_recommendation')
        go('priorities')
      }} />}

      {tab === 'why' && <WhyItRepeats />}

      {tab === 'curve' && <BendTheCurve onJump={go} option={optionFor('curve')} />}

      {tab === 'solved' && <Solved onLoadPackage={loadOption} />}

      {tab === 'override' && <Override onJump={go} />}

      {tab === 'priorities' && (
        <Priorities order={order} setOrder={setOrder} preset={preset} setPreset={setPreset}
          onSendToAdjust={sendToAdjust} />
      )}

      {tab === 'adjust' && (
        <Adjust seed={seed} option={optionFor('adjust')} onJump={jump}
          onDevelopment={() => go('development')}
          newValue={newValue} setNewValue={setNewValue} />
      )}

      {tab === 'development' && (
        <Development commercial={newValue} setCommercial={setNewValue}
          homes={homes} setHomes={setHomes}
          gap={project(5, MODEL.assumptions)[0].deficit}
          share={newGrowthPerDollar(MODEL.assumptions)} />
      )}

      <footer className="border-t py-10" style={{ borderColor: 'var(--grid)' }}>
        <div className="mx-auto max-w-6xl px-5 text-xs" style={{ color: 'var(--text-muted)' }}>
          {/* NAVIGATION AND THE DATA BLOCK ARE OFF THE FRONT PAGE.
              The chooser's whole job is one decision between four doors. A footer under
              it offering the walkthrough, Sources and Go deeper re-adds three of the
              destinations the page just finished removing, and the machine-readable
              block adds six addresses on top — so the shortest page on the site had the
              longest tail. They stay on every other page, where the reader is inside
              something and a way out is worth the room. */}
          {tab !== 'home' && (
            <>
              <button onClick={() => go('walk')}
                className="text-xs font-semibold mb-2 block"
                style={{ color: 'var(--series-cost)' }}>
                Start here &mdash; the walkthrough, from the beginning &rarr;
              </button>
              <button onClick={() => go('sources')}
                className="text-xs font-semibold mb-2 block"
                style={{ color: 'var(--series-cost)' }}>
                Sources &mdash; every document this is built on &rarr;
              </button>
              <button onClick={() => go('deeper')}
                className="text-xs font-semibold mb-3 block"
                style={{ color: 'var(--series-cost)' }}>
                Go deeper &mdash; every other page &rarr;
              </button>
              <DataFooter />
            </>
          )}

          {/* Said plainly and near the top of the block, because it is the sentence
              somebody quotes when they are asked "is this the Town's site?" — and because
              a site that looks official and is not would cost the Town something it did
              not agree to. */}
          <p className="mb-2">
            <strong style={{ color: 'var(--text-secondary)' }}>
              An independent tool for residents.
            </strong>{' '}
            Not affiliated with the Town of Lunenburg, the School Committee or the school
            district, and nothing here speaks for any of them. Everything on it is
            arithmetic anybody can check against the documents it cites.
          </p>
          <span style={{ color: 'var(--brand)' }}>Lunenburg</span> Budget Project &mdash;
          lunenburgbudgetproject.org. Figures for FY27 and earlier are from published
          documents; FY28 onward are projections.{' '}
          <VersionStamp onOpen={() => setNotesOpen(true)} />
        </div>
      </footer>

      <ReleaseNotesDialog open={notesOpen} onClose={() => setNotesOpen(false)} />
    </div>
  )
}

/** Where the page sits, and the way up.
 *
 *  Structural, not historical. It always reads the same for a given page no matter how
 *  somebody reached it, because that is what a breadcrumb is for: a claim about the shape
 *  of the site, which a reader can learn once and rely on. The route actually taken is the
 *  back button's job and it already does it.
 *
 *  Not sticky. The header above it already is, and two stacked bars would push every
 *  page's own pinned content down for the sake of a line that is only read on arrival. */
function Breadcrumb({ tab, goUp }: { tab: Tab; goUp: (t: Tab) => void }) {
  const trail: Tab[] = []
  for (let up = PARENT[tab]; up; up = PARENT[up]) trail.unshift(up)
  // Whichever tab owns the root, read from the table rather than named. It was hardcoded
  // to 'walk' and would have gone on claiming the walkthrough was the top of the site the
  // day the root became the chooser.
  trail.unshift(ROOT)

  return (
    <nav aria-label="Breadcrumb" className="border-b" style={{ borderColor: 'var(--grid)' }}>
      <ol className="mx-auto max-w-6xl px-5 py-2.5 flex items-center gap-1.5 flex-wrap
                     text-[12px]">
        {trail.map(t => (
          <li key={t} className="flex items-center gap-1.5">
            <button onClick={() => goUp(t)} className="font-semibold hover:underline"
              style={{ color: 'var(--series-cost)' }}>{LABEL[t]}</button>
            <span aria-hidden="true" style={{ color: 'var(--text-muted)' }}>&rsaquo;</span>
          </li>
        ))}
        <li aria-current="page" style={{ color: 'var(--text-secondary)' }}>{LABEL[tab]}</li>
      </ol>
    </nav>
  )
}
