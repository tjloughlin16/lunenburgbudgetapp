import * as XLSX from 'xlsx'

// ── Types ────────────────────────────────────────────────────────────────────

export interface DeseRow {
  district: string
  year: string          // e.g. "FY2023–24"
  enrollment: number
  administration: number
  instructionalLeadership: number
  teachers: number
  otherTeachingServices: number
  professionalDevelopment: number
  instructionalMaterials: number
  guidanceCounseling: number
  pupilServices: number
  operationsMaintenance: number
  insuranceRetirement: number
  total: number
}

export interface DeseData {
  rows: DeseRow[]
  districts: string[]   // in original order (Lunenburg first)
  years: string[]       // chronological
}

// ── Parser ───────────────────────────────────────────────────────────────────

export async function parseDeseFile(url: string): Promise<DeseData> {
  const resp = await fetch(url)
  if (!resp.ok) throw new Error(`Failed to fetch DESE data: ${resp.status}`)
  const buf = await resp.arrayBuffer()
  const wb = XLSX.read(buf)

  const ws = wb.Sheets['Per Pupil Raw']
  if (!ws) throw new Error('Sheet "Per Pupil Raw" not found in DESE file')

  // The sheet's first row is a title; the second row is the real header.
  // sheet_to_json with default settings treats the first row as headers,
  // so the second row becomes the header names and rows 2+ are data.
  const rawRows = XLSX.utils.sheet_to_json(ws, { defval: null }) as Record<string, unknown>[]

  // Row 0 of rawRows contains the actual column labels (the header row in the sheet)
  // Rows 1+ contain the real data
  const data = rawRows.slice(1).filter(
    r => r['DESE — Raw Per-Pupil Expenditures (source data)'] && r['__EMPTY']
  )

  const rows: DeseRow[] = data.map(r => ({
    district:                String(r['DESE — Raw Per-Pupil Expenditures (source data)']),
    year:                    String(r['__EMPTY']),
    enrollment:              Number(r['__EMPTY_1'])  || 0,
    administration:          Number(r['__EMPTY_2'])  || 0,
    instructionalLeadership: Number(r['__EMPTY_3'])  || 0,
    teachers:                Number(r['__EMPTY_4'])  || 0,
    otherTeachingServices:   Number(r['__EMPTY_5'])  || 0,
    professionalDevelopment: Number(r['__EMPTY_6'])  || 0,
    instructionalMaterials:  Number(r['__EMPTY_7'])  || 0,
    guidanceCounseling:      Number(r['__EMPTY_8'])  || 0,
    pupilServices:           Number(r['__EMPTY_9'])  || 0,
    operationsMaintenance:   Number(r['__EMPTY_10']) || 0,
    insuranceRetirement:     Number(r['__EMPTY_11']) || 0,
    total:                   Number(r['__EMPTY_12']) || 0,
  }))

  const districts = [...new Set(rows.map(r => r.district))]
  const years     = [...new Set(rows.map(r => r.year))]

  return { rows, districts, years }
}

// ── Helpers ──────────────────────────────────────────────────────────────────

export const DESE_CATEGORIES: { key: keyof DeseRow; label: string; color: string }[] = [
  { key: 'teachers',                label: 'Teachers',                    color: '#4f46e5' },
  { key: 'otherTeachingServices',   label: 'Other Teaching Services',     color: '#7c3aed' },
  { key: 'instructionalLeadership', label: 'Instructional Leadership',    color: '#2563eb' },
  { key: 'pupilServices',           label: 'Pupil Services',              color: '#0891b2' },
  { key: 'guidanceCounseling',      label: 'Guidance & Counseling',       color: '#0d9488' },
  { key: 'insuranceRetirement',     label: 'Insurance & Retirement',      color: '#ea580c' },
  { key: 'operationsMaintenance',   label: 'Operations & Maintenance',    color: '#d97706' },
  { key: 'administration',          label: 'Administration',              color: '#64748b' },
  { key: 'instructionalMaterials',  label: 'Instructional Materials/Tech',color: '#06b6d4' },
  { key: 'professionalDevelopment', label: 'Professional Development',    color: '#ec4899' },
]

export const DISTRICT_COLORS: Record<string, string> = {
  'Lunenburg':              '#2563eb',
  'Groton-Dunstable':       '#7c3aed',
  'Littleton':              '#059669',
  'Ashburnham-Westminster': '#d97706',
  'Ayer-Shirley':           '#dc2626',
  'Nashoba':                '#0891b2',
  'Wachusett':              '#9333ea',
  'Leominster':             '#16a34a',
  'Fitchburg':              '#ea580c',
}

export function getRow(rows: DeseRow[], district: string, year: string): DeseRow | undefined {
  return rows.find(r => r.district === district && r.year === year)
}

export function districtAverage(rows: DeseRow[], year: string): number {
  const yearRows = rows.filter(r => r.year === year)
  if (!yearRows.length) return 0
  return Math.round(yearRows.reduce((s, r) => s + r.total, 0) / yearRows.length)
}

export function rankDistrict(rows: DeseRow[], district: string, year: string): number {
  const yearRows = [...rows.filter(r => r.year === year)].sort((a, b) => a.total - b.total)
  return yearRows.findIndex(r => r.district === district) + 1
}
