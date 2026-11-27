/** THE POLICY CALCULATOR: today's free cash rules, the state's draft, or the reader's own shares,
 *  applied to the latest certified free cash, with every input editable.
 *
 *  TJ, 27 November 2026: "a 'Policy calculator' that the finance committee can use to adjust to
 *  show the outcomes towards free cash, that shows todays settings, policy suggestions, etc".
 *
 *  THE ONE EXCEPTION TO "A COMPONENT FORMATS NOTHING". Every default, every share and every band
 *  comes from the payload (scripts/build_policy_calculator.py, which asserts each rule verbatim on
 *  the page that prints it). But the results depend on what the reader types, so they can only be
 *  computed and formatted here. The arithmetic lives in policy-calculator-math.ts, and the
 *  generator's --check runs that file on the defaults against its own Python, so a figure this
 *  component draws at the defaults is a figure checked by script (rule 9).
 *
 *  RULE 7, ON EVERY NUMBER. Each one carries what it is: PUBLISHED (read off a document), YOUR
 *  INPUT (the reader changed it), or OUR ARITHMETIC (a rule applied to those). Our arithmetic is
 *  drawn the way the site draws our reading: an amber edge, never the look of a record.
 *
 *  RULE 8. Neither rule set is the answer. Both are drawn in series colours, side by side, at the
 *  same weight; no status colour (red, green) appears anywhere, and nothing says which is better. */
import { useMemo, useState } from 'react'
import type { CustomProps } from './index'
import { after, custom, draftShares, uses, type After, type Inputs, type Params, type Shares, type UseKey, type Uses } from './policy-calculator-math'

type Input = { key: keyof Inputs; label: string; value: number; text: string; source: string; basis: 'published' | 'input' }
type Rule = { key: string; value: number | null; source: string; quote: string }
type Preset = { key: 'today' | 'draft' | 'custom'; label: string; source: string; rules: Rule[] }
type Data = {
  inputs: Input[]; uses: { key: UseKey; label: string }[]; presets: Preset[]; params: Params
  defaults: Inputs
  text: { audit_note: string; budget_note: string; cap_reading: string; annual_note: string; floors_note: string }
}

const COLOR: Record<UseKey, string> = {
  // No thread-1: it is the site's coral, and a coral beside a rule reads as a warning (rule 8).
  keep: 'var(--thread-3)', general: 'var(--thread-2)', special: 'var(--thread-4)', opeb: 'var(--thread-5)',
  capital: 'var(--text-secondary)', other: 'var(--text-muted)', left: 'var(--surface-3)',
}
const SHARE_KEYS: Exclude<UseKey, 'left'>[] = ['keep', 'general', 'special', 'opeb', 'capital', 'other']

const usd = (n: number) => (n < 0 ? '-' : '') + '$' + Math.abs(Math.round(n)).toLocaleString('en-US')
const pct = (x: number, dp = 1) => (x * 100).toFixed(dp) + '%'
const secondary = { color: 'var(--text-secondary)' }
const muted = { color: 'var(--text-muted)' }

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

/** One rule set's split of the free cash, as a 100% bar. */
function SplitBar({ label, u, fc, active, names }: { label: string; u: Uses; fc: number; active: boolean; names: Record<UseKey, string> }) {
  const parts = (Object.keys(COLOR) as UseKey[]).map(k => ({ k, v: Math.max(0, u[k]) })).filter(p => p.v > 0)
  const over = u.left < 0
  return (
    <div className="mt-3" style={{ opacity: active ? 1 : 0.55 }}>
      <div className="flex items-baseline justify-between gap-2 text-[13px]">
        <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>{label}</span>
        <span style={secondary}>{over ? `assigns ${usd(-u.left)} more than the free cash` : `${usd(u.left)} left for Town Meeting`}</span>
      </div>
      <div className="mt-1 flex h-7 w-full overflow-hidden rounded-sm" style={{ background: 'var(--surface-2)' }}
        role="img" aria-label={`${label}: ` + parts.map(p => `${names[p.k]} ${usd(p.v)}`).join(', ')}>
        {parts.map(p => (
          <div key={p.k} title={`${names[p.k]}: ${usd(p.v)}`}
            style={{ width: `${(100 * p.v) / Math.max(fc, fc - u.left)}%`, background: COLOR[p.k],
              borderRight: '1px solid var(--surface-1)', boxShadow: p.k === 'left' ? 'inset 0 0 0 1px var(--grid)' : undefined }} />
        ))}
      </div>
    </div>
  )
}

