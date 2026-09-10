import { useState } from 'react'
import { MODEL, usd, type CostColumn } from '../model/engine'
import { ATHLETICS_SPLIT } from '../model/cuts'
import { Basis } from './Basis'
import { abs } from '../lib/abs'

/** WHAT A SPORT COSTS, ACCORDING TO THREE DOCUMENTS THAT DISAGREE.
 *
 *  This is the caveat that cannot be a footnote. Everywhere else on this site a per-sport
 *  figure is presented and a reader uses it to decide which team to give up; three
 *  documents from the same district state three different figures for the same sport in
 *  the same year, and the district has published no reconciliation. That has to be seen
 *  BEFORE the table, not under it.
 *
 *  Rule 7 governs every sentence here. The disagreement is a measurement. Why the three
 *  differ is not — a programmatic cost, an all-in cost and a season's booked expenses
 *  would legitimately differ, and no document says which each column is. Nothing here
 *  says one is wrong.
 *
 *  Every figure is computed in `model/athletics_sources.py`. Nothing is typed. */

const C = MODEL.athletics.costSources

export const COLUMN_LABEL: Record<CostColumn, string> = {
  costsBySport: 'Athletic Program Costs by Sport',
  deck: 'The 5/1/2024 funding deck',
  workbook: 'The district’s by-sport workbook',
}

export const COLUMN_SHORT: Record<CostColumn, string> = {
  costsBySport: 'Costs by Sport',
  deck: '5/1/2024 deck',
  workbook: `Workbook FY${String(C.fy).slice(2)}`,
}

export const COLUMNS = Object.keys(C.totals) as CostColumn[]

/** How many teams the three columns describe. Exported so a page can state the count
 *  without recounting it — one computation, one number. */
export const TEAM_COUNT = C.count

/** Per-sport costs by column, keyed by sport name, for anything that needs to re-price
 *  the roster on a reader's chosen basis. */
export const COSTS_BY_SPORT = new Map(C.sports.map(s => [s.name, s]))

export function columnTotal(col: CostColumn) { return C.totals[col] }

