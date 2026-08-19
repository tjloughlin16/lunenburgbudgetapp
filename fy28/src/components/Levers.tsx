import { Fragment, useState, type ReactNode } from 'react'
import {
  MODEL, usd, leverYield, leverStart, ladderRungs, ladderTaken, ladderMask,
  ladderContiguous, type Lever,
} from '../model/engine'

export function LeverWorkbench({ gap, vals, setVals, basis, setBasis, showTotal = true,
  zeroed = [], after = {}, payers = {} }: {
  gap: number
  vals: Record<string, number>
  setVals: (v: Record<string, number>) => void
  basis: Record<string, number>
  setBasis: (v: Record<string, number>) => void
  /** Off when the page already shows the running arithmetic above these dials. */
  showTotal?: boolean
  /** Levers that cannot earn anything given other choices — an athletics fee with no
   *  athletics, for instance. Shown struck through rather than silently wrong. */
  zeroed?: string[]
  /** Extra dials to drop into the grid immediately after a given lever, so controls
   *  about the same subject sit beside each other rather than a screen apart. */
  after?: Record<string, ReactNode>
  /** Levers whose payer pool is decided by choices made elsewhere on the page — an
   *  athletics fee can only be charged to athletes who still have a team. */
  payers?: Record<string, {
    effective: number; removed: number; reason: string
    /** What the program actually costs now, if choices elsewhere have shrunk it. */
    cap?: number
  }>
}) {
  const [openId, setOpenId] = useState<string | null>(null)

  // Lever arithmetic lives in the engine so this workbench, the running total and the
  // floating panel cannot drift apart.
  const dead = new Set(zeroed)
  /** What a lever is actually charged on: the reader's own figure, less anything their
   *  other choices have taken out of the pool. */
  const poolOf = (l: Lever) => payers[l.id]?.effective ?? basis[l.id] ?? l.basis
  /** A fee cannot raise more than the thing it pays for costs — and what it pays for
   *  shrinks when programs are cut, so the ceiling moves with them. */
  const capOf = (l: Lever) => payers[l.id]?.cap ?? l.cap
  const yieldOf = (l: Lever) =>
    dead.has(l.id) ? 0 : leverYield({ ...l, cap: capOf(l) }, vals[l.id] ?? 0, poolOf(l))
  const total = MODEL.levers.reduce((s, l) => s + yieldOf(l), 0)
  const pct = Math.min(100, (total / gap) * 100)
  const closed = total >= gap

  return (
    <div>
      {/* running total */}
      {showTotal && <div className="card p-5 mb-5 sticky top-12 z-10" style={{ background: 'var(--surface-1)' }}>
        <div className="flex flex-wrap items-end justify-between gap-4 mb-3">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest mb-1"
              style={{ color: 'var(--text-muted)' }}>Found without cutting anything</p>
            <p className="text-3xl font-bold tnum leading-none"
              style={{ color: closed ? 'var(--status-good)' : 'var(--text-primary)' }}>
              {usd(total)}
            </p>
          </div>
          <div className="text-right">
            <p className="text-[11px] font-semibold uppercase tracking-widest mb-1"
              style={{ color: 'var(--text-muted)' }}>FY28 gap</p>
            <p className="text-3xl font-bold tnum leading-none"
              style={{ color: 'var(--status-critical)' }}>{usd(gap)}</p>
          </div>
        </div>
        <div className="h-3 rounded-full overflow-hidden" style={{ background: 'var(--surface-3)' }}>
          <div className="h-full rounded-full transition-[width]"
            style={{ width: `${pct}%`,
                     background: closed ? 'var(--status-good)' : 'var(--series-cost)' }} />
        </div>
        <p className="text-[13px] mt-2.5" style={{ color: 'var(--text-secondary)' }}>
          {closed
            ? <><span aria-hidden="true" style={{ color: 'var(--status-good)' }}>✓ </span>
              <strong>The gap closes with no program cuts at all.</strong> Whether these
              choices are acceptable is the actual question — read the caveat under each one.</>
            : <>{pct.toFixed(0)}% of the way there. <strong>{usd(gap - total)}</strong> would
              still have to come out of programs.</>}
        </p>
      </div>}

      <div className="grid gap-3 md:grid-cols-2">
        {MODEL.levers.map(l => {
          const v = vals[l.id] ?? 0
          const y = yieldOf(l)
          const isFee = !l.isPercent && !l.isPercentPoint && !l.isLadder
          const rungs = l.isLadder ? ladderRungs(l) : []
          // For a ladder, v is a bit set. The slider shows how many are taken; whether
          // it still *describes* them is a separate question.
          const chosen = l.isLadder ? ladderTaken(l, v) : []
          const taken = chosen.length
          const inOrder = l.isLadder ? ladderContiguous(v) : true
          const capped = isFee && v * (basis[l.id] ?? l.basis) > l.cap
          return (
            <Fragment key={l.id}>
            <div className="card p-4">
              <div className="flex items-baseline justify-between gap-3 mb-1">
                <h3 className="text-[13px] font-bold">{l.name}</h3>
                <span className="text-[10px] font-bold uppercase tracking-widest shrink-0"
                  style={{ color: l.kind === 'revenue' ? 'var(--series-cost)' : 'var(--text-muted)' }}>
                  {l.kind === 'revenue' ? 'New revenue' : 'Cost saving'}
                </span>
              </div>

              <div className="flex items-baseline justify-between gap-3 mb-1">
                <span className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
                  {l.unit}
                  {l.current !== undefined && l.current > 0 && (
                    <strong> · today {l.isPercentPoint ? `${l.current}%` : usd(l.current)}</strong>
                  )}
                </span>
                <span className="flex items-baseline gap-1.5 shrink-0">
                  {!l.isPercent && !l.isPercentPoint && (l.current ?? 0) > 0 && (
                    <span className="text-[10px] font-bold px-1.5 py-0.5 rounded"
                      style={{
                        background: v > (l.current ?? 0)
                          ? 'color-mix(in srgb, var(--series-cost) 16%, var(--surface-1))'
                          : 'var(--surface-3)',
                        color: v > (l.current ?? 0) ? 'var(--series-cost)' : 'var(--text-muted)',
                      }}>
                      {(v / (l.current as number)).toFixed(1)}× today
                    </span>
                  )}
                  <span className="text-sm font-bold tnum">
                    {l.isLadder ? `${taken} of ${rungs.length}`
                      : l.isPercent || l.isPercentPoint ? `${v}%` : usd(v)}
                  </span>
                </span>
              </div>
              <input type="range" min={l.isPercent || l.isLadder ? 0 : (l.current ?? 0)}
                max={l.max} step={l.step} value={l.isLadder ? taken : v}
                aria-label={`${l.name}, ${l.unit}`}
                onChange={e => setVals({ ...vals,
                  [l.id]: l.isLadder ? ladderMask(Number(e.target.value))
                                     : Number(e.target.value) })}
                className="w-full" />
              {isFee && (
                <div className="flex items-start justify-between text-[10px] -mt-0.5"
                  style={{ color: 'var(--text-muted)' }}>
                  <button onClick={() => setVals({ ...vals, [l.id]: l.current ?? 0 })}
                    className="text-left leading-tight hover:opacity-70">
                    <span className="block w-px h-1.5 mb-0.5"
                      style={{ background: 'var(--axis)' }} aria-hidden="true" />
                    today {usd(l.current ?? 0)}
                  </button>
                  <span className="text-right leading-tight">
                    <span className="block w-px h-1.5 mb-0.5 ml-auto"
                      style={{ background: 'var(--axis)' }} aria-hidden="true" />
                    max {usd(l.max)}
                  </span>
                </div>
              )}
              {(l.isPercent || l.isPercentPoint) && !l.isLadder && (
                <div className="flex items-start justify-between text-[10px] -mt-0.5"
                  style={{ color: 'var(--text-muted)' }}>
                  <button onClick={() => setVals({ ...vals, [l.id]: leverStart(l) })}
                    className="text-left leading-tight hover:opacity-70">
                    <span className="block w-px h-1.5 mb-0.5"
                      style={{ background: 'var(--axis)' }} aria-hidden="true" />
                    today {leverStart(l)}%
                  </button>
                  <span className="text-right leading-tight">
                    <span className="block w-px h-1.5 mb-0.5 ml-auto"
                      style={{ background: 'var(--axis)' }} aria-hidden="true" />
                    max {l.max}%
                  </span>
                </div>
              )}

              {isFee && (
                <div className="flex items-center gap-2 mt-1.5">
                  <label htmlFor={`b-${l.id}`} className="text-[11px] shrink-0"
                    style={{ color: 'var(--text-muted)' }}>
                    {l.basisKnown === false ? 'Participants (estimate)' : 'Participants'}
                  </label>
                  <input id={`b-${l.id}`} type="number" min={0} step={10}
                    value={basis[l.id] ?? l.basis}
                    onChange={e => setBasis({ ...basis, [l.id]: Number(e.target.value) })}
                    className="w-20 px-1.5 py-0.5 rounded border text-[11px] tnum"
                    style={{ borderColor: 'var(--grid)', background: 'var(--surface-2)',
                             color: 'var(--text-primary)' }} />
                </div>
              )}
              {isFee && (payers[l.id]?.removed ?? 0) > 0 && (
                <p className="text-[10px] leading-snug mt-1"
                  style={{ color: 'var(--status-serious)' }}>
                  &minus; {payers[l.id].removed.toLocaleString()} {payers[l.id].reason}
                  {' '}= <strong>{poolOf(l).toLocaleString()} left to charge</strong>
                </p>
              )}

              {/* Flat break-even: what one participant would pay if the program
                  fully covered itself, ignoring waivers and drop-off. */}
              {isFee && (() => {
                const pool = poolOf(l)
                const cap = capOf(l)
                const full = pool > 0 ? cap / pool : 0
                const cur = l.current ?? 0
                return (
                  <div className="mt-2 pt-2 border-t" style={{ borderColor: 'var(--grid)' }}>
                    <div className="flex items-baseline justify-between gap-2">
                      <span className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
                        Full cost per participant
                      </span>
                      <span className="text-sm font-bold tnum">{usd(full)}</span>
                    </div>
                    <div className="h-1.5 rounded-full overflow-hidden mt-1"
                      style={{ background: 'var(--surface-3)' }}>
                      <div className="h-full rounded-full"
                        style={{ width: `${Math.min(100, (v / full) * 100)}%`,
                                 background: v >= full ? 'var(--status-good)'
                                   : 'var(--series-cost)' }} />
                    </div>
                    <p className="text-[10px] mt-1" style={{ color: 'var(--text-muted)' }}>
                      {usd(cap)} ÷ {pool.toLocaleString()} participants.
                      {cur > 0 && <> Today {usd(cur)} covers {((cur / full) * 100).toFixed(0)}%.</>}
                      {' '}Your setting covers {((v / full) * 100).toFixed(0)}% before waivers
                      and drop-off &mdash; which push the real figure higher.
                    </p>
                  </div>
                )
              })()}

              {l.isLadder && (() => {
                const last = chosen[chosen.length - 1] ?? null
                const next = rungs.find(r => !chosen.includes(r)) ?? null
                return (
                  <div className="mt-2">
                    <div className="flex items-start justify-between text-[10px] -mt-0.5"
                      style={{ color: 'var(--text-muted)' }}>
                      <button onClick={() => setVals({ ...vals, [l.id]: 0 })}
                        className="text-left leading-tight hover:opacity-70">
                        <span className="block w-px h-1.5 mb-0.5"
                          style={{ background: 'var(--axis)' }} aria-hidden="true" />
                        cut nothing
                      </button>
                      <span className="text-right leading-tight">
                        <span className="block w-px h-1.5 mb-0.5 ml-auto"
                          style={{ background: 'var(--axis)' }} aria-hidden="true" />
                        everything that can go
                      </span>
                    </div>
                    {/* Only the rung just crossed, so the dial stays a dial. The whole
                        ladder, with what each one costs the district, is in its own
                        panel below. */}
                    <div className="mt-2 pt-2 border-t text-[11px] leading-snug"
                      style={{ borderColor: 'var(--grid)' }}>
                      {last ? (
                        <>
                          <span className="font-semibold"
                            style={{ color: 'var(--status-critical)' }}>
                            <span aria-hidden="true">✕ </span>
                            {inOrder ? 'Just cut:' : 'Deepest cut:'}
                          </span>{' '}
                          <span>{last.label}</span>
                          <span className="tnum" style={{ color: 'var(--text-muted)' }}>
                            {' '}— {usd(last.amount)}{last.fte > 0 && ` · ${last.fte} FTE`}
                          </span>
                        </>
                      ) : (
                        <span style={{ color: 'var(--text-muted)' }}>
                          Nothing cut yet. Each step down is one named position or budget
                          line, least painful first — or pick them individually in the
                          panel below.
                        </span>
                      )}
                      {next && (
                        <span className="block" style={{ color: 'var(--text-muted)' }}>
                          Next step: {next.label} — {usd(next.amount)}
                        </span>
                      )}
                      {!inOrder && (
                        <span className="block" style={{ color: 'var(--status-serious)' }}>
                          Hand-picked below, so the slider no longer matches — dragging it
                          will replace your picks with the first {taken} in order.
                        </span>
                      )}
                      {!next && taken > 0 && (
                        <span className="block" style={{ color: 'var(--status-serious)' }}>
                          Everything that can be cut is cut. What is left is a
                          superintendent, a business manager, a special education
                          administrator and four principals.
                        </span>
                      )}
                    </div>
                  </div>
                )
              })()}

              <p className="text-lg font-bold tnum mt-2"
                style={{ color: y > 0 ? 'var(--status-good)' : 'var(--text-muted)',
                         textDecoration: dead.has(l.id) ? 'line-through' : 'none' }}>
                {usd(y)}
                <span className="text-[10px] font-normal ml-1.5"
                  style={{ color: 'var(--text-muted)' }}>
                  {capped ? 'capped at program cost'
                    : l.isLadder ? (taken === rungs.length && taken > 0
                      ? 'everything that can be cut is cut'
                      : `${taken} line${taken === 1 ? '' : 's'} cut`)
                    : l.isPercentPoint ? 'saved, paid by employees'
                    : l.current ? 'new money, above today’s fee' : ''}
                </span>
              </p>
              {l.selfFunding === null && l.peakYield !== undefined && (
                <p className="text-[10px] mt-0.5" style={{ color: 'var(--status-serious)' }}>
                  Self-funding unreachable — revenue peaks near {usd(l.peakFee ?? 0)}
                </p>
              )}

              <button onClick={() => setOpenId(openId === l.id ? null : l.id)}
                className="text-[11px] font-semibold mt-1.5"
                style={{ color: 'var(--series-cost)' }}>
                {openId === l.id ? 'Hide the catch' : 'What’s the catch?'}
              </button>

              {openId === l.id && (
                <div className="mt-2 pt-2 border-t text-[12px] leading-relaxed space-y-2"
                  style={{ borderColor: 'var(--grid)', color: 'var(--text-secondary)' }}>
                  <p>{l.what}</p>
                  <p><strong style={{ color: 'var(--status-serious)' }}>The catch: </strong>
                    {l.caveat}</p>
                  <p style={{ color: 'var(--text-muted)' }}>{l.benchmark}</p>
                </div>
              )}
            </div>
            {after[l.id]}
            </Fragment>
          )
        })}
      </div>
    </div>
  )
}
