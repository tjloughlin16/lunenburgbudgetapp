/** BLOCKS: the parts of a topic or hub the author ARRANGES (scripts/topic_blocks.py).
 *
 *  TJ, 25 October 2026: "you can build diagrams, charts, or whatever on the fly even if we
 *  dont have templates for them or havent used them before ... for ANY page, hub we build."
 *  The named blocks here are the ones that have been useful twice. Anything else is a CUSTOM
 *  block: a component in ./custom, registered in ./custom/index.ts, fed by its payload.
 *
 *  Nothing here words or computes a figure; every string arrives checked. What a claim RESTS
 *  ON is always drawn (rule 3): our reading carries the amber edge an estimate carries. */
import { Fragment, useLayoutEffect, useRef, useState, type ReactNode } from 'react'
import { CUSTOM_BLOCKS } from './custom'
import { InlineTopicChart, type InlineChart } from '../TopicCharts'

type Unit = { text: string }
type Basis = { kind: 'law' | 'record' | 'budget' | 'reading'; label: string }
type Tone = 'bad' | 'good' | 'neutral' | 'muted' | 'other'
type Legend = { key: string; label: string; tone: Tone; pattern?: string }[]

export type Block =
  | { block: 'explain'; place: Place; title: string; tone: 'define' | 'plain' | 'callout'; paragraphs: Unit[] }
  | { block: 'matrix'; place: Place; title: string; rows: string[]; columns: string[]; row_label: string
      col_label: string; legend: Legend; note?: Unit
      row_measures?: Measure[][]; col_measures?: Measure[][]; gaps?: Unit[]
      cells: { verdict: string; title: string; why: Unit; basis: Basis; lands_on?: string; measures: Measure[]
        chips?: { label: string; solidity: Measure['solidity'] }[] }[][] }
  | { block: 'timeline'; place: Place; title: string; periods: string[]; legend: Legend; verdicts: Legend; note?: Unit
      marker?: { after: number; label: string }; event_label: string
      groups: { heading: string; tracks: { label: string; states: (string | null)[]; event: number | null
        cut: boolean; tags: string[]; note?: Unit; verdict?: string; basis?: Basis }[] }[] }
  | { block: 'checks'; place: Place; title: string; columns: string[]; first: string; second: string; note?: Unit
      tone?: 'bad' | 'good'; so?: Unit
      rows: { label: string; why: Unit; marks: number[]; contrast: boolean }[] }
  | { block: 'panels'; place: Place; title: string; note?: Unit; so?: Unit
      cards: { title: string; sub?: Unit; so?: Unit; rows: { label: string; value: string; tone: Tone | null }[] }[] }
  | { block: 'custom'; place: Place; component: string; title: string; data: unknown; alt: string; basis?: Basis; so: Unit }
  | { block: 'chart'; place: Place; spec: InlineChart; so: Unit }
  | { block: 'terms'; place: Place; title: string; items: { term: string; means: Unit; surprises: Unit }[] }
/** A figure on a matrix, with how solid it is (scripts/topic_blocks.py measure()). */
type Measure = { label: string; value: string; solidity: 'published' | 'estimate' | 'gap' }
const SOLID: Record<Measure['solidity'], string> = { published: 'Published', estimate: 'Our estimate', gap: 'Gap in data' }

function Measures({ ms, compact }: { ms?: Measure[]; compact?: boolean }) {
  if (!ms?.length) return null
  return (
    <dl className={`${compact ? 'mt-1.5 pt-1.5' : 'mt-2 pt-2'} border-t space-y-1.5`} style={{ borderColor: 'var(--grid)' }}>
      {ms.map((m, i) => (
        <div key={i} className="min-w-0">
          <dt className="text-[12px] leading-tight" style={muted}>{m.label}</dt>
          <dd className="flex flex-wrap items-baseline gap-x-1.5 text-[13.5px] leading-snug">
            <span className="font-semibold tabular-nums" style={m.solidity === 'gap' ? { color: 'var(--status-bad)' } : undefined}>{m.value}</span>
            <span className="text-[10.5px] px-1 rounded-sm whitespace-nowrap" style={{
              color: 'var(--text-secondary)', background: 'var(--surface-3)',
              boxShadow: m.solidity === 'estimate' ? 'inset 3px 0 0 var(--status-warning)'
                : m.solidity === 'gap' ? 'inset 0 0 0 1px var(--status-bad)' : undefined }}>{SOLID[m.solidity]}</span>
          </dd>
        </div>
      ))}
    </dl>
  )
}

