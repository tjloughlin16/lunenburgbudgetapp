import { useEffect, useMemo, useState } from 'react'

/** EVERY VOTE, SEARCHABLE -- one component for Town Meeting's articles and every board's motions.
 *
 *  TJ, 23 October 2026: *"a single page that lists all town meeting votes, ever. and easily
 *  searchable and findable by FY"*, and then *"a very simple 'All Votes' per board too, with the
 *  same search mechanisms"*. So the search box and the list ARE the page (rule 7a): a text search,
 *  a fiscal-year menu, a meeting menu, a result menu, then the votes grouped by meeting, newest
 *  first. The address follows the controls (`?fy=2025&q=stabilization`) so a search is a link.
 *
 *  MODEL-DRIVEN (rule 7d). Everything is a payload written by scripts/build_vote_lists.py --
 *  `/data/town-meeting-votes.json` and `/data/votes/<board>.json`; this lays out and filters,
 *  it computes no figure. Every row says WHICH record its result comes from (rule 3): the
 *  Clerk's printed record or a board's minutes are records; our minutes of a recording are a
 *  motion as heard, and are labelled so on the row, not only in a footnote. */

export type VoteLink = { label: string; href: string }
export type VoteRec = { who: string; text: string; ref: string; href: string }
export type VoteRow = {
  id: string; n: string; title: string; title_from?: string
  amount?: string; result_amount?: string; sponsor?: string
  recs?: VoteRec[]; result: string; result_text?: string
  basis: string; quote: string; quote_kind: string; words?: string
  names_fy?: number[]; flags?: string[]; note?: string
  moved_by?: string; seconded_by?: string; conflict?: string; procedural?: boolean
  links: VoteLink[]
  /** The result in plain words, and why there is none where there is none. */
  result_label: string; reason?: string
  /** The record it should rest on and whether we have it (one to three words each), and the
   *  same in one sentence for the expansion. */
  chips: VoteChip[]; basis_note: string
}
export type VoteChip = { text: string; tone: 'ok' | 'video' | 'missing' | 'neutral'; href: string }
export type FyCoverage = { status: 'clerk' | 'part' | 'none'; short: string; text: string; tag: string }
export type VoteGroup = {
  id: string; label: string; date: string; date_printed: boolean; kind?: string
  fy: number; fy_basis: string; status: string; note: string; links: VoteLink[]; votes: VoteRow[]
}
export type VotePayload = {
  title: string; standfirst: string; kind: 'town-meeting' | 'board'
  coverage: string[]; grain: string; fy_rule: string; quote_rule: string
  basis: Record<string, string>; by_basis: Record<string, number>
  results: { key: string; n: number; label: string }[]; fys: number[]
  votes: number; meetings: number; groups: VoteGroup[]
  conflicts?: number; board?: string; slug?: string
  fy_coverage: Record<string, FyCoverage>
}

const BASIS_LONG: Record<string, string> = {
  clerk: 'Town Clerk’s record', ours: 'From our reading of the meeting video', none: 'Result not found',
  minutes: 'The town’s minutes', both: 'The town’s minutes, matched to the video', recording: 'From our reading of the meeting video',
}
const GOOD = new Set(['passed', 'amended and passed'])
const BAD = new Set(['failed'])
const OFF = new Set(['passed over', 'postponed', 'indefinitely postponed', 'no action', 'kept off the warrant'])
const PAGE = 40   // meetings drawn at once; "show more" draws the next

function tone(result: string) {
  if (GOOD.has(result)) return { color: 'var(--status-good)', border: 'var(--status-good)' }
  if (BAD.has(result)) return { color: 'var(--status-critical)', border: 'var(--status-critical)' }
  if (OFF.has(result)) return { color: 'var(--text-secondary)', border: 'var(--grid)' }
  return { color: 'var(--text-muted)', border: 'var(--grid)', dashed: true }
}

function readParams() {
  const p = new URLSearchParams(typeof window === 'undefined' ? '' : window.location.search)
  return { q: p.get('q') ?? '', fy: p.get('fy') ?? '', m: p.get('m') ?? '', result: p.get('result') ?? '', proc: p.get('procedural') === '1' }
}

