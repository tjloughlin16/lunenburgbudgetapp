import {
  ComposedChart, Line, ReferenceLine, ReferenceDot, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import { usd, usdShort } from '../model/engine'

export interface CurveArgs {
  current: number        // fee charged today
  payers: number         // participants before waivers
  dropoff: number        // % of participation lost per $100 of INCREASE
  waiver: number         // % granted a hardship waiver
  target?: number        // program cost to self-fund
  max: number
}

export function feeRevenue(f: number, a: CurveArgs) {
  const increase = Math.max(0, f - a.current)
  const retained = Math.max(0, 1 - (increase / 100) * (a.dropoff / 100))
  return f * a.payers * (1 - a.waiver / 100) * retained
}

/** The Laffer curve of school fees: revenue rises, peaks, then falls as families are
 *  priced out. The peak is the most a fee can ever raise. */
export function FeeCurve({ args, fee, label }: {
  args: CurveArgs; fee: number; label: string
}) {
  const data: { f: number; revenue: number; playing: number }[] = []
  for (let f = 0; f <= args.max; f += 10) {
    const increase = Math.max(0, f - args.current)
    const retained = Math.max(0, 1 - (increase / 100) * (args.dropoff / 100))
    data.push({ f, revenue: feeRevenue(f, args), playing: args.payers * retained })
  }
  let peak = data[0]
  for (const d of data) if (d.revenue > peak.revenue) peak = d
  // Keep the program-cost line on screen: the visible gap between the curve's peak
  // and that line IS the finding when self-funding is unreachable.
  const yMax = Math.max(peak.revenue, args.target ?? 0) * 1.12

  const atCurrent = feeRevenue(args.current, args)
  const atFee = feeRevenue(fee, args)
  const reachable = args.target !== undefined && peak.revenue >= args.target

  return (
    <div className="card p-5">
      <h3 className="text-sm font-bold mb-1">{label}</h3>
      <p className="text-[12px] mb-4" style={{ color: 'var(--text-secondary)' }}>
        Raising the fee brings in more per family but prices some families out. Past the
        peak, the district collects <em>less</em>, not more.
      </p>

      <div style={{ width: '100%', height: 220 }}>
        <ResponsiveContainer>
          <ComposedChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="f" type="number" domain={[0, args.max]}
              tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
              stroke="var(--axis)" tickLine={false}
              tickFormatter={v => `$${v}`} />
            <YAxis width={54} domain={[0, yMax]} tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
              stroke="var(--axis)" tickLine={false} axisLine={false}
              tickFormatter={v => usdShort(v as number)} />
            <Tooltip
              contentStyle={{ background: 'var(--surface-1)', border: '1px solid var(--grid)',
                              borderRadius: 10, fontSize: 12, color: 'var(--text-primary)' }}
              labelFormatter={v => `Fee of ${usd(v as number)}`}
              formatter={(v, n) => n === 'revenue'
                ? [usd(v as number), 'Raised']
                : [Math.round(v as number).toLocaleString(), 'Still participating']} />

            {args.target !== undefined && (
              <ReferenceLine y={args.target} stroke="var(--status-critical)"
                strokeDasharray="4 4"
                label={{ value: `Cost of the program — ${usdShort(args.target)}`,
                         position: 'insideTopRight',
                         fill: 'var(--status-critical)', fontSize: 10 }} />
            )}
            <ReferenceLine x={args.current} stroke="var(--axis)"
              label={{ value: 'today', position: 'insideTopLeft',
                       fill: 'var(--text-muted)', fontSize: 10 }} />
            <Line type="monotone" dataKey="revenue" stroke="var(--series-cost)"
              strokeWidth={2} dot={false} isAnimationActive={false} />
            <ReferenceDot x={peak.f} y={peak.revenue} r={5}
              fill="var(--surface-1)" stroke="var(--series-cost)" strokeWidth={2} />
            <ReferenceDot x={fee} y={atFee} r={5}
              fill="var(--status-critical)" stroke="var(--surface-1)" strokeWidth={2} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <dl className="grid grid-cols-3 gap-3 mt-3 pt-3 border-t text-center"
        style={{ borderColor: 'var(--grid)' }}>
        <Cell k="Today" v={usd(args.current)} s={`raises ${usdShort(atCurrent)}`} />
        <Cell k="Break-even peak" v={usd(peak.f)} s={`raises ${usdShort(peak.revenue)}`} accent />
        <Cell k="Your setting" v={usd(fee)} s={`raises ${usdShort(atFee)}`} />
      </dl>

      {args.target !== undefined && (
        <p className="text-[12px] leading-relaxed mt-3"
          style={{ color: reachable ? 'var(--text-secondary)' : 'var(--status-critical)' }}>
          {reachable
            ? <>The program costs {usd(args.target)}, which the curve does clear — full
              self-funding is achievable, though not cheaply.</>
            : <><strong>Self-funding is not reachable.</strong> The program costs{' '}
              {usd(args.target)}, but no fee raises more than {usd(peak.revenue)} because
              participation collapses faster than the fee climbs. The gap of{' '}
              {usd(args.target - peak.revenue)} has to come from somewhere else no matter
              what you charge.</>}
        </p>
      )}
    </div>
  )
}

function Cell({ k, v, s, accent }: { k: string; v: string; s: string; accent?: boolean }) {
  return (
    <div>
      <dt className="text-[10px] font-semibold uppercase tracking-widest"
        style={{ color: 'var(--text-muted)' }}>{k}</dt>
      <dd className="text-base font-bold tnum"
        style={{ color: accent ? 'var(--series-cost)' : 'var(--text-primary)' }}>{v}</dd>
      <dd className="text-[11px] tnum" style={{ color: 'var(--text-secondary)' }}>{s}</dd>
    </div>
  )
}