export type Place = 'top' | 'lead' | 'chart' | 'also1' | 'also2' | 'body' | 'end'

const eyebrow = 'text-[11px] font-semibold uppercase tracking-widest'
const muted = { color: 'var(--text-muted)' }
const secondary = { color: 'var(--text-secondary)' }

const TONE: Record<Tone, string> = {
  bad: 'var(--status-bad)', good: 'var(--status-good)', neutral: 'var(--brand)',
  muted: 'var(--axis)', other: 'var(--axis)',
}
const HATCH = 'repeating-linear-gradient(135deg, var(--axis) 0 4px, var(--surface-3) 4px 7px)'
/** A legend entry's swatch: its tone, or a pattern -- 'outline' (budgeted, not spent: an
 *  empty box in the tone), 'half' (another town pays the base, the tone the increase) or
 *  'empty' (LOOKED FOR AND NOT FOUND: a dashed empty box, so a checked absence can never be
 *  mistaken for a filled state -- a solid colour reads as "yes" whatever the legend says). */
function fill(t: Tone | undefined, pattern?: string): React.CSSProperties {
  if (!t) return { background: 'var(--surface-3)' }
  if (pattern === 'empty') return { background: 'transparent', outlineOffset: '-1.5px',
    outline: `1.5px dashed ${t === 'muted' ? 'var(--text-muted)' : TONE[t]}` }
  if (pattern === 'outline') return { background: 'transparent', boxShadow: `inset 0 0 0 2px ${TONE[t]}` }
  if (pattern === 'half') return { background: `linear-gradient(to bottom, transparent 50%, ${TONE[t]} 50%), ${HATCH}` }
  if (t === 'other') return { background: HATCH }
  return { background: TONE[t] }
}

/** **bold** in generated prose, and nothing else. */
function rich(s: string): ReactNode {
  return s.split(/(\*\*[^*]+\*\*)/).map((p, i) =>
    p.startsWith('**') && p.endsWith('**') ? <strong key={i}>{p.slice(2, -2)}</strong> : <Fragment key={i}>{p}</Fragment>)
}

/** What a claim rests on. Our reading is never drawn like the law. */
export function BasisTag({ b }: { b: Basis }) {
  const reading = b.kind === 'reading'
  return (
    <span className="inline-block text-[11px] leading-tight px-1.5 py-0.5 rounded-sm whitespace-nowrap"
      style={{
        color: reading ? 'var(--text-primary)' : 'var(--text-secondary)',
        background: 'var(--surface-3)',
        boxShadow: reading ? 'inset 3px 0 0 var(--status-warning)' : undefined,
      }}>{b.label}</span>
  )
}

function Head({ title }: { title: string }) {
  return <h2 className="text-[19px] font-semibold leading-snug" style={{ textWrap: 'balance' } as React.CSSProperties}>{title}</h2>
}

/** WHAT IT MEANS: every block that shows figures carries one (topic_blocks._so), styled as
 *  the ladder's conclusions style theirs (report.tsx), so the two read as one pattern. */
function So({ u, className = 'mt-3' }: { u?: Unit; className?: string }) {
  return u ? (
    <p className={`${className.includes('text-[') ? '' : 'text-[14.5px] '}leading-snug max-w-3xl ${className}`} style={{ ...secondary, borderColor: 'var(--grid)' }}>
      <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>What it means: </span>
      {rich(u.text)}</p>
  ) : null
}

function Note({ n }: { n?: Unit }) {
  return n ? <p className="text-[14px] mt-3 max-w-3xl" style={secondary}>{rich(n.text)}</p> : null
}

