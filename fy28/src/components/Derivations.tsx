import { useState } from 'react'
import { MODEL, usd, type Derivation } from '../model/engine'

const M = MODEL.method

/** `usd` rounds, which is wrong on a page whose whole job is showing exact arithmetic:
 *  a $0.50 rounding gap must not render as "$1". Show cents only when there are cents. */
const money = (n: number) => {
  const cents = Math.abs(n * 100) % 100
  if (cents < 0.5 || cents > 99.5) return usd(n)
  return (n < 0 ? '-' : '') + '$' + Math.abs(n).toLocaleString('en-US',
    { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const KIND_LABEL: Record<Derivation['kind'], string> = {
  lines: 'Budget lines',
  arithmetic: 'Derived from the figures above',
  catalog: 'Program catalog',
  ladder: 'Rung by rung',
}

/** Every rolled-up figure, rebuilt from the lines underneath it.
 *  The whole point is that a reader can check us, so nothing is collapsed away
 *  permanently and nothing that fails to reconcile is hidden. */
export function Derivations() {
  const [open, setOpen] = useState<string | null>('athletics_ladder')
  const [q, setQ] = useState('')

  const needle = q.trim().toLowerCase()
  const shown = needle
    ? M.derivations.filter(d =>
        (d.label + d.question + d.answer).toLowerCase().includes(needle) ||
        (d.lines ?? []).some(l =>
          (l.item + l.group).toLowerCase().includes(needle)) ||
        (d.entries ?? []).some(e => e.name.toLowerCase().includes(needle)))
    : M.derivations

  const unreconciled = M.derivations.filter(d => !d.reconciled).length

  return (
    <div>
      <div className="card p-5 mb-4">
        <div className="grid gap-4 sm:grid-cols-3">
          <Fact label="Figures rebuilt" value={String(M.derivations.length)}
            sub="every roll-up the app quotes" />
          <Fact label="Budget lines named"
            value={String(M.derivations.reduce((n, d) => n + (d.lineCount ?? 0), 0))}
            sub="each one traceable to the district's own spreadsheet" />
          <Fact label="That do not reconcile" value={String(unreconciled)}
            tone={unreconciled === 0 ? 'good' : 'critical'}
            sub={unreconciled === 0
              ? 'every total matches the lines beneath it'
              : 'shown below with the gap, not hidden'} />
        </div>
        <p className="text-[12px] leading-relaxed mt-4 pt-4 border-t"
          style={{ borderColor: 'var(--grid)', color: 'var(--text-secondary)' }}>
          Every figure below is rebuilt from{' '}
          <strong style={{ color: 'var(--text-primary)' }}>{M.sourceDoc}</strong> and
          checked against the number the rest of this app uses. Open one to see the
          individual budget lines and add them up yourself. Where a roll-up depends on a
          judgement call — which lines count as &ldquo;administration&rdquo;, which
          scenario column to read — the judgement is stated rather than buried.
        </p>
      </div>

      <label className="block mb-4">
        <span className="sr-only">Search the budget lines</span>
        <input type="search" value={q} onChange={e => setQ(e.target.value)}
          placeholder="Search a figure or a budget line — try &ldquo;athletic&rdquo;, &ldquo;music&rdquo;, &ldquo;transportation&rdquo;"
          className="w-full px-3 py-2 rounded-lg text-[13px] border"
          style={{ background: 'var(--surface-1)', borderColor: 'var(--grid)',
                   color: 'var(--text-primary)' }} />
      </label>

      {shown.length === 0 && (
        <p className="text-[13px] py-6 text-center" style={{ color: 'var(--text-muted)' }}>
          No figure or budget line matches &ldquo;{q}&rdquo;.
        </p>
      )}

      <div className="space-y-3">
        {shown.map(d => (
          <Card key={d.id} d={d} open={open === d.id}
            onToggle={() => setOpen(open === d.id ? null : d.id)} />
        ))}
      </div>

      <h3 className="text-sm font-bold mt-10 mb-3">
        And the top-line budget itself
      </h3>
      <ScenarioTotals />
    </div>
  )
}

function Card({ d, open, onToggle }: {
  d: Derivation; open: boolean; onToggle: () => void
}) {
  const parts = d.lineCount ?? d.terms?.length ?? d.entries?.length ?? d.rungs?.length ?? 0
  return (
    <div className="card overflow-hidden" id={`derivation-${d.id}`}>
      <button onClick={onToggle} aria-expanded={open}
        className="w-full text-left p-5 flex items-start justify-between gap-4">
        <span className="min-w-0">
          <span className="block text-[13px] font-bold">{d.question}</span>
          <span className="block text-[12px] mt-0.5" style={{ color: 'var(--text-muted)' }}>
            {d.label} · {KIND_LABEL[d.kind]} · {parts}{' '}
            {d.kind === 'lines' ? 'budget lines' : d.kind === 'ladder' ? 'rungs' : 'parts'} · {d.scenario}
          </span>
        </span>
        <span className="shrink-0 text-right">
          <span className="block text-xl font-bold tnum leading-none">{money(d.total)}</span>
          <span className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
            {open ? 'hide the lines' : 'show the lines'}
          </span>
        </span>
      </button>

      {open && (
        <div className="px-5 pb-5">
          <p className="text-[13px] leading-relaxed mb-4"
            style={{ color: 'var(--text-secondary)' }}>{d.answer}</p>

          {d.kind === 'lines' && <LineTable d={d} />}
          {d.kind === 'arithmetic' && <TermTable d={d} />}
          {d.kind === 'catalog' && <EntryTable d={d} />}
          {d.kind === 'ladder' && <LadderTable d={d} />}

          <Reconciliation d={d} />

          {d.notes.length > 0 && (
            <ul className="text-[12px] leading-relaxed mt-4 space-y-2 list-disc pl-4"
              style={{ color: 'var(--text-secondary)' }}>
              {d.notes.map(n => <li key={n.slice(0, 24)}>{n}</li>)}
            </ul>
          )}

          <p className="text-[11px] mt-4 pt-3 border-t"
            style={{ borderColor: 'var(--grid)', color: 'var(--text-muted)' }}>
            Source: {d.source}
          </p>
        </div>
      )}
    </div>
  )
}

function LineTable({ d }: { d: Derivation }) {
  const lines = d.lines ?? []
  // Group by DESE function group so the reader sees the budget's own structure.
  const groups: { group: string; lines: typeof lines }[] = []
  for (const l of lines) {
    const last = groups.at(-1)
    if (last && last.group === l.group) last.lines.push(l)
    else groups.push({ group: l.group, lines: [l] })
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs tnum min-w-[420px]">
        <caption className="sr-only">
          Budget lines making up {d.label}, {d.scenario}
        </caption>
        <thead>
          <tr className="text-left" style={{ color: 'var(--text-muted)' }}>
            <th className="font-semibold py-1.5">Budget line</th>
            <th className="font-semibold py-1.5 text-right">{d.scenario}</th>
          </tr>
        </thead>
        <tbody>
          {groups.map(g => (
            <FragmentRows key={g.group} group={g.group} lines={g.lines} />
          ))}
          <tr className="border-t-2 font-bold" style={{ borderColor: 'var(--axis)' }}>
            <td className="py-2">Total</td>
            <td className="py-2 text-right">{money(d.total)}</td>
          </tr>
        </tbody>
      </table>
    </div>
  )
}

const HISTORY_LABEL: Record<string, string> = {
  fy23_actual: 'FY23 actual', fy24_actual: 'FY24 actual', fy25_actual: 'FY25 actual',
  fy26_final: 'FY26 budget', fy26_actual_td: 'FY26 spent to date',
  fy26_encumb_td: 'FY26 encumbered',
}

function FragmentRows({ group, lines }: {
  group: string
  lines: { group: string; item: string; amount: number
           note?: string; history?: Record<string, number> }[]
}) {
  const subtotal = lines.reduce((n, l) => n + l.amount, 0)
  return (
    <>
      <tr>
        <td colSpan={2} className="pt-3 pb-1 text-[11px] font-bold uppercase tracking-widest"
          style={{ color: 'var(--text-muted)' }}>
          {group}
          {lines.length > 1 && (
            <span className="ml-2 font-normal normal-case tracking-normal tnum">
              {money(subtotal)}
            </span>
          )}
        </td>
      </tr>
      {lines.map(l => (
        <tr key={l.item} className="border-t" style={{ borderColor: 'var(--grid)' }}>
          <td className="py-1.5 pl-3">
            {l.item}
            {l.note && (
              <>
                <span className="ml-2 text-[10px] font-bold uppercase tracking-widest"
                  style={{ color: 'var(--status-serious)' }}>
                  <span aria-hidden="true">⚠ </span>read this
                </span>
                <span className="block text-[11px] leading-relaxed mt-1 pl-0 pr-4 normal-case"
                  style={{ color: 'var(--text-secondary)' }}>{l.note}</span>
                {l.history && (
                  <span className="flex flex-wrap gap-x-3 gap-y-0.5 mt-1 text-[11px]"
                    style={{ color: 'var(--text-muted)' }}>
                    {Object.entries(l.history).map(([k, v]) => (
                      <span key={k}>{HISTORY_LABEL[k] ?? k} {money(v)}</span>
                    ))}
                  </span>
                )}
              </>
            )}
          </td>
          <td className="py-1.5 text-right align-top">{money(l.amount)}</td>
        </tr>
      ))}
    </>
  )
}

function TermTable({ d }: { d: Derivation }) {
  return (
    <table className="w-full text-xs tnum">
      <tbody>
        {(d.terms ?? []).map(t => (
          <tr key={t.ref} className="border-t" style={{ borderColor: 'var(--grid)' }}>
            <td className="py-1.5">
              <span className="font-bold mr-2" aria-hidden="true">
                {t.sign < 0 ? '−' : '+'}
              </span>
              <a href={`#derivation-${t.ref}`} className="underline">{t.label}</a>
            </td>
            <td className="py-1.5 text-right">{money(t.amount)}</td>
          </tr>
        ))}
        <tr className="border-t-2 font-bold" style={{ borderColor: 'var(--axis)' }}>
          <td className="py-2">Total</td>
          <td className="py-2 text-right">{money(d.total)}</td>
        </tr>
      </tbody>
    </table>
  )
}

function EntryTable({ d }: { d: Derivation }) {
  const entries = d.entries ?? []
  const estimated = d.estimatedAmount ?? 0
  return (
    <>
      <table className="w-full text-xs tnum">
        <tbody>
          {entries.map(e => (
            <tr key={e.name} className="border-t" style={{ borderColor: 'var(--grid)' }}>
              <td className="py-1.5">
                {e.name}
                <span className="ml-2 text-[10px] uppercase tracking-widest font-bold"
                  style={{ color: e.estimated ? 'var(--status-serious)' : 'var(--text-muted)' }}>
                  {e.estimated ? 'our estimate' : e.status}
                </span>
                <span className="block text-[11px]" style={{ color: 'var(--text-muted)' }}>
                  {M.sourceCodes[e.source] ?? e.source}
                </span>
              </td>
              <td className="py-1.5 text-right align-top">{usd(e.amount)}</td>
            </tr>
          ))}
          <tr className="border-t-2 font-bold" style={{ borderColor: 'var(--axis)' }}>
            <td className="py-2">Total</td>
            <td className="py-2 text-right">{money(d.total)}</td>
          </tr>
        </tbody>
      </table>
      {estimated > 0 && (
        <p className="text-[12px] mt-3 p-2.5 rounded-lg border"
          style={{ borderColor: 'var(--status-serious)', color: 'var(--text-secondary)' }}>
          <strong style={{ color: 'var(--text-primary)' }}>{usd(estimated)}</strong> of
          this total — {Math.round((estimated / d.total) * 100)}% — is our estimate rather
          than a published district figure.
        </p>
      )}
    </>
  )
}

/** The athletics ladder: each rung adds one line to the one below it, and each carries
 *  the fee that would self-fund it. The jump when the buses go back is the whole point. */
function LadderTable({ d }: { d: Derivation }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs tnum min-w-[520px]">
        <caption className="sr-only">
          Athletics cost by basis, with the fee that would self-fund each
        </caption>
        <thead>
          <tr className="text-left" style={{ color: 'var(--text-muted)' }}>
            <th className="font-semibold py-1.5">Basis</th>
            <th className="font-semibold py-1.5 text-right">Adds</th>
            <th className="font-semibold py-1.5 text-right">Costs</th>
            <th className="font-semibold py-1.5 text-right">Fees cover</th>
            <th className="font-semibold py-1.5 text-right">Self-funds at</th>
          </tr>
        </thead>
        <tbody>
          {(d.rungs ?? []).map(r => {
            const reach = r.selfFundFee !== null
            return (
              <tr key={r.id} className="border-t align-top"
                style={{ borderColor: 'var(--grid)' }}>
                <td className="py-2">
                  {r.label}
                  {!r.published && (
                    <span className="ml-2 text-[10px] font-bold uppercase tracking-widest"
                      style={{ color: 'var(--status-serious)' }}>our construction</span>
                  )}
                  <span className="block text-[11px] font-normal"
                    style={{ color: 'var(--text-muted)' }}>{r.scenario}</span>
                </td>
                <td className="py-2 text-right" style={{ color: 'var(--text-muted)' }}>
                  {r.add === null ? '—' : (
                    <>
                      +{money(r.add)}
                      <span className="block text-[11px]">{r.addLabel}</span>
                    </>
                  )}
                </td>
                <td className="py-2 text-right font-semibold">{money(r.running)}</td>
                <td className="py-2 text-right">{Math.round(r.coverageNow * 100)}%</td>
                <td className="py-2 text-right font-bold"
                  style={{ color: reach ? 'var(--text-primary)' : 'var(--status-critical)' }}>
                  {reach ? usd(r.selfFundFee as number) : 'out of reach'}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
      <ul className="text-[11px] mt-3 space-y-1.5" style={{ color: 'var(--text-muted)' }}>
        {(d.rungs ?? []).map(r => (
          <li key={r.id}><strong>{r.label}:</strong> {r.sub}</li>
        ))}
      </ul>
    </div>
  )
}

function Reconciliation({ d }: { d: Derivation }) {
  const ok = d.reconciled
  const exact = Math.abs(d.delta) < 0.005
  return (
    <p className="text-[12px] mt-4 flex items-baseline gap-2"
      style={{ color: ok ? 'var(--status-good)' : 'var(--status-critical)' }}>
      <span aria-hidden="true">{ok ? '✓' : '✕'}</span>
      <span style={{ color: 'var(--text-secondary)' }}>
        {ok ? 'Reconciles. ' : 'Does not reconcile. '}
        The lines above total <strong className="tnum">{money(d.total)}</strong>; the app
        quotes <strong className="tnum">{money(d.expected)}</strong>
        {exact
          ? '. Exact match.'
          : <> — a difference of <strong className="tnum">{money(Math.abs(d.delta))}</strong>
              {ok ? ', which is rounding.' : '. We have not resolved it.'}</>}
      </span>
    </p>
  )
}

/** The district's own scenario totals, rebuilt line by line. */
function ScenarioTotals() {
  return (
    <div className="card p-5">
      <div className="overflow-x-auto">
        <table className="w-full text-xs tnum min-w-[540px]">
          <caption className="sr-only">
            FY27 budget scenario totals, stated versus rebuilt from the detail lines
          </caption>
          <thead>
            <tr className="text-left" style={{ color: 'var(--text-muted)' }}>
              <th className="font-semibold py-1.5">Scenario</th>
              <th className="font-semibold py-1.5 text-right">Detail lines</th>
              <th className="font-semibold py-1.5 text-right">Salary reserve</th>
              <th className="font-semibold py-1.5 text-right">Rebuilt</th>
              <th className="font-semibold py-1.5 text-right">Stated</th>
              <th className="font-semibold py-1.5 text-right">Difference</th>
            </tr>
          </thead>
          <tbody>
            {M.scenarioTotals.map(s => (
              <tr key={s.column} className="border-t" style={{ borderColor: 'var(--grid)' }}>
                <td className="py-1.5 font-medium">{s.label}</td>
                <td className="py-1.5 text-right">{money(s.detailLines)}</td>
                <td className="py-1.5 text-right">{money(s.salaryReserve)}</td>
                <td className="py-1.5 text-right font-semibold">{money(s.rebuilt)}</td>
                <td className="py-1.5 text-right">{money(s.stated)}</td>
                <td className="py-1.5 text-right"
                  style={{ color: s.reconciled ? 'var(--status-good)' : 'var(--status-critical)' }}>
                  {s.delta === 0 ? 'exact' : money(Math.abs(s.delta))}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-[11px] mt-3" style={{ color: 'var(--text-muted)' }}>
        {M.scenarioNote}
      </p>
    </div>
  )
}

function Fact({ label, value, sub, tone }: {
  label: string; value: string; sub: string; tone?: 'good' | 'critical'
}) {
  return (
    <div>
      <p className="text-[11px] font-bold uppercase tracking-widest"
        style={{ color: 'var(--text-muted)' }}>{label}</p>
      <p className="text-2xl font-bold tnum leading-tight"
        style={{ color: tone === 'good' ? 'var(--status-good)'
          : tone === 'critical' ? 'var(--status-critical)' : 'var(--text-primary)' }}>
        {value}
      </p>
      <p className="text-[12px]" style={{ color: 'var(--text-secondary)' }}>{sub}</p>
    </div>
  )
}
