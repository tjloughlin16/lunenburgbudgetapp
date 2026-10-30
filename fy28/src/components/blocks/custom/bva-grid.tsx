/** EACH LINE, YEAR BY YEAR (budget-against-actual). One row per school line (by account), one
 *  column per fiscal year from FY2018: each cell what the line spent less what it was voted that
 *  year, shaded by how far against the vote -- warm where it spent past it, cool where under --
 *  with a mark for each flag it carried (U underfunded, O overbudgeted, R restarted high).
 *
 *  The years before the journal are the Finance Committee's workbook and are shaded apart; a
 *  line-year is read from one record only (scripts/line_flags.py). Each journal year's heading
 *  opens that year in the FY breakdown, where the year's flagged lines are listed with their
 *  transfers: the pattern across years here, the year's story there (TJ, 29 October 2026).
 *  Every string and figure is the payload's (scripts/build_budget_against_actual.py, grid()). */
import { useMemo, useState } from 'react'
import type { CustomProps } from './index'
import { itemHrefs, useItemIndex } from './fy-items'
import { Chip, WideScroll } from './fy-shared'
import { FLAG_TONE, type FlagKey } from './fy-flags'

/** [miss text, flag letters, spent / voted (null: nothing voted), voted text, spent text] */
type Cell = [string, string, number | null, string, string] | null
type Row = { name: string; account: string; cat: string; c: Cell[]; s: number; nf: number }
type Col = { fy: string; src: 'workbook' | 'ledger'; href: string | null; n: Record<FlagKey, string>; lines: string }
type Data = { years: Col[]; rows: Row[]; flags: Record<FlagKey, string>; text: Record<string, string> & { mark: Record<'u' | 'o' | 'r', string> } }

const muted = { color: 'var(--text-muted)' }
const link = { color: 'var(--link, var(--thread-2))' }
const FIRST = 40
const LETTER: Record<string, FlagKey> = { u: 'under', o: 'over', r: 'restart' }

/** How far from the vote, as a background: log2 of spent / voted, clipped at a factor of two. */
function shade(r: number | null): string | undefined {
  if (r == null || r <= 0) return undefined
  const f = Math.max(-1, Math.min(1, Math.log2(r)))
  if (Math.abs(f) < 0.03) return undefined
  const pct = Math.round(8 + Math.abs(f) * 40)
  return `color-mix(in srgb, ${f > 0 ? 'var(--thread-1)' : 'var(--thread-2)'} ${pct}%, transparent)`
}

