import type { LineItem, BudgetData, FiscalYear } from './types'

// ── Department definitions ─────────────────────────────────────────────────

export interface DepartmentDef {
  id: string
  label: string
  abbrev: string       // short label for tab pills
  group: 'school' | 'program' | 'staff'
  description: string
  colorClass: string   // tailwind border/badge color key (used in component)
}

export const DEPARTMENTS: DepartmentDef[] = [
  // ── Schools ───────────────────────────────────────────────────────────────
  {
    id: 'ps', label: 'Primary School', abbrev: 'P.S.',
    group: 'school',
    description: 'All budget lines attributed to the Primary School building, including teachers, principal office, instructional materials, and school-specific staff.',
    colorClass: 'sky',
  },
  {
    id: 'es', label: 'Elementary School', abbrev: 'E.S.',
    group: 'school',
    description: 'All budget lines attributed to the Elementary School building.',
    colorClass: 'amber',
  },
  {
    id: 'ms', label: 'Middle School', abbrev: 'M.S.',
    group: 'school',
    description: 'All budget lines attributed to the Middle School building.',
    colorClass: 'violet',
  },
  {
    id: 'hs', label: 'High School', abbrev: 'H.S.',
    group: 'school',
    description: 'All budget lines attributed to the High School building, including department heads stipends and HS-specific instructional materials.',
    colorClass: 'rose',
  },

  // ── Programs ──────────────────────────────────────────────────────────────
  {
    id: 'sped', label: 'Special Education', abbrev: 'Spec. Ed',
    group: 'program',
    description: 'Special education teachers, paraprofessionals, therapeutic services, psychological services, substitutes, and out-of-district tuitions. These costs are largely driven by individual student IEPs and federal/state mandates.',
    colorClass: 'purple',
  },
  {
    id: 'athletics', label: 'Athletics & Activities', abbrev: 'Athletics',
    group: 'program',
    description: 'Athletic program expenses, coaching staff salaries, and after-school advisor salaries.',
    colorClass: 'green',
  },
  {
    id: 'music', label: 'Music & Performing Arts', abbrev: 'Music',
    group: 'program',
    description: 'Music teachers, band directors, chorus, orchestra, and related instructional materials and instruments across all school buildings.',
    colorClass: 'pink',
  },
  {
    id: 'admin', label: 'Administration', abbrev: 'Admin',
    group: 'staff',
    description: "District-wide administration: school committee, superintendent's office, business office, legal services, HR, administrative technology, and building principals.",
    colorClass: 'slate',
  },
  {
    id: 'guidance', label: 'Guidance & Student Support', abbrev: 'Guidance',
    group: 'staff',
    description: 'Guidance counselors, psychologists, social workers, and school nurses — the student support and mental health infrastructure.',
    colorClass: 'teal',
  },
  {
    id: 'health', label: 'Health Services', abbrev: 'Health',
    group: 'program',
    description: 'School nursing staff and medical/health services for students.',
    colorClass: 'emerald',
  },
  {
    id: 'transportation', label: 'Transportation', abbrev: 'Transport',
    group: 'program',
    description: 'Student transportation including regular bus routes and specialized transport for students with disabilities.',
    colorClass: 'orange',
  },
  {
    id: 'technology', label: 'Technology', abbrev: 'Tech',
    group: 'program',
    description: 'Instructional technology, networking, telecommunications, and digital infrastructure.',
    colorClass: 'cyan',
  },
  {
    id: 'facilities', label: 'Facilities & Operations', abbrev: 'Facilities',
    group: 'program',
    description: 'Custodial services, building heating, utilities, grounds maintenance, building repairs, and maintenance.',
    colorClass: 'stone',
  },
  {
    id: 'benefits', label: 'Benefits & Insurance', abbrev: 'Benefits',
    group: 'program',
    description: 'Employee health insurance, retirement contributions, workers compensation, and crossing guard costs. These are largely non-discretionary fixed obligations.',
    colorClass: 'indigo',
  },
  {
    id: 'teachers', label: 'Classroom Teachers', abbrev: 'Teachers',
    group: 'staff',
    description: 'General education classroom teachers across all school buildings — the core instructional staff. Does not include special education teachers (counted under Special Education) or specialists like music, guidance, or librarians.',
    colorClass: 'blue',
  },
  {
    id: 'paras', label: 'Paraprofessionals', abbrev: 'Paras',
    group: 'staff',
    description: 'Paraprofessional staff across all buildings, including both general education and special education paraprofessionals. Sped paras are also counted under Special Education.',
    colorClass: 'yellow',
  },
  {
    id: 'nurses', label: 'School Nurses', abbrev: 'Nurses',
    group: 'staff',
    description: 'School nursing staff salaries across all buildings plus a district nurse coordinator. Non-salary health expenses are counted under Health Services.',
    colorClass: 'red',
  },
  {
    id: 'librarians', label: 'Librarians', abbrev: 'Library',
    group: 'staff',
    description: 'School librarians at the Primary, Elementary, Middle, and High Schools.',
    colorClass: 'lime',
  },
  {
    id: 'substitutes', label: 'Substitutes', abbrev: 'Subs',
    group: 'staff',
    description: 'Substitute teacher salaries across all buildings, including both general education and special education substitutes.',
    colorClass: 'gray',
  },
  {
    id: 'coaches', label: 'Coaches & Advisors', abbrev: 'Coaches',
    group: 'staff',
    description: 'Athletic director, trainer, coaches, and after-school activity advisors. Non-salary athletic expenses (equipment, transportation, insurance) are counted under Athletics & Activities.',
    colorClass: 'fuchsia',
  },
  {
    id: 'contracted', label: 'Contracted Services', abbrev: 'Contracted',
    group: 'program',
    description: 'Spending on outside vendors and contracted services: IT/computer contracts, building and grounds maintenance contracts, networking, purchased professional services, and student transportation (almost entirely outsourced to a bus vendor).',
    colorClass: 'zinc',
  },
]

