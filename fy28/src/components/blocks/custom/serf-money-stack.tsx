/** VOTED, REPAID, OVER: one bar a year for the three special education lines (the SERF hub).
 *
 *  TJ, 25 October 2026: "a chart that shows the amount allocated, then, how much is 'paid
 *  back' and the overrun, all in one chart". Each bar is what the lines cost, all funds, laid
 *  end to end on one scale from zero:
 *
 *      spent inside the vote | voted, not spent | spent above a line's vote | the state's repayment
 *      '-------- what was voted --------'
 *
 *  so the voted budget is the first two parts and the bill is every solid part. Everything is
 *  formatted by build_serf_topics.py; this draws marks from numbers and prints the given text. */
import type { CustomProps } from './index'

type Row = { fy: string; voted: number; within: number; over: number; state: number
  t_voted: string; t_over: string; t_state: string; t_spent: string }
type Data = { rows: Row[]; read?: string; legend: { within: string; unspent: string; over: string; state: string }; note: string }

const C = {
  within: 'var(--text-muted)',
  over: 'var(--status-bad)',
  state: 'var(--status-good)',
}
const HATCH = 'repeating-linear-gradient(135deg, var(--grid) 0 3px, transparent 3px 6px)'

function Key({ swatch, label }: { swatch: React.CSSProperties; label: string }) {
  return (
    <li className="inline-flex items-center gap-1.5">
      <span className="inline-block w-3.5 h-3 rounded-sm shrink-0" style={swatch} />{label}
    </li>
  )
}

export default function SerfMoneyStack({ data, alt }: CustomProps) {
  const d = data as Data
  const max = Math.max(...d.rows.map(r => r.voted + r.over + r.state))
  const pct = (v: number) => `${(100 * v) / max}%`
  return (
    <figure aria-label={alt} className="max-w-3xl">
      {d.read ? <p className="text-[14px] leading-snug mb-2" style={{ color: 'var(--text-secondary)' }}>{d.read}</p> : null}
      <ul className="flex flex-wrap gap-x-5 gap-y-1.5 text-[13px]" style={{ color: 'var(--text-secondary)' }}>
        <Key swatch={{ background: C.within, opacity: 0.55 }} label={d.legend.within} />
        <Key swatch={{ background: HATCH, boxShadow: 'inset 0 0 0 1px var(--grid)' }} label={d.legend.unspent} />
        <Key swatch={{ background: C.over }} label={d.legend.over} />
        <Key swatch={{ background: C.state }} label={d.legend.state} />
      </ul>
      <div className="mt-3 grid gap-y-1.5 text-[13px] grid-cols-[52px_1fr] sm:grid-cols-[60px_1fr_auto] gap-x-3 items-center">
        <span />
        <span className="hidden sm:block" />
        <span className="hidden sm:flex gap-3 justify-end text-[11.5px]" style={{ color: 'var(--text-muted)' }}>
          <span className="w-[86px] text-right">Over</span><span className="w-[86px] text-right">Repaid, spent</span>
        </span>
        {d.rows.map(r => {
          const tip = `${r.fy}: voted ${r.t_voted}; over ${r.t_over}; paid from the repayment ${r.t_state}; all spent ${r.t_spent}`
          return [
            <span key={r.fy + 'l'} className="tabular-nums" style={{ color: 'var(--text-secondary)' }}>{r.fy}</span>,
            <div key={r.fy + 'b'} title={tip} aria-label={tip} className="flex h-[18px] min-w-0">
              <span style={{ width: pct(r.within), background: C.within, opacity: 0.55 }} />
              {r.voted > r.within ? <span style={{ width: pct(r.voted - r.within), background: HATCH }} /> : null}
              {r.over ? <span style={{ width: pct(r.over), background: C.over }} /> : null}
              {r.state ? <span style={{ width: pct(r.state), background: C.state }} /> : null}
            </div>,
            <span key={r.fy + 't'} className="col-start-2 sm:col-start-auto flex gap-3 justify-start sm:justify-end tabular-nums text-[12.5px] -mt-1 sm:mt-0">
              <span className="sm:w-[86px] sm:text-right" style={{ color: r.over ? C.over : 'var(--text-muted)' }}>
                <span className="sm:hidden">Over </span>{r.t_over}</span>
              <span className="sm:w-[86px] sm:text-right" style={{ color: C.state }}>
                <span className="sm:hidden">Repaid </span>{r.t_state}</span>
            </span>,
          ]
        })}
      </div>
      <figcaption className="text-[13.5px] mt-3 max-w-3xl" style={{ color: 'var(--text-secondary)' }}>{d.note}</figcaption>
    </figure>
  )
}
