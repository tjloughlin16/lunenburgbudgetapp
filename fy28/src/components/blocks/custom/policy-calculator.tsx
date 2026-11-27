/** THE POLICY CALCULATOR: a dial for every free cash rule, set to today's rules or the state's
 *  draft, applied to the latest certified free cash, with every starting figure editable.
 *
 *  TJ, 27 November 2026: "a 'Policy calculator' that the finance committee can use to adjust to
 *  show the outcomes towards free cash, that shows todays settings, policy suggestions, etc" --
 *  and then: "i assumed i would have dials to move". So every rule is a dial, and the two rule
 *  sets are two settings of the same dials. Each dial marks where both sit on it, so moving away
 *  from either is visible.
 *
 *  LAYOUT. Equal things side by side, never a tall column beside a short one (TJ: "the right
 *  column with lots of info, and the left column with 1 item... wasted space"): the dials are a
 *  grid of like cards, each carrying the dollars it produces, and the outcomes a row of like
 *  charts.
 *
 *  THE STABILIZATION CHARTS ARE BULLET CHARTS: the balance as a bar (before, plus this year's
 *  deposit), the draft's range shaded behind it and today's line across it, each labelled on the
 *  chart, a percentage axis under it, and one sentence saying where the result sits against each.
 *
 *  THE ONE EXCEPTION TO "A COMPONENT FORMATS NOTHING". Every default, dial setting, range and band
 *  comes from the payload (scripts/build_policy_calculator.py asserts each rule verbatim on the page
 *  that prints it). The results depend on what the reader moves, so they are computed and formatted
 *  here; the arithmetic is policy-calculator-math.ts, which the generator's --check runs on both
 *  settings against its own Python (rule 9).
 *
 *  RULE 7: every number is tagged PUBLISHED, YOUR INPUT or OUR ARITHMETIC. RULE 8: the two rule
 *  sets are drawn at the same weight in greys; no status colour appears, and nothing says which
 *  setting is better. */
import { useMemo, useState } from 'react'
import type { CustomProps } from './index'
import { after, allocate, type DialKey, type Dials, type Inputs, type UseKey, type Uses } from './policy-calculator-math'

type Input = { key: keyof Inputs; label: string; value: number; text: string; source: string }
type Setting = { value: number | null; source: string | null; quote: string | null }
type Dial = { key: DialKey; label: string; unit: 'fc' | 'budget' | 'usd'; feeds: UseKey; min: number; max: number; step: number; today: Setting; draft: Setting; practice: Setting }
type PresetKey = 'today' | 'practice' | 'draft'
type Preset = { key: PresetKey; label: string; source: string; settings: Dials }
type Data = {
  inputs: Input[]; dials: Dial[]; capital_range: [number, number]; uses: { key: UseKey; label: string }[]; presets: Preset[]; practice_discretionary: Disc[]
  rules: { today: { floor: number; cap: number }; draft: { cap: number; stab_annual: [number, number] } }
  bands: { general_draft: [number, number]; special_draft: [number, number]; fc_draft: [number, number]; general_today: number }
  defaults: Inputs
  text: Record<'audit_note' | 'budget_note' | 'cap_reading' | 'annual_note' | 'floors_note' | 'order_note', string>
}
// No thread-1: it is the site's coral, and a coral beside a rule reads as a warning (rule 8).
const COLOR: Record<UseKey, string> = {
  keep: 'var(--thread-3)', general: 'var(--thread-2)', special: 'var(--thread-4)', opeb: 'var(--thread-5)',
  capital: 'var(--text-secondary)', other: 'var(--text-muted)', left: 'var(--surface-3)',
}
const TODAY = 'var(--text-primary)', DRAFT = 'var(--text-muted)', PRACTICE = 'var(--text-secondary)'

