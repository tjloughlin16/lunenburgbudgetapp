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
import { GoDeeper } from './pages/GoDeeper'
import { LABEL, PARENT, pathFor, tabFromPath, type Tab } from './routes'


/** The pages you use rather than read.
 *
 *  Kept out of the reading order on purpose, so they do not sit among the chapters
 *  pretending to be another chapter, and given the same weight as each other because
 *  they are the same kind of thing: a board of controls with a result attached. One
 *  moves amounts, the other moves rates, and between them they are what the rest of the
 *  site is written to prepare somebody for. */
const CTAS: { id: Tab; label: string; short: string; glyph: string; sub: string }[] = [
  { id: 'curve', label: 'Bend the curve', short: 'Bend the curve', glyph: '\u2197',
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
  /** The page they clicked from, so a breadcrumb can show the route actually taken. Null
   *  after a deep link or a back button, where the honest answer is that we do not know
   *  and the structural parent is used instead. */
  const [from, setFrom] = useState<Tab | null>(null)
  // The commercial build rate is the same decision on two pages, so it lives here rather
  // than being duplicated. Housing is modeled on Development only.
  const [newValue, setNewValue] = useState(MODEL.taxBase.currentNewGrowthValue)
  const [homes, setHomes] = useState(MODEL.taxBase.fy23NewValue)
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
    requestAnimationFrame(() => document.getElementById(id)?.scrollIntoView())
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

  const go = (t: Tab) => {
    if (t !== tab) setFrom(tab)
    setTab(t); navigate(t); window.scrollTo({ top: 0 })
  }

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
          <button onClick={() => go('walk')}
            className="font-bold text-sm shrink-0 mr-1"
            title="Back to the start of the walkthrough">
            <span className="hidden sm:inline">Lunenburg FY28</span>
            <span className="sm:hidden">FY28</span>
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

          <div className="flex items-center gap-1.5 ml-auto shrink-0">
            {CTAS.map(c => (
              <button key={c.id} onClick={() => go(c.id)} title={c.sub}
                aria-current={tab === c.id ? 'page' : undefined}
                className="cta flex items-center gap-1.5 text-xs font-bold
                           px-3 py-2 rounded-md whitespace-nowrap shrink-0
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

      {tab !== 'walk' && <Breadcrumb tab={tab} from={from} go={go} />}

      {tab === 'walk' && <Walkthrough onJump={go} />}

      {tab === 'deeper' && <GoDeeper onJump={go} />}

      {tab === 'answers' && <Answers onJump={go} />}

      {tab === 'money' && <FindTheMoney onJump={go} />}

      {tab === 'context' && <Context onRecommend={() => {
        setOrder(MODEL.presets.our_recommendation.order)
        setPreset('our_recommendation')
        go('priorities')
      }} />}

      {tab === 'why' && <WhyItRepeats />}

      {tab === 'curve' && <BendTheCurve onJump={go} />}

      {tab === 'override' && <Override onJump={go} />}

      {tab === 'priorities' && (
        <Priorities order={order} setOrder={setOrder} preset={preset} setPreset={setPreset}
          onSendToAdjust={sendToAdjust} />
      )}

      {tab === 'adjust' && (
        <Adjust seed={seed} onJump={jump} onDevelopment={() => go('development')}
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
          <button onClick={() => go('deeper')}
            className="text-xs font-semibold mb-3 block"
            style={{ color: 'var(--series-cost)' }}>
            Go deeper &mdash; every other page &rarr;
          </button>
          Lunenburg FY28 budget projection &mdash; an independent tool for residents.
          Figures for FY27 and earlier are from published documents; FY28 onward are
          projections. Last updated August 2026.
        </div>
      </footer>
    </div>
  )
}

/** Where you are, and the way back.
 *
 *  Every page except the walkthrough is now a drill-in, and several are reachable from
 *  more than one place — Straight answers from Go deeper, from the walkthrough's exit, and
 *  from a link somebody was sent. So the trail prefers the route actually taken and falls
 *  back to the structural parent when the page was opened cold, which is the only honest
 *  thing it can do.
 *
 *  Not sticky. The header above it already is, and two stacked bars would push every
 *  page's own pinned content down for the sake of a line that is only read on arrival. */
function Breadcrumb({ tab, from, go }: {
  tab: Tab; from: Tab | null; go: (t: Tab) => void
}) {
  const via = from && from !== 'walk' && from !== tab ? from : PARENT[tab] ?? null
  const trail: Tab[] = via ? ['walk', via] : ['walk']

  return (
    <nav aria-label="Breadcrumb"
      className="border-b" style={{ borderColor: 'var(--grid)' }}>
      <ol className="mx-auto max-w-6xl px-5 py-2.5 flex items-center gap-1.5 flex-wrap
                     text-[12px]">
        {trail.map(t => (
          <li key={t} className="flex items-center gap-1.5">
            <button onClick={() => go(t)} className="font-semibold hover:underline"
              style={{ color: 'var(--series-cost)' }}>{LABEL[t]}</button>
            <span aria-hidden="true" style={{ color: 'var(--text-muted)' }}>&rsaquo;</span>
          </li>
        ))}
        <li aria-current="page" style={{ color: 'var(--text-secondary)' }}>{LABEL[tab]}</li>
      </ol>
    </nav>
  )
}
