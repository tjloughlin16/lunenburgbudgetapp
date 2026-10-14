/** ONE PAGE COMPONENT FOR EVERY TOPIC AND HUB -- /transportation, /athletics, and each
 *  /<category>/<topic> under them. The model and the registry are scripts/topics.py; every
 *  payload is generated and validated (scripts/topic.py), so nothing here words or
 *  computes a figure.
 *
 *  WHY. TJ, 12 October 2026: "nobody will ever read these full reports... break up all these
 *  long reports into smaller pages", so a reader "can dive in at any depth on a particular
 *  topic, vs scrolling a 64 minute read page". A topic answers one question: its finding,
 *  one chart, its facts, two to four conclusions that open to what they rest on, its
 *  figures, what was said about it, and where the figures come from. A hub is the
 *  category's top: the answer, the chart, the matrix of facts, the conclusions, and a card
 *  per topic.
 *
 *  A topic listed on two shelves (athletic transportation, on both Transportation and
 *  Athletics) has ONE address and says which other shelf it is on. Never two copies. */
import { createElement, useEffect, useState } from 'react'
import { abs } from '../lib/abs'
import { pageTitle, setShareMeta } from '../lib/title'
import { topicIdFromPath } from '../routes'
import {
  FigureTable, Ladder, ReportShell,
  type FigureTableData, type LadderData, type LadderEvidence, type LadderFact, type LadderUnit,
} from '../components/report'
import { ANALYSIS_CHARTS } from '../components/analysisCharts'
import { InlineTopicChart, isInline, type InlineChart } from '../components/TopicCharts'
import { Brief, Tag, type Chain, type Step } from '../components/brief'
import { TopicLink } from '../components/TopicLink'

type IndexTopic = {
  id: string; title: string; path: string; home: string; shelves: string[]
  finding: string | null; minutes: number | null; ready: boolean
}
type IndexCategory = {
  id: string; shelf: string; title: string; path: string; answer: string | null
  groups: { title: string | null; topics: string[] }[]
  elsewhere: { href: string; title: string }[]
  full_report: { href: string; label: string }
}
type Index = { categories: IndexCategory[]; topics: Record<string, IndexTopic> }

type Said = { quote: string; board: string; date: string; href: string; label: string; caption?: boolean }
/** A bespoke component in ANALYSIS_CHARTS fed by a payload, or an inline spec written by
 *  scripts/topic.py (series, ranking, parts, image) and drawn by TopicCharts. */
type ChartRef = { id: string; source: string } | InlineChart | null
type TopicPayload = {
  kind: 'topic'; id: string; title: string; category: string; path: string; shelves: string[]
  finding: LadderUnit; chart: ChartRef; facts: LadderFact[]
  conclusions: (LadderUnit & { rests_on: string[]; notes?: Step[] })[]
  table: FigureTableData | null; said: Said[]; sources: { label: string; href: string }[]
  full_report: { href: string; label: string }
}
type HubPayload = {
  kind: 'hub'; id: string; title: string; category: string; answer: LadderUnit; chart: ChartRef
  ladder: LadderData; chains: Chain[]; table: FigureTableData | null
  full_report: { href: string; label: string }
}

const link = { color: 'var(--series-cost)' }
const eyebrow = 'text-[11px] font-semibold uppercase tracking-widest'

/** The page's signature chart: inline, or from the site's registry. */
function TopicChart({ chart, alt }: { chart: ChartRef; alt: string }) {
  if (isInline(chart)) return <InlineTopicChart c={chart} />
  return <RegistryChart chart={chart} alt={alt} />
}

function RegistryChart({ chart, alt }: { chart: { id: string; source: string } | null; alt: string }) {
  const [data, setData] = useState<unknown>(null)
  useEffect(() => {
    if (!chart) return
    fetch(chart.source).then(r => r.json()).then(setData).catch(() => setData(null))
  }, [chart?.source])
  const entry = chart ? ANALYSIS_CHARTS[chart.id] : undefined
  if (!chart || !entry || !data || !entry.needs(data as Record<string, unknown>)) return null
  return <figure className="report-body mt-5 [&>figure]:max-w-none">
    {createElement(entry.render as (p: { data: unknown; alt: string }) => React.ReactNode, { data, alt })}</figure>
}

