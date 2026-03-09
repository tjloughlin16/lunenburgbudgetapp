import { useState, useEffect, useMemo } from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, BarChart, Bar, Legend, Cell,
} from 'recharts'
import {
  parseDeseFile, type DeseData, type DeseRow,
  DESE_CATEGORIES, DISTRICT_COLORS,
  districtAverage, rankDistrict, getRow,
} from '../data/deseParser'

// ── Formatting ────────────────────────────────────────────────────────────────

function fmtFull$(n: number) {
  return `$${n.toLocaleString()}`
}

function shortYear(y: string) {
  // "FY2023–24" → "FY24"
  const m = y.match(/FY(\d{4})/)
  if (!m) return y
  return 'FY' + m[1].slice(2)
}

// ── Small UI pieces ───────────────────────────────────────────────────────────

function KpiCard({
  label, value, sub, highlight,
}: {
  label: string; value: string; sub?: string; highlight?: boolean
}) {
  return (
    <div className={`rounded-xl border p-4 ${highlight ? 'border-blue-200 bg-blue-50' : 'border-gray-200 bg-white'}`}>
      <p className={`text-xs font-semibold uppercase tracking-wide ${highlight ? 'text-blue-500' : 'text-gray-400'}`}>
        {label}
      </p>
      <p className={`text-2xl font-bold mt-1 ${highlight ? 'text-blue-700' : 'text-gray-900'}`}>{value}</p>
      {sub && <p className="text-xs text-gray-500 mt-0.5">{sub}</p>}
    </div>
  )
}

function TabBtn({
  active, onClick, children,
}: {
  active: boolean; onClick: () => void; children: React.ReactNode
}) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
        active ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-100'
      }`}
    >
      {children}
    </button>
  )
}

function DistrictToggle({
  district, visible, onToggle,
}: {
  district: string; visible: boolean; onToggle: () => void
}) {
  const color = DISTRICT_COLORS[district] ?? '#6b7280'
  const isLunenburg = district === 'Lunenburg'
  return (
    <button
      onClick={onToggle}
      className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-medium transition-all ${
        visible
          ? 'opacity-100'
          : 'opacity-30 grayscale'
      } ${isLunenburg ? 'border-blue-300 bg-blue-50' : 'border-gray-200 bg-white'}`}
    >
      <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />
      {district}
    </button>
  )
}

// ── Custom tooltip for line chart ─────────────────────────────────────────────

function TrendTooltip({ active, payload, label }: {
  active?: boolean; payload?: { name: string; value: number; color: string }[]; label?: string
}) {
  if (!active || !payload?.length) return null
  const sorted = [...payload].sort((a, b) => b.value - a.value)
  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-lg p-3 text-xs min-w-48">
      <p className="font-bold text-gray-700 mb-2">{label}</p>
      {sorted.map(p => (
        <div key={p.name} className="flex items-center justify-between gap-4 py-0.5">
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: p.color }} />
            <span className={p.name === 'Lunenburg' ? 'font-bold text-blue-700' : 'text-gray-600'}>{p.name}</span>
          </div>
          <span className="font-mono font-semibold text-gray-900">{fmtFull$(p.value)}</span>
        </div>
      ))}
    </div>
  )
}

// ── Snapshot tooltip ──────────────────────────────────────────────────────────

function SnapshotTooltip({ active, payload }: {
  active?: boolean; payload?: { payload: DeseRow }[]
}) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  const isLunenburg = d.district === 'Lunenburg'
  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-lg p-3 text-xs min-w-52">
      <p className={`font-bold mb-2 ${isLunenburg ? 'text-blue-700' : 'text-gray-800'}`}>
        {d.district}
      </p>
      <div className="space-y-0.5">
        {DESE_CATEGORIES.map(cat => (
          <div key={cat.key} className="flex justify-between gap-4">
            <span className="text-gray-500">{cat.label}</span>
            <span className="font-mono text-gray-800">{fmtFull$(d[cat.key] as number)}</span>
          </div>
        ))}
        <div className="flex justify-between gap-4 border-t border-gray-100 pt-1 mt-1 font-semibold">
          <span>Total per pupil</span>
          <span className="font-mono text-gray-900">{fmtFull$(d.total)}</span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-gray-500">Enrollment</span>
          <span className="font-mono text-gray-700">{d.enrollment.toLocaleString()}</span>
        </div>
      </div>
    </div>
  )
}

