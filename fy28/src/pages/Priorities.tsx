import { useMemo, useState } from 'react'
import { MODEL, project, runCascade, usd } from '../model/engine'
import { Section, Note } from '../components/primitives'
import { PriorityBuilder } from '../components/PriorityBuilder'
import { CutLine, type Tick } from '../components/CutLine'
import { YearChart } from '../components/YearChart'
import { Timeline, Landmarks } from '../components/Timeline'
import { PriorityImpact, ActiveRanking } from '../components/PriorityImpact'

/** One dial: the ranking.
 *
 *  This page answers a single question — if nobody raises a dollar and nobody argues about
 *  individual line items, what does a given set of priorities give up, and when? It runs
 *  against the district's published assumptions and nothing else. Deliberately separate
 *  from the adjustments page: mixing the two would let a fee increase quietly rescue a
 *  ranking, which is exactly the thing this page exists to make visible. */
export function Priorities({ order, setOrder, preset, setPreset, onSendToAdjust }: {
  order: string[]
  setOrder: (o: string[]) => void
  preset: string | null
  setPreset: (p: string | null) => void
  onSendToAdjust: () => void
}) {
  const [target, setTarget] = useState<number | null>(null)

  const years = useMemo(() => runCascade(order, MODEL.assumptions, 5), [order])
  const plain = useMemo(() => project(5, MODEL.assumptions), [])
  const presetName = preset ? MODEL.presets[preset].name : null

  const ticks: Tick[] = useMemo(() => {
    let cum = 0
    return years.map(y => ({ fy: y.fy, cumulative: (cum += y.deficit) }))
  }, [years])
  const maxTarget = Math.max(ticks.at(-1)?.cumulative ?? 0, 3_600_000)
  const effectiveTarget = target ?? years[0].deficit

  return (
    <div>
      <div className="mx-auto max-w-6xl px-5 pt-12 pb-2">
        <p className="text-xs font-semibold uppercase tracking-widest mb-3"
          style={{ color: 'var(--text-muted)' }}>Set the order, watch it happen</p>
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight leading-[1.1] max-w-3xl">
          What should be protected?
        </h1>
        <p className="mt-4 text-[15px] leading-relaxed max-w-2xl"
          style={{ color: 'var(--text-secondary)' }}>
          You cannot pick individual line items here &mdash; that is the next page. Here you
          set only the order in which things are given up, and the model cuts from the
          bottom until each year&rsquo;s gap is closed. It runs against the
          district&rsquo;s own published growth rates, with no fee increases and no savings,
          so what you see is what a ranking costs on its own.
        </p>
      </div>

      <Section id="ranking" eyebrow="Your turn" title="The ranking"
        lede={<>Below is the ranking Lunenburg&rsquo;s School Committee revealed through its
          own four FY27 budget scenarios &mdash; the order in which it gave things up.
          Ashburnham-Westminster ranked the same list almost upside down. Change it to
          yours.</>}>
        <PriorityBuilder order={order} setOrder={setOrder}
          preset={preset} setPreset={setPreset} />
        <PriorityImpact years={years} />
      </Section>

      <Section id="cut-line" eyebrow="The consequence" title="Where the cut line falls"
        lede={<>Drag the slider to set how big a hole has to be closed, or pick a year
          marker. Everything below the line is gone. The order comes from the priorities you
          set above &mdash; so if you dislike this outcome, the fix is upstream.</>}>
        <ActiveRanking order={order} presetName={presetName} />
        <CutLine order={order} target={effectiveTarget} setTarget={setTarget}
          ticks={ticks} max={maxTarget} />

        <div className="card p-4 mt-5 flex flex-wrap items-center justify-between gap-3">
          <p className="text-[13px] leading-relaxed max-w-xl"
            style={{ color: 'var(--text-secondary)' }}>
            <strong>Disagree with some of it?</strong> Take this ranking&rsquo;s FY28 cuts
            over to the adjustments page as a starting point &mdash; every item becomes a
            switch you can flip, alongside the fees and savings that could replace them.
            This page is not affected by anything you do there.
          </p>
          <button onClick={onSendToAdjust}
            className="px-3.5 py-2 rounded-lg text-xs font-semibold shrink-0"
            style={{ background: 'var(--series-cost)', color: '#fff' }}>
            Open these {usd(years[0].cutTotal)} of cuts in Adjust →
          </button>
        </div>
      </Section>

      <Section id="years" eyebrow="The trajectory" title="What each year takes"
        lede={<>Costs rise faster than Proposition 2&frac12; lets revenue rise. Unless
          something changes, the gap reopens every year &mdash; and every year the cut line
          moves further up your priority list.</>}>
        <ActiveRanking order={order} presetName={presetName} />
        <YearChart years={plain} />

        <h3 className="text-sm font-bold mt-10 mb-3">The year each thing is lost</h3>
        <Landmarks years={years} />
        <Note>Based on the priorities you set. Reorder them and these dates move.</Note>

        <h3 className="text-sm font-bold mt-10 mb-3">Year by year</h3>
        <Timeline years={years} />
        <Note>
          The cascade cuts until each year&rsquo;s hole is covered, so the last thing cut
          usually overshoots &mdash; programs come in whole units and you cannot cut 60%
          of a teacher.
        </Note>
      </Section>
    </div>
  )
}