/** The panel. Leads with the disagreement, then the per-sport detail, then the method. */
export function CostDisagreement({ detail = true, onFullTable }: {
  /** The per-sport table. Off where the panel rides above a control rather than above a
   *  table of its own — the disagreement still leads, the 25 rows do not repeat. */
  detail?: boolean
  onFullTable?: () => void
} = {}) {
  const [open, setOpen] = useState(false)
  const [sort, setSort] = useState<'spread' | 'name'>('spread')
  const rows = [...C.sports].sort((a, b) =>
    sort === 'name' ? a.name.localeCompare(b.name)
      : (b.spreadPct ?? 0) - (a.spreadPct ?? 0))
  const widest = rows[0]
  const maxHigh = Math.max(...C.sports.map(s => s.high))
  const wbYears = Object.keys(C.workbookYears).sort()

  return (
    <div className="card p-5" style={{ borderColor: 'var(--status-bad)', borderWidth: 2 }}>
      <div className="flex flex-wrap items-baseline justify-between gap-2 mb-1">
        <h3 className="text-sm font-bold">
          Three documents, three answers to what a sport costs
        </h3>
        <Basis level="contested" />
      </div>

      {/* The thing first: how far apart they are, in total and at the extreme. */}
      <div className="grid gap-3 sm:grid-cols-3 mt-3 mb-4">
        {COLUMNS.map(col => (
          <div key={col} className="rounded-lg p-3 border"
            style={{ borderColor: 'var(--grid)', background: 'var(--surface-1)' }}>
            <p className="text-[10px] font-bold uppercase tracking-widest leading-tight"
              style={{ color: 'var(--text-muted)' }}>{COLUMN_LABEL[col]}</p>
            <p className="text-2xl font-bold tnum mt-1">{usd(C.totals[col])}</p>
            <p className="text-[10px] mt-0.5" style={{ color: 'var(--text-muted)' }}>
              all {C.count} teams, FY{String(C.fy).slice(2)}
              {col === C.derivedColumn ? ' · derived from the extract' : ' · transcribed'}
            </p>
          </div>
        ))}
      </div>

      <p className="text-[13px] leading-relaxed">
        The three totals span <strong>{usd(C.totalSpread)}</strong> — the highest is{' '}
        <strong>{C.totalSpreadPct.toFixed(0)}% above</strong> the lowest. Per sport it is
        far wider: <strong>{widest.name}</strong> is stated at {usd(widest.low)} in one
        document and {usd(widest.high)} in another, a difference of{' '}
        <strong>{(widest.spreadPct ?? 0).toFixed(0)}%</strong>.{' '}
        {C.agreeing === 0
          ? <><strong>No team</strong> carries the same figure in all three.</>
          : <>Only <strong>{C.agreeing} of {C.count}</strong> teams carry the same figure
              in all three.</>}
      </p>
      <p className="text-[13px] leading-relaxed mt-2" style={{ color: 'var(--text-secondary)' }}>
        <strong style={{ color: 'var(--text-primary)' }}>What this does not show. </strong>
        Which figure is right, or that any of them is wrong. A programmatic cost, an all-in
        cost and a season’s booked expenses would all differ legitimately, and no document
        we hold says which each column is. Nothing published reconciles them.{' '}
        <strong style={{ color: 'var(--text-primary)' }}>What would settle it. </strong>
        A reconciliation from the district of its own three statements, sport by sport.
      </p>

      {!detail && onFullTable && (
        <button onClick={onFullTable} className="text-[12px] font-semibold underline mt-3"
          style={{ color: 'var(--series-cost)' }}>
          See all {C.count} teams in all three documents &rarr;
        </button>
      )}

      {detail && <>
      {/* The per-sport detail. */}
      <div className="flex flex-wrap items-baseline justify-between gap-2 mt-5 mb-2">
        <h4 className="text-[12px] font-bold">Every team, in all three documents</h4>
        <span className="flex gap-1 shrink-0">
          {([['spread', 'Widest gap'], ['name', 'A–Z']] as const).map(([k, label]) => (
            <button key={k} onClick={() => setSort(k)} aria-pressed={sort === k}
              className="px-2 py-0.5 rounded text-[10px] font-semibold border"
              style={{ borderColor: sort === k ? 'var(--series-cost)' : 'var(--grid)',
                       background: sort === k ? 'var(--series-cost)' : 'var(--surface-1)',
                       color: sort === k ? '#fff' : 'var(--text-secondary)' }}>{label}</button>
          ))}
        </span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-[12px] tnum sm:min-w-[620px]">
          <caption className="sr-only">
            Each Lunenburg team with the cost stated by each of three district documents
            for FY{C.fy}, and the range between them
          </caption>
          <thead>
            <tr className="text-left" style={{ color: 'var(--text-muted)' }}>
              <th className="font-semibold py-1.5">Team</th>
              {COLUMNS.map(col => (
                <th key={col} className="font-semibold py-1.5 text-right pl-3">
                  {COLUMN_SHORT[col]}
                </th>
              ))}
              <th className="font-semibold py-1.5 pl-3">Range</th>
              <th className="font-semibold py-1.5 text-right pl-3">Gap</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(s => (
              <tr key={s.name} className="border-t" style={{ borderColor: 'var(--grid)' }}>
                <td className="py-1.5 pr-2">{s.name}</td>
                {COLUMNS.map(col => {
                  const v = s.columns[col]
                  const extreme = v !== undefined && (v === s.low || v === s.high)
                    && s.spread > 0
                  return (
                    <td key={col} className="py-1.5 text-right pl-3"
                      style={{ color: v === undefined ? 'var(--text-muted)'
                        : extreme && v === s.high ? 'var(--status-bad)'
                        : extreme ? 'var(--text-secondary)' : undefined }}>
                      {v === undefined ? '—' : usd(v)}
                    </td>
                  )
                })}
                <td className="py-1.5 pl-3 w-32">
                  <span className="block h-2 rounded-full relative"
                    style={{ background: 'var(--surface-3)' }}>
                    <span className="absolute h-2 rounded-full"
                      style={{ left: `${(s.low / maxHigh) * 100}%`,
                               width: `${Math.max(1.5, ((s.high - s.low) / maxHigh) * 100)}%`,
                               background: 'var(--status-bad)' }} />
                  </span>
                </td>
                <td className="py-1.5 text-right pl-3 font-semibold"
                  style={{ color: (s.spreadPct ?? 0) >= 100 ? 'var(--status-bad)'
                    : (s.spreadPct ?? 0) > 0 ? 'var(--status-serious)' : 'var(--status-good)' }}>
                  {s.spreadPct === null ? '—'
                    : s.spreadPct === 0 ? 'agree' : `+${s.spreadPct.toFixed(0)}%`}
                </td>
              </tr>
            ))}
            <tr className="border-t-2 font-bold" style={{ borderColor: 'var(--axis)' }}>
              <td className="py-2">All {C.count} teams</td>
              {COLUMNS.map(col => (
                <td key={col} className="py-2 text-right pl-3">{usd(C.totals[col])}</td>
              ))}
              <td />
              <td className="py-2 text-right pl-3" style={{ color: 'var(--status-bad)' }}>
                +{C.totalSpreadPct.toFixed(0)}%
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* The key comes AFTER the thing it is a key to. */}
      <div className="mt-4 pt-3 border-t space-y-2" style={{ borderColor: 'var(--grid)' }}>
        {COLUMNS.map(col => (
          <p key={col} className="text-[12px] leading-relaxed">
            <span className="font-bold">{COLUMN_LABEL[col]}. </span>
            <span style={{ color: 'var(--text-secondary)' }}>{C.columnMeaning[col]}</span>{' '}
            <Basis level="stated">
              {col === C.derivedColumn
                ? 'derived from our extract, cell by cell'
                : 'transcribed from the document; no machine-readable extract exists'}
            </Basis>
          </p>
        ))}
      </div>

      <button onClick={() => setOpen(!open)}
        className="text-[12px] font-semibold underline mt-3"
        style={{ color: 'var(--text-secondary)' }}>
        {open ? 'Hide' : 'Show'} how the derived column was built, and what it excludes
      </button>
      {open && (
        <div className="mt-2 text-[12px] leading-relaxed space-y-2"
          style={{ color: 'var(--text-secondary)' }}>
          <p>
            The workbook column is not typed anywhere. It is read out of{' '}
            <a className="underline" href={abs('/docs/data/athletics-by-sport.csv')}>
              athletics-by-sport.csv</a> — {C.source} Every figure carries the cell it came
            from: {widest.name} is{' '}
            {widest.cells.length ? widest.cells.join(' + ') : 'absent from the workbook'}.
            The build refuses to publish the column at all unless every team resolves and
            the mapped rows add back to the workbook’s own column total.
          </p>
          <p>
            <strong style={{ color: 'var(--text-primary)' }}>Two workbook rows are held
            out</strong>, named rather than dropped:{' '}
            {C.excluded.map(e => `${e.sport} (${e.level}) — ${e.why}`).join(' ')}
          </p>
          <p>
            The workbook covers more than one year, and they are kept apart rather than
            blended:{' '}
            {wbYears.map((fy, i) => (
              <span key={fy}>
                {i > 0 && ', '}FY{fy.slice(2)} {usd(C.workbookYears[fy].total)}
              </span>
            ))}
            . Only FY{C.fy} is compared with the other two columns, because both of those
            are FY{String(C.fy).slice(2)}-basis documents and comparing across years would
            measure the year as well as the disagreement.
          </p>
        </div>
      )}
      </>}
    </div>
  )
}