/** A balance as a share of the budget, before and after, against the rules' bands. */
function Gauge({ title, before, after: a, bands, ticks, note }: {
  title: string; before: number; after: number; bands: { lo: number; hi: number; label: string; c: string }[]
  ticks: { at: number; label: string; c: string }[]; note?: string
}) {
  const max = Math.max(0.12, a * 1.15, before * 1.15, ...ticks.map(t => t.at * 1.15), ...bands.map(b => b.hi * 1.15))
  const X = (v: number) => `${Math.min(100, (100 * v) / max)}%`
  return (
    <div className="rounded-md p-3" style={{ background: 'var(--surface-1)', border: '1px solid var(--grid)' }}>
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-[13.5px] font-semibold" style={{ color: 'var(--text-primary)' }}>{title}</span>
        <Tag k="ours" />
      </div>
      <div className="mt-1 text-[22px] font-semibold tabular-nums" style={{ color: 'var(--text-primary)' }}>
        {pct(a, 2)} <span className="text-[13px] font-normal" style={secondary}>of the budget, from {pct(before, 2)}</span>
      </div>
      <div className="relative mt-3 h-9">
        <div className="absolute left-0 right-0 top-3 h-3 rounded-sm" style={{ background: 'var(--surface-2)' }} />
        {bands.map(b => (
          <div key={b.label} className="absolute top-3 h-3" title={b.label}
            style={{ left: X(b.lo), width: `calc(${X(b.hi)} - ${X(b.lo)})`, background: b.c, opacity: 0.35 }} />
        ))}
        {ticks.map(t => (
          <div key={t.label} className="absolute top-1 h-7 w-0" title={t.label} style={{ left: X(t.at), borderLeft: `2px solid ${t.c}` }} />
        ))}
        <div className="absolute top-3 h-3 w-0" style={{ left: X(before), borderLeft: '2px dotted var(--text-muted)' }} title={`Before: ${pct(before, 2)}`} />
        <div className="absolute top-2 h-5 w-1.5 -ml-[3px] rounded-sm" style={{ left: X(a), background: 'var(--text-primary)' }} title={`After: ${pct(a, 2)}`} />
      </div>
      <ul className="mt-1 space-y-0.5 text-[12px]" style={secondary}>
        {bands.map(b => <li key={b.label}><span className="inline-block w-2.5 h-2.5 mr-1.5 align-middle rounded-sm" style={{ background: b.c, opacity: 0.6 }} />{b.label}</li>)}
        {ticks.map(t => <li key={t.label}><span className="inline-block w-2.5 h-0.5 mr-1.5 align-middle" style={{ background: t.c }} />{t.label}</li>)}
      </ul>
      {note ? <p className="mt-1.5 text-[12px]" style={muted}>{note}</p> : null}
    </div>
  )
}

function Figure({ title, value, sub, kind = 'ours' }: { title: string; value: string; sub: string; kind?: Kind }) {
  return (
    <div className="rounded-md p-3" style={{ background: 'var(--surface-1)', border: '1px solid var(--grid)' }}>
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-[13.5px] font-semibold" style={{ color: 'var(--text-primary)' }}>{title}</span>
        <Tag k={kind} />
      </div>
      <div className="mt-1 text-[22px] font-semibold tabular-nums" style={{ color: 'var(--text-primary)' }}>{value}</div>
      <p className="mt-0.5 text-[12.5px]" style={secondary}>{sub}</p>
    </div>
  )
}

