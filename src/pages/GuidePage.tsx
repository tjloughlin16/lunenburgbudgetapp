import { useBudgetStore } from '../store/budgetStore'
import { CATEGORY_CODES, CATEGORY_LABELS, CATEGORY_COLORS, CATEGORY_DESCRIPTIONS } from '../data/types'
import type { CategoryCode } from '../data/types'

// ── Reusable layout pieces ────────────────────────────────────────────────────

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-100 bg-gray-50">
        <h2 className="text-lg font-bold text-gray-900">{title}</h2>
      </div>
      <div className="px-6 py-5 space-y-4 text-sm text-gray-700 leading-relaxed">
        {children}
      </div>
    </section>
  )
}

function Callout({ icon, color, children }: { icon: string; color: string; children: React.ReactNode }) {
  return (
    <div className={`flex gap-3 rounded-lg p-4 ${color}`}>
      <span className="text-lg flex-shrink-0">{icon}</span>
      <div className="text-sm leading-relaxed">{children}</div>
    </div>
  )
}

function Term({ word, children }: { word: string; children: React.ReactNode }) {
  return (
    <div className="border-l-2 border-blue-300 pl-4">
      <p className="font-semibold text-gray-900">{word}</p>
      <p className="text-gray-600 mt-0.5">{children}</p>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export function GuidePage() {
  const { years } = useBudgetStore()

  // Split discovered years into actuals vs. proposed for the explanation
  const actualsYears = years.filter(y => !y.isProjected)
  const proposedYear = years.find(y => y.isProjected)

  return (
    <div className="p-6 space-y-6 max-w-3xl">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">How to Read the Budget</h1>
        <p className="text-gray-500 mt-1">
          A plain-English guide to understanding the Lunenburg Public Schools budget spreadsheet
        </p>
      </div>

      {/* 1 — Big picture */}
      <Section title="The Big Picture">
        <p>
          The school budget spreadsheet is a detailed list of <strong>every dollar</strong> the
          district plans to spend — from teacher salaries to printer paper. It's organized into
          roughly 400 line items grouped by department and split across five fiscal years so
          you can see trends over time.
        </p>
        <p>
          The budget is divided into <strong>two major sections</strong>:
        </p>
        <div className="grid sm:grid-cols-2 gap-3 not-prose">
          <div className="rounded-lg border-2 border-blue-200 bg-blue-50 p-4">
            <p className="font-bold text-blue-800">District Expenses</p>
            <p className="text-blue-700 mt-1 text-sm">
              Everything that <em>isn't</em> a salary: textbooks, technology, contracts,
              utilities, insurance, field trip buses, office supplies, and so on.
            </p>
          </div>
          <div className="rounded-lg border-2 border-purple-200 bg-purple-50 p-4">
            <p className="font-bold text-purple-800">District Salaries</p>
            <p className="text-purple-700 mt-1 text-sm">
              Every employee's compensation: teachers, principals, paraprofessionals,
              custodians, secretaries, coaches, and administrators.
            </p>
          </div>
        </div>
        <Callout icon="💡" color="bg-amber-50 text-amber-800">
          <strong>Why two sections?</strong> School budgets traditionally separate
          "people costs" from "operating costs" because salaries are by far the largest
          driver — typically 75–80% of a school budget — and need their own level of scrutiny.
        </Callout>
      </Section>

      {/* 2 — Account codes */}
      <Section title="The Account Code System">
        <p>
          Every row in the budget has a <strong>4-digit account code</strong> in the first
          column (e.g., <code className="bg-gray-100 px-1 rounded font-mono">2305</code>).
          This code is the key to understanding where money is going.
        </p>
        <p>
          The <strong>first digit</strong> tells you the broad category. The remaining three
          digits identify the specific department or program within that category:
        </p>

        <div className="not-prose overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b-2 border-gray-200">
                <th className="py-2 pr-4 text-left text-xs font-semibold text-gray-400 uppercase tracking-wide w-16">Code</th>
                <th className="py-2 pr-4 text-left text-xs font-semibold text-gray-400 uppercase tracking-wide">Category</th>
                <th className="py-2 text-left text-xs font-semibold text-gray-400 uppercase tracking-wide">What it covers</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {(CATEGORY_CODES as CategoryCode[]).map(code => (
                <tr key={code}>
                  <td className="py-2.5 pr-4">
                    <span
                      className="inline-flex items-center justify-center w-8 h-8 rounded-lg text-white text-sm font-bold"
                      style={{ backgroundColor: CATEGORY_COLORS[code] }}
                    >
                      {code}
                    </span>
                  </td>
                  <td className="py-2.5 pr-4 font-semibold text-gray-800">
                    {CATEGORY_LABELS[code]}
                  </td>
                  <td className="py-2.5 text-gray-600">
                    {CODE_DESCRIPTIONS[code]}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <Callout icon="📌" color="bg-blue-50 text-blue-800">
          <strong>Example:</strong> Account code <code className="bg-blue-100 px-1 rounded font-mono">2305</code> is
          in category <strong>2 (Instructional)</strong>. You'd find it in both
          the Expenses section (instructional materials) <em>and</em> the Salaries section
          (instructional staff pay) — with different line items under each.
        </Callout>
      </Section>

      {/* 3 — Same code, two sections */}
      <Section title='Why You See "Instructional · salaries" and "Instructional · expenses"'>
        <p>
          This is one of the trickiest things about reading this budget — and a common source
          of confusion.
        </p>
        <p>
          Because the spreadsheet has <em>two separate sections</em> (Expenses and Salaries),
          the same account code prefix can appear <strong>twice</strong> — once in each section.
          For example:
        </p>
        <div className="not-prose space-y-2">
          <div className="flex items-start gap-3 rounded-lg bg-gray-50 p-3">
            <span className="font-mono text-sm bg-gray-200 px-2 py-0.5 rounded mt-0.5">2305</span>
            <div>
              <p className="font-semibold text-gray-800">In the Expenses section</p>
              <p className="text-gray-600 text-sm">Library books, online databases, classroom materials</p>
            </div>
          </div>
          <div className="flex items-start gap-3 rounded-lg bg-gray-50 p-3">
            <span className="font-mono text-sm bg-gray-200 px-2 py-0.5 rounded mt-0.5">2305</span>
            <div>
              <p className="font-semibold text-gray-800">In the Salaries section</p>
              <p className="text-gray-600 text-sm">Library staff salaries and benefits</p>
            </div>
          </div>
        </div>
        <p>
          In this explorer, the <strong>Compare Years</strong> page and <strong>drill-down</strong> pages
          show both separately so you can see exactly which part changed. The little tag
          like <code className="bg-gray-100 px-1 rounded text-xs">Instructional · salaries</code> tells
          you: "this is the <em>salaries</em> portion of Instructional spending."
        </p>
        <Callout icon="🔍" color="bg-green-50 text-green-800">
          To find the full cost of a department, add up its Expenses entry <em>and</em> its
          Salaries entry. The Dashboard's <strong>Spending Map</strong> does this automatically —
          clicking a tile shows you both sections combined.
        </Callout>
      </Section>

      {/* 4 — Year columns */}
      <Section title="What the Year Columns Mean">
        <p>
          The budget spreadsheet shows {years.length > 0 ? years.length : 'five'} fiscal years
          side by side. Reading left to right, older years appear first:
        </p>
        <div className="not-prose space-y-2">
          {actualsYears.map((y, i) => (
            <div key={y.key} className="flex items-center gap-3">
              <span className="w-20 font-mono text-sm font-semibold text-gray-700">{y.short}</span>
              <span className="flex-1 h-px bg-gray-200" />
              <span className="text-gray-600 text-sm">
                {i === actualsYears.length - 1 ? 'Most recent actual spending' : 'Actual spending — final numbers'}
              </span>
            </div>
          ))}
          {proposedYear && (
            <div className="flex items-center gap-3">
              <span className="w-20 font-mono text-sm font-bold text-blue-700">{proposedYear.short}</span>
              <span className="flex-1 h-px bg-blue-200" />
              <span className="text-blue-700 text-sm font-medium">
                Proposed — this is what the School Committee is requesting
              </span>
            </div>
          )}
        </div>
        <div className="not-prose space-y-3 mt-2">
          <Term word="Actuals">
            What the district <em>actually spent</em> that year. The books are closed; this is
            the final, audited number.
          </Term>
          <Term word="Budget / Proposed">
            What the district is <em>asking to spend</em>. This number may change before the
            Town Meeting vote and is not guaranteed.
          </Term>
          <Term word="% Change">
            The last column in any table shows the percentage difference between the two most
            recent years. A <span className="text-red-600 font-medium">red ▲</span> means
            costs went up; a <span className="text-green-600 font-medium">green ▼</span> means
            costs went down.
          </Term>
        </div>
        <Callout icon="📅" color="bg-gray-50 text-gray-700">
          A Massachusetts fiscal year runs <strong>July 1 – June 30</strong>. "FY27" means
          July 1, 2026 through June 30, 2027. The school year that starts in September 2026
          is funded by the FY27 budget.
        </Callout>
      </Section>

      {/* 5 — Group headers vs line items */}
      <Section title="Group Headers vs. Line Items">
        <p>
          Within each section, the budget is organized into <strong>department groups</strong>.
          Each group has:
        </p>
        <div className="not-prose space-y-3">
          <div className="rounded-lg border border-gray-200 overflow-hidden text-sm">
            {/* Mock table header */}
            <div className="bg-gray-50 px-3 py-1.5 text-xs text-gray-400 font-semibold uppercase tracking-wide flex gap-4">
              <span className="w-28">Code</span>
              <span>Description</span>
            </div>
            {/* Group header row */}
            <div className="px-3 py-2 flex gap-4 bg-gray-50 border-t border-gray-200 font-semibold text-gray-900">
              <span className="w-28 font-mono text-xs">2305</span>
              <span>Library Services</span>
              <span className="ml-auto text-blue-600 text-xs">← Group header (department name)</span>
            </div>
            {/* Line items */}
            {[
              ['', 'Library Books & Materials', '← Non-salary line item'],
              ['', 'Online Database Subscriptions', ''],
              ['', 'Equipment & Supplies', ''],
            ].map(([code, desc, note], i) => (
              <div key={i} className="px-3 py-1.5 flex gap-4 border-t border-gray-100 text-gray-600 pl-8">
                <span className="w-28 font-mono text-xs text-gray-300">{code || '—'}</span>
                <span>{desc}</span>
                {note && <span className="ml-auto text-green-600 text-xs">{note}</span>}
              </div>
            ))}
          </div>
        </div>
        <p className="mt-2">
          The <strong>group header row</strong> (bold, with the 4-digit code) names the
          department. The <strong>line item rows</strong> below it, indented without their own
          code, are the individual purchases or positions within that department.
        </p>
        <p>
          When you click a tile in the <strong>Spending Map</strong> or a row in
          the <strong>Compare Years</strong> view, you land on a drill-down page that shows
          all the line items inside that group.
        </p>
      </Section>

      {/* 6 — FAQ */}
      <Section title="Frequently Asked Questions">
        <div className="space-y-5">
          <Faq q="Why doesn't the grand total equal Expenses + Salaries added separately?">
            It does — but watch out for double-counting group header rows. The totals in this
            app sum only the <em>line item</em> rows (not the header rows), so the math is clean.
          </Faq>
          <Faq q='What does "—" or blank mean in a year column?'>
            A dash means there was no budget or spending for that line item in that year.
            This is common for new programs (no prior-year data) or discontinued items
            (no future-year data).
          </Faq>
          <Faq q="What is 'Salary Reserve'?">
            A district-level placeholder for anticipated salary increases that haven't yet
            been assigned to specific departments — for example, budgeting for a contract
            negotiation that's still in progress. It sits outside any department group.
          </Faq>
          <Faq q="How do I find a specific teacher's salary?">
            Individual salaries are not broken out in this budget — only department totals
            are shown. Detailed salary data is available through the Massachusetts public
            records process.
          </Faq>
          <Faq q="What happens after Town Meeting votes on this budget?">
            If the budget passes, the proposed FY{proposedYear?.short.replace('FY', '') ?? '27'} column
            becomes the approved budget and the district can begin spending against it in July.
            If it fails, the School Committee must revise and resubmit.
          </Faq>
          <Faq q="Where does the money come from?">
            Lunenburg Public Schools is funded primarily through local property taxes (the
            Town's assessment), supplemented by Chapter 70 state aid and various federal
            grants. This budget shows how the money is <em>spent</em>, not how it's raised.
          </Faq>
        </div>
      </Section>

      {/* 7 — Using this tool */}
      <Section title="Getting the Most from This Explorer">
        <div className="not-prose space-y-3">
          {[
            {
              icon: '🗺️',
              title: 'Start with the Spending Map',
              desc: 'The treemap on the Dashboard gives you an instant visual sense of where the money goes. Bigger tiles = more money. Click any tile to drill into that department.',
            },
            {
              icon: '💡',
              title: 'Check the Insights tab',
              desc: 'Auto-generated plain-English takeaways highlight the biggest changes, cost drivers, and historical context — great if you\'re short on time.',
            },
            {
              icon: '📊',
              title: 'Use Compare Years to track changes',
              desc: 'Switch to the Compare tab to see every department side-by-side sorted by largest change. Red numbers went up; green numbers went down.',
            },
            {
              icon: '🔎',
              title: 'Search for anything',
              desc: 'Type any word in the search bar (e.g., "textbooks", "special ed", "custodian") to find matching line items across the entire budget.',
            },
            {
              icon: '📥',
              title: 'Export the data',
              desc: 'The Export button downloads a CSV of the current view — all five years — that you can open in Excel or Google Sheets for your own analysis.',
            },
          ].map(tip => (
            <div key={tip.title} className="flex gap-3">
              <span className="text-xl flex-shrink-0">{tip.icon}</span>
              <div>
                <p className="font-semibold text-gray-900">{tip.title}</p>
                <p className="text-gray-600 text-sm mt-0.5">{tip.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </Section>
    </div>
  )
}

// ── Static helpers ────────────────────────────────────────────────────────────

const CODE_DESCRIPTIONS = CATEGORY_DESCRIPTIONS

function Faq({ q, children }: { q: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="font-semibold text-gray-900">Q: {q}</p>
      <p className="text-gray-600 mt-1">A: {children as string}</p>
    </div>
  )
}