function LegendRow({ legend }: { legend: Legend }) {
  return (
    <ul className="flex flex-wrap gap-x-5 gap-y-1.5 mt-2 text-[13px]">
      {legend.map(l => (
        <li key={l.key} className="inline-flex items-center gap-1.5">
          <span aria-hidden className="inline-block w-5 h-3 rounded-sm" style={fill(l.tone, l.pattern)} />
          {l.label}</li>
      ))}
    </ul>
  )
}

function Explain({ b }: { b: Extract<Block, { block: 'explain' }> }) {
  const box = b.tone !== 'plain'
  return (
    <section className={`mt-6 max-w-3xl ${box ? 'rounded-md px-4 py-3' : ''}`}
      style={b.tone === 'define' ? { background: 'color-mix(in srgb, var(--status-good) 9%, var(--surface-1))' }
        : b.tone === 'callout' ? { background: 'var(--surface-1)', border: '1px solid var(--grid)',
            borderLeft: '5px solid var(--status-bad)' } : undefined}>
      <Head title={b.title} />
      {b.paragraphs.map((p, i) => <p key={i} className="text-[15px] leading-relaxed mt-2">{rich(p.text)}</p>)}
    </section>
  )
}

function MatrixCell({ c, l, col }: { c: Extract<Block, { block: 'matrix' }>['cells'][number][number]
  l?: Legend[number]; col?: string }) {
  return (
    <div className="rounded flex flex-col gap-1 px-3 pt-2 pb-3 min-w-0"
      style={{ background: 'var(--surface-1)', border: '1px solid var(--grid)',
        borderTop: `5px ${l?.tone === 'good' ? 'dashed' : 'solid'} ${TONE[l?.tone ?? 'muted']}`}}>
      {col ? <span className="text-[12px]" style={muted}>{col}</span> : null}
      <span className={eyebrow} style={{ color: TONE[l?.tone ?? 'muted'] }}>{l?.label}</span>
      {c.chips?.length ? (
        <span className="flex flex-wrap gap-1">
          {c.chips.map(ch => (
            <span key={ch.label} className="text-[11.5px] font-semibold px-1.5 py-0.5 rounded-sm whitespace-nowrap"
              style={{ color: 'var(--surface-1)', background: 'var(--text-primary)',
                boxShadow: ch.solidity === 'estimate' ? 'inset 3px 0 0 var(--status-warning)' : undefined }}
              title={SOLID[ch.solidity]}>{ch.label}<span className="font-normal opacity-80"> · {SOLID[ch.solidity]}</span></span>))}
        </span>) : null}
      <span className="text-[14.5px] font-semibold leading-snug">{c.title}</span>
      {c.lands_on ? <span className="text-[13px]" style={muted}>Lands on: <span style={{ color: 'var(--text-primary)' }}>{c.lands_on}</span></span> : null}
      <span className="text-[13.5px] leading-snug mb-1.5">{rich(c.why.text)}</span>
      <span className="mt-auto"><BasisTag b={c.basis} /></span>
      <Measures ms={c.measures} compact />
    </div>
  )
}

/** A DECISION MATRIX: a reader finds their case by position. On a phone the grid would scroll
 *  sideways, so there it stacks -- one row heading, then its cells, each naming its column. */
