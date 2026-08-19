import { useState } from 'react'
import { MODEL, usd } from '../model/engine'
import {
  BY_ID, CURATED, OTHER_RESTORES, REST_BY_CAT, REST_COUNT, restoreId,
  type CutItem, type CutState,
} from '../model/cuts'

/** Switch programs off by hand.
 *
 *  The groups above the fold are the ones people actually name in a budget meeting. The
 *  rest of the budget is real and cuttable too, but putting fifty checkboxes on screen at
 *  once turns a decision into a data-entry exercise — so it lives behind one click. */
export function CutBoard({ state, setState, onJump }: {
  state: CutState
  setState: (s: CutState) => void
  onJump: (anchor: string) => void
}) {
  const [showAll, setShowAll] = useState(false)

  const restoreTotal = OTHER_RESTORES
    .filter(r => (state[restoreId(r.id)] ?? 0) > 0)
    .reduce((sum, r) => sum + r.cost, 0)

  const set = (id: string, n: number) => {
    const next = { ...state }
    if (n <= 0) delete next[id]
    else next[id] = n
    setState(next)
  }

  return (
    <div className="grid gap-3">
      {CURATED.map(g => (
        <Group key={g.id} title={g.title} blurb={g.blurb}
          items={g.ids.map(id => BY_ID.get(id)).filter((i): i is CutItem => !!i)}
          state={state} set={set}
          action={<button onClick={() => onJump(g.anchor)}
            className="text-[11px] font-semibold shrink-0"
            style={{ color: 'var(--series-cost)' }}>Why this matters →</button>} />
      ))}

      {/* Restoring is the mirror image of cutting, so it gets its own board rather than
          being a special kind of checkbox in the middle of the cut list. */}
      <div className="card p-4">
        <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 mb-1">
          <h3 className="text-[13px] font-bold">Put back what was already cut</h3>
          {restoreTotal > 0 && (
            <span className="text-[13px] font-bold tnum"
              style={{ color: 'var(--series-revenue)' }}>+{usd(restoreTotal)}</span>
          )}
        </div>
        <p className="text-[12px] leading-relaxed mb-2" style={{ color: 'var(--text-secondary)' }}>
          The teachers, interventionists and programs the FY27 balanced budget eliminated.
          Nothing stops a future budget funding them again &mdash; but each one{' '}
          <strong>adds</strong> to the gap rather than closing it. Athletics has its own
          put-back list on the board above.
        </p>
        <ul>
          {OTHER_RESTORES.map(r => {
            const key = restoreId(r.id)
            const on = (state[key] ?? 0) > 0
            return (
              <li key={r.id} className="border-b last:border-0"
                style={{ borderColor: 'var(--grid)' }}>
                <label className="flex items-center gap-2.5 py-2 cursor-pointer">
                  <input type="checkbox" checked={on}
                    onChange={e => set(key, e.target.checked ? 1 : 0)}
                    className="shrink-0" style={{ accentColor: 'var(--series-revenue)' }} />
                  <span className="flex-1 min-w-0">
                    <span className="block text-[12px] leading-snug">{r.label}</span>
                    <span className="block text-[10px]" style={{ color: 'var(--text-muted)' }}>
                      {r.fte > 0 && <span className="tnum mr-1.5">{r.fte} FTE ·</span>}
                      {r.impact}
                    </span>
                  </span>
                  <span className="text-[12px] tnum shrink-0"
                    style={{ color: on ? 'var(--series-revenue)' : 'var(--text-secondary)' }}>
                    +{usd(r.cost)}
                  </span>
                </label>
              </li>
            )
          })}
        </ul>
      </div>

      <div className="card p-4">
        <button onClick={() => setShowAll(v => !v)} aria-expanded={showAll}
          className="w-full flex items-baseline justify-between gap-3 text-left">
          <span className="text-[13px] font-bold">
            Every other line in the budget
            <span className="ml-2 text-[11px] font-normal" style={{ color: 'var(--text-muted)' }}>
              {REST_COUNT} more
            </span>
          </span>
          <span className="text-[11px] font-semibold shrink-0"
            style={{ color: 'var(--series-cost)' }}>
            {showAll ? 'Hide' : 'Show'}
          </span>
        </button>
        {!showAll && (
          <p className="text-[12px] mt-1" style={{ color: 'var(--text-secondary)' }}>
            Classroom teachers, special education, counsellors, nurses, custodians,
            networks. Most of the budget is here, and almost none of it is optional.
          </p>
        )}
        {showAll && (
          <div className="mt-3 grid gap-4">
            {REST_BY_CAT.map(g => (
              <div key={g.cat}>
                <h4 className="text-[11px] font-bold uppercase tracking-widest mb-1"
                  style={{ color: 'var(--text-muted)' }}>{g.label}</h4>
                <ul>
                  {g.items.map(i => (
                    <Row key={i.id} item={i} n={state[i.id] ?? 0} set={set} />
                  ))}
                </ul>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function Group({ title, blurb, items, state, set, action }: {
  title: string; blurb: string; items: CutItem[]
  state: CutState; set: (id: string, n: number) => void
  action?: React.ReactNode
}) {
  const chosen = items.filter(i => (state[i.id] ?? 0) > 0)
  const total = chosen.reduce((s, i) => s + i.cost * Math.min(state[i.id], i.repeatable), 0)
  return (
    <div className="card p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 mb-1">
        <h3 className="text-[13px] font-bold">{title}</h3>
        <span className="flex items-baseline gap-3 shrink-0">
          {total > 0 && (
            <span className="text-[13px] font-bold tnum"
              style={{ color: 'var(--status-critical)' }}>{usd(total)}</span>
          )}
          {action}
        </span>
      </div>
      <p className="text-[12px] leading-relaxed mb-2" style={{ color: 'var(--text-secondary)' }}>
        {blurb}
      </p>
      <ul>{items.map(i => <Row key={i.id} item={i} n={state[i.id] ?? 0} set={set} />)}</ul>
    </div>
  )
}

function Row({ item, n, set }: {
  item: CutItem; n: number; set: (id: string, n: number) => void
}) {
  const [open, setOpen] = useState(false)
  const blocked = item.mandate === 'legal'
  const on = n > 0
  const many = item.repeatable > 1

  return (
    <li className="border-b last:border-0" style={{ borderColor: 'var(--grid)' }}>
      <div className="flex items-center gap-2.5 py-2">
        {many ? (
          <span className="flex items-center gap-1 shrink-0">
            <button onClick={() => set(item.id, n - 1)} disabled={n === 0}
              aria-label={`One fewer ${item.label}`}
              className="w-6 h-6 rounded border text-xs disabled:opacity-25"
              style={{ borderColor: 'var(--grid)' }}>−</button>
            <span className="w-4 text-center text-[12px] font-bold tnum">{n}</span>
            <button onClick={() => set(item.id, n + 1)}
              disabled={n >= item.repeatable}
              aria-label={`One more ${item.label}`}
              className="w-6 h-6 rounded border text-xs disabled:opacity-25"
              style={{ borderColor: 'var(--grid)' }}>+</button>
          </span>
        ) : (
          <input type="checkbox" checked={on}
            aria-label={blocked ? `Cut ${item.label} — not lawful` : `Cut ${item.label}`}
            onChange={e => set(item.id, e.target.checked ? 1 : 0)}
            className="shrink-0"
            style={{ accentColor: blocked ? 'var(--status-warning)'
              : 'var(--status-critical)' }} />
        )}

        <span className="flex-1 min-w-0">
          <span className="block text-[12px] leading-snug"
            style={{ textDecoration: on ? 'line-through' : 'none',
                     color: on ? 'var(--text-muted)' : 'var(--text-primary)' }}>
            {item.label}
          </span>
          <span className="flex items-center gap-2 text-[10px]"
            style={{ color: 'var(--text-muted)' }}>
            {blocked && (
              <span style={{ color: 'var(--status-warning)' }}>
                <span aria-hidden="true">⚖ </span>
                {on ? 'Required by law — this budget could not be adopted'
                    : 'Required by law'}
              </span>
            )}
            {item.status === 'restoring' && (
              <span style={{ color: 'var(--status-serious)' }}>
                One-time money — keeping it in FY28 is a new cost
              </span>
            )}
            {item.fte > 0 && <span className="tnum">{item.fte} FTE each</span>}
            <button onClick={() => setOpen(o => !o)} className="underline">
              {open ? 'less' : 'what this means'}
            </button>
          </span>
        </span>

        <span className="text-[12px] tnum shrink-0"
          style={{ color: on ? (blocked ? 'var(--status-warning)' : 'var(--status-critical)')
            : 'var(--text-secondary)' }}>
          {usd(item.cost * (many && n > 0 ? n : 1))}
          {many && <span className="text-[10px]"> {n > 0 ? '' : 'each'}</span>}
        </span>
      </div>
      {open && (
        <p className="text-[11px] leading-relaxed pb-2.5 pl-7 pr-1"
          style={{ color: 'var(--text-secondary)' }}>
          {item.impact}
          <span className="block mt-1" style={{ color: 'var(--text-muted)' }}>
            {MODEL.categories[item.cat]?.label ?? item.cat} · {item.source}
          </span>
        </p>
      )}
    </li>
  )
}
