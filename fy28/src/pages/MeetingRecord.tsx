import { useEffect, useState } from 'react'
import { ReportShell, Body, H2 } from '../components/report'

/* THE MEETING, FOR EVERY MEETING: /meeting-minutes/<board>/<date> where no recording page
 * answers. Payload: scripts/build_meeting_pages.py, one file per board and year.
 *
 * TJ, 26 October 2026: *"i cant find the combined meeting page based on a search."* Only
 * the 1,617 meetings we had written minutes for had a page; the other five and a half
 * thousand were a search hit opening a bare .txt. This puts the agenda, the town's
 * minutes, the votes those minutes record and the recording in one place -- the town's
 * documents first, because they are the record. */

type Doc = { copy: string | null; text: string | null; url: string | null; created: string | null }
type Vote = { motion: string; moved_by: string; seconded_by: string; outcome: string; procedural: boolean; quote: string }
type Meeting = {
  board: string; board_slug: string; date: string; as_printed: string | null; part_of: string | null
  agenda: Doc | null; minutes: Doc | null; minutes_ocr: boolean
  videos: string[]; captions_disabled: boolean; ours: string | null; ours_headline: string | null
  votes: Vote[]; missing: string[]
}

const link = { color: 'var(--series-cost)' }
const muted = { color: 'var(--text-muted)' }

function longDate(iso: string) {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d).toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })
}

/** The extracted text, read on the page. Open by default for the minutes: they are what
 *  a reader came for. Loaded only when opened. */
function TextOf({ label, d, open, ocr }: { label: string; d: Doc; open?: boolean; ocr?: boolean }) {
  const [shown, setShown] = useState(Boolean(open))
  const [text, setText] = useState<string | null>(null)
  const [err, setErr] = useState(false)
  useEffect(() => {
    if (!shown || text !== null || !d.text) return
    fetch(d.text).then(r => { if (!r.ok) throw new Error(); return r.text() })
      .then(t => setText(t.replace(/^===OCR===.*\n/m, '')
        // The extractor's page markers, as the page breaks they are.
        .replace(/^===PAGE (\d+)===$/gm, (_, n) => (n === '1' ? '' : `\u2014 page ${n} \u2014`)).trim()))
      .catch(() => setErr(true))
  }, [shown, text, d.text])
  return (
    <div className="card p-4 mt-3 max-w-3xl">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <p className="text-[15px] font-bold">{label}</p>
        <p className="text-[12.5px]" style={muted}>
          {d.copy && <a className="underline" style={link} href={d.copy}>our copy</a>}
          {d.url && <> &middot; <a className="underline" style={link} href={d.url} target="_blank" rel="noreferrer">the town&rsquo;s</a></>}
          {d.text && <> &middot; <a className="underline" style={link} href={d.text}>text</a></>}
        </p>
      </div>
      {d.text ? (
        <>
          <button type="button" className="text-[13px] underline mt-2" style={link} onClick={() => setShown(s => !s)}>
            {shown ? 'Hide the text' : 'Read it here'}</button>
          {shown && (
            err ? <p className="text-[13px] mt-2" style={muted}>The text did not load. Our copy is linked above.</p>
            : text === null ? <p className="text-[13px] mt-2" style={muted}>Loading&hellip;</p>
            : <>
                {ocr && <p className="text-[12px] mt-2" style={muted}>Read from a scan by OCR: check a figure against our copy before quoting it.</p>}
                <pre className="mt-2 text-[13.5px] leading-relaxed whitespace-pre-wrap break-words"
                  style={{ fontFamily: 'inherit', color: 'var(--text-secondary)', maxHeight: '70vh', overflowY: 'auto' }}>{text}</pre>
              </>
          )}
        </>
      ) : <p className="text-[13px] mt-2" style={muted}>No text has been extracted from this document. Our copy is linked above.</p>}
    </div>
  )
}

