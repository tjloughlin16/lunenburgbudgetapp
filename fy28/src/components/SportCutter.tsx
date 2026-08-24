import { useState } from 'react'
import { MODEL, usd } from '../model/engine'
import {
  ATHLETICS_SPLIT, ATHLETIC_RESTORES, HS_SPORTS, MS_SPORTS, OVERHEAD_LINES, TEAM_ORDER,
  overheadId, overheadSaving, perAthlete, restoreId, setTeamDepth, sportId, sportSaving,
  teamRank, teamsCut, teamsInOrder, type CutState,
} from '../model/cuts'

/** The athletics dial.
 *
 *  Sits with the fees and the administration ladder rather than with the cut lists,
 *  because it is the same kind of object: one control, dragged, with its argument in a
 *  panel underneath. Cutting teams is a cut — which is why the section it lives in is no
 *  longer called "money that is not a cut". */
export function TeamSlider({ state, setState }: {
  state: CutState; setState: (s: CutState) => void
}) {
  const cutIds = new Set(teamsCut(state).map(t => t.name))
  const n = cutIds.size
  const all = n === HS_SPORTS.length
  const inOrder = teamsInOrder(state)
  const last = inOrder
    ? TEAM_ORDER[n - 1] ?? null
    : [...TEAM_ORDER].reverse().find(t => cutIds.has(t.name)) ?? null
  const next = TEAM_ORDER.find(t => !cutIds.has(t.name)) ?? null
  const athletesCut = HS_SPORTS
    .filter(t => cutIds.has(t.name))
    .reduce((sum, t) => sum + t.students, 0)
  const variableSaved = HS_SPORTS
    .filter(t => cutIds.has(t.name))
    .reduce((sum, t) => sum + sportSaving(t), 0)
  const overheadGone = overheadSaving(state)
  const overheadLeft = ATHLETICS_SPLIT.fixed - overheadGone
  const saved = variableSaved + overheadGone
  const setAll = (on: boolean) => setState(setTeamDepth(state, on ? HS_SPORTS.length : 0))

  return (
    <div className="card p-4">
      <div className="flex items-baseline justify-between gap-3 mb-1">
        <h3 className="text-[13px] font-bold">Athletics, team by team</h3>
        <span className="text-[10px] font-bold uppercase tracking-widest shrink-0"
          style={{ color: 'var(--text-muted)' }}>Program cut</span>
      </div>

      <div className="flex items-baseline justify-between gap-3 mb-1">
        <span className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
          fewest athletes displaced per dollar first
        </span>
        <span className="text-sm font-bold tnum">{n} of {HS_SPORTS.length}</span>
      </div>
      <input type="range" min={0} max={HS_SPORTS.length} step={1} value={n}
        aria-label="Number of high school teams cut" className="w-full"
        onChange={e => setState(setTeamDepth(state, Number(e.target.value)))} />
      <div className="flex items-start justify-between text-[10px] -mt-0.5"
        style={{ color: 'var(--text-muted)' }}>
        <button onClick={() => setAll(false)}
          className="text-left leading-tight hover:opacity-70">
          <span className="block w-px h-1.5 mb-0.5"
            style={{ background: 'var(--axis)' }} aria-hidden="true" />
          keep every team
        </button>
        <button onClick={() => setAll(true)}
          className="text-right leading-tight hover:opacity-70">
          <span className="block w-px h-1.5 mb-0.5 ml-auto"
            style={{ background: 'var(--axis)' }} aria-hidden="true" />
          cut every team
        </button>
      </div>

      <div className="mt-2 pt-2 border-t text-[11px] leading-snug"
        style={{ borderColor: 'var(--grid)' }}>
        {last ? (
          <>
            <span className="font-semibold" style={{ color: 'var(--status-critical)' }}>
              <span aria-hidden="true">✕ </span>
              {inOrder ? 'Just cut:' : 'Deepest cut:'}
            </span>{' '}
            <span>{last.name}</span>
            <span className="tnum" style={{ color: 'var(--text-muted)' }}>
              {' '}— {usd(sportSaving(last))} · {last.students} athletes
            </span>
            <span className="block tnum" style={{ color: 'var(--text-muted)' }}>
              {athletesCut} of {HS_SPORTS.reduce((a, t) => a + t.students, 0)}{' '}
              participations gone
            </span>
          </>
        ) : (
          <span style={{ color: 'var(--text-muted)' }}>
            Every team still stands. Drag to give them up in order, or pick them
            individually in the panel below.
          </span>
        )}
        {next && (
          <span className="block" style={{ color: 'var(--text-muted)' }}>
            Next: {next.name} — {usd(sportSaving(next))} · {next.students} athletes
          </span>
        )}
        {!inOrder && (
          <span className="block" style={{ color: 'var(--status-serious)' }}>
            Hand-picked in the panel below, so the slider no longer matches — dragging it
            will replace your picks with the first {n} in order.
          </span>
        )}
      </div>

      <p className="text-lg font-bold tnum mt-2"
        style={{ color: saved > 0 ? 'var(--status-good)' : 'var(--text-muted)' }}>
        {usd(saved)}
        <span className="text-[10px] font-normal ml-1.5" style={{ color: 'var(--text-muted)' }}>
          {all ? 'including the overhead that only goes when every team does'
            : n > 0 ? 'coaching and equipment only' : ''}
        </span>
      </p>
      {!all && n > 0 && overheadLeft > 0 && (
        <p className="text-[10px] mt-0.5" style={{ color: 'var(--status-serious)' }}>
          {usd(overheadLeft)} of overhead is untouched, so each surviving athlete carries
          more of it. Itemised in the panel below, where it can be cut directly.
        </p>
      )}
    </div>
  )
}