export default function PolicyCalculator({ data, alt }: CustomProps) {
  const d = data as Data
  const p = d.params
  const [preset, setPreset] = useState<Preset['key']>('today')
  const [x, setX] = useState<Inputs>(d.defaults)
  const [shares, setShares] = useState<Shares>(() => draftShares(p, d.defaults))
  const names = useMemo(() => Object.fromEntries(d.uses.map(u => [u.key, u.label])) as Record<UseKey, string>, [d.uses])
  const changed = (k: keyof Inputs) => x[k] !== d.defaults[k]

  const all = useMemo(() => ({ today: uses('today', p, x), draft: uses('draft', p, x), custom: custom(x, shares) }), [p, x, shares])
  const u = all[preset]
  const a: After = after(x, u)
  const before = after(x, { keep: 0, general: 0, special: 0, opeb: 0, capital: 0, other: 0, left: x.fc })
  const P = d.presets.find(q => q.key === preset)!
  const shareSum = SHARE_KEYS.reduce((s, k) => s + shares[k], 0)

  const set = (k: keyof Inputs, v: number) => setX(o => ({ ...o, [k]: Number.isFinite(v) ? v : 0 }))
  const setShare = (k: Exclude<UseKey, 'left'>, v: number) => setShares(o => {
    const others = SHARE_KEYS.reduce((s, j) => (j === k ? s : s + o[j]), 0)
    return { ...o, [k]: Math.max(0, Math.min(v, 1 - others)) }
  })
  const reset = () => { setX(d.defaults); setShares(draftShares(p, d.defaults)) }
  const anyChanged = (Object.keys(d.defaults) as (keyof Inputs)[]).some(changed)

  // The two rule sets drawn at the same weight in greys: today's as a line, the draft's as a band.
  const tone = { today: 'var(--text-primary)', draft: 'var(--text-muted)' }
  return (
    <div className="w-full max-w-4xl min-w-0" aria-label={alt}>
      {/* THE RULE SET */}
      <div className="flex flex-wrap gap-1.5" role="tablist" aria-label="Rule set">
        {d.presets.map(q => (
          <button key={q.key} type="button" role="tab" aria-selected={preset === q.key} onClick={() => setPreset(q.key)}
            className="px-3 py-1.5 rounded-md text-[14px] font-medium"
            style={preset === q.key
              ? { background: 'var(--text-primary)', color: 'var(--surface-1)' }
              : { background: 'var(--surface-2)', color: 'var(--text-primary)' }}>{q.label}</button>
        ))}
      </div>
      <p className="mt-1.5 text-[12.5px]" style={muted}>{P.source}</p>

      {/* THE SIGNATURE: what each rule set does with the same free cash */}
      <div className="mt-3 rounded-md p-3" style={{ background: 'var(--surface-1)', border: '1px solid var(--grid)' }}>
        <div className="flex items-baseline justify-between gap-2">
          <span className="text-[13.5px]" style={secondary}>Where {usd(x.fc)} of free cash goes</span>
          <Tag k="ours" />
        </div>
        <SplitBar label={d.presets[0].label} u={all.today} fc={x.fc} active={preset === 'today'} names={names} />
        <SplitBar label={d.presets[1].label} u={all.draft} fc={x.fc} active={preset === 'draft'} names={names} />
        {preset === 'custom' ? <SplitBar label={d.presets[2].label} u={all.custom} fc={x.fc} active names={names} /> : null}
        <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[12px]" style={secondary}>
          {d.uses.map(q => (
            <li key={q.key}><span className="inline-block w-2.5 h-2.5 mr-1.5 align-middle rounded-sm"
              style={{ background: COLOR[q.key], boxShadow: q.key === 'left' ? 'inset 0 0 0 1px var(--grid)' : undefined }} />{q.label}</li>
          ))}
        </ul>
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-[1fr_1.1fr]">
        {/* THE DOLLARS, for the rule set chosen */}
        <div className="min-w-0">
          <table className="w-full text-[14px] tabular-nums">
            <thead><tr className="text-left text-[12px]" style={muted}>
              <th className="font-normal pb-1">{P.label}</th><th className="font-normal pb-1 text-right">Dollars</th><th className="font-normal pb-1 text-right">Share</th>
            </tr></thead>
            <tbody>
              {d.uses.map(q => {
                const v = u[q.key]
                if (q.key !== 'left' && v === 0 && preset !== 'custom') return null
                return (
                  <tr key={q.key} style={{ borderTop: '1px solid var(--grid)' }}>
                    <td className="py-1.5 pr-2"><span className="inline-block w-2.5 h-2.5 mr-1.5 align-middle rounded-sm"
                      style={{ background: COLOR[q.key], boxShadow: q.key === 'left' ? 'inset 0 0 0 1px var(--grid)' : undefined }} />
                      <span className={q.key === 'left' ? 'font-semibold' : ''}>{q.label}</span></td>
                    <td className="py-1.5 text-right">{usd(v)}</td>
                    <td className="py-1.5 pl-2 text-right" style={secondary}>{x.fc ? pct(v / x.fc, 1) : ''}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          {preset === 'draft' ? <p className="mt-2 text-[12.5px]" style={muted}>{d.text.floors_note}</p> : null}

          {/* THE DIALS each rule set leaves to the reader */}
          {preset === 'today' ? (
            <label className="mt-3 block text-[13px]">
              <span style={secondary}>{d.inputs.find(i => i.key === 'special_plan')!.label}</span>
              <Money value={x.special_plan} onChange={v => set('special_plan', v)} />
              <span className="mt-0.5 block text-[12px]" style={muted}>{d.inputs.find(i => i.key === 'special_plan')!.source}</span>
            </label>
          ) : null}
          {preset === 'draft' ? (
            <label className="mt-3 block text-[13px]">
              <span style={secondary}>Cash capital share: <b style={{ color: 'var(--text-primary)' }}>{pct(x.capital_share, 0)}</b> of the free cash</span>
              <input type="range" className="mt-1 block w-full" min={p.draft.capital[0] * 100} max={p.draft.capital[1] * 100} step={1}
                value={Math.round(x.capital_share * 100)} onChange={e => set('capital_share', Number(e.target.value) / 100)} />
              <span className="flex justify-between text-[11.5px]" style={muted}><span>{pct(p.draft.capital[0], 0)}</span><span>{pct(p.draft.capital[1], 0)}</span></span>
            </label>
          ) : null}
          {preset === 'custom' ? (
            <div className="mt-3 space-y-2">
              {SHARE_KEYS.map(k => (
                <label key={k} className="block text-[13px]">
                  <span className="flex justify-between" style={secondary}><span>{names[k]}</span>
                    <b className="tabular-nums" style={{ color: 'var(--text-primary)' }}>{pct(shares[k], 0)}</b></span>
                  <input type="range" className="block w-full" min={0} max={100} step={1} value={Math.round(shares[k] * 100)}
                    onChange={e => setShare(k, Number(e.target.value) / 100)} aria-label={`${names[k]}, percent of free cash`} />
                </label>
              ))}
              <p className="text-[12px]" style={muted}>The shares add to {pct(shareSum, 0)}; a slider stops where the total would pass the whole free cash.</p>
            </div>
          ) : null}
        </div>

        {/* THE OUTCOMES */}
        <div className="grid gap-3 min-w-0">
          <Gauge title="General stabilization" before={before.general_pct} after={a.general_pct}
            bands={[{ lo: p.bands.general_draft[0], hi: p.bands.general_draft[1], label: `State draft: ${pct(p.bands.general_draft[0], 0)} to ${pct(p.bands.general_draft[1], 0)} of the budget`, c: tone.draft }]}
            ticks={[{ at: p.bands.general_today, label: `Today's rules: at least ${pct(p.bands.general_today, 0)}`, c: tone.today },
              { at: p.today.floor, label: `Today's rules: never below ${pct(p.today.floor, 0)} of the prior year's budget`, c: 'var(--text-muted)' }]} />
          <Gauge title="Special purpose stabilization" before={before.special_pct} after={a.special_pct}
            bands={[{ lo: p.bands.special_draft[0], hi: p.bands.special_draft[1], label: `State draft: ${pct(p.bands.special_draft[0], 0)} to ${pct(p.bands.special_draft[1], 0)} of the budget`, c: tone.draft }]}
            ticks={[]} note="Today's rules set no target for these funds." />
          <Gauge title="All stabilization funds" before={before.all_pct} after={a.all_pct} bands={[]}
            ticks={[{ at: p.today.cap, label: `Today's rules: the total not above ${pct(p.today.cap, 0)} of the prior year's budget`, c: tone.today }]}
            note={`${d.text.cap_reading} The state draft caps the year's deposits instead: ${pct(a.deposits_pct, 2)} of the budget here, against its ${pct(p.draft.cap, 0)}.`} />
          <div className="grid gap-3 sm:grid-cols-2">
            <Figure title="Retiree health trust" value={usd(a.opeb_trust)}
              sub={`${pct(a.funded, 1)} of the ${usd(x.opeb_liability)} liability, from ${pct(before.funded, 1)}`} />
            <Figure title="Next year's starting free cash" value={usd(a.next_fc)}
              sub={preset === 'today' ? 'Today\'s rules set nothing aside; whatever Town Meeting leaves unspent carries over.'
                : `${pct(a.next_fc_pct, 2)} of the budget, set aside before the next certification. The draft's target for a certification is ${pct(p.bands.fc_draft[0], 0)} to ${pct(p.bands.fc_draft[1], 0)}.`} />
          </div>
        </div>
      </div>

      {/* THE INPUTS */}
      <details className="mt-5 rounded-md" style={{ border: '1px solid var(--grid)' }} open>
        <summary className="cursor-pointer px-3 py-2 text-[14px] font-semibold">The figures it starts from</summary>
        <div className="px-3 pb-3">
          <div className="grid gap-3 sm:grid-cols-2">
            {d.inputs.filter(i => i.key !== 'special_plan').map(i => (
              <label key={i.key} className="block text-[13px]">
                <span className="flex items-baseline justify-between gap-2"><span style={secondary}>{i.label}</span>
                  <Tag k={changed(i.key) ? 'input' : 'published'} /></span>
                <Money value={x[i.key]} onChange={v => set(i.key, v)} />
                <span className="mt-0.5 block text-[12px]" style={muted}>{changed(i.key) ? `Published: ${i.text}. ${i.source}` : i.source}</span>
              </label>
            ))}
          </div>
          {anyChanged ? <button type="button" onClick={reset} className="mt-3 px-3 py-1 rounded-md text-[13px]"
            style={{ background: 'var(--surface-2)', color: 'var(--text-primary)' }}>Back to the published figures</button> : null}
          <ul className="mt-3 space-y-1 text-[12.5px]" style={muted}>
            <li>{d.text.audit_note}</li>
            <li>{d.text.budget_note}</li>
            <li>{d.text.annual_note} At this budget that is {usd(p.draft.stab_annual[0] * x.budget)} or {usd(p.draft.stab_annual[1] * x.budget)} a year.</li>
          </ul>
        </div>
      </details>

      {/* THE RULES, as printed */}
      {P.rules.length ? (
        <details className="mt-3 rounded-md" style={{ border: '1px solid var(--grid)' }}>
          <summary className="cursor-pointer px-3 py-2 text-[14px] font-semibold">{P.label}, as printed</summary>
          <ul className="px-3 pb-3 space-y-2">
            {P.rules.map((r, i) => (
              <li key={r.key + i} className="text-[13px]">
                <q style={{ color: 'var(--text-primary)' }}>{r.quote}</q>
                <span className="block text-[12px]" style={muted}>{r.source}</span>
              </li>
            ))}
          </ul>
        </details>
      ) : null}
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