const usd = (n: number) => (n < 0 ? '-' : '') + '$' + Math.abs(Math.round(n)).toLocaleString('en-US')
const pct = (x: number, dp = 1) => (x * 100).toFixed(dp) + '%'
const pctTrim = (x: number) => { const v = x * 100; return (Number.isInteger(Math.round(v * 100) / 100) ? v.toFixed(0) : v.toFixed(2).replace(/0$/, '')) + '%' }
const secondary = { color: 'var(--text-secondary)' }
const muted = { color: 'var(--text-muted)' }
const card = { background: 'var(--surface-1)', border: '1px solid var(--grid)' }

type Kind = 'published' | 'input' | 'ours'
function Tag({ k }: { k: Kind }) {
  const label = k === 'published' ? 'Published' : k === 'input' ? 'Your input' : 'Our arithmetic'
  return (
    <span className="inline-block text-[10.5px] leading-tight px-1.5 py-0.5 rounded-sm whitespace-nowrap align-middle"
      style={{
        color: k === 'published' ? 'var(--text-secondary)' : 'var(--text-primary)',
        background: k === 'input' ? 'transparent' : 'var(--surface-3)',
        border: k === 'input' ? '1px dashed var(--text-muted)' : '1px solid transparent',
        boxShadow: k === 'ours' ? 'inset 3px 0 0 var(--status-warning)' : undefined,
      }}>{label}</span>
  )
}

function dialText(d: Dial, v: number, fc: number) {
  if (d.unit === 'usd') return d.key === 'other_cap' && v >= fc ? 'No cap' : usd(v)
  return pctTrim(v) + (d.unit === 'budget' ? ' of the budget' : ' of free cash')
}
function settingText(d: Dial, s: Setting, voted = false) {
  if (s.value === null) return d.key === 'other_cap' ? 'no cap' : voted ? 'none voted' : 'no rule'
  if (!s.quote) return voted ? 'none voted' : 'no rule'
  return d.unit === 'usd' ? (d.key === 'special_dollars' ? 'set in capital planning' : usd(s.value)) : pctTrim(s.value)
}

// THREE LAYERS (TJ, 27 November 2026: "we have the pot amount. THATS not what these dials change.
// THEN, we have the 'off the top' things that are forced in policy. And then, whatever doesnt come off
// the top, is 'discretionary'"). The free cash is the POT, an input no dial moves; the dials are what a
// rule takes OFF THE TOP; the rest is DISCRETIONARY, Town Meeting's to decide. Under Today in practice
// the discretionary part is drawn split into how Town Meeting actually used it, in lighter shades.
const DISCRETIONARY = 'Discretionary'
type Disc = { key: 'capital' | 'other' | 'stayed'; label: string; share: number }
const DISC_COLOR: Record<Disc['key'], string> = { capital: 'var(--text-secondary)', other: 'var(--text-muted)', stayed: 'var(--surface-3)' }

