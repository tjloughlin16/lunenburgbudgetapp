import { abs } from '../lib/abs'
/** HOW FAR THE MONEY CAN BE FOLLOWED — the ladder, drawn.
 *
 *  WHY THIS IS A PICTURE AND THE REST OF THE PAGE IS A LIST. The other gaps on
 *  /what-we-cannot-answer are a set: any one of them could be closed without touching the
 *  others. This one is a DEPTH. Six questions about the same dollar, ordered coarse to
 *  fine, and the answering stops part-way down. A list of six bullets says "here are six
 *  things"; a ladder with a break in it says WHERE it stops, which is the finding.
 *
 *  THE FORM. Not a plot — there is no magnitude being compared across the rungs, and a bar
 *  chart of "traceability" would be inventing a quantity that does not exist. It is a
 *  status ladder: one rail down the left, one rung per question, and the rail changes
 *  under the break. The figures beside each rung are counts and dollars that say how much
 *  is on that rung, not how far down it is.
 *
 *  COLOUR IS NEVER THE CARRIER. Four states, four DISTINCT SHAPES (a tick, a half-filled
 *  circle, a cross, a bar), and the state's name written out on every rung. A reader who
 *  cannot separate the green from the red loses nothing, and so does a reader looking at
 *  it printed. The four `--trace-*` tokens were run through the dataviz validator in both
 *  themes; the note beside them in index.css says which two checks fail on purpose.
 *
 *  RULE 2 — NOT ONE FIGURE IS TYPED HERE. Every count, amount, question, key and reason
 *  arrives from /data/traceability.json, written by scripts/build_traceability_ladder.py
 *  from the ledger and from the town's own gap register. The prose in this file is
 *  structural only: it says what a rung IS, never what any rung says.
 *
 *  RULE 7 — the `why` on a rung is quoted from `money_gaps` / `money_edges` rather than
 *  restated. What the generator asserts, this renders.
 *
 *  A TABLE TWIN SITS UNDER IT. Everything the diagram encodes in position and shape is in
 *  the table in words, so the diagram is an aid and never the only copy.
 */

export type TraceState = 'answerable' | 'partly' | 'no' | 'never'

type Figure = { kind: 'count' | 'usd' | 'ratio'; value: number; of?: number
  label: string; zeroed?: boolean }

export type Rung = {
  n: number; state: TraceState; tier: number | null
  question: string; key: string; holds: string; limit: string
  why?: string; why_of?: string; basis?: string
  wanted?: { document: string; detail: string; closes: string | null }
  control?: {
    fund: string; name: string; postings: number; first_fy: number; last_fy: number
    funds_like_it: number; numbered: number; named: number; commented: number
    kinds: { src: string; meaning: string; postings: number }[]
  }
  figures: Figure[]
}

export type Trace = {
  generated_by: string; source: string; vocabulary: string
  as_of: { fy: number; accounts_period: number; revenue_period: number
    revenue_history_from: number; revenue_history_to: number }
  headline: { answerable: number; partly: number; unanswerable: number; never: number
    rungs: number; control_fund: string; control_postings: number
    control_of_funds: number }
  states: { state: TraceState; label: string; rungs: number[] }[]
  rungs: Rung[]
}

const COLOR: Record<TraceState, string> = {
  answerable: 'var(--trace-answerable)',
  partly: 'var(--trace-partial)',
  no: 'var(--trace-none)',
  never: 'var(--trace-never)',
}

/** The word beside every mark. Colour is the third encoding here, not the first. */
const WORD: Record<TraceState, string> = {
  answerable: 'answerable',
  partly: 'in part',
  no: 'not answerable',
  never: 'never answerable',
}

const usd = (n: number) =>
  '$' + Math.round(n).toLocaleString('en-US')
const num = (n: number) => n.toLocaleString('en-US')

/** Four marks, four shapes. Drawn rather than typed so they hold their weight at any size
 *  and inherit the rung's colour through `stroke`/`fill`. */