function haystack(g: VoteGroup, v: VoteRow) {
  const s = [v.n, v.title, v.amount, v.result_amount, v.sponsor, v.quote, v.words, v.result, v.result_text,
    v.moved_by, v.seconded_by, g.label, ...(v.recs ?? []).map(r => `${r.who} ${r.text}`),
    ...(v.names_fy ?? []).map(y => `FY${y} FY${String(y).slice(2)}`)].filter(Boolean).join(' ').toLowerCase()
  // "250000" finds "$250,000", and "art 5" finds "Art. 5"
  return `${s} ${s.replace(/,/g, '')} ${s.replace(/\./g, '')}`
}

export function VoteList({ p }: { p: VotePayload }) {
  const init = useMemo(readParams, [])
  const [q, setQ] = useState(init.q)
  const [fy, setFy] = useState(init.fy)
  const [m, setM] = useState(init.m)
  const [result, setResult] = useState(init.result)
  const [proc, setProc] = useState(init.proc)
  const [shown, setShown] = useState(PAGE)
  const hasProc = useMemo(() => p.groups.some(g => g.votes.some(v => v.procedural)), [p])

  // The address follows the controls; replaceState, because a filter is not a page to go back to.
  useEffect(() => {
    const u = new URLSearchParams(window.location.search)
    const put = (k: string, v: string) => (v ? u.set(k, v) : u.delete(k))
    put('q', q.trim()); put('fy', fy); put('m', m); put('result', result); put('procedural', proc ? '1' : '')
    const s = u.toString()
    window.history.replaceState(window.history.state, '', `${window.location.pathname}${s ? `?${s}` : ''}${window.location.hash}`)
  }, [q, fy, m, result, proc])
  useEffect(() => setShown(PAGE), [q, fy, m, result, proc])

  const index = useMemo(() => p.groups.map(g => ({ g, rows: g.votes.map(v => ({ v, hay: haystack(g, v) })) })), [p])
  const terms = q.toLowerCase().replace(/[“”"]/g, '').split(/\s+/).filter(Boolean).map(t => t.replace(/^\$/, ''))
  const meetingsInFy = p.groups.filter(g => !fy || String(g.fy) === fy)

  const filtered = index
    .filter(({ g }) => (!fy || String(g.fy) === fy) && (!m || g.id === m))
    .map(({ g, rows }) => ({
      g, votes: rows.filter(({ v, hay }) =>
        (proc || !v.procedural) && (!result || v.result === result) && terms.every(t => hay.includes(t))).map(r => r.v),
    }))
    .filter(x => x.votes.length > 0)
  const total = filtered.reduce((n, x) => n + x.votes.length, 0)
  const all = p.groups.reduce((n, g) => n + g.votes.filter(v => proc || !v.procedural).length, 0)
  const procN = useMemo(() => p.groups.reduce((n, g) => n + g.votes.filter(v => v.procedural).length, 0), [p])
  const fyCount = (y: number) => p.groups.filter(g => g.fy === y).reduce((n, g) => n + g.votes.filter(v => proc || !v.procedural).length, 0)
  const busy = q || fy || m || result

  const field = 'min-w-0 w-full rounded border px-2.5 py-2 text-[14px]'
  const fieldStyle = { borderColor: 'var(--grid)', background: 'var(--surface-1)', color: 'var(--text-primary)' }

  return (
    <div className="mt-6 min-w-0">
      <div className="card p-3 sm:p-4 max-w-4xl" role="search">
        <label className="block">
          <span className="sr-only">Search the votes</span>
          <input type="search" value={q} onChange={e => setQ(e.target.value)} className={field} style={fieldStyle}
            placeholder={p.kind === 'town-meeting' ? 'Search: stabilization, $250,000, Art. 5, school…' : 'Search: budget, transfer, mover, a word from the minutes…'}
            aria-label="Search the votes" />
        </label>
        <div className="grid gap-2 mt-2 grid-cols-1 sm:grid-cols-3">
          <label className="block min-w-0"><span className="sr-only">Fiscal year</span>
            <select value={fy} onChange={e => { setFy(e.target.value); setM('') }} className={field} style={fieldStyle} aria-label="Fiscal year">
              <option value="">Every fiscal year</option>
              {p.fys.map(y => { const tag = p.fy_coverage[String(y)]?.tag
                return <option key={y} value={String(y)}>FY{y} ({fyCount(y).toLocaleString('en-US')}){tag ? ` — ${tag}` : ''}</option> })}
            </select>
          </label>
          <label className="block min-w-0"><span className="sr-only">Meeting</span>
            <select value={m} onChange={e => setM(e.target.value)} className={field} style={fieldStyle} aria-label="Meeting">
              <option value="">Every meeting{fy ? ` in FY${fy}` : ''}</option>
              {meetingsInFy.map(g => <option key={g.id} value={g.id}>{g.label}</option>)}
            </select>
          </label>
          <label className="block min-w-0"><span className="sr-only">Result</span>
            <select value={result} onChange={e => setResult(e.target.value)} className={field} style={fieldStyle} aria-label="Result">
              <option value="">Any result</option>
              {p.results.map(r => <option key={r.key} value={r.key}>{r.label} ({r.n.toLocaleString('en-US')})</option>)}
            </select>
          </label>
        </div>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2 text-[13px]" style={{ color: 'var(--text-secondary)' }}>
          <span className="tnum" aria-live="polite">
            {total.toLocaleString('en-US')} of {all.toLocaleString('en-US')} {p.kind === 'town-meeting' ? 'articles' : 'votes'}
            {' '}at {filtered.length.toLocaleString('en-US')} meeting{filtered.length === 1 ? '' : 's'}
            {hasProc && !proc ? ` · ${procN.toLocaleString('en-US')} procedural hidden` : ''}
          </span>
          {hasProc && (
            <label className="inline-flex items-center gap-1.5 cursor-pointer">
              <input type="checkbox" checked={proc} onChange={e => setProc(e.target.checked)} /> show procedural votes
            </label>
          )}
          {busy && <button type="button" className="underline" onClick={() => { setQ(''); setFy(''); setM(''); setResult('') }}>clear</button>}
        </div>
        <Legend kind={p.kind} />
      </div>

      <p className="text-[12.5px] mt-3 max-w-3xl" style={{ color: 'var(--text-muted)' }}>{p.coverage[0]}{' '}
        <a className="underline" href="#what-this-covers">What this covers</a>
      </p>

      {filtered.length === 0 && (
        <p className="text-[15px] mt-6" style={{ color: 'var(--text-secondary)' }}>
          No {p.kind === 'town-meeting' ? 'article' : 'vote'} in the records we have matches. That says nothing about
          what was voted at a meeting we have no record of &mdash; see what this covers, below.
        </p>
      )}

      <div className="mt-4">
        {filtered.slice(0, shown).map(({ g, votes }, i, arr) => (
          <div key={g.id}>
            {(i === 0 || arr[i - 1].g.fy !== g.fy) && <FyHead fy={g.fy} c={p.fy_coverage[String(g.fy)]} />}
            <Meeting g={g} votes={votes} kind={p.kind} />
          </div>
        ))}
      </div>
      {filtered.length > shown && (
        <button type="button" className="mt-4 underline text-[14px] font-semibold" style={{ color: 'var(--series-cost)' }}
          onClick={() => setShown(shown + PAGE)}>
          Show {Math.min(PAGE, filtered.length - shown)} more meetings ({(filtered.length - shown).toLocaleString('en-US')} left)
        </button>
      )}

      <section id="what-this-covers" className="mt-12 max-w-3xl scroll-mt-24">
        <h2 className="text-xl font-bold">What this covers</h2>
        <ul className="mt-2 text-[14px] leading-relaxed list-disc pl-5" style={{ color: 'var(--text-secondary)' }}>
          {p.coverage.map((c, i) => <li key={i}>{c}</li>)}
        </ul>
        <h3 className="text-[15px] font-bold mt-4">Where each result comes from</h3>
        <ul className="mt-1 text-[14px] leading-relaxed list-none p-0" style={{ color: 'var(--text-secondary)' }}>
          {Object.entries(p.basis).map(([k, v]) => (
            <li key={k}><strong style={{ color: 'var(--text-primary)' }}>{BASIS_LONG[k] ?? k}</strong> ({(p.by_basis[k] ?? 0).toLocaleString('en-US')}): {v}.</li>
          ))}
        </ul>
        <p className="text-[13.5px] mt-3" style={{ color: 'var(--text-secondary)' }}>{p.fy_rule}</p>
        <p className="text-[13.5px] mt-2" style={{ color: 'var(--text-secondary)' }}>{p.quote_rule}</p>
        <p className="text-[13.5px] mt-2" style={{ color: 'var(--text-secondary)' }}>{p.grain}</p>
        <p className="text-[12.5px] mt-3" style={{ color: 'var(--text-muted)' }}>
          Every row, as data: <a className="underline" href={p.kind === 'town-meeting' ? '/data/town-meeting-votes.json' : `/data/votes/${p.slug}.json`}>
            {p.kind === 'town-meeting' ? '/data/town-meeting-votes.json' : `/data/votes/${p.slug}.json`}</a>.
          What the record cannot answer is on <a className="underline" href="/what-we-cannot-answer">what we cannot answer</a>.
        </p>
      </section>
    </div>
  )
}

/** WHAT THE CHIPS MEAN -- one line each, beside the filters, after the thing they are a key to
 *  (rule 7a). */
function Legend({ kind }: { kind: VotePayload['kind'] }) {
  const rec = kind === 'town-meeting' ? 'Clerk’s record' : 'Town minutes'
  const rows: [VoteChip, string][] = kind === 'town-meeting' ? [
    [{ text: `${rec} ✓`, tone: 'ok', href: '' }, 'source: the Town Clerk’s official record'],
    [{ text: 'From video', tone: 'video', href: '' }, 'source: our reading of the meeting video — may be wrong'],
    [{ text: 'No Clerk’s record yet', tone: 'missing', href: '' }, 'the record it should come from isn’t published yet'],
  ] : [
    [{ text: `${rec} ✓`, tone: 'ok', href: '' }, 'source: the town’s own minutes'],
    [{ text: 'From video', tone: 'video', href: '' }, 'source: our reading of the meeting video — may be wrong'],
    [{ text: 'No town minutes yet', tone: 'missing', href: '' }, 'the record it should come from isn’t available'],
  ]
  return (
    <ul className="list-none p-0 m-0 mt-2 text-[12px] grid gap-0.5" style={{ color: 'var(--text-muted)' }}>
      {rows.map(([c, t]) => <li key={c.text}><Chip c={c} /> {t}</li>)}
    </ul>
  )
}

/** THE YEAR'S RECORD, before its meetings: do we hold the record needed to be accurate? */
function FyHead({ fy, c }: { fy: number; c?: FyCoverage }) {
  const col = !c ? 'var(--text-muted)' : c.status === 'clerk' ? 'var(--status-good)' : c.status === 'part' ? 'var(--status-warning)' : 'var(--status-critical)'
  return (
    <div className="mt-10 card p-3 max-w-4xl min-w-0" style={{ borderLeft: `4px solid ${col}` }} id={`fy${fy}`}>
      <p className="text-[19px] font-bold tnum">FY{fy} <span className="text-[13px] font-normal" style={{ color: 'var(--text-muted)' }}>July {fy - 1} &ndash; June {fy}</span></p>
      {c && <p className="text-[14px] font-semibold mt-0.5 break-words" style={{ color: col }}>{c.short}</p>}
      {c && (
        <details className="mt-1">
          <summary className="cursor-pointer text-[12.5px] underline" style={{ color: 'var(--text-muted)' }}>what we have for FY{fy}</summary>
          <p className="text-[13px] mt-1 break-words" style={{ color: 'var(--text-secondary)' }}>{c.text}</p>
        </details>
      )}
    </div>
  )
}

function Meeting({ g, votes, kind }: { g: VoteGroup; votes: VoteRow[]; kind: VotePayload['kind'] }) {
  return (
    <section className="mt-6 min-w-0" id={g.id} aria-label={g.label}>
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 pb-1.5" style={{ borderBottom: '2px solid var(--grid)' }}>
        <h2 className="text-[17px] sm:text-lg font-bold leading-snug break-words min-w-0">{g.label}</h2>
        <span className="text-[12px] font-semibold tnum" style={{ color: 'var(--text-muted)' }} title={g.fy_basis}>FY{g.fy}{g.date_printed ? '' : ' (the report’s year)'}</span>
        {g.status && <span className="text-[12px] font-semibold" style={{ color: 'var(--status-warning)' }}>{g.status}</span>}
        <span className="text-[12px] flex flex-wrap gap-x-2" style={{ color: 'var(--text-muted)' }}>
          {g.links.map(l => <a key={l.href} className="underline" href={l.href} target="_blank" rel="noreferrer">{l.label}</a>)}
        </span>
      </div>
      {g.note && <p className="text-[12px] mt-1" style={{ color: 'var(--text-muted)' }}>{g.note}</p>}
      <ul className="list-none p-0 m-0">
        {votes.map(v => <Row key={v.id} v={v} kind={kind} />)}
      </ul>
    </section>
  )
}

/** A SOURCE CHIP, one to three words. FILLED means "this is where the result comes from": 'ok'
 *  an official record, 'video' our reading of the meeting video (the amber of this site's "our
 *  estimate" marks). DASHED AND MUTED means "the record it should come from, which we don't
 *  have" -- never the source. Two chips in one style read as two sources (TJ, 23 Oct 2026). */
function Chip({ c }: { c: VoteChip }) {
  const st = c.tone === 'ok'
    ? { color: 'var(--status-good)', border: '1px solid var(--status-good)', background: 'color-mix(in srgb, var(--status-good) 12%, transparent)' }
    : c.tone === 'video'
      ? { color: 'var(--text-primary)', border: '1px solid var(--status-warning)', background: 'color-mix(in srgb, var(--status-warning) 22%, transparent)' }
      : c.tone === 'missing'
        ? { color: 'var(--text-muted)', border: '1px dashed var(--axis)', background: 'transparent', fontWeight: 500 }
        : { color: 'var(--text-secondary)', border: '1px solid var(--grid)', background: 'transparent' }
  const cls = 'inline-block whitespace-nowrap text-[11.5px] font-semibold px-1.5 py-px rounded no-underline'
  return c.href
    ? <a className={cls + ' hover:underline'} style={st} href={c.href} target="_blank" rel="noreferrer"
        onClick={e => e.stopPropagation()}>{c.text}</a>
    : <span className={cls} style={st}>{c.text}</span>
}

function Row({ v, kind }: { v: VoteRow; kind: VotePayload['kind'] }) {
  const t = tone(v.result)
  return (
    <li className="py-2 min-w-0" style={{ borderBottom: '1px solid var(--grid)' }} id={v.id}>
      <details>
        <summary className="cursor-pointer list-none min-w-0">
          <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1 min-w-0">
            {v.n && <span className="text-[13px] font-bold tnum shrink-0" style={{ color: 'var(--text-muted)' }}>{v.n}</span>}
            <span className="text-[14.5px] font-semibold leading-snug break-words min-w-0 flex-1 basis-[14rem]"
              style={{ color: v.procedural ? 'var(--text-muted)' : 'var(--text-primary)' }}>{v.title || '(no title in the record)'}</span>
            {v.amount && <span className="text-[13px] font-semibold tnum shrink-0">{v.amount}</span>}
            <span className="text-[11.5px] font-bold uppercase tracking-wide px-1.5 py-0.5 rounded max-w-full break-words"
              style={{ color: t.color, border: `1px ${t.dashed ? 'dashed' : 'solid'} ${t.border}` }}
              title={v.result_text || v.result_label}>{v.result_text && v.result_text.length <= 22 ? v.result_text : v.result_label}</span>
          </div>
          <div className="flex flex-wrap items-center gap-1.5 mt-1">
            {v.chips.slice(0, 2).map(c => <Chip key={c.text} c={c} />)}
            {v.conflict && <span className="text-[11.5px] font-semibold" style={{ color: 'var(--status-critical)' }}>records disagree</span>}
            <span className="text-[11.5px] underline" style={{ color: 'var(--text-muted)' }}>details</span>
          </div>
        </summary>
        <div className="mt-2 text-[13.5px] max-w-3xl min-w-0" style={{ borderLeft: '3px solid var(--grid)', paddingLeft: 10 }}>
          <p className="break-words" style={{ color: v.chips.some(c => c.tone === 'video') ? 'var(--text-primary)' : 'var(--text-secondary)' }}>{v.basis_note}</p>
          {v.quote && (
            <p className="mt-2 break-words">
              <span className="text-[11px] font-bold uppercase tracking-wide block" style={{ color: 'var(--text-muted)' }}>
                {v.quote_kind === 'verbatim' ? (kind === 'town-meeting' ? 'The Clerk’s record, word for word' : 'The minutes, word for word')
                  : v.quote_kind === 'as heard' ? 'What we heard on the video — our words, not a quote'
                  : 'Our extractor’s reading — not found word for word on the page'}
              </span>
              {v.quote_kind === 'verbatim' ? <q>{v.quote}</q> : v.quote}
            </p>
          )}
          {v.conflict && <p className="mt-1 font-semibold" style={{ color: 'var(--status-critical)' }}>The two records disagree: {v.conflict}.</p>}
          {(v.moved_by || v.seconded_by) && (
            <p className="mt-1" style={{ color: 'var(--text-secondary)' }}>
              {v.moved_by ? `Moved by ${v.moved_by}` : ''}{v.moved_by && v.seconded_by ? '; ' : ''}{v.seconded_by ? `seconded by ${v.seconded_by}` : ''}.
            </p>
          )}
          {v.result_text && v.result_text.length > 22 && <p className="mt-1 break-words" style={{ color: 'var(--text-secondary)' }}>Outcome as recorded: {v.result_text}</p>}
          {v.result_amount && <p className="mt-1">Voted: <span className="tnum font-semibold">{v.result_amount}</span></p>}
          {v.sponsor && <p className="mt-1" style={{ color: 'var(--text-secondary)' }}>Submitted by {v.sponsor}.</p>}
          {(v.recs ?? []).map(r => (
            <p key={r.who} className="mt-1 break-words" style={{ color: 'var(--text-secondary)' }}>
              {r.who} recommended: {r.text} &mdash; {r.href ? <a className="underline" href={r.href} target="_blank" rel="noreferrer">{r.ref}</a> : r.ref}
            </p>
          ))}
          {v.names_fy && v.names_fy.length > 0 && <p className="mt-1" style={{ color: 'var(--text-secondary)' }}>The article names {v.names_fy.map(y => `FY${y}`).join(', ')}.</p>}
          {v.words && (
            <details className="mt-1">
              <summary className="cursor-pointer underline text-[12.5px]">The warrant’s words</summary>
              <p className="mt-1 break-words" style={{ color: 'var(--text-secondary)' }}>{v.words}</p>
            </details>
          )}
          {v.note && <p className="mt-1 text-[12.5px]" style={{ color: 'var(--text-muted)' }}>Numbered by {v.note}.</p>}
          {v.links.length > 0 && (
            <p className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[12.5px]">
              {v.links.map(l => (
                <a key={l.href + l.label} className="underline break-words font-semibold" style={{ color: 'var(--series-cost)' }}
                  href={l.href} target="_blank" rel="noreferrer">{l.label} ↗</a>
              ))}
            </p>
          )}
        </div>
      </details>
    </li>
  )
}

export default VoteList