// ── School key detection (shared with insights.ts) ─────────────────────────
// Strips leading numeric code then checks for abbreviation or full-name form.

export function getSchoolKey(text: string): string | null {
  const t = text.replace(/^\d+\s*[-–]\s*/, '').trim()
  const m = t.match(/^([A-Z]\.[A-Z]\.)\s/)
  if (m) return m[1].replace(/\./g, '').toLowerCase()  // "ps"|"es"|"ms"|"hs"
  if (/^Primary\s+School\b/i.test(t))     return 'ps'
  if (/^Elementary\s+School\b/i.test(t))  return 'es'
  if (/^Middle\s+School\b/i.test(t))      return 'ms'
  if (/^High\s+School\b/i.test(t))        return 'hs'
  return null
}

// ── Filter line items for a given department ───────────────────────────────

export interface DeptLineItem {
  id: string
  description: string
  section: 'expenses' | 'salaries'
  parentLabel: string
  values: Record<string, number | null>  // keyed by year key e.g. "fy27"
  delta: number
  pctChange: number | null
  parentCode: string | null
}

export function filterItemsForDepartment(
  deptId: string,
  data: BudgetData,
  primaryYear: FiscalYear,
  compareYear: FiscalYear,
): DeptLineItem[] {
  const groupLabelByCode = new Map(data.groups.map(g => [g.code, g.label]))
  const groupCatByCode   = new Map(data.groups.map(g => [g.code, g.categoryCode]))

  const SCHOOL_IDS = new Set(['ps', 'es', 'ms', 'hs'])

  function matches(item: LineItem): boolean {
    if (item.isGroupHeader || item.section === 'summary') return false

    const parentLabel = item.parentCode ? (groupLabelByCode.get(item.parentCode) ?? '') : ''
    const parentCat   = item.parentCode ? (groupCatByCode.get(item.parentCode) ?? null) : null
    const parentCode  = item.parentCode ?? ''

    if (SCHOOL_IDS.has(deptId)) {
      const key = getSchoolKey(item.description) ?? getSchoolKey(parentLabel) ?? 'district'
      return key === deptId
    }

    // Helper: does a string contain any of the given substrings?
    const has = (str: string, ...terms: string[]) =>
      terms.some(t => str.toLowerCase().includes(t.toLowerCase()))

    switch (deptId) {
      case 'sped':
        return has(parentLabel, 'special ed', 'special education', 'therapeutic', 'curriculum/spec ed') ||
               has(parentCode,  'special ed', 'special education', 'therapeutic') ||
               has(item.description, 'special ed', 'sped') ||
               parentCode.startsWith('9300') ||  // private tuitions (usually sped)
               parentCode.startsWith('9400')     // collaborative tuitions
      case 'athletics':
        return parentCode.startsWith('3510') || parentCode.startsWith('3520')
      case 'music':
        return has(item.description, 'music', 'band', 'chorus', 'orchestra', 'choir') ||
               has(parentLabel,      'music', 'band', 'chorus', 'orchestra', 'choir')
      case 'admin':
        return parentCat === '1' || parentCode.startsWith('2210')
      case 'guidance':
        return parentCode.startsWith('2710') ||  // guidance expenses + salaries
               parentCode.startsWith('2800') ||  // psych services
               parentCode.startsWith('2900')     // social worker salaries
      case 'health':
        return parentCode.startsWith('3200')
      case 'transportation':
        return parentCode.startsWith('3300') || parentCode.startsWith('5500') // crossing guards
      case 'technology':
        return parentCode.startsWith('2451') || parentCode.startsWith('4400') || parentCode.startsWith('1450')
      case 'facilities':
        return parentCat === '4' &&
               !parentCode.startsWith('4400')  // 4400 is telecom → goes to technology
      case 'benefits':
        return parentCode.startsWith('5200')
      case 'teachers':
        return parentCode.startsWith('2305')
      case 'paras':
        return parentCode.startsWith('2330')
      case 'nurses':
        return parentCode.startsWith('3200') && item.section === 'salaries'
      case 'librarians':
        return parentCode.startsWith('2340')
      case 'substitutes':
        return parentCode.startsWith('2325')
      case 'coaches':
        return (parentCode.startsWith('3510') || parentCode.startsWith('3520')) && item.section === 'salaries'
      case 'contracted': {
        const d = item.description.toLowerCase()
        return d.includes('contract') || d.includes('contrct') || d.includes('purchased service') ||
               parentCode.startsWith('3300')  // transportation — fully outsourced bus vendor
      }
      default:
        return false
    }
  }

  const pct = (a: number, b: number) => Math.abs(a) < 0.005 ? null : (b - a) / a

  return data.lineItems
    .filter(matches)
    .map(item => {
      const parentLabel = item.parentCode
        ? (groupLabelByCode.get(item.parentCode) ?? item.parentCode)
        : ''
      const a = item.values[compareYear] ?? 0
      const b = item.values[primaryYear] ?? 0
      // Strip school prefix from description for school views
      const displayDesc = SCHOOL_IDS.has(deptId)
        ? item.description.replace(/^[A-Z]\.[A-Z]\.\s*/,'').replace(/^(Primary|Elementary|Middle|High)\s+School\s*/i,'').trim() || item.description
        : item.description
      // Clean parent label
      const cleanParent = parentLabel.replace(/^\d+\s*[-–]\s*/, '').trim()

      return {
        id: item.id,
        description: displayDesc,
        section: item.section as 'expenses' | 'salaries',
        parentLabel: cleanParent,
        values: item.values as Record<string, number | null>,
        delta: b - a,
        pctChange: pct(a, b),
        parentCode: item.parentCode,
      }
    })
}

// ── CSV export ─────────────────────────────────────────────────────────────

import Papa from 'papaparse'
import type { YearColumn } from './types'

export function downloadDepartmentCSV(
  deptLabel: string,
  items: DeptLineItem[],
  years: YearColumn[],
  primaryYear: FiscalYear,
  compareYear: FiscalYear,
): void {
  const rows = items.map(item => {
    const row: Record<string, string | number> = {
      Department: deptLabel,
      Description: item.description,
      Section: item.section,
      'Parent Group': item.parentLabel,
    }
    for (const y of years) {
      const v = item.values[y.key]
      row[y.label] = v !== null ? v : ''
    }
    const a = item.values[compareYear] ?? 0
    const b = item.values[primaryYear] ?? 0
    row['Delta ($)'] = b - a
    const pctChange = Math.abs(a) > 0.005 ? (b - a) / a : null
    row['% Change'] = pctChange !== null ? `${(pctChange * 100).toFixed(1)}%` : ''
    return row
  })

  const csv = Papa.unparse(rows)
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `lunenburg-budget-${deptLabel.toLowerCase().replace(/[^a-z0-9]+/g, '-')}.csv`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}