function Mark({ state, size = 22 }: { state: TraceState; size?: number }) {
  const c = COLOR[state]
  const common = { width: size, height: size, viewBox: '0 0 24 24', 'aria-hidden': true }
  if (state === 'answerable') {
    return (
      <svg {...common}>
        <circle cx="12" cy="12" r="10.5" fill="none" stroke={c} strokeWidth="1.4"
          opacity=".45" />
        <path d="M7 12.4 l3.3 3.4 L17 8.6" fill="none" stroke={c} strokeWidth="2.6"
          strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    )
  }
  if (state === 'partly') {
    return (
      <svg {...common}>
        <circle cx="12" cy="12" r="8.5" fill="none" stroke={c} strokeWidth="2.4" />
        <path d="M12 3.5 a8.5 8.5 0 0 1 0 17 z" fill={c} />
      </svg>
    )
  }
  if (state === 'no') {
    return (
      <svg {...common}>
        <circle cx="12" cy="12" r="10.5" fill="none" stroke={c} strokeWidth="1.4"
          opacity=".45" />
        <path d="M7.6 7.6 L16.4 16.4 M16.4 7.6 L7.6 16.4" fill="none" stroke={c}
          strokeWidth="2.6" strokeLinecap="round" />
      </svg>
    )
  }
  return (
    <svg {...common}>
      <circle cx="12" cy="12" r="10.5" fill="none" stroke={c} strokeWidth="1.4"
        opacity=".45" />
      <path d="M6.6 12 H17.4" fill="none" stroke={c} strokeWidth="2.6"
        strokeLinecap="round" />
    </svg>
  )
}

/** One figure beside a rung. `zeroed` marks a count of things that have NONE of the thing
 *  the rung is about — 635 accounts with no transaction detail is a count of absence, and
 *  it is struck through so it cannot be read as a count of what is held. */
function Fig({ f }: { f: Figure }) {
  const value = f.kind === 'usd' ? usd(f.value)
    : f.kind === 'ratio' ? `${num(f.value)} of ${num(f.of ?? 0)}`
      : num(f.value)
  return (
    <div className="min-w-0">
      <p className="text-[17px] font-bold leading-none tnum"
        style={{ color: f.zeroed ? 'var(--text-muted)' : 'var(--text-primary)',
          textDecoration: f.zeroed ? 'line-through' : undefined }}>{value}</p>
      <p className="text-[11.5px] mt-1 leading-snug" style={{ color: 'var(--text-muted)' }}>
        {f.label}
      </p>
    </div>
  )
}

/** The rail segment beside a rung. It is the only part of the drawing that carries meaning
 *  by continuity: solid where the following holds, dashed where it half-holds, and gone
 *  below the break. */
function Rail({ state, first, last }: { state: TraceState; first: boolean; last: boolean }) {
  const c = COLOR[state]
  const dash = state === 'partly' ? '5 4' : state === 'answerable' ? undefined : '2 5'
  return (
    <div className="relative flex-none" style={{ width: 24 }} aria-hidden="true">
      <svg width="24" height="100%" preserveAspectRatio="none"
        style={{ position: 'absolute', inset: 0 }}>
        {!first && (
          <line x1="12" y1="0" x2="12" y2="3" stroke={c} strokeWidth="2"
            strokeDasharray={dash} opacity=".55" />
        )}
        {!last && (
          <line x1="12" y1="27" x2="12" y2="100%" stroke={c} strokeWidth="2"
            strokeDasharray={dash} opacity=".55" />
        )}
      </svg>
      <div style={{ position: 'absolute', top: 3, left: 1 }}>
        <Mark state={state} />
      </div>
    </div>
  )
}