/** One setting's split of the pot: off the top, then discretionary. */
function SplitBar({ label, u, fc, strong, names, disc }: { label: string; u: Uses; fc: number; strong: boolean; names: Record<UseKey, string>; disc?: Disc[] }) {
  const keys: UseKey[] = ['keep', 'general', 'special', 'opeb', 'capital', 'other']
  const top = keys.map(k => ({ k, v: Math.max(0, u[k]) })).filter(p => p.v > 0)
  // Shown as the pot less the discretionary part, each rounded once, so the two always foot to the pot.
  const offTop = Math.round(fc) - Math.round(u.left)
  const used = disc?.map(q => ({ ...q, v: q.share * fc })).filter(q => q.v > 0)
  const W = (v: number) => `${(100 * v) / fc}%`
  return (
    <div className="mt-3" style={{ opacity: strong ? 1 : 0.6 }}>
      <div className="flex items-baseline justify-between gap-2 text-[13px]">
        <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>{label}</span>
        <span style={secondary}>{usd(offTop)} off the top · <span style={{ color: 'var(--text-primary)' }}>{usd(u.left)} discretionary</span></span>
      </div>
      <div className="mt-1 flex h-7 w-full overflow-hidden rounded-sm" style={{ background: 'var(--surface-2)' }}
        role="img" aria-label={`${label}: off the top ` + top.map(p => `${names[p.k]} ${usd(p.v)}`).join(', ') + `; discretionary ${usd(u.left)}`}>
        {top.map(p => (
          <div key={p.k} title={`Off the top, ${names[p.k]}: ${usd(p.v)}`}
            style={{ width: W(p.v), background: COLOR[p.k], borderRight: '1px solid var(--surface-1)' }} />
        ))}
        {used?.length ? used.map(q => (
          <div key={q.key} title={`Discretionary, ${q.label.toLowerCase()}: ${usd(q.v)}`}
            style={{ width: W(q.v), background: DISC_COLOR[q.key], opacity: q.key === 'stayed' ? 1 : 0.45,
              borderRight: '1px solid var(--surface-1)', boxShadow: q.key === 'stayed' ? 'inset 0 0 0 1px var(--grid)' : undefined }} />
        )) : u.left > 0 ? <div title={`Discretionary: ${usd(u.left)}`} style={{ width: W(u.left), background: COLOR.left, boxShadow: 'inset 0 0 0 1px var(--grid)' }} /> : null}
      </div>
      {used?.length ? <div className="mt-1 text-[12px]" style={secondary}>Of the discretionary part, at the same shares: {used.map(q => `${q.label.toLowerCase()} ${usd(q.v)}`).join(', ')}.</div> : null}
    </div>
  )
}

/** A dial: the setting, the dollars it produced, and where both rule sets sit on it. */
function DialCard({ d, v, amount, fc, onChange, range }: { d: Dial; v: number; amount?: number; fc: number; onChange: (v: number) => void; range?: [number, number] }) {
  const max = d.unit === 'usd' ? Math.max(d.max, fc) : d.max
  const X = (n: number) => `${Math.max(0, Math.min(100, (100 * (n - d.min)) / (max - d.min)))}%`
  const marks = ([['Today', d.today, TODAY], ['In practice', d.practice, PRACTICE], ['Draft', d.draft, DRAFT]] as const)
    .filter(([, s]) => s.quote && s.value !== null && !(d.key === 'special_dollars'))
  return (
    <div className="rounded-md p-3 flex flex-col" style={card}>
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-[13.5px] font-semibold" style={{ color: 'var(--text-primary)' }}>
          <span className="inline-block w-2.5 h-2.5 mr-1.5 rounded-sm align-middle" style={{ background: COLOR[d.feeds] }} />{d.label}</span>
        {amount !== undefined ? <span className="text-[13.5px] tabular-nums font-semibold" style={{ color: 'var(--text-primary)' }}>{usd(amount)}</span> : null}
      </div>
      <div className="mt-0.5 text-[13px] tabular-nums" style={secondary}>{dialText(d, v, fc)}</div>
      <div className="relative mt-2 h-8">
        {range ? <div className="absolute top-[13px] h-1.5 rounded-sm" title="The draft's range"
          style={{ left: X(range[0]), width: `calc(${X(range[1])} - ${X(range[0])})`, background: DRAFT, opacity: 0.45 }} /> : null}
        {marks.map(([n, s, c]) => (
          <div key={n} className="absolute top-0 h-8 pointer-events-none" style={{ left: X(s.value!) }}>
            <div className="h-2.5 w-0 -ml-px" style={{ borderLeft: `2px ${n === 'In practice' ? 'dotted' : 'solid'} ${c}` }} />
          </div>
        ))}
        <input type="range" className="absolute inset-x-0 top-[6px] w-full" min={d.min} max={max} step={d.step}
          value={Math.min(v, max)} onChange={e => onChange(Number(e.target.value))} aria-label={d.label} />
      </div>
      <div className="mt-auto pt-1 flex flex-wrap gap-x-3 text-[11.5px]" style={muted}>
        <span title={d.today.quote ?? undefined}><span className="inline-block w-2 h-0.5 mr-1 align-middle" style={{ background: TODAY }} />Today: {settingText(d, d.today)}</span>
        <span title={d.practice.quote ?? undefined}><span className="inline-block w-2 h-0 mr-1 align-middle" style={{ borderTop: `2px dotted ${PRACTICE}` }} />In practice: {settingText(d, d.practice, true)}</span>
        <span title={d.draft.quote ?? undefined}><span className="inline-block w-2 h-0.5 mr-1 align-middle" style={{ background: DRAFT }} />Draft: {settingText(d, d.draft)}{range ? ` (${pctTrim(range[0])} to ${pctTrim(range[1])})` : ''}</span>
      </div>
    </div>
  )
}