/** WHAT CUTTING A TEAM ACTUALLY SAVES — the part that changes a vote.
 *
 *  A resident reads a per-sport figure as the saving from folding that team. It is not,
 *  and the district's own workbook shows why in its own hand: a notes column headed
 *  `Costs for all 3 Seasons` in which league membership, trainer supplies, CPR
 *  certification and the online forms subscription are divided by three and pushed into
 *  season totals. Those costs sit INSIDE a per-sport figure and do not leave with a team.
 *
 *  The model already handles this and has since the cut board was built — this says so
 *  on the page, where the decision is made, rather than only in the code. */
export function WhatCuttingSaves() {
  const notes = C.sharedNotes
  const pool = ATHLETICS_SPLIT.variable
  const fixed = ATHLETICS_SPLIT.fixed
  const total = ATHLETICS_SPLIT.total
  const fixedPct = total > 0 ? (fixed / total) * 100 : 0

  return (
    <div className="card p-5" style={{ borderColor: 'var(--status-serious)' }}>
      <h3 className="text-sm font-bold mb-1">
        Cutting a team does not save what the team costs
      </h3>
      <p className="text-[13px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
        Of the {usd(total)} the adopted budget spends on athletics,{' '}
        <strong style={{ color: 'var(--text-primary)' }}>{usd(fixed)}</strong> —{' '}
        {fixedPct.toFixed(0)}% of it — is the athletic director, the trainer, the
        secretary, insurance and league dues, and it is paid whether the school fields
        twenty teams or one. Only <strong style={{ color: 'var(--text-primary)' }}>
        {usd(pool)}</strong> of coaching stipends and equipment moves when a team folds.
      </p>
      <p className="text-[13px] leading-relaxed mt-2" style={{ color: 'var(--text-secondary)' }}>
        <strong style={{ color: 'var(--text-primary)' }}>The cut board is built on that
        split.</strong> It spreads the {usd(pool)} pool across the teams using the
        published per-sport figures as <em>weights</em> — relative size — and never as
        absolute savings. That is why one team is worth far less there than its cost in
        any of the three columns above, and why cost per surviving athlete <em>rises</em>{' '}
        as teams are cut.
      </p>

      <p className="text-[12px] font-bold uppercase tracking-widest mt-4 mb-1"
        style={{ color: 'var(--text-muted)' }}>
        The district divides shared costs itself, in the same workbook
      </p>
      <p className="text-[12px] leading-relaxed mb-2" style={{ color: 'var(--text-secondary)' }}>
        Beside the per-sport totals sits a column headed{' '}
        <em>{C.sharedNoteColumn}</em>. These are its {notes.length} entries, exactly as the
        cells read — district-wide costs being split three ways and pushed into season
        totals, which is how they end up inside a per-sport figure.
      </p>
      <ul className="text-[12px] tnum grid gap-x-6 sm:grid-cols-2"
        style={{ color: 'var(--text-secondary)' }}>
        {notes.map(n => (
          <li key={n.cell} className="flex justify-between gap-3 border-b py-1"
            style={{ borderColor: 'var(--grid)' }}>
            <span>“{n.note}”</span>
            <span className="shrink-0" style={{ color: 'var(--text-muted)' }}>{n.cell}</span>
          </li>
        ))}
      </ul>
      <p className="text-[12px] leading-relaxed mt-3 pt-3 border-t"
        style={{ borderColor: 'var(--grid)', color: 'var(--text-secondary)' }}>
        <strong style={{ color: 'var(--text-primary)' }}>What this does not show. </strong>
        Which shared costs would actually fall if a team went. A league assessment, a
        trainer’s hours and an insurance premium may each move with the number of teams, or
        not at all, and nothing here tests it. The split above is the district’s FY27
        budget lines, not a study of what is avoidable.
      </p>
      <p className="text-[12px] leading-relaxed mt-2" style={{ color: 'var(--text-secondary)' }}>
        <strong style={{ color: 'var(--text-primary)' }}>It has been asked out loud. </strong>
        School Committee minutes of 26 February 2025 record, in the same item as the fee
        rise, that <em>“Mr. Bigelow is asked to suggest a sport to cut.”</em>{' '}
        <a className="underline"
          href={abs('/docs/minutes/text/school-committee/2025-02-26-minutes-7076.txt')}>
          Read the minutes</a>. Sixteen months later, on 24 June 2026, the committee heard
        that questions about the cost of middle school athletics had received answers that
        were <em>“inconsistent”</em>, and that “the community still lacks a clear
        understanding of both the financial picture and the path forward.”{' '}
        <a className="underline"
          href={abs('/docs/minutes/text/school-committee/2026-06-24-minutes-7869.txt')}>
          Read the minutes</a>. The three columns above are what a person answering that
        question has to work with.
      </p>
      <p className="text-[11px] mt-2" style={{ color: 'var(--text-muted)' }}>
        The meeting archive searched for those quotes covers 2025 onward. Anything said
        about a sport’s cost in 2023 or 2024 is not in it yet.
      </p>
    </div>
  )
}