function Shelf({ ix, t }: { ix: Index; t: { shelves: string[] } }) {
  const cat = (id: string) => ix.categories.find(c => c.id === id)
  const [, ...also] = t.shelves
  if (!also.length) return null
  return (
    <p className="text-[13px] mt-1" style={{ color: 'var(--text-muted)' }}>
      {also.length ? <>Also under {also.map((a, i) => (
        <span key={a}>{i ? ', ' : ''}<a href={abs(cat(a)?.path ?? '/')} className="underline" style={link}>
          {cat(a)?.shelf}</a></span>))}</> : null}
    </p>
  )
}

function SaidList({ said }: { said: Said[] }) {
  if (!said.length) return null
  return (
    <section className="mt-10 max-w-3xl">
      <h2 className={eyebrow} style={{ color: 'var(--text-muted)' }}>What was said</h2>
      <ul className="mt-2 space-y-3">
        {said.map((s, i) => (
          <li key={i} className="pl-3 border-l-2" style={{ borderColor: s.caption ? 'var(--axis)' : 'var(--grid)' }}>
            <p className="text-[14.5px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
              “{s.quote}”</p>
            <p className="text-[12.5px] mt-0.5"><a href={s.href} className="underline" style={link}>
              {s.label}</a>{s.caption ? <span style={{ color: 'var(--text-muted)' }}> — machine captions, a finding aid</span> : null}</p>
          </li>
        ))}
      </ul>
    </section>
  )
}

/* NO "FULL REPORT" LINE. TJ, 12 October 2026: "we dont need FULL reports.... we need all
 * the smaller reports broken out". A page ends at its own sources. */
function Sources({ sources }: { sources: { label: string; href: string }[] }) {
  return (
    <section className="mt-10 max-w-3xl">
      <h2 className={eyebrow} style={{ color: 'var(--text-muted)' }}>Sources</h2>
      <ul className="mt-2 space-y-1 text-[13px]">
        {sources.map(s => (
          <li key={s.href}><a href={abs(s.href)} className="underline" style={link}>{s.label}</a></li>
        ))}
      </ul>
    </section>
  )
}

/** The cards on a hub: one per topic, grouped as the registry groups them, each drawn as
 *  a TopicLink -- the one shape a topic has wherever it is listed. */
function TopicCards({ ix, cat }: { ix: Index; cat: IndexCategory }) {
  const shelfOf = (id: string) => ix.categories.find(c => c.id === id)?.shelf
  return (
    <section className="mt-10 max-w-3xl" id="topics">
      {cat.groups.map((g, gi) => (
        <div key={gi} className={gi ? 'mt-6' : undefined}>
          <h2 className={eyebrow} style={{ color: 'var(--text-muted)' }}>{g.title ?? `${cat.shelf}, topic by topic`}</h2>
          <ul className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-4 mt-2">
            {g.topics.map(id => ix.topics[id]).filter(Boolean).map(t => (
              <li key={t.id}><TopicLink t={t} also={t.shelves.filter(s => s !== cat.id)
                .map(shelfOf).filter((x): x is string => !!x)} /></li>
            ))}
          </ul>
        </div>
      ))}
      <Elsewhere cat={cat} />
    </section>
  )
}

function Elsewhere({ cat }: { cat: IndexCategory }) {
  return cat.elsewhere.length ? (
    <div className="mt-6">
      <h2 className={eyebrow} style={{ color: 'var(--text-muted)' }}>Elsewhere on the site</h2>
      <ul className="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-[14px]">
        {cat.elsewhere.map(e => <li key={e.href}><a href={abs(e.href)} className="underline" style={link}>{e.title}</a></li>)}
      </ul>
    </div>
  ) : null
}

/** Previous, next, and back to the hub -- so a reader moves through a shelf without it. */
function ShelfNav({ ix, t }: { ix: Index; t: TopicPayload }) {
  const cat = ix.categories.find(c => c.id === t.category)
  if (!cat) return null
  const order = cat.groups.flatMap(g => g.topics).filter(id => ix.topics[id]?.ready)
  const i = order.indexOf(t.id)
  const prev = i > 0 ? ix.topics[order[i - 1]] : null
  const next = i >= 0 && i < order.length - 1 ? ix.topics[order[i + 1]] : null
  return (
    <nav aria-label={`More in ${cat.shelf}`} className="no-print mt-10 pt-4 border-t max-w-3xl grid grid-cols-2 gap-4 text-[14px]"
      style={{ borderColor: 'var(--grid)' }}>
      <div>{prev ? <><p className="text-[11px]" style={{ color: 'var(--text-muted)' }}>Previous</p>
        <a href={abs(prev.path)} className="underline" style={link}>{prev.title}</a></> : null}</div>
      <div className="text-right">{next ? <><p className="text-[11px]" style={{ color: 'var(--text-muted)' }}>Next</p>
        <a href={abs(next.path)} className="underline" style={link}>{next.title}</a></> : null}</div>
      <p className="col-span-2 text-center text-[13px]">
        <a href={abs(cat.path)} className="underline" style={link}>All of {cat.shelf}</a></p>
    </nav>
  )
}