/** A BULLET CHART: the balance before and this year's deposit as a bar, against the draft's range
 *  (shaded) and today's line, every part labelled on the chart. */
function Bullet({ title, before, after: a, deposit, band, line, verdict }: {
  title: string; before: number; after: number; deposit: number
  band?: { lo: number; hi: number; label: string }; line?: { at: number; label: string }; verdict: string
}) {
  const W = 320, top = 34, bh = 16
  const hi = Math.max(a, before, band?.hi ?? 0, line?.at ?? 0) * 1.12
  const step = hi > 0.16 ? 0.04 : 0.02
  const max = Math.ceil(hi / step) * step
  const X = (v: number) => (W * v) / max
  const ticks = Array.from({ length: Math.round(max / step) + 1 }, (_, i) => i * step)
  const anchor = (x: number) => (x > W * 0.6 ? 'end' : 'start')
  return (
    <div className="rounded-md p-3 flex flex-col" style={card}>
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-[13.5px] font-semibold" style={{ color: 'var(--text-primary)' }}>{title}</span>
        <Tag k="ours" />
      </div>
      <div className="mt-1 text-[22px] font-semibold tabular-nums" style={{ color: 'var(--text-primary)' }}>
        {pct(a, 2)} <span className="text-[13px] font-normal" style={secondary}>of the budget</span>
      </div>
      <p className="text-[12.5px]" style={secondary}>{deposit > 0 ? `${pct(before, 2)} before this year's ${usd(deposit)} deposit` : 'No deposit this year'}</p>
      <svg viewBox={`-4 0 ${W + 8} ${top + bh + 22}`} className="mt-2 w-full h-auto" role="img"
        aria-label={`${title}: ${pct(a, 2)} of the budget. ${verdict}`}>
        {band ? <g>
          <rect x={X(band.lo)} y={top - 6} width={X(band.hi) - X(band.lo)} height={bh + 12} fill={DRAFT} opacity={0.22} />
          {/* Labelled at the range's far end, so it never sits on today's line at its near end. */}
          <text x={X(band.hi) - 3} y={top - 10} fontSize="11" textAnchor="end" fill="var(--text-secondary)">{band.label}</text>
        </g> : null}
        <rect x={0} y={top} width={X(before)} height={bh} fill="var(--text-secondary)"><title>{`Before: ${pct(before, 2)}`}</title></rect>
        <rect x={X(before)} y={top} width={Math.max(0, X(a) - X(before))} height={bh} fill="var(--thread-2)"><title>{`This year's deposit: ${usd(deposit)}`}</title></rect>
        {line ? <g>
          <line x1={X(line.at)} x2={X(line.at)} y1={band ? top - 24 : top - 8} y2={top + bh + 4} stroke={TODAY} strokeWidth={2} />
          <text x={X(line.at) + (anchor(X(line.at)) === 'end' ? -4 : 4)} y={band ? top - 26 : top - 10} fontSize="11" fontWeight="600"
            textAnchor={anchor(X(line.at))} fill="var(--text-primary)">{line.label}</text>
        </g> : null}
        {ticks.map(t => (
          <g key={t}>
            <line x1={X(t)} x2={X(t)} y1={top + bh + 4} y2={top + bh + 8} stroke="var(--grid)" />
            <text x={X(t)} y={top + bh + 19} fontSize="10.5" textAnchor={t === 0 ? 'start' : t >= max - 1e-9 ? 'end' : 'middle'} fill="var(--text-muted)">{pctTrim(t)}</text>
          </g>
        ))}
      </svg>
      <p className="mt-1 text-[13px] leading-snug" style={{ color: 'var(--text-primary)' }}>{verdict}</p>
    </div>
  )
}