function Row({ r, first, last }: { r: Rung; first: boolean; last: boolean }) {
  const c = COLOR[r.state]
  return (
    <li className="flex gap-3 sm:gap-4">
      <Rail state={r.state} first={first} last={last} />
      <div className="min-w-0 flex-1 pb-9">
        <div className="flex flex-wrap items-baseline gap-x-2.5 gap-y-1">
          <span className="text-[11px] font-semibold tnum"
            style={{ color: 'var(--text-muted)' }}>{r.n}</span>
          <h3 className="text-[15.5px] sm:text-[17px] font-bold leading-snug">
            {r.question}
          </h3>
          <span className="text-[10.5px] font-semibold uppercase tracking-wider
                           px-1.5 py-0.5 rounded"
            style={{ color: c, border: `1px solid ${c}` }}>{WORD[r.state]}</span>
        </div>
        <p className="text-[11.5px] mt-1.5 font-mono" style={{ color: 'var(--text-muted)' }}>
          {r.key}
        </p>

        <p className="text-[13.5px] leading-relaxed mt-2.5 max-w-2xl"
          style={{ color: 'var(--text-secondary)' }}>{r.holds}</p>
        <p className="text-[13.5px] leading-relaxed mt-1.5 max-w-2xl"
          style={{ color: 'var(--text-secondary)' }}>
          <span className="font-semibold uppercase tracking-wider text-[10.5px]"
            style={{ color: 'var(--text-muted)' }}>what it does not reach&nbsp;&middot;&nbsp;</span>
          {r.limit}
        </p>
        {r.why && (
          <p className="text-[13px] leading-relaxed mt-1.5 max-w-2xl"
            style={{ color: 'var(--text-secondary)' }}>
            <span className="font-semibold uppercase tracking-wider text-[10.5px]"
              style={{ color: 'var(--text-muted)' }}>
              the register says&nbsp;&middot;&nbsp;</span>
            {r.why.replace(/\*\*/g, '')}
          </p>
        )}

        {r.figures.length > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-x-4 gap-y-3 mt-4 max-w-2xl">
            {r.figures.map(f => <Fig key={f.label} f={f} />)}
          </div>
        )}

        {r.control && (
          <div className="card px-4 py-3.5 mt-4 max-w-2xl"
            style={{ borderLeft: `3px solid ${COLOR.answerable}` }}>
            <p className="text-[10.5px] font-semibold uppercase tracking-widest mb-1.5"
              style={{ color: 'var(--text-muted)' }}>
              the one place this rung is answered
            </p>
            <p className="text-[13.5px] leading-relaxed"
              style={{ color: 'var(--text-secondary)' }}>
              Fund <code>{r.control.fund}</code>, the {r.control.name}, FY
              {r.control.first_fy % 100}&ndash;FY{r.control.last_fy % 100}:{' '}
              <strong style={{ color: 'var(--text-primary)' }}>
                {num(r.control.postings)} postings</strong>, obtained by records request.
              Every one carries a document number; {num(r.control.named)} name a
              counterparty and {num(r.control.commented)} carry the clerk&rsquo;s own
              comment. It is <strong style={{ color: 'var(--text-primary)' }}>
                one fund of {num(r.control.funds_like_it)}</strong> the schools ran that
              year &mdash; which is why the rest is <em>unpublished</em> rather than
              impossible. The town produced this report; it has not been asked to run it
              for anything else.
            </p>
            <div className="flex flex-wrap gap-1.5 mt-2.5">
              {r.control.kinds.map(k => (
                <span key={k.src} className="text-[11px] px-2 py-1 rounded"
                  style={{ background: 'var(--surface-3)', color: 'var(--text-secondary)' }}
                  title={k.meaning}>
                  <code className="font-semibold">{k.src}</code>{' '}
                  <span className="tnum">{num(k.postings)}</span>{' '}
                  <span style={{ color: 'var(--text-muted)' }}>{k.meaning}</span>
                </span>
              ))}
            </div>
          </div>
        )}

        {r.wanted && (
          <p className="text-[12.5px] leading-relaxed mt-3 max-w-2xl"
            style={{ color: 'var(--text-muted)' }}>
            <span className="font-semibold uppercase tracking-wider text-[10.5px]">
              {r.state === 'never' ? 'would document the convention' : 'would close it'}
              &nbsp;&middot;&nbsp;</span>
            <strong style={{ color: 'var(--text-secondary)' }}>
              {r.wanted.document.replace(/`/g, '')}</strong>
            {' — '}{r.wanted.detail.replace(/`/g, '')}
          </p>
        )}
      </div>
    </li>
  )
}

