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
import { pathFor, tabFromPath, type Tab } from './routes'


/** The pages you use rather than read.
 *
 *  Kept out of the chapter strip on purpose, so they do not sit in the reading order
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

const TABS: { id: Tab; label: string; sub: string }[] = [
  { id: 'walk', label: 'Start here', sub: 'Eleven steps, in order, assuming you know nothing about the budget' },
  { id: 'answers', label: 'Straight answers', sub: 'The questions people actually ask, in plain English, with the arithmetic' },
  { id: 'money', label: 'Find the money', sub: 'Pick a number. See what raising it costs on every lever, with no projection involved' },
  { id: 'context', label: 'The situation', sub: 'What happened, what it costs, where the numbers come from' },
  { id: 'why', label: 'Why it repeats', sub: 'The two growth rates behind every year of this' },
  { id: 'override', label: 'Overrides', sub: 'How big, for how long, and written for whom — the arithmetic of a ballot question' },
  { id: 'priorities', label: 'Priorities', sub: 'Set the order things are given up in, and watch it happen' },
  { id: 'development', label: 'Development', sub: 'What building commercial and residential actually changes' },
]

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
  // The commercial build rate is the same decision on two pages, so it lives here rather
  // than being duplicated. Housing is modeled on Development only.
  const [newValue, setNewValue] = useState(MODEL.taxBase.currentNewGrowthValue)
  const [homes, setHomes] = useState(MODEL.taxBase.fy23NewValue)
  const pending = useRef<string | null>(null)
  const strip = useRef<HTMLDivElement>(null)

  // The back button has to work, or a shared link is a trap: follow one, look around,
  // and there is no way back to where you came from.
  useEffect(() => {
    const onPop = () => setTab(tabFromPath(window.location.pathname))
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

  // On a phone the chapter strip scrolls, so arriving on a tab whose pill is off to the
  // right would leave nothing marked as current. Bring it into view when the tab changes.
  useEffect(() => {
    const pill = strip.current?.querySelector<HTMLElement>(`[data-tab="${tab}"]`)
    pill?.scrollIntoView({ block: 'nearest', inline: 'nearest' })
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

  const go = (t: Tab) => { setTab(t); navigate(t); window.scrollTo({ top: 0 }) }

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
        {/* Seven controls do not fit across a phone, and forcing them to try was what
            made the whole page scroll sideways. The single row wants 836px, so below lg
            the brand and the one button take the top line and the chapters get a strip of
            their own that scrolls inside itself. */}
        <nav aria-label="Sections"
          className="mx-auto max-w-6xl px-5 lg:h-12 lg:flex lg:items-center lg:gap-1">
          <div className="flex items-center gap-3 h-12 lg:contents">
            {/* Two buttons and a wordmark do not fit across a phone, and the chapter strip
                below already says which site this is. */}
            <span className="font-bold text-sm shrink-0 lg:mr-3">
              <span className="hidden sm:inline">Lunenburg FY28</span>
              <span className="sm:hidden">FY28</span>
            </span>
            <div className="flex items-center gap-1.5 ml-auto lg:order-last shrink-0">
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
          </div>
          <div ref={strip}
            className="no-scrollbar flex items-center gap-1 overflow-x-auto
                       overscroll-x-contain pb-2 -mx-5 px-5 lg:contents">
            {TABS.map(t => (
              <button key={t.id} onClick={() => go(t.id)} title={t.sub}
                data-tab={t.id}
                aria-current={tab === t.id ? 'page' : undefined}
                className="text-xs font-semibold px-2.5 py-1.5 lg:py-1 rounded-md
                           whitespace-nowrap shrink-0"
                style={{
                  background: tab === t.id ? 'var(--surface-3)' : 'transparent',
                  color: tab === t.id ? 'var(--text-primary)' : 'var(--text-secondary)',
                }}>
                {t.label}
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

      {tab === 'walk' && <Walkthrough onJump={go} />}

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
          Lunenburg FY28 budget projection &mdash; an independent tool for residents.
          Figures for FY27 and earlier are from published documents; FY28 onward are
          projections. Last updated August 2026.
        </div>
      </footer>
    </div>
  )
}