function Figure({ title, value, sub }: { title: string; value: string; sub: string }) {
  return (
    <div className="rounded-md p-3" style={card}>
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-[13.5px] font-semibold" style={{ color: 'var(--text-primary)' }}>{title}</span>
        <Tag k="ours" />
      </div>
      <div className="mt-1 text-[22px] font-semibold tabular-nums" style={{ color: 'var(--text-primary)' }}>{value}</div>
      <p className="mt-0.5 text-[12.5px]" style={secondary}>{sub}</p>
    </div>
  )
}

const against = (v: number, lo: number, hi?: number) =>
  hi === undefined ? (v >= lo ? 'above' : 'below') : v < lo ? 'below' : v > hi ? 'above' : 'inside'

type Mode = PresetKey | 'mine'
type Mine = { dials: Dials; from: PresetKey }
const STORE = 'policy-calculator:your-settings'

/** Your settings from this browser, if they are whole and every dial is a number; otherwise none. */
function loadMine(d: Data): Mine | null {
  try {
    const m = JSON.parse(localStorage.getItem(STORE) ?? 'null') as Mine | null
    if (!m || !d.presets.some(p => p.key === m.from)) return null
    return d.dials.every(q => Number.isFinite(m.dials?.[q.key])) ? m : null
  } catch { return null }
}
function saveMine(m: Mine | null) {
  try { if (m) localStorage.setItem(STORE, JSON.stringify(m)); else localStorage.removeItem(STORE) } catch { /* a convenience */ }
}