// ── Trend Tab ─────────────────────────────────────────────────────────────────

function TrendTab({
  data, visible, onToggle,
}: {
  data: DeseData; visible: string[]; onToggle: (d: string) => void
}) {
  const chartData = useMemo(() => {
    return data.years.map(year => {
      const point: Record<string, string | number> = { year: shortYear(year) }
      for (const district of data.districts) {
        const row = getRow(data.rows, district, year)
        point[district] = row?.total ?? 0
      }
      return point
    })
  }, [data])

  return (
    <div className="space-y-4">
      {/* District toggles */}
      <div className="flex flex-wrap gap-2">
        {data.districts.map(d => (
          <DistrictToggle
            key={d}
            district={d}
            visible={visible.includes(d)}
            onToggle={() => onToggle(d)}
          />
        ))}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <p className="text-sm font-semibold text-gray-700 mb-1">Per-Pupil Expenditure Over Time</p>
        <p className="text-xs text-gray-400 mb-4">Total in-district expenditure per enrolled student · Source: DESE</p>
        <ResponsiveContainer width="100%" height={340}>
          <LineChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis dataKey="year" tick={{ fontSize: 11, fill: '#94a3b8' }} />
            <YAxis
              tickFormatter={v => `$${(v / 1000).toFixed(0)}K`}
              tick={{ fontSize: 11, fill: '#94a3b8' }}
              domain={['auto', 'auto']}
            />
            <Tooltip content={<TrendTooltip />} />
            {data.districts.map(district => (
              <Line
                key={district}
                dataKey={district}
                stroke={DISTRICT_COLORS[district] ?? '#94a3b8'}
                strokeWidth={district === 'Lunenburg' ? 3 : 1.5}
                dot={district === 'Lunenburg' ? { r: 4, fill: '#2563eb' } : false}
                hide={!visible.includes(district)}
                activeDot={{ r: 5 }}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Summary table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-100 bg-gray-50">
          <p className="text-sm font-semibold text-gray-700">Per-Pupil Total by District &amp; Year</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-gray-100">
                <th className="py-2 px-4 text-left text-gray-400 font-semibold">District</th>
                {data.years.map(y => (
                  <th key={y} className="py-2 px-3 text-right text-gray-400 font-semibold whitespace-nowrap">
                    {shortYear(y)}
                  </th>
                ))}
                <th className="py-2 px-3 text-right text-gray-400 font-semibold">7-yr change</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {data.districts.filter(d => visible.includes(d)).map(district => {
                const firstRow = getRow(data.rows, district, data.years[0])
                const lastRow  = getRow(data.rows, district, data.years[data.years.length - 1])
                const change = firstRow && lastRow
                  ? ((lastRow.total - firstRow.total) / firstRow.total * 100)
                  : null
                const isLunenburg = district === 'Lunenburg'
                return (
                  <tr key={district} className={isLunenburg ? 'bg-blue-50' : 'hover:bg-gray-50'}>
                    <td className={`py-2 px-4 font-medium ${isLunenburg ? 'text-blue-700' : 'text-gray-800'}`}>
                      <div className="flex items-center gap-2">
                        <span
                          className="w-2 h-2 rounded-full flex-shrink-0"
                          style={{ backgroundColor: DISTRICT_COLORS[district] ?? '#94a3b8' }}
                        />
                        {district}
                      </div>
                    </td>
                    {data.years.map(year => {
                      const row = getRow(data.rows, district, year)
                      return (
                        <td key={year} className={`py-2 px-3 text-right font-mono ${isLunenburg ? 'text-blue-700 font-semibold' : 'text-gray-700'}`}>
                          {row ? fmtFull$(row.total) : '—'}
                        </td>
                      )
                    })}
                    <td className={`py-2 px-3 text-right font-mono font-semibold ${
                      change === null ? 'text-gray-300' :
                      change > 0 ? 'text-red-600' : 'text-green-600'
                    }`}>
                      {change !== null ? `${change >= 0 ? '+' : ''}${change.toFixed(1)}%` : '—'}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

// ── Snapshot Tab ──────────────────────────────────────────────────────────────

function SnapshotTab({ data, selectedYear, onYearChange }: {
  data: DeseData; selectedYear: string; onYearChange: (y: string) => void
}) {
  const yearRows = useMemo(() => {
    return [...data.rows.filter(r => r.year === selectedYear)]
      .sort((a, b) => a.total - b.total)
  }, [data.rows, selectedYear])

  const avg = districtAverage(data.rows, selectedYear)
  const lunRow = getRow(data.rows, 'Lunenburg', selectedYear)
  const lunRank = rankDistrict(data.rows, 'Lunenburg', selectedYear)

  return (
    <div className="space-y-4">
      {/* Year picker */}
      <div className="flex items-center gap-3">
        <span className="text-sm text-gray-600 font-medium">Year:</span>
        <div className="flex gap-1 flex-wrap">
          {data.years.map(y => (
            <button
              key={y}
              onClick={() => onYearChange(y)}
              className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                y === selectedYear ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {shortYear(y)}
            </button>
          ))}
        </div>
      </div>

      {/* KPIs for this year */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <KpiCard
          highlight
          label="Lunenburg per pupil"
          value={lunRow ? fmtFull$(lunRow.total) : '—'}
          sub={selectedYear}
        />
        <KpiCard
          label="9-district average"
          value={fmtFull$(avg)}
          sub={lunRow ? `Lunenburg ${lunRow.total > avg ? 'above' : 'below'} avg by ${fmtFull$(Math.abs(lunRow.total - avg))}` : undefined}
        />
        <KpiCard
          label="Lunenburg rank"
          value={`#${lunRank} of ${data.districts.length}`}
          sub={lunRank <= 3 ? 'Lower cost district' : lunRank >= 7 ? 'Higher cost district' : 'Mid-range'}
        />
        <KpiCard
          label="Lunenburg enrollment"
          value={lunRow ? lunRow.enrollment.toLocaleString() : '—'}
          sub="students"
        />
      </div>

      {/* Horizontal bar chart */}
      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <p className="text-sm font-semibold text-gray-700 mb-1">Total Per-Pupil Expenditure — {selectedYear}</p>
        <p className="text-xs text-gray-400 mb-4">Sorted lowest to highest · Hover for category breakdown</p>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={yearRows} layout="vertical" margin={{ top: 0, right: 60, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f1f5f9" />
            <XAxis
              type="number"
              tickFormatter={v => `$${(v / 1000).toFixed(0)}K`}
              tick={{ fontSize: 11, fill: '#94a3b8' }}
            />
            <YAxis
              type="category"
              dataKey="district"
              width={148}
              tick={({ x, y, payload }: { x: string | number; y: string | number; payload: { value: string } }) => (
                <text
                  x={Number(x) - 4}
                  y={Number(y) + 4}
                  textAnchor="end"
                  fontSize={11}
                  fontWeight={payload.value === 'Lunenburg' ? 700 : 400}
                  fill={payload.value === 'Lunenburg' ? '#2563eb' : '#64748b'}
                >
                  {payload.value}
                </text>
              )}
            />
            <Tooltip content={<SnapshotTooltip />} />
            <Bar dataKey="total" radius={[0, 4, 4, 0]}>
              {yearRows.map(row => (
                <Cell
                  key={row.district}
                  fill={DISTRICT_COLORS[row.district] ?? '#94a3b8'}
                  opacity={row.district === 'Lunenburg' ? 1 : 0.7}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        {/* Average line label */}
        <p className="text-xs text-gray-400 mt-1 text-right">9-district average: {fmtFull$(avg)}</p>
      </div>

      {/* Detail table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-100 bg-gray-50">
          <p className="text-sm font-semibold text-gray-700">
            Category Breakdown — {selectedYear}
            <span className="ml-2 text-xs font-normal text-gray-400">(per pupil)</span>
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-gray-100">
                <th className="py-2 px-4 text-left text-gray-400 font-semibold sticky left-0 bg-white">District</th>
                {DESE_CATEGORIES.map(cat => (
                  <th key={cat.key as string} className="py-2 px-2 text-right text-gray-400 font-semibold whitespace-nowrap">
                    {cat.label.split(' ')[0]}
                    <br />
                    <span className="text-gray-300 font-normal">{cat.label.split(' ').slice(1).join(' ')}</span>
                  </th>
                ))}
                <th className="py-2 px-3 text-right text-gray-400 font-semibold">Total</th>
                <th className="py-2 px-3 text-right text-gray-400 font-semibold">Enrollment</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {/* Column averages row */}
              <tr className="bg-gray-50 border-b-2 border-gray-200">
                <td className="py-2 px-4 font-semibold text-gray-500 sticky left-0 bg-gray-50">9-District Avg</td>
                {DESE_CATEGORIES.map(cat => {
                  const catAvg = Math.round(
                    data.rows.filter(r => r.year === selectedYear)
                      .reduce((s, r) => s + (r[cat.key] as number), 0) / data.districts.length
                  )
                  return (
                    <td key={cat.key as string} className="py-2 px-2 text-right font-mono text-gray-500">
                      {fmtFull$(catAvg)}
                    </td>
                  )
                })}
                <td className="py-2 px-3 text-right font-mono font-semibold text-gray-600">{fmtFull$(avg)}</td>
                <td className="py-2 px-3 text-right font-mono text-gray-500">
                  {Math.round(data.rows.filter(r => r.year === selectedYear).reduce((s, r) => s + r.enrollment, 0) / data.districts.length).toLocaleString()}
                </td>
              </tr>
              {[...yearRows].reverse().map(row => {
                const isLunenburg = row.district === 'Lunenburg'
                return (
                  <tr key={row.district} className={isLunenburg ? 'bg-blue-50' : 'hover:bg-gray-50'}>
                    <td className={`py-2 px-4 font-medium sticky left-0 ${isLunenburg ? 'text-blue-700 bg-blue-50' : 'text-gray-800 bg-white'}`}>
                      <div className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full flex-shrink-0"
                          style={{ backgroundColor: DISTRICT_COLORS[row.district] ?? '#94a3b8' }} />
                        {row.district}
                      </div>
                    </td>
                    {DESE_CATEGORIES.map(cat => {
                      const val = row[cat.key] as number
                      const catAvg = Math.round(
                        data.rows.filter(r => r.year === selectedYear)
                          .reduce((s, r) => s + (r[cat.key] as number), 0) / data.districts.length
                      )
                      const above = val > catAvg
                      return (
                        <td key={cat.key as string}
                          className={`py-2 px-2 text-right font-mono ${
                            isLunenburg
                              ? above ? 'text-red-600 font-semibold' : 'text-green-700 font-semibold'
                              : 'text-gray-700'
                          }`}
                        >
                          {fmtFull$(val)}
                        </td>
                      )
                    })}
                    <td className={`py-2 px-3 text-right font-mono font-bold ${isLunenburg ? 'text-blue-700' : 'text-gray-800'}`}>
                      {fmtFull$(row.total)}
                    </td>
                    <td className="py-2 px-3 text-right font-mono text-gray-500">
                      {row.enrollment.toLocaleString()}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
        {/* Legend for Lunenburg coloring */}
        <div className="px-4 py-2 border-t border-gray-100 bg-gray-50 flex gap-4 text-xs text-gray-400">
          <span><span className="text-red-500 font-semibold">Red</span> = Lunenburg above average for that category</span>
          <span><span className="text-green-600 font-semibold">Green</span> = Lunenburg below average</span>
        </div>
      </div>
    </div>
  )
}

// ── Breakdown Tab ─────────────────────────────────────────────────────────────

function BreakdownTab({ data, selectedYear, onYearChange }: {
  data: DeseData; selectedYear: string; onYearChange: (y: string) => void
}) {
  const chartData = useMemo(() => {
    return data.rows
      .filter(r => r.year === selectedYear)
      .sort((a, b) => b.total - a.total)
  }, [data.rows, selectedYear])

  return (
    <div className="space-y-4">
      {/* Year picker */}
      <div className="flex items-center gap-3">
        <span className="text-sm text-gray-600 font-medium">Year:</span>
        <div className="flex gap-1 flex-wrap">
          {data.years.map(y => (
            <button
              key={y}
              onClick={() => onYearChange(y)}
              className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                y === selectedYear ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {shortYear(y)}
            </button>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <p className="text-sm font-semibold text-gray-700 mb-1">Spending Composition by District — {selectedYear}</p>
        <p className="text-xs text-gray-400 mb-4">
          Stacked bars show per-pupil spending by category · Total bar height = total per-pupil expenditure
        </p>
        <ResponsiveContainer width="100%" height={400}>
          <BarChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 60 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
            <XAxis
              dataKey="district"
              tick={({ x, y, payload }: { x: string | number; y: string | number; payload: { value: string } }) => (
                <text
                  x={Number(x)}
                  y={Number(y) + 10}
                  textAnchor="end"
                  transform={`rotate(-35, ${Number(x)}, ${Number(y) + 10})`}
                  fontSize={11}
                  fontWeight={payload.value === 'Lunenburg' ? 700 : 400}
                  fill={payload.value === 'Lunenburg' ? '#2563eb' : '#64748b'}
                >
                  {payload.value}
                </text>
              )}
            />
            <YAxis
              tickFormatter={v => `$${(v / 1000).toFixed(0)}K`}
              tick={{ fontSize: 11, fill: '#94a3b8' }}
            />
            <Tooltip
              formatter={(value: number | undefined, name: string | undefined) => [value != null ? fmtFull$(value) : '—', name ?? '']}
              contentStyle={{ fontSize: 11, borderRadius: 8 }}
            />
            <Legend
              wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
              formatter={(value: string) => DESE_CATEGORIES.find(c => c.key === value)?.label ?? value}
            />
            {DESE_CATEGORIES.map(cat => (
              <Bar
                key={cat.key as string}
                dataKey={cat.key as string}
                name={cat.key as string}
                stackId="a"
                fill={cat.color}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Category share table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-100 bg-gray-50">
          <p className="text-sm font-semibold text-gray-700">
            Category as % of Total — {selectedYear}
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-gray-100">
                <th className="py-2 px-4 text-left text-gray-400 font-semibold">Category</th>
                {[...chartData].sort((a, b) => {
                  if (a.district === 'Lunenburg') return -1
                  if (b.district === 'Lunenburg') return 1
                  return b.total - a.total
                }).map(row => (
                  <th key={row.district} className={`py-2 px-3 text-right text-xs font-semibold whitespace-nowrap ${
                    row.district === 'Lunenburg' ? 'text-blue-500' : 'text-gray-400'
                  }`}>
                    {row.district === 'Lunenburg' ? '★ ' : ''}{row.district.split('-')[0]}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {DESE_CATEGORIES.map(cat => {
                const sortedRows = [...chartData].sort((a, b) => {
                  if (a.district === 'Lunenburg') return -1
                  if (b.district === 'Lunenburg') return 1
                  return b.total - a.total
                })
                return (
                  <tr key={cat.key as string} className="hover:bg-gray-50">
                    <td className="py-2 px-4 text-gray-700 flex items-center gap-2">
                      <span className="w-2.5 h-2.5 rounded-sm flex-shrink-0" style={{ backgroundColor: cat.color }} />
                      {cat.label}
                    </td>
                    {sortedRows.map(row => {
                      const share = row.total > 0 ? ((row[cat.key] as number) / row.total * 100) : 0
                      const isLunenburg = row.district === 'Lunenburg'
                      return (
                        <td key={row.district} className={`py-2 px-3 text-right font-mono ${
                          isLunenburg ? 'text-blue-700 font-semibold' : 'text-gray-600'
                        }`}>
                          {share.toFixed(1)}%
                        </td>
                      )
                    })}
                  </tr>
                )
              })}
              {/* Total row */}
              <tr className="border-t-2 border-gray-200 font-semibold">
                <td className="py-2 px-4 text-gray-700">Total per pupil</td>
                {[...chartData].sort((a, b) => {
                  if (a.district === 'Lunenburg') return -1
                  if (b.district === 'Lunenburg') return 1
                  return b.total - a.total
                }).map(row => (
                  <td key={row.district} className={`py-2 px-3 text-right font-mono ${
                    row.district === 'Lunenburg' ? 'text-blue-700' : 'text-gray-700'
                  }`}>
                    {fmtFull$(row.total)}
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

type Tab = 'trend' | 'snapshot' | 'breakdown'

export function DistrictComparePage() {
  const [deseData, setDeseData]       = useState<DeseData | null>(null)
  const [loading, setLoading]         = useState(true)
  const [error, setError]             = useState<string | null>(null)
  const [activeTab, setActiveTab]     = useState<Tab>('trend')
  const [selectedYear, setSelectedYear] = useState<string>('')
  const [visibleDistricts, setVisibleDistricts] = useState<string[]>([])

  useEffect(() => {
    parseDeseFile('./data/dese-all-districts.xlsx')
      .then(data => {
        setDeseData(data)
        setSelectedYear(data.years[data.years.length - 1])
        setVisibleDistricts(data.districts)
        setLoading(false)
      })
      .catch(e => {
        setError(String(e))
        setLoading(false)
      })
  }, [])

  function toggleDistrict(district: string) {
    if (district === 'Lunenburg') return // always visible
    setVisibleDistricts(prev =>
      prev.includes(district) ? prev.filter(d => d !== district) : [...prev, district]
    )
  }

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center h-64">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-sm text-gray-500">Loading DESE district data…</p>
        </div>
      </div>
    )
  }

  if (error || !deseData) {
    return (
      <div className="p-6">
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          <p className="font-semibold">Failed to load district comparison data</p>
          <p className="mt-1 text-xs font-mono">{error}</p>
        </div>
      </div>
    )
  }

  const latestYear = deseData.years[deseData.years.length - 1]
  const lunLatest  = getRow(deseData.rows, 'Lunenburg', latestYear)
  const avg        = districtAverage(deseData.rows, latestYear)
  const rank       = rankDistrict(deseData.rows, 'Lunenburg', latestYear)
  const lunEarliest = getRow(deseData.rows, 'Lunenburg', deseData.years[0])
  const lunGrowth = lunLatest && lunEarliest
    ? ((lunLatest.total - lunEarliest.total) / lunEarliest.total * 100)
    : null

  return (
    <div className="p-6 space-y-6 max-w-6xl">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">District Comparison</h1>
        <p className="text-gray-500 mt-1 text-sm">
          Lunenburg Public Schools vs. 8 peer districts · DESE per-pupil expenditure data ·{' '}
          {deseData.years[0]} – {latestYear}
        </p>
      </div>

      {/* Top KPIs */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <KpiCard
          highlight
          label={`Lunenburg ${shortYear(latestYear)}`}
          value={lunLatest ? fmtFull$(lunLatest.total) : '—'}
          sub="per-pupil expenditure"
        />
        <KpiCard
          label="9-district average"
          value={fmtFull$(avg)}
          sub={`${latestYear}`}
        />
        <KpiCard
          label="Lunenburg rank"
          value={`#${rank} of ${deseData.districts.length}`}
          sub={rank <= 3 ? 'Among lowest cost' : rank >= 7 ? 'Among highest cost' : 'Mid-range'}
        />
        <KpiCard
          label={`Growth ${shortYear(deseData.years[0])}–${shortYear(latestYear)}`}
          value={lunGrowth !== null ? `+${lunGrowth.toFixed(1)}%` : '—'}
          sub="Lunenburg 7-year trend"
        />
      </div>

      {/* Source note */}
      <div className="rounded-lg bg-amber-50 border border-amber-200 px-4 py-2.5 text-xs text-amber-800 flex items-start gap-2">
        <span className="flex-shrink-0 mt-0.5">ℹ</span>
        <span>
          This page uses <strong>DESE per-pupil expenditure data</strong> (actual spending ÷ enrollment) for{' '}
          {deseData.years[0]} through {latestYear}. These are <em>audited actuals</em>, not proposed budgets.
          The Lunenburg budget spreadsheet covers proposed FY27+ spending, which is a different dataset.
          Peer districts were selected based on geographic and demographic similarity.
        </span>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-gray-200 pb-3">
        <TabBtn active={activeTab === 'trend'} onClick={() => setActiveTab('trend')}>
          Spending Trend
        </TabBtn>
        <TabBtn active={activeTab === 'snapshot'} onClick={() => setActiveTab('snapshot')}>
          Peer Snapshot
        </TabBtn>
        <TabBtn active={activeTab === 'breakdown'} onClick={() => setActiveTab('breakdown')}>
          Category Breakdown
        </TabBtn>
      </div>

      {/* Tab content */}
      {activeTab === 'trend' && (
        <TrendTab
          data={deseData}
          visible={visibleDistricts}
          onToggle={toggleDistrict}
        />
      )}
      {activeTab === 'snapshot' && (
        <SnapshotTab
          data={deseData}
          selectedYear={selectedYear}
          onYearChange={setSelectedYear}
        />
      )}
      {activeTab === 'breakdown' && (
        <BreakdownTab
          data={deseData}
          selectedYear={selectedYear}
          onYearChange={setSelectedYear}
        />
      )}
    </div>
  )
}