function Matrix({ b }: { b: Extract<Block, { block: 'matrix' }> }) {
  const tone = Object.fromEntries(b.legend.map(l => [l.key, l]))
  return (
    <section className="mt-8">
      <Head title={b.title} />
      {b.row_label || b.col_label ? (
        <p className="text-[14px] mt-1" style={secondary}>
          {b.row_label ? <>Down the side: {b.row_label}. </> : null}
          {b.col_label ? <>Across the top: {b.col_label}.</> : null}</p>) : null}
      <div className="sm:hidden mt-3 space-y-5">
        {b.col_measures ? (
          <div className="space-y-2">
            {b.columns.map((c, ci) => (
              <div key={c} className="rounded px-3 py-2" style={{ background: 'var(--surface-3)' }}>
                <p className={eyebrow} style={muted}>{c}</p>
                <Measures ms={b.col_measures?.[ci]} compact />
              </div>))}
          </div>) : null}
        {b.rows.map((r, ri) => (
          <div key={r}>
            <p className="text-[16px] font-semibold">{r}</p>
            <Measures ms={b.row_measures?.[ri]} compact />
            <div className="mt-2 space-y-2">
              {b.cells[ri].map((c, ci) => <MatrixCell key={ci} c={c} l={tone[c.verdict]} col={b.columns[ci]} />)}
            </div>
          </div>
        ))}
      </div>
      <div className="hidden sm:block overflow-x-auto mt-3 -mx-1 px-1">
        <div className="grid gap-2" style={{ gridTemplateColumns: `180px repeat(${b.columns.length}, minmax(210px, 1fr))`,
          minWidth: 180 + 220 * b.columns.length }}>
          <div />
          {b.columns.map((c, ci) => (
            <div key={c} className="self-start pb-0.5 min-w-0">
              <div className={eyebrow} style={muted}>{c}</div>
              <Measures ms={b.col_measures?.[ci]} compact />
            </div>))}
          {b.rows.map((r, ri) => (
            <Fragment key={r}>
              <div className="pt-3 pr-2 min-w-0">
                <div className="text-[16px] font-semibold leading-snug">{r}</div>
                <Measures ms={b.row_measures?.[ri]} compact />
              </div>
              {b.cells[ri].map((c, ci) => <MatrixCell key={ci} c={c} l={tone[c.verdict]} />)}
            </Fragment>
          ))}
        </div>
      </div>
      <Note n={b.note} />
      {b.gaps?.length ? (
        <div className="mt-4 max-w-3xl rounded-md px-4 py-3" style={{ boxShadow: 'inset 0 0 0 1px var(--grid)' }}>
          <p className="text-[15px] font-semibold">What the published record does not say</p>
          <p className="text-[13.5px] mt-0.5" style={secondary}>The district holds the answers. Each one would fill in part of the grid above.</p>
          <ol className="mt-2 list-decimal pl-5 space-y-1 text-[14px]">
            {b.gaps.map((g, i) => <li key={i}>{g.text}</li>)}
          </ol>
        </div>) : null}
    </section>
  )
}

/** A STATE TIMELINE. Each row's cells are coloured by the legend; the marker is a dashed
 *  line after one period, placed from the cells' measured positions so it survives reflow. */