export default function PolicyCalculator({ data, alt }: CustomProps) {
  const d = data as Data
  const [x, setX] = useState<Inputs>(d.defaults)
  // YOUR SETTINGS ARE A SLOT, NOT A STATE OF THE DIALS (TJ, 27 November 2026: "if i adjust, i want
  // to click the draft, etc but be able to pop back to what i set"). Moving a dial saves the dials as
  // they then stand; choosing a rule set shows it without discarding them; Clear discards them. Kept
  // in this browser so a reload keeps them -- a convenience, so storage that fails costs nothing.
  const [mine, setMine] = useState<Mine | null>(() => loadMine(d))
  const [mode, setMode] = useState<Mode>(() => (loadMine(d) ? 'mine' : 'today'))
  const names = useMemo(() => Object.fromEntries(d.uses.map(u => [u.key, u.label])) as Record<UseKey, string>, [d.uses])

  // A preset's "no cap" is the whole free cash, so it follows the free cash the reader types.
  const settingsOf = (p: Preset): Dials => ({ ...p.settings, other_cap: p.settings.other_cap >= d.defaults.fc ? Math.max(x.fc, p.settings.other_cap) : p.settings.other_cap })
  const base = mode === 'mine' ? (mine?.from ?? 'today') : mode
  const preset = d.presets.find(p => p.key === base)!
  const dials: Dials = mode === 'mine' && mine ? mine.dials : settingsOf(preset)
  const keep = (m: Mine | null) => { setMine(m); saveMine(m) }
  const move = (k: DialKey, v: number) => {
    keep({ dials: { ...dials, [k]: v }, from: base }); setMode('mine')
  }
  const clear = () => { keep(null); setMode(base) }
  const split = (k: PresetKey) => allocate(x, settingsOf(d.presets.find(p => p.key === k)!))
  const u = allocate(x, dials)
  const a = after(x, u)
  const before = after(x, allocate(x, { ...dials, general_target: 0, opeb: 0, special_dollars: 0, general: 0, special: 0, keep: 0, capital: 0, other: 0 }))
  const changed = (k: keyof Inputs) => x[k] !== d.defaults[k]
  const anyChanged = (Object.keys(d.defaults) as (keyof Inputs)[]).some(changed)
  const setInput = (k: keyof Inputs, v: number) => setX(o => ({ ...o, [k]: Number.isFinite(v) ? v : 0 }))
  const label = mode === 'mine' ? `Your settings (from ${preset.label.toLowerCase()})` : preset.label
  const btn = (on: boolean) => on
    ? { background: 'var(--text-primary)', color: 'var(--surface-1)' }
    : { background: 'var(--surface-2)', color: 'var(--text-primary)' }

  const b = d.bands, r = d.rules
  const gVerdict = `${a.general_pct >= b.general_today ? 'At or above' : 'Below'} today's ${pctTrim(b.general_today)} minimum; ${against(a.general_pct, b.general_draft[0], b.general_draft[1])} the draft's ${pctTrim(b.general_draft[0])} to ${pctTrim(b.general_draft[1])} range.`
  const sVerdict = `${against(a.special_pct, b.special_draft[0], b.special_draft[1]).replace(/^./, c => c.toUpperCase())} the draft's ${pctTrim(b.special_draft[0])} to ${pctTrim(b.special_draft[1])} range. Today's rules set no target for these funds.`
  const aVerdict = `${a.all_pct > r.today.cap ? 'Above' : 'At or below'} today's ${pctTrim(r.today.cap)} ceiling on all funds. This year's deposits are ${pct(a.deposits_pct, 2)} of the budget, against the draft's ${pctTrim(r.draft.cap)} cap on deposits.`

  return (
    <div className="w-full max-w-5xl min-w-0" aria-label={alt}>
      {/* PINNED WHILE THE CALCULATOR IS ON SCREEN: which setting is showing, the switch between them,
          and what the dials leave for Town Meeting (TJ: "a pinned header ... that shows the amount of
          money left for town meeting appropriation from the dials set"). */}
      <div className="sticky z-20 -mx-4 px-4 sm:mx-0 sm:px-3 py-2 sm:rounded-b-md border-b"
        style={{ top: 'var(--header-h)', background: 'var(--surface-2)', borderColor: 'var(--grid)' }}>
        <div className="flex flex-wrap items-center gap-1.5">
          {d.presets.map(p => (
            <button key={p.key} type="button" aria-pressed={mode === p.key} onClick={() => setMode(p.key)}
              className="px-2.5 py-1 rounded-md text-[13.5px] font-medium" style={btn(mode === p.key)}>{p.label}</button>
          ))}
          {mine ? <>
            <button type="button" aria-pressed={mode === 'mine'} onClick={() => setMode('mine')}
              className="px-2.5 py-1 rounded-md text-[13.5px] font-medium"
              style={{ ...btn(mode === 'mine'), outline: mode === 'mine' ? undefined : '1px dashed var(--text-muted)' }}>Your settings</button>
            <button type="button" onClick={clear} className="px-2 py-1 rounded-md text-[12.5px] underline"
              style={{ color: 'var(--text-secondary)' }} aria-label="Clear your settings">Clear</button>
          </> : null}
          <span className="ml-auto text-right leading-tight">
            <span className="block text-[11.5px]" style={muted}>{DISCRETIONARY}</span>
            <span className="text-[18px] font-semibold tabular-nums" style={{ color: 'var(--text-primary)' }}>{usd(u.left)}</span>
            <span className="ml-1.5 text-[12px] tabular-nums" style={secondary}>{pct(u.left / x.fc, 0)}</span>
          </span>
        </div>
      </div>
      <p className="mt-2 text-[12.5px]" style={muted}>{mode === 'mine' ? 'Your settings, moved from ' + preset.label.toLowerCase() + ': ' + preset.source : preset.source}.
        {mine && mode !== 'mine' ? ' Your settings are kept; moving a dial here starts them again from this rule set.' : ''}
        {!mine ? ' Move any dial to save your own settings.' : ''}</p>

      {/* THE SIGNATURE: what each setting does with the same free cash */}
      <div className="mt-3 rounded-md p-3" style={card}>
        <div className="flex items-baseline justify-between gap-2">
          <span className="text-[13.5px]" style={secondary}>The pot: {usd(x.fc)} of free cash, split off the top and discretionary</span>
          <Tag k="ours" />
        </div>
        {d.presets.map(p => <SplitBar key={p.key} label={p.label} u={split(p.key)} fc={x.fc} strong={mode === p.key} names={names} disc={p.key === 'practice' ? d.practice_discretionary : undefined} />)}
        {mine ? <SplitBar label="Your settings" u={allocate(x, mine.dials)} fc={x.fc} strong={mode === 'mine'} names={names} /> : null}
        <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[12px]" style={secondary}>
          {d.uses.map(q => (
            <li key={q.key}><span className="inline-block w-2.5 h-2.5 mr-1.5 align-middle rounded-sm"
              style={{ background: COLOR[q.key], boxShadow: q.key === 'left' ? 'inset 0 0 0 1px var(--grid)' : undefined }} />{q.label}</li>
          ))}
        </ul>
      </div>

      {/* THE DIALS */}
      <h3 className="mt-6 text-[16px] font-semibold">Off the top: the dials <span className="text-[13px] font-normal" style={muted}>· {label}</span></h3>
      <p className="mt-0.5 text-[12.5px]" style={muted}>{d.text.order_note} {d.text.floors_note}</p>
      <div className="mt-2 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {d.dials.map(q => (
          <DialCard key={q.key} d={q} v={dials[q.key]} fc={x.fc} amount={q.key === 'other_cap' ? undefined : u.by[q.key]}
            range={q.key === 'capital' ? d.capital_range : undefined}
            onChange={v => move(q.key, v)} />
        ))}
      </div>
      <div className="mt-3 rounded-md p-3 flex flex-wrap items-baseline justify-between gap-2" style={{ ...card, background: 'var(--surface-2)' }}>
        <span className="text-[15px] font-semibold" style={{ color: 'var(--text-primary)' }}>{DISCRETIONARY}<span className="block text-[12.5px] font-normal" style={secondary}>What no rule takes off the top: Town Meeting decides it, capital included</span></span>
        <span className="text-[22px] font-semibold tabular-nums" style={{ color: 'var(--text-primary)' }}>{usd(u.left)}
          <span className="ml-2 text-[13px] font-normal" style={secondary}>{pct(u.left / x.fc, 1)} of the free cash</span></span>
        {u.short > 0 ? <p className="w-full text-[12.5px]" style={secondary}>The dials ask for {usd(u.short)} more than the free cash holds; the last dials in the order get less than they ask.</p> : null}
      </div>

      {/* THE OUTCOMES */}
      <h3 className="mt-6 text-[16px] font-semibold">What it does to the balances</h3>
      <div className="mt-2 grid gap-3 lg:grid-cols-3">
        <Bullet title="General stabilization" before={before.general_pct} after={a.general_pct} deposit={u.general}
          band={{ lo: b.general_draft[0], hi: b.general_draft[1], label: `Draft: ${pctTrim(b.general_draft[0])} to ${pctTrim(b.general_draft[1])}` }}
          line={{ at: b.general_today, label: `Today: at least ${pctTrim(b.general_today)}` }} verdict={gVerdict} />
        <Bullet title="Special purpose stabilization" before={before.special_pct} after={a.special_pct} deposit={u.special}
          band={{ lo: b.special_draft[0], hi: b.special_draft[1], label: `Draft: ${pctTrim(b.special_draft[0])} to ${pctTrim(b.special_draft[1])}` }} verdict={sVerdict} />
        <Bullet title="All stabilization funds" before={before.all_pct} after={a.all_pct} deposit={u.general + u.special}
          line={{ at: r.today.cap, label: `Today: at most ${pctTrim(r.today.cap)}` }} verdict={aVerdict} />
      </div>
      <p className="mt-2 text-[12px]" style={muted}>{d.text.cap_reading}</p>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <Figure title="Retiree health trust" value={usd(a.opeb_trust)}
          sub={`${pct(a.funded, 1)} of the ${usd(x.opeb_liability)} liability, from ${pct(before.funded, 1)}`} />
        <Figure title="Next year's starting free cash" value={usd(a.next_fc)}
          sub={a.next_fc > 0 ? `${pct(a.next_fc_pct, 2)} of the budget, kept back before the next certification. The draft's target for a certification is ${pctTrim(b.fc_draft[0])} to ${pctTrim(b.fc_draft[1])}.`
            : 'Nothing is kept back by rule; whatever Town Meeting leaves unspent carries over.'} />
      </div>

      {/* THE STARTING FIGURES */}
      <details className="mt-5 rounded-md" style={{ border: '1px solid var(--grid)' }}>
        <summary className="cursor-pointer px-3 py-2 text-[14px] font-semibold">The figures it starts from{anyChanged ? ' (edited)' : ''}</summary>
        <div className="px-3 pb-3">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {d.inputs.map(i => (
              <label key={i.key} className="block text-[13px]">
                <span className="flex items-baseline justify-between gap-2"><span style={secondary}>{i.label}</span>
                  <Tag k={changed(i.key) ? 'input' : 'published'} /></span>
                <Money value={x[i.key]} onChange={v => setInput(i.key, v)} />
                <span className="mt-0.5 block text-[12px]" style={muted}>{changed(i.key) ? `Published: ${i.text}. ${i.source}` : i.source}</span>
              </label>
            ))}
          </div>
          {anyChanged ? <button type="button" onClick={() => setX(d.defaults)} className="mt-3 px-3 py-1 rounded-md text-[13px]"
            style={{ background: 'var(--surface-2)', color: 'var(--text-primary)' }}>Back to the published figures</button> : null}
          <ul className="mt-3 space-y-1 text-[12.5px]" style={muted}>
            <li>{d.text.audit_note}</li>
            <li>{d.text.budget_note}</li>
            <li>{d.text.annual_note} At this budget that is {usd(r.draft.stab_annual[0] * x.budget)} or {usd(r.draft.stab_annual[1] * x.budget)} a year.</li>
          </ul>
        </div>
      </details>

      {/* THE RULES, as printed */}
      <details className="mt-3 rounded-md" style={{ border: '1px solid var(--grid)' }}>
        <summary className="cursor-pointer px-3 py-2 text-[14px] font-semibold">The rules behind each dial, as printed</summary>
        <ul className="px-3 pb-3 space-y-2">
          {d.dials.flatMap(q => ([['Today', q.today], ['In practice', q.practice], ['Draft', q.draft]] as const)
            .filter(([, s]) => s.quote)
            .map(([n, s]) => (
              <li key={q.key + n} className="text-[13px]">
                <span className="font-semibold">{q.label}, {n.toLowerCase()}: </span>
                <q style={{ color: 'var(--text-primary)' }}>{s.quote}</q>
                <span className="block text-[12px]" style={muted}>{s.source}</span>
              </li>)))}
        </ul>
      </details>
    </div>
  )
}

/** A dollar field: shows commas, accepts anything with digits in it. */
function Money({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  const [draft, setDraft] = useState<string | null>(null)
  return (
    <input inputMode="decimal" className="mt-1 block w-full rounded-md px-2 py-1.5 text-[15px] tabular-nums"
      style={{ background: 'var(--surface-2)', color: 'var(--text-primary)', border: '1px solid var(--grid)' }}
      value={draft ?? usd(value)}
      onFocus={() => setDraft(String(Math.round(value)))}
      onChange={e => { setDraft(e.target.value); const n = Number(e.target.value.replace(/[^0-9.]/g, '')); if (e.target.value.trim() !== '') onChange(n) }}
      onBlur={() => setDraft(null)} />
  )
}