export function TraceLadder({ t }: { t: Trace }) {
  const h = t.headline
  const stop = t.rungs.find(r => r.state !== 'answerable')

  return (
    <section>
      {/* RULE 7b — the conclusion, then the picture, then what a rung is. Never the
          other way round. */}
      <p className="text-[15px] sm:text-[17px] leading-relaxed max-w-2xl mt-4"
        style={{ color: 'var(--text-secondary)' }}>
        Six questions about the same dollar, coarsest first. The archive answers{' '}
        <strong style={{ color: 'var(--text-primary)' }}>{h.answerable}</strong>,
        answers <strong style={{ color: 'var(--text-primary)' }}>{h.partly}</strong> in
        part, and cannot answer the last{' '}
        <strong style={{ color: 'var(--text-primary)' }}>
          {h.unanswerable + h.never}</strong>.
        {stop && <> The following stops at rung {stop.n}.</>} The bottom rungs are answered
        in full for <strong style={{ color: 'var(--text-primary)' }}>
          one fund of {num(h.control_of_funds)}</strong> &mdash;{' '}
        {num(h.control_postings)} postings for the athletics revolving fund &mdash; which
        is what shows the rest to be unpublished rather than impossible. One rung is the
        exception: no key for it exists on either side, and no document can make one.
      </p>

      {/* The legend. Present because there are four states; every mark is also named on
          the rung it belongs to, so this is a summary and not the only key. */}
      <div className="flex flex-wrap gap-x-5 gap-y-2 mt-6">
        {t.states.map(s => (
          <span key={s.state} className="flex items-center gap-2">
            <Mark state={s.state} size={18} />
            <span className="text-[12.5px]" style={{ color: 'var(--text-secondary)' }}>
              <strong style={{ color: 'var(--text-primary)' }}>{WORD[s.state]}</strong>
              {' — '}{s.label}
            </span>
          </span>
        ))}
      </div>

      <ol className="mt-8">
        {t.rungs.map((r, i) => (
          <Row key={r.n} r={r} first={i === 0} last={i === t.rungs.length - 1} />
        ))}
      </ol>

      {/* THE TABLE TWIN. Same six rungs, same four states, in words — for a reader who
          cannot see the drawing, for print, and for anyone who would rather scan it. */}
      <p className="text-[11px] font-semibold uppercase tracking-widest mt-4 mb-3"
        style={{ color: 'var(--text-muted)' }}>The same six rungs, as a table</p>
      <div className="overflow-x-auto">
        <table className="w-full text-[13px]" style={{ borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ color: 'var(--text-muted)' }}>
              <th className="text-left font-semibold py-2 pr-3">#</th>
              <th className="text-left font-semibold py-2 pr-3">question</th>
              <th className="text-left font-semibold py-2 pr-3">the key it turns on</th>
              <th className="text-left font-semibold py-2 pr-3">state</th>
              <th className="text-left font-semibold py-2">why</th>
            </tr>
          </thead>
          <tbody>
            {t.rungs.map(r => (
              <tr key={r.n} style={{ borderTop: '1px solid var(--grid)' }}>
                <td className="py-2.5 pr-3 tnum align-top"
                  style={{ color: 'var(--text-muted)' }}>{r.n}</td>
                <td className="py-2.5 pr-3 align-top font-semibold">{r.question}</td>
                <td className="py-2.5 pr-3 align-top text-[12px] font-mono"
                  style={{ color: 'var(--text-muted)' }}>{r.key}</td>
                <td className="py-2.5 pr-3 align-top font-semibold whitespace-nowrap"
                  style={{ color: COLOR[r.state] }}>{WORD[r.state]}</td>
                <td className="py-2.5 align-top" style={{ color: 'var(--text-secondary)' }}>
                  {(r.why ?? r.limit).replace(/\*\*/g, '')}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="text-xs leading-relaxed mt-5 max-w-2xl"
        style={{ color: 'var(--text-muted)' }}>
        Every figure on this ladder is computed at build time by{' '}
        <code>{t.generated_by}</code> from {t.source} &mdash; the FY{t.as_of.fy % 100}{' '}
        ledger at period {t.as_of.accounts_period} for the accounts and period{' '}
        {t.as_of.revenue_period} for the revenue, which is the only snapshot that carries
        it. The reason on each rung is quoted from the town&rsquo;s gap register rather
        than written here. Published as{' '}
        <a href={abs('/data/traceability.json')} className="underline"
          style={{ color: 'var(--series-cost)' }}><code>/data/traceability.json</code></a>.
        The levels and the keys are the ones already used in {t.vocabulary}.
      </p>
    </section>
  )
}