export function MeetingRecord({ board, date }: { board: string; date: string }) {
  const [m, setM] = useState<Meeting | null | undefined>(undefined)
  useEffect(() => {
    fetch(`/data/meetings/${board}/${date.slice(0, 4)}.json`)
      .then(r => { if (!r.ok) throw new Error(); return r.json() })
      .then(j => setM((j.meetings as Meeting[]).find(x => x.date === date) ?? null))
      .catch(() => setM(null))
  }, [board, date])

  if (m === undefined) return <ReportShell title="" loading />
  if (m === null) {
    return (
      <ReportShell title="No meeting at this address" noPrint>
        <Body>The register holds no {board.replace(/-/g, ' ')} meeting on {date}. The board&rsquo;s meetings are at{' '}
          <a className="underline" style={link} href={`/boards/${board}/meetings`}>/boards/{board}/meetings</a>.</Body>
      </ReportShell>
    )
  }

  const held = [m.agenda && 'agenda', m.minutes && 'minutes', m.videos.length && 'recording'].filter(Boolean) as string[]
  const lacks = [!m.agenda && 'no agenda', !m.minutes && 'no minutes', !m.videos.length && 'no recording'].filter(Boolean) as string[]
  const motions = m.votes.filter(v => !v.procedural)

  return (
    <ReportShell title={`${m.board}, ${longDate(m.date)}`} kicker="Meeting" dataUrl={`/data/meetings/${board}/${date.slice(0, 4)}.json`}
      standfirst={<>The town published {held.length ? held.join(', ').replace(/, ([^,]*)$/, ' and $1') : 'nothing we hold'} for this meeting{lacks.length ? `; we hold ${lacks.join(', ').replace(/, ([^,]*)$/, ' and $1')}` : ''}.</>}
      meta={
        <p className="mt-3 text-[13.5px]" style={{ color: 'var(--text-secondary)' }}>
          <a className="underline" style={link} href={`/boards/${m.board_slug}/meetings`}>Every {m.board} meeting &rarr;</a>
          {m.as_printed && <span style={muted}> &middot; printed as &ldquo;{m.as_printed}&rdquo;</span>}
        </p>
      }>

      {m.minutes && <TextOf label="Minutes" d={m.minutes} open ocr={m.minutes_ocr} />}

      {m.votes.length > 0 && (<>
        <H2 id="votes">Votes the minutes record</H2>
        <p className="text-[13.5px] max-w-2xl" style={{ color: 'var(--text-secondary)' }}>
          {m.votes.length} {m.votes.length === 1 ? 'vote' : 'votes'}, {motions.length} of them on more than procedure. Read out of the minutes by a
          language model; each quote is checked word for word against them, and the minutes are the record.</p>
        <ol className="mt-3 space-y-3 max-w-3xl">
          {m.votes.map((v, i) => (
            <li key={i} className="card p-3.5" style={v.procedural ? { opacity: 0.75 } : undefined}>
              <p className="text-[14.5px] font-semibold leading-snug">{v.motion}</p>
              <p className="text-[13px] mt-1" style={{ color: 'var(--text-secondary)' }}>
                {v.outcome || 'outcome not stated'}
                {v.moved_by && <> &middot; moved by {v.moved_by}</>}
                {v.seconded_by && <>, seconded by {v.seconded_by}</>}
              </p>
              {v.quote && <p className="text-[12.5px] mt-1.5 italic" style={muted}>&ldquo;{v.quote}&rdquo;</p>}
            </li>
          ))}
        </ol>
      </>)}

      {m.agenda && (<>
        <H2 id="agenda">Agenda</H2>
        <TextOf label="Agenda" d={m.agenda} open={!m.minutes} />
      </>)}

      {m.videos.length > 0 && (<>
        <H2 id="recording">Recording</H2>
        <ul className="mt-2 text-[14px] space-y-1">
          {m.videos.map((u, i) => <li key={u}><a className="underline" style={link} href={u} target="_blank" rel="noreferrer">
            {m.videos.length > 1 ? `Part ${i + 1}` : 'The video'}</a>{m.captions_disabled && <span style={muted}> &middot; captions disabled</span>}</li>)}
        </ul>
        {m.ours && <Body>Our minutes of the recording: <a className="underline" style={link} href={m.ours}>{m.ours_headline || 'read them'}</a>.</Body>}
      </>)}
    </ReportShell>
  )
}