function Timeline({ b }: { b: Extract<Block, { block: 'timeline' }> }) {
  const tone = Object.fromEntries(b.legend.map(l => [l.key, l]))
  const verdict = Object.fromEntries((b.verdicts ?? []).map(l => [l.key, l]))
  const n = b.periods.length
  const cols = `repeat(${n}, minmax(0, 1fr))`
  const row = 'grid gap-x-4 gap-y-2 items-center sm:grid-cols-[minmax(0,280px)_minmax(0,1fr)]'
  return (
    <section className="mt-8">
      <Head title={b.title} />
      <LegendRow legend={b.legend} />
      <p className="text-[12px] mt-1" style={muted}>
        ▼ {b.event_label}{b.marker ? <> &nbsp;┆ {b.marker.label}</> : null}</p>
      <div className="overflow-x-auto">
        <div style={{ minWidth: 360 }}>
          {b.groups.map(g => (
            <div key={g.heading} className="mt-5">
              <h3 className="text-[15px] font-semibold">{g.heading}</h3>
              <div className={row}>
                <div className="hidden sm:block" />
                <Strip cols={cols} marker={b.marker?.after}>
                  {b.periods.map((p, i) => <div key={i} className="text-[10.5px] text-center" style={muted}>{p}</div>)}
                </Strip>
              </div>
              {g.tracks.map(t => (
                <div key={t.label} className={`${row} py-3 border-t`} style={{ borderColor: 'var(--grid)' }}>
                  <div className="min-w-0">
                    <p className="text-[14.5px] font-semibold leading-snug">{t.label}</p>
                    {t.note ? <p className="text-[13px] leading-snug mt-0.5" style={secondary}>{rich(t.note.text)}</p> : null}
                    <div className="flex flex-wrap gap-1.5 mt-1.5">
                      {t.verdict && verdict[t.verdict] ? <span className="text-[11px] px-1.5 py-0.5 rounded-sm font-semibold"
                        style={{ color: 'var(--surface-1)', background: TONE[verdict[t.verdict].tone] }}>{verdict[t.verdict].label}</span> : null}
                      {t.basis ? <BasisTag b={t.basis} /> : null}
                      {t.tags.map(x => <span key={x} className="text-[11px] px-1.5 py-0.5 rounded-sm"
                        style={{ boxShadow: 'inset 0 0 0 1px var(--grid)' }}>{x}</span>)}
                    </div>
                  </div>
                  <Strip cols={cols} marker={b.marker?.after} label={`${t.label}: ` + t.states.map((s, i) =>
                    `${b.periods[i]} ${s ? tone[s]?.label : 'nothing'}`).join(', ')}>
                    {t.states.map((s, i) => (
                      <div key={i} className="relative h-7 rounded-sm" title={`${b.periods[i]}: ${s ? tone[s]?.label : 'nothing'}`}
                        style={{ ...fill(s ? tone[s]?.tone : undefined, s ? tone[s]?.pattern : undefined),
                          ...(t.cut && t.event === i ? { borderLeft: '2px solid var(--text-primary)' } : {}) }}>
                        {t.event === i ? <span aria-hidden className="absolute -top-2.5 -left-1 text-[10px] leading-none"
                          style={{ color: 'var(--text-primary)' }}>▼</span> : null}
                      </div>
                    ))}
                  </Strip>
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>
      <Note n={b.note} />
    </section>
  )
}

function Strip({ cols, marker, label, children }: { cols: string; marker?: number; label?: string; children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null)
  const [x, setX] = useState<number | null>(null)
  useLayoutEffect(() => {
    const el = ref.current
    if (!el || marker == null) return
    const place = () => {
      const a = el.children[marker] as HTMLElement | undefined, b2 = el.children[marker + 1] as HTMLElement | undefined
      if (a && b2) setX((a.offsetLeft + a.offsetWidth + b2.offsetLeft) / 2)
    }
    place()
    const ro = new ResizeObserver(place)
    ro.observe(el)
    return () => ro.disconnect()
  }, [marker])
  return (
    <div ref={ref} className="relative grid gap-[3px]" style={{ gridTemplateColumns: cols }}
      role={label ? 'img' : undefined} aria-label={label}>
      {children}
      {x != null ? <span aria-hidden className="absolute -top-0.5 -bottom-0.5 border-l-2 border-dashed pointer-events-none"
        style={{ left: x - 1, borderColor: 'var(--text-muted)' }} /> : null}
    </div>
  )
}

function Checks({ b }: { b: Extract<Block, { block: 'checks' }> }) {
  return (
    <section className="mt-8">
      <Head title={b.title} />
      <div className="overflow-x-auto mt-3">
        <table className="w-full text-[14px] border-collapse" style={{ minWidth: 560 + 76 * b.columns.length }}>
          <thead><tr>
            {[b.first, b.second, ...b.columns].map((h, i) => (
              <th key={h} className={`${eyebrow} px-3 py-2 align-bottom ${i > 1 ? 'text-center' : 'text-left'}`}
                style={{ ...muted, borderBottom: '1px solid var(--grid)' }}>{h}</th>))}
          </tr></thead>
          <tbody>
            {b.rows.map(r => (
              <tr key={r.label} style={r.contrast ? { background: 'color-mix(in srgb, var(--status-good) 9%, transparent)' } : undefined}>
                <td className="px-3 py-2.5 align-top font-semibold w-[30%]" style={{ borderTop: '1px solid var(--grid)' }}>{r.label}</td>
                <td className="px-3 py-2.5 align-top" style={{ borderTop: '1px solid var(--grid)' }}>{rich(r.why.text)}</td>
                {b.columns.map((c, i) => (
                  <td key={c} className="px-2 py-2.5 align-top text-center w-[76px]" style={{ borderTop: '1px solid var(--grid)' }}>
                    {r.marks.includes(i)
                      ? <span aria-label={`marked: ${c}`} style={{ color: r.contrast ? 'var(--text-muted)' : TONE[b.tone ?? 'bad'], fontSize: 17 }}>
                          {r.contrast ? '—' : '●'}</span> : null}
                  </td>))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Note n={b.note} />
      <So u={b.so} />
    </section>
  )
}

function Panels({ b }: { b: Extract<Block, { block: 'panels' }> }) {
  return (
    <section className={`mt-8 ${b.cards.length > 2 ? '' : 'max-w-3xl'}`}>
      <Head title={b.title} />
      <div className={`grid gap-4 mt-3 ${['', '', 'sm:grid-cols-2', 'md:grid-cols-3', 'sm:grid-cols-2 lg:grid-cols-4'][b.cards.length]}`}>
        {b.cards.map(c => (
          <div key={c.title} className="rounded-md px-4 py-3 min-w-0" style={{ background: 'var(--surface-1)', border: '1px solid var(--grid)' }}>
            <p className="text-[16px] font-semibold">{c.title}</p>
            {c.sub ? <p className="text-[13.5px] mt-0.5 mb-2" style={secondary}>{rich(c.sub.text)}</p> : null}
            {c.rows.map(r => (
              <div key={r.label} className="flex justify-between gap-3 py-1.5 text-[14px] border-t" style={{ borderColor: 'var(--grid)' }}>
                <span style={secondary}>{r.label}</span>
                <span className="font-semibold whitespace-nowrap tabular-nums" style={r.tone ? { color: TONE[r.tone] } : undefined}>{r.value}</span>
              </div>))}
            <So u={c.so} className="mt-2 pt-2 border-t text-[13.5px]" />
          </div>
        ))}
      </div>
      <Note n={b.note} />
      <So u={b.so} />
    </section>
  )
}

function Custom({ b }: { b: Extract<Block, { block: 'custom' }> }) {
  const C = CUSTOM_BLOCKS[b.component]
  if (!C) return null
  // A control, not a chart (the FY breakdown's year picker): drawn without the block's heading
  // and its "what it means" line, which a control has nothing to put in.
  if ((b.data as { bare?: boolean } | null)?.bare) return <section className="mt-6"><C data={b.data} alt={b.alt} /></section>
  return (
    <section className="mt-8">
      <Head title={b.title} />
      {b.basis ? <p className="mt-1"><BasisTag b={b.basis} /></p> : null}
      <div className="mt-3"><C data={b.data} alt={b.alt} /></div>
      <So u={b.so} />
    </section>
  )
}

function Terms({ b }: { b: Extract<Block, { block: 'terms' }> }) {
  return (
    <section className="mt-8 max-w-3xl">
      <Head title={b.title} />
      <dl className="mt-3 grid gap-x-6 gap-y-4 sm:grid-cols-2">
        {b.items.map(t => (
          <div key={t.term} className="pl-3 border-l-2" style={{ borderColor: 'var(--grid)' }}>
            <dt className="text-[15px] font-semibold">{t.term}</dt>
            <dd className="text-[14px] leading-snug mt-0.5" style={secondary}>{t.means.text}</dd>
            <dd className="text-[14px] leading-snug mt-1"><span className="font-semibold">Why it surprises: </span>{t.surprises.text}</dd>
          </div>))}
      </dl>
    </section>
  )
}

/** One block. A topic page draws its blocks one at a time, in its `flow` (scripts/topic.py). */
export function OneBlock({ b }: { b: Block }) {
  switch (b.block) {
    case 'explain': return <Explain b={b} />
    case 'matrix': return <Matrix b={b} />
    case 'timeline': return <Timeline b={b} />
    case 'checks': return <Checks b={b} />
    case 'panels': return <Panels b={b} />
    case 'custom': return <Custom b={b} />
    case 'chart': return <div><InlineTopicChart c={b.spec} /><So u={b.so} /></div>
    case 'terms': return <Terms b={b} />
  }
}

/** Every block at one place on a HUB, in the order the generator gave. */
export function Blocks({ blocks, place }: { blocks?: Block[]; place: Place }) {
  const bs = (blocks ?? []).filter(b => b.place === place)
  if (!bs.length) return null
  return <>{bs.map((b, i) => <OneBlock key={i} b={b} />)}</>
}