/** `fallback`: the hub to show for an address that names no topic -- the aliases of
 *  /athletics (`/sports`, `/athletic`) land on the athletics hub, not on transportation. */
export function Topic({ fallback = 'transportation' }: { fallback?: string }) {
  const id = topicIdFromPath(window.location.pathname) ?? fallback
  const [ix, setIx] = useState<Index | null>(null)
  const [p, setP] = useState<TopicPayload | HubPayload | null>(null)
  const [err, setErr] = useState<string | null>(null)
  useEffect(() => {
    fetch('/data/topics.json').then(r => r.json()).then(setIx).catch(e => setErr(String(e)))
    fetch(`/data/topics/${id}.json`)
      .then(r => { if (!r.ok) throw new Error(`No page called ${id} yet.`); return r.json() })
      .then(setP).catch(e => setErr(String(e.message ?? e)))
  }, [id])
  // THE LINK PREVIEW IS THE PAGE'S OWN. TJ, 14 October 2026: every topic link shared on
  // Facebook previewed as "Reports and analyses" with the site's disclaimer, because this
  // set the tab title once the payload arrived and left og:title and og:description at the
  // app's generic fallback. A topic's preview is its title and its finding; a hub's, its
  // title and its answer. The prerender captures them, so a scraper gets the same.
  useEffect(() => {
    if (!p) return
    const t = pageTitle(p.title)
    if (t) document.title = t
    setShareMeta({ title: t, description: p.kind === 'topic' ? p.finding.text : p.answer.text,
                   page: true, type: 'article' })
  }, [p])

  const title = p?.title ?? ix?.topics[id]?.title ?? ix?.categories.find(c => c.id === id)?.title ?? ''
  const cat = ix?.categories.find(c => c.id === (p?.category ?? id))
  // The eyebrow IS the way back to the shelf on a topic page; on a hub it is just the name.
  const shelf = cat ? (p?.kind === 'topic'
    ? <a href={abs(cat.path)} className="hover:underline">{cat.shelf}</a> : cat.shelf) : null

  return (
    <ReportShell kicker={shelf ?? 'Reports'} title={title} err={err} loading={!p && !err}
      dataUrl={`/data/topics/${id}.json`}>
      {p && ix && p.kind === 'hub' ? (
        <>
          <p className="text-[19px] leading-snug font-semibold mt-6 max-w-3xl">{p.answer.text}</p>
          <p className="text-[13px] mt-2"><a href="#topics" className="underline" style={link}>
            Go straight to the topics &darr;</a></p>
          <TopicChart chart={p.chart} alt={title} />
          <Ladder l={p.ladder} evidence={Object.fromEntries(p.chains.map(c => [c.id, {
            tag: <Tag v={c.verdict} label={c.label} />, question: c.question,
            body: <Brief steps={c.steps} base={p.full_report.href} />,
          } satisfies LadderEvidence]))} />
          {ix.categories.find(c => c.id === p.id)
            ? <TopicCards ix={ix} cat={ix.categories.find(c => c.id === p.id)!} /> : null}
          {p.table ? <section className="mt-10 max-w-3xl"><FigureTable t={p.table} /></section> : null}
        </>
      ) : p && ix && p.kind === 'topic' ? (
        <>
          <Shelf ix={ix} t={p} />
          <p className="text-[19px] leading-snug font-semibold mt-4 max-w-3xl">{p.finding.text}</p>
          <TopicChart chart={p.chart} alt={p.title} />
          <Ladder
            l={{ tiers: [{ title: 'The facts', facts: p.facts }], title: 'What it shows',
                 conclusions: p.conclusions.map((c, i) => ({ ...c, chain: c.notes?.length ? `n${i}` : undefined })) }}
            evidence={Object.fromEntries(p.conclusions.map((c, i) => [`n${i}`, {
              tag: null, question: '', body: <Brief steps={c.notes ?? []} base={p.full_report.href} />,
            } satisfies LadderEvidence]))} />
          {p.table ? <section className="mt-10 max-w-3xl"><FigureTable t={p.table} /></section> : null}
          <SaidList said={p.said} />
          <Sources sources={p.sources} />
          <ShelfNav ix={ix} t={p} />
        </>
      ) : null}
    </ReportShell>
  )
}