export default function BvaGrid({ data, alt }: CustomProps) {
  const d = data as Data
  const t = d.text
  const hrefs = itemHrefs(useItemIndex())
  const [q, setQ] = useState('')
  const [only, setOnly] = useState(false)
  const [all, setAll] = useState(false)
  const [sort, setSort] = useState<{ k: number | 'name' | 'cat' | 'nf' | 's'; dir: 1 | -1 }>({ k: 's', dir: -1 })
  const rows = useMemo(() => {
    const ql = q.trim().toLowerCase()
    const out = d.rows.filter(r => (!only || r.nf > 0) && (!ql || `${r.name} ${r.cat}`.toLowerCase().includes(ql)))
    const k = sort.k
    return [...out].sort((a, b) => k === 'name' ? sort.dir * a.name.localeCompare(b.name)
      : k === 'cat' ? sort.dir * a.cat.localeCompare(b.cat) || b.s - a.s
        : k === 'nf' ? sort.dir * (a.nf - b.nf) || b.s - a.s
          : k === 's' ? sort.dir * (a.s - b.s)
            : ((a.c[k] ? 0 : 1) - (b.c[k] ? 0 : 1)) || sort.dir * ((a.c[k]?.[2] ?? 1) - (b.c[k]?.[2] ?? 1)))
  }, [d, q, only, sort])
  const shown = all || q ? rows : rows.slice(0, FIRST)
  const firstLedger = d.years.findIndex(y => y.src === 'ledger')
  const by = (k: typeof sort.k) => setSort(s => ({ k, dir: s.k === k ? (-s.dir as 1 | -1) : (typeof k === 'number' ? 1 : k === 'name' || k === 'cat' ? 1 : -1) }))
  const arrow = (k: typeof sort.k) => sort.k === k ? (sort.dir < 0 ? ' ↓' : ' ↑') : ''
  return (
    <figure aria-label={alt}>
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-[12.5px]">
        {(['u', 'o', 'r'] as const).map(l => (
          <span key={l} className="inline-flex items-center gap-1.5">
            <span className="font-bold text-[11px] px-1 rounded" style={{ color: FLAG_TONE[LETTER[l]], border: `1px solid ${FLAG_TONE[LETTER[l]]}` }}>{t.mark[l]}</span>
            {d.flags[LETTER[l]]}</span>))}
        <span className="inline-flex items-center gap-1.5"><span className="inline-block w-3 h-3 rounded-sm" style={{ background: shade(1.6) }} />{t.over}</span>
        <span className="inline-flex items-center gap-1.5"><span className="inline-block w-3 h-3 rounded-sm" style={{ background: shade(0.6) }} />{t.under}</span>
      </div>
      <p className="text-[12.5px] mt-1" style={muted}>{t.cell}</p>
      <div className="flex flex-wrap gap-2 items-center mt-3">
        <input value={q} onChange={e => setQ(e.target.value)} placeholder={t.filter} aria-label={t.filter}
          className="w-full max-w-xs px-2 py-1 rounded border text-[13px]" style={{ borderColor: 'var(--grid)', background: 'var(--surface-1)', color: 'var(--text-primary)' }} />
        <Chip on={!only} onClick={() => setOnly(false)}>{t.every}</Chip>
        <Chip on={only} onClick={() => setOnly(true)}>{t.only}</Chip>
        <span className="text-[12px]" style={muted}>{rows.length} {t.lines_n} · {t.sort}</span>
      </div>
      <WideScroll cue={t.scroll}>
        <table className="w-full text-[12.5px] tabular-nums border-collapse min-w-[980px]">
          <thead>
            <tr className="text-[11.5px] font-semibold" style={{ color: 'var(--text-secondary)' }}>
              <th colSpan={2} />
              {firstLedger > 0 ? <th colSpan={firstLedger} className="px-1 pt-1 text-center border-b" style={{ borderColor: 'var(--grid)', background: 'var(--surface-3)' }}>{t.workbook}</th> : null}
              <th colSpan={d.years.length - Math.max(0, firstLedger)} className="px-1 pt-1 text-center border-b border-l" style={{ borderColor: 'var(--grid)' }}>{t.ledger}</th>
              <th />
            </tr>
            <tr className="border-b text-[12px]" style={{ borderColor: 'var(--grid)', color: 'var(--text-secondary)' }}>
              <th className="px-2 py-1 text-left font-semibold cursor-pointer select-none sticky left-0 z-10 min-w-[15rem]" style={{ background: 'var(--surface-1)' }}
                onClick={() => by('name')}>{t.line}{arrow('name')}</th>
              <th className="px-2 py-1 text-left font-semibold cursor-pointer select-none" onClick={() => by('cat')}>{t.cat}{arrow('cat')}</th>
              {d.years.map((y, i) => (
                <th key={y.fy} className={`px-1.5 py-1 text-right font-semibold align-bottom ${i === firstLedger ? 'border-l' : ''}`}
                  style={{ borderColor: 'var(--grid)', background: y.src === 'workbook' ? 'var(--surface-3)' : undefined }}>
                  {y.href ? <a href={y.href} className="underline block" style={link} title={t.open_year}>{y.fy} ↗</a> : <span className="block">{y.fy}</span>}
                  <button type="button" className="block w-full text-right text-[10.5px] font-normal cursor-pointer" style={muted} onClick={() => by(i)}
                    title={`${d.flags.under} ${y.n.under} · ${d.flags.over} ${y.n.over} · ${d.flags.restart} ${y.n.restart}`}>
                    <span style={{ color: FLAG_TONE.under }}>{t.mark.u}</span>{y.n.under}{' '}
                    <span style={{ color: FLAG_TONE.over }}>{t.mark.o}</span>{y.n.over}{' '}
                    <span style={{ color: FLAG_TONE.restart }}>{t.mark.r}</span>{y.n.restart}{arrow(i)}</button>
                </th>))}
              <th className="px-2 py-1 text-right font-semibold cursor-pointer select-none border-l" style={{ borderColor: 'var(--grid)' }}
                onClick={() => by('nf')}>{t.flagged_years}{arrow('nf')}</th>
            </tr>
          </thead>
          <tbody>
            {shown.map(r => {
              const h = hrefs.line(r.account)
              return (
                <tr key={r.account} className="border-b" style={{ borderColor: 'var(--grid)' }}>
                  <td className="px-2 py-1 sticky left-0 z-10" style={{ background: 'var(--surface-1)' }}>
                    {h ? <a href={h} className="underline" style={link}>{r.name}</a> : r.name}</td>
                  <td className="px-2 py-1 text-[11.5px] whitespace-nowrap" style={muted}>{r.cat}</td>
                  {r.c.map((c, i) => (
                    <td key={i} className={`px-1.5 py-1 text-right whitespace-nowrap ${i === firstLedger ? 'border-l' : ''}`}
                      style={{ borderColor: 'var(--grid)', background: c ? shade(c[2]) : undefined }}
                      title={c ? `${r.name} · ${d.years[i].fy} · ${c[3]} → ${c[4]}${c[1] ? ' · ' + c[1].split('').map(l => d.flags[LETTER[l]]).join(', ') : ''}` : t.none}>
                      {c ? <>{c[0]}{c[1] ? <span className="ml-0.5 text-[10px] font-bold align-super">{c[1].split('').map(l => (
                        <span key={l} style={{ color: FLAG_TONE[LETTER[l]] }}>{t.mark[l as 'u' | 'o' | 'r']}</span>))}</span> : null}</> : <span style={muted}>·</span>}
                    </td>))}
                  <td className="px-2 py-1 text-right border-l" style={{ borderColor: 'var(--grid)' }}>{r.nf || ''}</td>
                </tr>)
            })}
          </tbody>
        </table>
      </WideScroll>
      {!q && rows.length > FIRST ? (
        <button type="button" className="mt-2 text-[12.5px] underline" style={link} onClick={() => setAll(a => !a)}>
          {all ? t.show_fewer : `${t.show_all} (${rows.length})`}</button>) : null}
      <p className="text-[12px] mt-2" style={muted}>{t.workbook}: {t.workbook_note}</p>
      <p className="text-[12px] mt-1" style={muted}>{t.workbook_restart} {t.no_restart}</p>
      <p className="text-[12px] mt-1" style={muted}>{t.ledger}: {t.ledger_note}</p>
    </figure>)
}
