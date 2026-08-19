import {
  MODEL, usd, ladderRungs, ladderLawful, ladderTaken, ladderToggle, ladderMask,
  ladderContiguous, ladderUnlawful, type Lever,
} from '../model/engine'

/** A ladder lever, opened right up.
 *
 *  The slider on the workbench is a dial: it shows the rung you just crossed and nothing
 *  more. This is the argument behind it — every line, what it costs, what the district
 *  loses, and the point at which the ladder simply stops because the remaining posts are
 *  ones a Massachusetts district is required to have. Clicking a rung is the same control
 *  as dragging the slider to it. */
export function LadderDetail({ id, value, setValue }: {
  id: string; value: number; setValue: (n: number) => void
}) {
  const lever = MODEL.levers.find(l => l.id === id) as Lever | undefined
  if (!lever?.rungs) return null
  // What the ladder is a share OF — the published administration total, not a constant
  // typed into this file.
  const pool = MODEL.buckets.admin
  const rungs = ladderRungs(lever)
  const chosen = ladderTaken(lever, value)
  const taken = chosen.length
  const total = chosen.reduce((s, r) => s + r.amount, 0)
  const fte = chosen.reduce((s, r) => s + r.fte, 0)
  const inOrder = ladderContiguous(value)
  const wall = lever.rungs.filter(r => r.blocked)
  const wallTotal = wall.reduce((s, r) => s + r.amount, 0)
  const unlawful = ladderUnlawful(lever, value)
  const unlawfulTotal = unlawful.reduce((s, r) => s + r.amount, 0)
  const lawfulCount = ladderLawful(lever).length

  let running = 0
  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-4 mb-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest mb-1"
            style={{ color: 'var(--text-muted)' }}>
            {taken} of {rungs.length} cut{fte > 0 && ` · ${fte.toFixed(1)} FTE`}
          </p>
          <p className="text-3xl font-bold tnum leading-none"
            style={{ color: total > 0 ? 'var(--status-critical)' : 'var(--text-muted)' }}>
            {usd(total)}
          </p>
        </div>
        <div className="max-w-sm">
          <p className="text-[12px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            Tick any position to cut it. They are independent &mdash; keep the middle
            school clerk and cut the curriculum director if that is your judgement.
          </p>
          <p className="text-[11px] leading-relaxed mt-1.5"
            style={{ color: inOrder ? 'var(--text-muted)' : 'var(--status-serious)' }}>
            {inOrder
              ? 'The slider above is a shortcut for taking them in order, least painful '
                + 'first. Tick out of order and it stops matching.'
              : `Your picks are out of order, so the slider above no longer describes them.
                 Dragging it will replace these ${taken} picks with the first ${taken}
                 in order.`}
          </p>
          <div className="flex flex-wrap gap-2 mt-2">
            <button onClick={() => setValue(ladderMask(lawfulCount))}
              className="px-2.5 py-1 rounded-lg text-[11px] font-semibold border"
              style={{ borderColor: 'var(--grid)', color: 'var(--text-secondary)' }}>
              Cut everything a lawful budget can
            </button>
            <button onClick={() => setValue(0)} disabled={taken === 0}
              className="px-2.5 py-1 rounded-lg text-[11px] font-semibold border disabled:opacity-30"
              style={{ borderColor: 'var(--grid)', color: 'var(--text-secondary)' }}>
              Keep it all
            </button>
          </div>
        </div>
      </div>

      <ol>
        {lever.rungs.map(r => {
          const i = rungs.indexOf(r)
          const on = chosen.includes(r)
          if (!r.blocked && on) running += r.amount
          return (
            <li key={r.id} className="border-b last:border-0"
              style={{ borderColor: 'var(--grid)' }}>
              <label
                className={`w-full text-left flex items-baseline gap-2.5 py-2.5 ${
                  r.blocked ? '' : 'cursor-pointer'}`}>
                <input type="checkbox" checked={on}
                  aria-label={r.blocked
                    ? `Cut ${r.label} — not lawful` : `Cut ${r.label}`}
                  onChange={() => setValue(ladderToggle(value, i))}
                  className="shrink-0"
                  style={{ accentColor: r.blocked ? 'var(--status-warning)'
                    : 'var(--status-critical)' }} />
                {r.blocked && (
                  <span aria-hidden="true" className="shrink-0 text-[13px]"
                    style={{ color: 'var(--status-warning)' }}>⚖</span>
                )}
                <span className="flex-1 min-w-0">
                  <span className="block text-[13px] leading-snug"
                    style={{ textDecoration: on ? 'line-through' : 'none',
                             color: r.blocked ? 'var(--text-muted)'
                               : on ? 'var(--text-muted)' : 'var(--text-primary)' }}>
                    {r.label}
                    {r.fte > 0 && (
                      <span className="ml-1.5 text-[11px] tnum"
                        style={{ color: 'var(--text-muted)' }}>{r.fte} FTE</span>
                    )}
                  </span>
                  <span className="block text-[11px] leading-relaxed mt-0.5"
                    style={{ color: r.blocked ? 'var(--status-warning)'
                      : 'var(--text-secondary)' }}>
                    {r.blocked && <strong>Not lawful to cut. </strong>}{r.note}
                  </span>
                </span>
                <span className="text-right shrink-0">
                  <span className="block text-[13px] font-bold tnum"
                    style={{ color: r.blocked ? 'var(--text-muted)'
                      : on ? 'var(--status-critical)' : 'var(--text-secondary)' }}>
                    {usd(r.amount)}
                  </span>
                  {on && (
                    <span className="block text-[10px] tnum"
                      style={{ color: 'var(--text-muted)' }}>
                      running {usd(running)}
                    </span>
                  )}
                </span>
              </label>
            </li>
          )
        })}
      </ol>

      {unlawful.length > 0 && (
        <div className="rounded-lg p-3 mt-4 border"
          style={{ borderColor: 'var(--status-warning)',
                   background: 'color-mix(in srgb, var(--status-warning) 10%, transparent)' }}>
          <p className="text-[12px] leading-relaxed">
            <strong style={{ color: 'var(--status-warning)' }}>
              <span aria-hidden="true">⚖ </span>
              {usd(unlawfulTotal)} of this is not a budget the district may adopt.
            </strong>{' '}
            You have cut {unlawful.length}{' '}
            {unlawful.length === 1 ? 'role' : 'roles'} the Commonwealth requires
            &mdash; {unlawful.map(r => r.label).join(', ')}. The saving is real
            arithmetic and it is counted above, but a district that filed this budget
            would be told to file a different one. Treat it as an answer to &ldquo;how
            much is even there?&rdquo;, not as a proposal.
          </p>
        </div>
      )}

      <div className="mt-4 pt-3 border-t" style={{ borderColor: 'var(--grid)' }}>
        <p className="text-[12px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          <strong>Where a lawful budget stops.</strong> Taking every line a district may
          actually cut saves {usd(lever.cap)} &mdash;{' '}
          {((lever.cap / pool) * 100).toFixed(0)}% of the {usd(pool)} the district spends
          on administration. The {usd(wallTotal)} past that is {wall.length} roles
          Massachusetts requires a district to have. You can tick them anyway &mdash; the
          number is the point, because even taking all of it does not close the gap on its
          own. That is why &ldquo;cut administration&rdquo; is a smaller answer than it
          sounds, not why it is a bad idea.
        </p>
        <div className="rounded-lg p-3 mt-3" style={{ background: 'var(--surface-3)' }}>
          <h4 className="text-[12px] font-bold mb-1">Assistant principals</h4>
          <p className="text-[11px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            Lunenburg cuts and rehires assistant principals often, so they deserve their own
            switch &mdash; but <strong>the salary lines do not separate them</strong>. Each
            school is budgeted as one line, &ldquo;Principal/Asst. Prin.&rdquo;, and the
            figure is identical in all four FY27 scenarios, so there is no difference to
            infer a split from. Splitting them here would be a number we invented sitting
            next to numbers we did not. Where the district <em>has</em> priced an assistant
            principal, it is a separate control:
          </p>
          <ul className="text-[11px] leading-relaxed mt-1.5 space-y-1"
            style={{ color: 'var(--text-secondary)' }}>
            <li>
              <strong>High School, half time &rarr; full time &mdash; $90,450.</strong>{' '}
              Cut to half time for FY27 and restored with one-time money. It is its own
              tick box under <em>The September restorations</em>, and not keeping it is a
              real FY28 saving.
            </li>
            <li>
              <strong>Primary / Turkey Hill &mdash; $152,829.</strong> Cut by attrition in
              the FY27 balanced budget, which is why those two schools now share one. It is
              its own tick box under <em>Put back what was already cut</em>, where hiring
              it again is a cost.
            </li>
            <li>
              <strong>Middle School &mdash; not published.</strong> The district has never
              priced this post separately, so this tool does not offer a figure for it.
            </li>
          </ul>
        </div>

        <p className="text-[11px] leading-relaxed mt-2" style={{ color: 'var(--text-muted)' }}>
          Every amount is a line in the FY27 balanced column of the district&rsquo;s
          line-item budget, 23 March 2026. <strong>The order is our judgement</strong>,
          not the district&rsquo;s &mdash; drag past a rung you would have protected and
          you are accepting our ranking, not theirs. The two administrative technology
          lines ($154,981 of contracted services and $145,884 of technology personnel) are
          deliberately not here: they belong to the technology slider, and counting them
          twice is how a model quietly closes a gap it has not closed.
        </p>
      </div>
    </div>
  )
}