/** The argument behind the athletics dial.
 *
 *  Two things make this harder than it looks, and both are shown rather than hidden.
 *  First, most of the athletics budget does not move when one team folds — the director,
 *  the trainer, the secretary, insurance and league dues are paid regardless — so a
 *  single team is worth far less than people expect. Second, middle school sports are
 *  already gone, so "cut middle school sports" saves nothing at all. */
export function TeamBoard({ state, setState }: {
  state: CutState; setState: (s: CutState) => void
}) {
  const cutIds = new Set(HS_SPORTS.filter(s => state[sportId(s)] > 0).map(s => s.name))
  // The grid used to render the district's own document order, which is roughly by
  // season — so the cut-order numbers landed scattered and looked arbitrary. Ranked is
  // the default because it makes the slider legible; A–Z is there for finding a team.
  const [sort, setSort] = useState<'order' | 'name'>('order')
  const listed = sort === 'order'
    ? TEAM_ORDER
    : [...HS_SPORTS].sort((a, b) => a.name.localeCompare(b.name))

  const overheadGone = overheadSaving(state)
  const restoreTotal = ATHLETIC_RESTORES
    .filter(r => (state[restoreId(r.id)] ?? 0) > 0)
    .reduce((sum, r) => sum + r.cost, 0)
  const fullRestore = ATHLETIC_RESTORES.reduce((sum, r) => sum + r.cost, 0)
  const n = cutIds.size
  const all = n === HS_SPORTS.length
  const variableSaved = HS_SPORTS
    .filter(s => cutIds.has(s.name))
    .reduce((sum, s) => sum + sportSaving(s), 0)
  const saved = variableSaved + (all ? ATHLETICS_SPLIT.fixed : 0)

  const inOrder = teamsInOrder(state)

  const toggle = (name: string, on: boolean) => {
    const next = { ...state }
    const s = HS_SPORTS.find(x => x.name === name)
    if (!s) return
    if (on) next[sportId(s)] = 1
    else delete next[sportId(s)]
    setState(next)
  }
  const setAll = (on: boolean) => {
    const next = { ...state }
    for (const s of HS_SPORTS) {
      if (on) next[sportId(s)] = 1
      else delete next[sportId(s)]
    }
    setState(next)
  }

  return (
    <div className="card p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 mb-1">
        <h3 className="text-[13px] font-bold">Athletics, team by team</h3>
        <span className="text-[11px] tnum" style={{ color: 'var(--text-muted)' }}>
          {n} of {HS_SPORTS.length} teams cut
        </span>
      </div>
      <p className="text-[12px] leading-relaxed mb-3" style={{ color: 'var(--text-secondary)' }}>
        The adopted budget spends {usd(ATHLETICS_SPLIT.total)} on athletics, but only{' '}
        <strong>{usd(ATHLETICS_SPLIT.variable)}</strong> of it moves when a team folds —
        coaching stipends and equipment. The other {usd(ATHLETICS_SPLIT.fixed)} is the
        director, the trainer, the secretary, insurance and league dues, and it is paid
        whether the school fields twenty teams or one.
      </p>

      <div className="flex flex-wrap items-center gap-2 mb-2">
        <button onClick={() => setAll(true)}
          className="px-2.5 py-1 rounded-lg text-[11px] font-semibold border"
          style={{ borderColor: 'var(--grid)', color: 'var(--text-secondary)' }}>
          Cut every team
        </button>
        <button onClick={() => setAll(false)} disabled={n === 0}
          className="px-2.5 py-1 rounded-lg text-[11px] font-semibold border disabled:opacity-30"
          style={{ borderColor: 'var(--grid)', color: 'var(--text-secondary)' }}>
          Keep them all
        </button>
        {!inOrder && (
          <span className="text-[11px]" style={{ color: 'var(--status-serious)' }}>
            Hand-picked — the slider above no longer matches these {n}.
          </span>
        )}
      </div>

      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1
        mb-1 pb-1 border-b" style={{ borderColor: 'var(--grid)' }}>
        <p className="text-[11px] leading-relaxed flex-1 min-w-[16rem]"
          style={{ color: 'var(--text-muted)' }}>
          The number is where the slider reaches each team. Teams are ordered by cost per
          athlete, most expensive first, so each step displaces as few students as the
          money allows. Ticking a box ignores the order entirely.
        </p>
        <span className="flex gap-1 shrink-0">
          {([['order', 'Cut order'], ['name', 'A–Z']] as const).map(([k, label]) => (
            <button key={k} onClick={() => setSort(k)} aria-pressed={sort === k}
              className="px-2 py-0.5 rounded text-[10px] font-semibold border"
              style={{
                borderColor: sort === k ? 'var(--series-cost)' : 'var(--grid)',
                background: sort === k ? 'var(--series-cost)' : 'var(--surface-1)',
                color: sort === k ? '#fff' : 'var(--text-secondary)',
              }}>{label}</button>
          ))}
        </span>
      </div>
      <ul className="grid gap-x-4 sm:grid-cols-2">
        {listed.map(s => {
          const on = cutIds.has(s.name)
          return (
            <li key={s.name}>
              <label className="flex items-center gap-2.5 py-1.5 cursor-pointer">
                <input type="checkbox" checked={on}
                  onChange={e => toggle(s.name, e.target.checked)}
                  className="shrink-0" style={{ accentColor: 'var(--status-critical)' }} />
                <span className="tnum text-[10px] shrink-0 w-4 text-right"
                  title={`${s.name} is number ${teamRank(s)} in the cut order — the `
                    + `slider reaches it at ${teamRank(s)} of ${HS_SPORTS.length}`}
                  style={{ color: 'var(--text-muted)' }}>{teamRank(s)}</span>
                <span className="flex-1 min-w-0 text-[12px]"
                  style={{ textDecoration: on ? 'line-through' : 'none',
                           color: on ? 'var(--text-muted)' : 'var(--text-primary)' }}>
                  {s.name}
                  <span className="ml-1.5 text-[10px]" style={{ color: 'var(--text-muted)' }}>
                    {s.students} playing · {usd(perAthlete(s))}/athlete
                  </span>
                </span>
                <span className="text-[12px] tnum shrink-0"
                  style={{ color: on ? 'var(--status-critical)' : 'var(--text-secondary)' }}>
                  {usd(sportSaving(s))}
                </span>
              </label>
            </li>
          )
        })}
      </ul>

      <div className="mt-3 pt-3 border-t" style={{ borderColor: 'var(--grid)' }}>
        <div className="flex items-baseline justify-between gap-3">
          <span className="text-[12px]" style={{ color: 'var(--text-secondary)' }}>
            Saved by cutting {n === 0 ? 'nothing' : `${n} team${n === 1 ? '' : 's'}`}
          </span>
          <span className="text-xl font-bold tnum"
            style={{ color: saved > 0 ? 'var(--status-critical)' : 'var(--text-muted)' }}>
            {usd(saved)}
          </span>
        </div>
        {all && (
          <p className="text-[11px] mt-1" style={{ color: 'var(--status-serious)' }}>
            Every team is gone, so the {usd(ATHLETICS_SPLIT.fixed)} of athletics overhead
            goes with it — that is the only point at which it does. There is no longer an
            athletics program to charge a fee against, so the fee slider stops earning.
          </p>
        )}
        {!all && n > 0 && (
          <p className="text-[11px] mt-1" style={{ color: 'var(--text-muted)' }}>
            {usd(ATHLETICS_SPLIT.fixed)} of athletics overhead is unaffected. It only comes
            off if every team goes.
          </p>
        )}
      </div>

      <div className="mt-3 pt-3 border-t" style={{ borderColor: 'var(--grid)' }}>
        <div className="flex items-baseline justify-between gap-3 mb-1">
          <h4 className="text-[12px] font-bold">
            The overhead — what does not move when a team folds
          </h4>
          <span className="text-[13px] font-bold tnum"
            style={{ color: overheadGone > 0 ? 'var(--status-critical)' : 'var(--text-secondary)' }}>
            {usd(ATHLETICS_SPLIT.fixed - overheadGone)} left
          </span>
        </div>
        <p className="text-[12px] leading-relaxed mb-2" style={{ color: 'var(--text-secondary)' }}>
          This is the {usd(ATHLETICS_SPLIT.fixed)} that makes cost per athlete <em>rise</em>{' '}
          as teams are cut: it is paid whether the school fields twenty teams or one, so
          the fewer athletes there are, the more of it each one carries. Cut all twenty
          teams and it goes with them. Short of that, it only goes if you cut it here.
        </p>
        <ul>
          {OVERHEAD_LINES.map(l => {
            const key = overheadId(l.id)
            const on = all || (state[key] ?? 0) > 0
            return (
              <li key={l.id} className="border-b last:border-0"
                style={{ borderColor: 'var(--grid)' }}>
                <label className="flex items-baseline gap-2.5 py-2 cursor-pointer">
                  <input type="checkbox" checked={on} disabled={all}
                    aria-label={`Cut ${l.label}`}
                    onChange={e => {
                      const next = { ...state }
                      if (e.target.checked) next[key] = 1
                      else delete next[key]
                      setState(next)
                    }}
                    className="shrink-0"
                    style={{ accentColor: l.endsProgram ? 'var(--status-warning)'
                      : 'var(--status-critical)' }} />
                  {l.endsProgram && (
                    <span aria-hidden="true" className="shrink-0 text-[12px]"
                      style={{ color: 'var(--status-warning)' }}>⚖</span>
                  )}
                  <span className="flex-1 min-w-0">
                    <span className="block text-[12px] leading-snug"
                      style={{ textDecoration: on ? 'line-through' : 'none',
                               color: on ? 'var(--text-muted)' : 'var(--text-primary)' }}>
                      {l.label}
                      {l.fte > 0 && (
                        <span className="ml-1.5 text-[10px] tnum"
                          style={{ color: 'var(--text-muted)' }}>{l.fte} FTE</span>
                      )}
                    </span>
                    <span className="block text-[10px] leading-relaxed"
                      style={{ color: l.endsProgram ? 'var(--status-warning)'
                        : 'var(--text-muted)' }}>
                      {l.endsProgram && <strong>Ends the program. </strong>}{l.note}
                    </span>
                  </span>
                  <span className="text-[12px] tnum shrink-0"
                    style={{ color: on ? 'var(--status-critical)' : 'var(--text-secondary)' }}>
                    {usd(l.amount)}
                  </span>
                </label>
              </li>
            )
          })}
        </ul>
        {all && (
          <p className="text-[11px] mt-1.5" style={{ color: 'var(--status-serious)' }}>
            Every team is cut, so all {usd(ATHLETICS_SPLIT.fixed)} goes automatically —
            there is nothing left for it to run.
          </p>
        )}
        <p className="text-[10px] leading-relaxed mt-2" style={{ color: 'var(--text-muted)' }}>
          Six lines from the FY27 balanced column, adding to {usd(ATHLETICS_SPLIT.fixed)}.
          Source: {ATHLETICS_SPLIT.source}
        </p>
      </div>

      <div className="mt-3 pt-3 border-t" style={{ borderColor: 'var(--grid)' }}>
        <div className="flex items-baseline justify-between gap-3 mb-1">
          <h4 className="text-[12px] font-bold">
            Put back what the balanced budget already cut
          </h4>
          {restoreTotal > 0 && (
            <span className="text-[13px] font-bold tnum"
              style={{ color: 'var(--series-revenue)' }}>+{usd(restoreTotal)}</span>
          )}
        </div>
        <p className="text-[12px] leading-relaxed mb-2" style={{ color: 'var(--text-secondary)' }}>
          Middle school sports, the buses and the coaching stipends are gone, so cutting
          them again saves nothing &mdash; the live question is what it costs to have them
          back. Each of these <strong>adds</strong> to the gap.
        </p>
        <ul>
          {ATHLETIC_RESTORES.map(r => {
            const key = restoreId(r.id)
            const on = (state[key] ?? 0) > 0
            return (
              <li key={r.id}>
                <label className="flex items-center gap-2.5 py-1.5 cursor-pointer">
                  <input type="checkbox" checked={on}
                    onChange={e => {
                      const next = { ...state }
                      if (e.target.checked) next[key] = 1
                      else delete next[key]
                      setState(next)
                    }}
                    className="shrink-0" style={{ accentColor: 'var(--series-revenue)' }} />
                  <span className="flex-1 min-w-0 text-[12px] leading-snug">
                    {r.label}
                    {r.fte > 0 && (
                      <span className="ml-1.5 text-[10px]" style={{ color: 'var(--text-muted)' }}>
                        {r.fte} FTE
                      </span>
                    )}
                    <span className="block text-[10px]" style={{ color: 'var(--text-muted)' }}>
                      {r.id === 'ms_freshman_coaches'
                        ? `Coaching stipends for all ${MS_SPORTS.length} middle school teams `
                          + `and the freshman teams — ${MS_SPORTS.reduce((a, x) => a + x.students, 0)} `
                          + 'participations'
                        : r.impact}
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
        <p className="text-[11px] mt-1.5" style={{ color: 'var(--text-muted)' }}>
          Putting all four back costs {usd(fullRestore)} and rebuilds the{' '}
          {usd(ATHLETICS_SPLIT.total + fullRestore)} program the district ran before the
          override failed.
        </p>
      </div>

      <p className="text-[10px] leading-relaxed mt-3" style={{ color: 'var(--text-muted)' }}>
        The numbered order the slider follows is <strong>our judgment</strong>, not the
        district&rsquo;s: teams are given up in order of cost per athlete, highest first,
        so each step displaces as few students as the money allows. No ranking of teams is
        neutral &mdash; tick them individually if you disagree with ours.{' '}
        Per-team figures spread the FY27 coaching-and-equipment pool across teams using the
        district's published per-sport costs as weights. Those published figures are from an
        FY24 athletics document and total {usd(MODEL.athletics.perSportTotal)} — more than
        the whole FY27 athletics budget — so they are used for relative size, not as
        absolute savings. Source: {ATHLETICS_SPLIT.source}
      </p>
    </div>
  )
}
