import {
  Bar, BarChart, CartesianGrid, Line, LineChart, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { usd } from '../model/engine'
import { GENERAL, GRANTS, fy } from './StoppedFundingCharts'

/** The charts for /when-grants-end. Every series arrives from
 *  /data/grant-unwinding.json, written by scripts/build_grant_unwinding.py — nothing here
 *  computes a figure and nothing here has one typed into it (rule 2).
 *
 *  COLOUR IS INHERITED, NOT INVENTED. `GENERAL` and `GRANTS` are the two marks
 *  /what-stopped-being-funded already uses for exactly this split, on exactly this DESE
 *  table. A second palette for the same two funds would teach a reader that the colours
 *  mean something local to a page, which is the one thing a palette must not do. So they
 *  are imported rather than redeclared, and `TableTwin` with them.
 *
 *  THE SWAP AND THE REDUCTION ARE DRAWN IN SEPARATE PANELS, ON A SHARED SCALE, AND THAT
 *  IS THE WHOLE ARGUMENT OF THE PAGE. Putting them in one frame would let the eye add
 *  them up, and the sum of those two classes is the district-wide netting this page
 *  exists to refuse. Two panels, same y domain, so they can be compared by height and
 *  cannot be compared by addition.
 *
 *  THE GRANT SHARE IS PLOTTED FROM ZERO. The town's share of the same total runs from
 *  81% to 94%, so drawing it needs a truncated axis, and a truncated axis on a share is
 *  how a 13-point move gets drawn as a cliff. The complement carries the identical
 *  information and starts at zero honestly; the town's share is in the table twin, where
 *  a reader can read it as a number rather than as a height. */

export { TableTwin, fy } from './StoppedFundingCharts'

function Key({ items }: { items: { color: string; label: string }[] }) {
  return (
    <div className="flex flex-wrap gap-x-5 gap-y-1.5 mt-3">
      {items.map(i => (
        <span key={i.label} className="inline-flex items-center gap-1.5 text-[11.5px]"
          style={{ color: 'var(--text-secondary)' }}>
          <span className="inline-block rounded-[2px]"
            style={{ width: 12, height: 12, background: i.color }} />
          {i.label}
        </span>
      ))}
    </div>
  )
}

/* ------------------------------------------------ the grant share of all school spending */

export type SeriesPoint = {
  fy: number; gen_fund: number; grants: number; total: number; town_share: number
}

function ShareTip({ active, payload }: {
  active?: boolean; payload?: { payload: SeriesPoint }[]
}) {
  const p = payload?.[0]?.payload
  if (!active || !p) return null
  return (
    <div className="card p-2.5 text-[12px]" style={{ minWidth: 250 }}>
      <div className="font-bold mb-1">{fy(p.fy)}</div>
      <div className="flex justify-between gap-4">
        <span style={{ color: 'var(--text-secondary)' }}>Grants and revolving</span>
        <span className="tnum">
          {(100 - p.town_share).toFixed(1)}% &middot; {usd(p.grants)}
        </span>
      </div>
      <div className="flex justify-between gap-4">
        <span style={{ color: 'var(--text-secondary)' }}>General fund</span>
        <span className="tnum">{p.town_share.toFixed(1)}% &middot; {usd(p.gen_fund)}</span>
      </div>
      <div className="flex justify-between gap-4 mt-1 font-semibold">
        <span>All funds</span><span className="tnum">{usd(p.total)}</span>
      </div>
    </div>
  )
}

/** The share of all school spending that grants and revolving funds paid, year by year.
 *  Plotted from zero. A single mark, because there is a single question. */
export function GrantShare({ series }: { series: SeriesPoint[] }) {
  const rows = series.map(p => ({ ...p, grant_share: 100 - p.town_share }))
  const top = Math.ceil(Math.max(...rows.map(r => r.grant_share)) + 2)
  return (
    <div className="mt-5">
      <div style={{ height: 240 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={rows} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tickFormatter={fy} tick={{ fontSize: 11 }}
              stroke="var(--axis)" interval="preserveStartEnd" />
            <YAxis domain={[0, top]} tickFormatter={v => `${v}%`} tick={{ fontSize: 11 }}
              stroke="var(--axis)" width={44} />
            <Tooltip content={<ShareTip />} />
            <Line type="linear" dataKey="grant_share" stroke={GRANTS} strokeWidth={2}
              dot={{ r: 2.5 }} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <Key items={[{
        color: GRANTS,
        label: 'grants and revolving funds, as a share of all school spending',
      }]} />
    </div>
  )
}

/* ------------------------------------------------------ the two funds, stacked, 17 years */

function StackTip({ active, payload }: {
  active?: boolean; payload?: { payload: SeriesPoint }[]
}) {
  const p = payload?.[0]?.payload
  if (!active || !p) return null
  return <ShareTip active payload={[{ payload: p }]} />
}

/** Both funds as parts of one total — DESE's own `total` column, which the extract
 *  reconciles to before any of this is published. */
export function BothFunds({ series }: { series: SeriesPoint[] }) {
  return (
    <div className="mt-5">
      <div style={{ height: 250 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={series} margin={{ top: 8, right: 6, left: 0, bottom: 0 }}
            barCategoryGap="18%">
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tickFormatter={fy} tick={{ fontSize: 11 }}
              stroke="var(--axis)" interval="preserveStartEnd" />
            <YAxis tickFormatter={v => usd(v)} tick={{ fontSize: 11 }} stroke="var(--axis)"
              width={64} />
            <Tooltip cursor={{ fill: 'var(--surface-3)' }} content={<StackTip />} />
            <Bar dataKey="gen_fund" stackId="f" isAnimationActive={false} fill={GENERAL} />
            <Bar dataKey="grants" stackId="f" isAnimationActive={false} fill={GRANTS}
              radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <Key items={[
        { color: GENERAL, label: 'general fund — what the town appropriates' },
        { color: GRANTS, label: 'grants and revolving funds — outside the budget everyone votes on' },
      ]} />
    </div>
  )
}

/* ------------------------------------------- the swap and the reduction, never summed */

export type ClassTotals = { n: number; d_grants: number; d_gen_fund: number }
export type YearRow = {
  fy: number
  swap: ClassTotals
  reduction: ClassTotals
  grant_growth: ClassTotals
  other: ClassTotals
  aggregate: { n: number; d_grants: number; d_gen_fund: number; d_total: number }
}

function ClassTip({ active, payload, label, kind }: {
  active?: boolean; label?: number
  payload?: { payload: { fy: number; d_grants: number; d_gen_fund: number; n: number } }[]
  kind: 'swap' | 'reduction'
}) {
  const p = payload?.[0]?.payload
  if (!active || !p) return null
  return (
    <div className="card p-2.5 text-[12px]" style={{ minWidth: 250 }}>
      <div className="font-bold mb-1">{fy(Number(label ?? p.fy))}</div>
      <div style={{ color: 'var(--text-muted)' }} className="mb-1.5">
        {p.n} function{p.n === 1 ? '' : 's'} where grants fell and the general fund{' '}
        {kind === 'swap' ? 'rose' : 'did not rise'}
      </div>
      <div className="flex justify-between gap-4">
        <span style={{ color: 'var(--text-secondary)' }}>Grants and revolving</span>
        <span className="tnum">{usd(p.d_grants)}</span>
      </div>
      <div className="flex justify-between gap-4">
        <span style={{ color: 'var(--text-secondary)' }}>General fund</span>
        <span className="tnum">{usd(p.d_gen_fund)}</span>
      </div>
    </div>
  )
}

function Panel({ rows, kind, title, note, domain }: {
  rows: { fy: number; d_grants: number; d_gen_fund: number; n: number }[]
  kind: 'swap' | 'reduction'; title: string; note: string
  domain: [number, number]
}) {
  return (
    <div>
      <p className="text-[11px] font-semibold uppercase tracking-widest mb-0.5"
        style={{ color: 'var(--text-muted)' }}>{title}</p>
      <p className="text-[12.5px] mb-1.5" style={{ color: 'var(--text-secondary)' }}>{note}</p>
      <div style={{ height: 190 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} margin={{ top: 6, right: 6, left: 0, bottom: 0 }}
            barCategoryGap="16%">
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tickFormatter={fy} tick={{ fontSize: 11 }}
              stroke="var(--axis)" interval="preserveStartEnd" />
            <YAxis domain={domain} tickFormatter={v => usd(v)} tick={{ fontSize: 11 }}
              stroke="var(--axis)" width={64} />
            <ReferenceLine y={0} stroke="var(--axis)" />
            <Tooltip cursor={{ fill: 'var(--surface-3)' }}
              content={<ClassTip kind={kind} />} />
            <Bar dataKey="d_grants" isAnimationActive={false} fill={GRANTS} />
            <Bar dataKey="d_gen_fund" isAnimationActive={false} fill={GENERAL} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

/** TWO PANELS, ONE SHARED SCALE, NEVER ONE FRAME.
 *
 *  Top: the functions where grants fell and the general fund rose. The two bars mirror
 *  each other, and that mirroring IS the reading — something the town started paying for.
 *  Bottom: the functions where grants fell and the general fund did not rise. Both bars
 *  point down.
 *
 *  Drawing them together would produce a net, and a net across these two classes is the
 *  district-wide netting this page refuses to report. Sharing the y domain is what lets
 *  a reader compare them without one. */
export function SwapAndReduction({ years }: { years: YearRow[] }) {
  const swap = years.map(y => ({ fy: y.fy, ...y.swap }))
  const red = years.map(y => ({ fy: y.fy, ...y.reduction }))
  const all = [...swap, ...red].flatMap(r => [r.d_grants, r.d_gen_fund])
  const pad = 1.08
  const domain: [number, number] = [Math.min(...all, 0) * pad, Math.max(...all, 0) * pad]
  return (
    <div className="mt-5 flex flex-col gap-6">
      <Panel rows={swap} kind="swap" domain={domain}
        title="Grants fell, the general fund rose"
        note="The two bars mirror. Same function, same year, the money arriving from a different fund." />
      <Panel rows={red} kind="reduction" domain={domain}
        title="Grants fell, the general fund did not rise"
        note="Both bars point down. Nothing replaced the grant money in these functions." />
      <Key items={[
        { color: GRANTS, label: 'change in grants and revolving funds' },
        { color: GENERAL, label: 'change in the general fund' },
      ]} />
    </div>
  )
}

/* -------------------------------------------------- one year's functions, ranked by size */

export type Move = {
  fy: number; func_code: string; func_desc: string; in_out: string
  d_grants: number; d_gen_fund: number; d_total: number
}

/** Ranked opposed bars for one year's functions. Length on a shared baseline, because the
 *  reader's question is how one function compares with the others. */
export function MoveRows({ moves }: { moves: Move[] }) {
  const top = Math.max(...moves.flatMap(m => [Math.abs(m.d_grants), Math.abs(m.d_gen_fund)]), 1)
  return (
    <div className="mt-5 flex flex-col gap-3">
      {moves.map(m => (
        <div key={`${m.func_code}-${m.in_out}`}>
          <div className="flex items-baseline justify-between gap-3">
            <span className="text-[13px] font-semibold">
              {m.func_desc}{' '}
              <span className="font-normal tnum" style={{ color: 'var(--text-muted)' }}>
                {m.func_code}
              </span>
            </span>
            <span className="text-[12.5px] tnum whitespace-nowrap"
              style={{ color: 'var(--text-secondary)' }}>
              {usd(m.d_grants)} &middot; {usd(m.d_gen_fund)}
            </span>
          </div>
          <div className="mt-1 flex flex-col gap-[3px]">
            {([['g', m.d_grants, GRANTS], ['f', m.d_gen_fund, GENERAL]] as const).map(
              ([k, v, c]) => (
                <div key={k} className="rounded-[3px]"
                  style={{ background: 'var(--surface-3)', height: 9 }}>
                  <div className="rounded-[3px]" style={{
                    width: `${Math.max(1.2, (Math.abs(v) / top) * 100)}%`,
                    height: 9, background: c, opacity: v < 0 ? 0.55 : 1,
                  }} />
                </div>
              ))}
          </div>
        </div>
      ))}
      <Key items={[
        { color: GRANTS, label: 'grants and revolving — paler where the bar is a fall' },
        { color: GENERAL, label: 'general fund — paler where the bar is a fall' },
      ]} />
    </div>
  )
}
