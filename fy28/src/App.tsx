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
import { Solved } from './pages/Solved'
import { GoDeeper } from './pages/GoDeeper'
import { Sources } from './pages/Sources'
import { Athletics } from './pages/Athletics'
import { Rates } from './pages/Rates'
import { DataFooter } from './components/DataFooter'
import { DataTopLine } from './components/DataTopLine'
import { AgentsIndex } from './components/AgentsIndex'
import { FreeCash } from './pages/FreeCash'
import { DataRoom } from './pages/DataRoom'
import { Reports } from './pages/Reports'
import { LABEL, PARENT, pathFor, tabFromPath, type Tab } from './routes'
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

/** The chapter strip is gone.
 *
 *  Seven pills competing for a phone's width was the site telling a first-time reader that
 *  it had seven equally good beginnings, which was never true. The walkthrough is the way
 *  in, the two boards are the things you use, and everything else keeps its address and
 *  its content behind one quiet door. Nothing has been removed — see pages/GoDeeper. */
const DEEPER: { id: Tab; label: string; sub: string } =
  { id: 'deeper', label: 'Go deeper',
    sub: 'Every other page — the questions, the levers priced in full, and where the numbers come from' }

/** Three pages, three jobs.
 *
 *  The two interactive pages are deliberately separate scenarios. Priorities asks what a
 *  ranking gives up on its own; Adjust asks what you would actually do. Letting a fee
 *  increase on one quietly rescue the other would hide the point of both. The only thing
 *  that crosses between them is a starting list of cuts, sent one way, on request. */
export default function App() {
  const [tab, setTab] = useState<Tab>(() => tabFromPath(window.location.pathname))
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
          className="mx-auto max-w-6xl px-5 h-12 flex items-center gap-3">
          {/* The site outgrew its name. It was "Lunenburg FY28" when it was a projection
              of one budget year; it is now an argument about why the year keeps
              recurring and what would stop it, and the address people will type is
              lunenburgbudgetproject.org. A brand that disagrees with the domain is a
              small tax on everybody who tries to tell somebody else about it.
              FY28 has not gone anywhere — it is all over the walkthrough, where it is a
              fact rather than a title. */}
          <button onClick={() => go('walk')}
            className="font-bold shrink-0 mr-1 leading-none text-left"
            title="Back to the start of the walkthrough">
            {/* Two lines on a phone rather than a shorter name. "Budget Project" alone
                saved thirty pixels and dropped the only word that says which town this
                is about — which is the one word a link shared into a Lunenburg Facebook
                group cannot do without. */}
            <span className="hidden sm:inline text-sm">
              <span style={{ color: 'var(--brand)' }}>Lunenburg</span> Budget Project
            </span>
            <span className="sm:hidden block text-[11px]">
              <span className="block" style={{ color: 'var(--brand)' }}>Lunenburg</span>
              <span className="block">Budget Project</span>
            </span>
          </button>

          {/* Reachable on a phone from the walkthrough's last room and the footer, so it
              gives up its place in the bar rather than squeezing the two boards. */}
          <button onClick={() => go(DEEPER.id)} title={DEEPER.sub}
            aria-current={tab === DEEPER.id ? 'page' : undefined}
            className="hidden sm:inline-flex text-xs font-semibold px-2.5 py-1.5 rounded-md
                       whitespace-nowrap shrink-0"
            style={{ background: tab === DEEPER.id ? 'var(--surface-3)' : 'transparent',
                     color: tab === DEEPER.id ? 'var(--text-primary)' : 'var(--text-secondary)' }}>
            {DEEPER.label}
          </button>

          {/* Kept on a phone where Go deeper is not. The claim this whole site rests on is
              that a resident can check it, and evidence that only appears on a desktop is
              a weaker claim than it sounds. Two words, so it costs the CTAs almost
              nothing. */}
          <button onClick={() => go('sources')} title="Every document this is built on"
            aria-current={tab === 'sources' ? 'page' : undefined}
            className="inline-flex text-xs font-semibold px-2.5 py-1.5 rounded-md
                       whitespace-nowrap shrink-0"
            style={{ background: tab === 'sources' ? 'var(--surface-3)' : 'transparent',
                     color: tab === 'sources' ? 'var(--text-primary)' : 'var(--text-secondary)' }}>
            Sources
          </button>

          {/* Scrolls rather than wraps or truncates: three buttons plus the brand is
              wider than a small phone, and a nav that reflows to two rows moves the page
              under the reader's thumb. */}
          <div className="no-scrollbar flex items-center gap-1.5 ml-auto min-w-0
                          overflow-x-auto overscroll-x-contain">
            {CTAS.map(c => (
              <button key={c.id} onClick={() => go(c.id)} title={c.sub}
                aria-current={tab === c.id ? 'page' : undefined}
                className="cta flex items-center gap-1.5 text-xs font-bold
                           px-2.5 py-2 rounded-md whitespace-nowrap shrink-0
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

      {/* FIRST thing under the header, and that position is the whole point -- the same
          links in the footer sit at 95% of a 250KB page and are cut off before any
          fetch tool reaches them. See DataTopLine.tsx. */}
      <DataTopLine />

      {/* Under the header rather than inside it: the header is sticky and this is not
          worth the vertical space on every scroll, but it has to be seen on arrival. */}
      <UpdatedBar onOpen={() => setNotesOpen(true)} />

      {tab !== 'walk' && <Breadcrumb tab={tab} goUp={goUp} />}

      {tab === 'walk' && <Walkthrough onJump={go} />}

      {tab === 'deeper' && <GoDeeper onJump={go} />}

      {tab === 'sources' && <Sources onJump={go} />}
      {tab === 'athletics' && <Athletics onJump={go} />}
      {tab === 'rates' && <Rates />}
      {tab === 'freecash' && <FreeCash />}
      {tab === 'reports' && <Reports />}
      {tab === 'agents' && <AgentsIndex />}
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
          {/* The only route to the other pages on a phone, where the header gives up its
              Go deeper button to fit the two boards. */}
          {/* First line of the footer on every page. The sentence below promises the
              reader can check this against the documents it cites; a promise with no link
              under it is decoration. */}
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
  trail.unshift('walk')

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
