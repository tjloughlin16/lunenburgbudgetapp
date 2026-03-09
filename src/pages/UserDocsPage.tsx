import { useState } from 'react'
import { Link } from 'react-router-dom'

// ── Layout primitives ──────────────────────────────────────────────────────────

function DocSection({
  id,
  title,
  subtitle,
  children,
}: {
  id: string
  title: string
  subtitle?: string
  children: React.ReactNode
}) {
  return (
    <section id={id} className="bg-white rounded-xl border border-gray-200 overflow-hidden scroll-mt-20">
      <div className="px-6 py-4 border-b border-gray-100 bg-gray-50">
        <h2 className="text-lg font-bold text-gray-900">{title}</h2>
        {subtitle && <p className="text-sm text-gray-500 mt-0.5">{subtitle}</p>}
      </div>
      <div className="px-6 py-5 space-y-4 text-sm text-gray-700 leading-relaxed">{children}</div>
    </section>
  )
}

function SubSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="space-y-2">
      <h3 className="font-bold text-gray-900 text-base border-b border-gray-100 pb-1">{title}</h3>
      <div className="space-y-2">{children}</div>
    </div>
  )
}

function Callout({
  kind = 'info',
  title,
  children,
}: {
  kind?: 'info' | 'tip' | 'warn' | 'note'
  title?: string
  children: React.ReactNode
}) {
  const styles = {
    info: 'bg-blue-50 border-blue-200 text-blue-900',
    tip: 'bg-green-50 border-green-200 text-green-900',
    warn: 'bg-amber-50 border-amber-200 text-amber-900',
    note: 'bg-gray-50 border-gray-200 text-gray-700',
  }
  const icons = { info: 'ℹ', tip: '✓', warn: '⚠', note: '·' }
  return (
    <div className={`rounded-lg border p-4 ${styles[kind]}`}>
      {title && (
        <p className="font-semibold mb-1">
          {icons[kind]} {title}
        </p>
      )}
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

function NavPill({ href, label }: { href: string; label: string }) {
  return (
    <a
      href={href}
      className="inline-flex items-center px-3 py-1 rounded-full bg-gray-100 hover:bg-gray-200 text-gray-700 text-xs font-medium transition-colors"
    >
      {label}
    </a>
  )
}

// ── Technical doc primitives ───────────────────────────────────────────────────

function CodeBlock({ children }: { children: React.ReactNode }) {
  return (
    <pre className="bg-gray-950 text-gray-100 rounded-lg p-4 overflow-x-auto text-xs leading-relaxed font-mono">
      {children}
    </pre>
  )
}

// Colored spans for fake syntax highlighting
const K = ({ c }: { c: string }) => <span className="text-violet-400">{c}</span>       // keyword
const T = ({ c }: { c: string }) => <span className="text-teal-300">{c}</span>          // type
const S = ({ c }: { c: string }) => <span className="text-amber-300">{c}</span>         // string
const Cm = ({ c }: { c: string }) => <span className="text-gray-500">{c}</span>         // comment
const Fn = ({ c }: { c: string }) => <span className="text-sky-300">{c}</span>          // function name
const Num = ({ c }: { c: string }) => <span className="text-orange-300">{c}</span>      // number
const Kw2 = ({ c }: { c: string }) => <span className="text-pink-300">{c}</span>        // secondary keyword

function ParamTable({
  params,
}: {
  params: { name: string; type: string; required?: boolean; default?: string; desc: string }[]
}) {
  return (
    <div className="not-prose overflow-x-auto rounded-lg border border-gray-200">
      <table className="w-full text-xs">
        <thead>
          <tr className="bg-gray-50 border-b border-gray-200">
            <th className="py-2 px-3 text-left text-gray-500 font-semibold uppercase tracking-wide">Parameter</th>
            <th className="py-2 px-3 text-left text-gray-500 font-semibold uppercase tracking-wide">Type</th>
            <th className="py-2 px-3 text-left text-gray-500 font-semibold uppercase tracking-wide">Req.</th>
            <th className="py-2 px-3 text-left text-gray-500 font-semibold uppercase tracking-wide">Default</th>
            <th className="py-2 px-3 text-left text-gray-500 font-semibold uppercase tracking-wide">Description</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {params.map(p => (
            <tr key={p.name}>
              <td className="py-2 px-3 font-mono font-semibold text-gray-800">{p.name}</td>
              <td className="py-2 px-3 font-mono text-teal-700">{p.type}</td>
              <td className="py-2 px-3 text-center">{p.required !== false ? '✓' : <span className="text-gray-300">—</span>}</td>
              <td className="py-2 px-3 font-mono text-gray-400">{p.default ?? <span className="text-gray-300">—</span>}</td>
              <td className="py-2 px-3 text-gray-600 leading-relaxed">{p.desc}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function ReturnBox({ type, desc }: { type: string; desc: string }) {
  return (
    <div className="flex gap-3 items-start rounded-lg bg-gray-50 border border-gray-200 p-3 text-sm">
      <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide mt-0.5 flex-shrink-0">Returns</span>
      <div className="min-w-0">
        <code className="font-mono text-teal-700 text-xs">{type}</code>
        <p className="text-gray-600 mt-0.5 text-xs leading-relaxed">{desc}</p>
      </div>
    </div>
  )
}

function FnHeader({ name, signature }: { name: string; signature: string }) {
  return (
    <div className="rounded-t-lg bg-gray-950 px-4 py-3 flex items-center gap-3 -mb-1">
      <span className="inline-flex items-center px-2 py-0.5 rounded bg-sky-900 text-sky-300 text-xs font-mono font-semibold">fn</span>
      <span className="font-mono text-sky-300 text-sm font-semibold">{name}</span>
      <span className="font-mono text-gray-400 text-xs truncate">{signature}</span>
    </div>
  )
}

function PageLink({ to, label }: { to: string; label: string }) {
  return (
    <Link
      to={to}
      className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800 font-medium underline underline-offset-2"
    >
      {label}
    </Link>
  )
}

// ── TOC ────────────────────────────────────────────────────────────────────────

const TOC_ITEMS = [
  { id: 'overview', label: 'Overview' },
  { id: 'navigation', label: 'Navigating the App' },
  { id: 'global-controls', label: 'Global Controls' },
  { id: 'insights', label: 'Insights Page' },
  { id: 'budget-breakdown', label: 'Budget Breakdown' },
  { id: 'departments', label: 'Departments & Schools' },
  { id: 'yoy', label: 'Year-Over-Year Analysis' },
  { id: 'flow', label: 'Prop 2½ Calculator' },
  { id: 'compare', label: 'Compare Years' },
  { id: 'search', label: 'Search' },
  { id: 'drilldown', label: 'Drill-Down Pages' },
  { id: 'export', label: 'Exporting Data' },
  { id: 'sharing', label: 'Sharing & URLs' },
  { id: 'data-model', label: 'Data Model Deep Dive' },
  { id: 'api-store', label: 'API: useBudgetStore' },
  { id: 'api-parser', label: 'API: parseBudgetFile' },
  { id: 'api-transforms', label: 'API: Transforms' },
  { id: 'api-insights', label: 'API: Insights Engine' },
  { id: 'api-types', label: 'API: Type Reference' },
  { id: 'glossary', label: 'Glossary' },
]

// ── Page ───────────────────────────────────────────────────────────────────────

export function UserDocsPage() {
  const [tocOpen, setTocOpen] = useState(false)

  return (
    <div className="p-6 max-w-4xl space-y-8">
      {/* Header */}
      <div className="border-b border-gray-200 pb-6">
        <div className="flex items-center gap-2 text-xs text-gray-400 mb-3 font-mono">
          <span>INTERNAL</span>
          <span>·</span>
          <span>NOT LINKED FROM NAV</span>
          <span>·</span>
          <span>/#/user-docs</span>
        </div>
        <h1 className="text-3xl font-bold text-gray-900">Lunenburg Budget Explorer — User Documentation</h1>
        <p className="text-gray-500 mt-2 text-base leading-relaxed">
          A comprehensive reference for every feature of the Lunenburg Public Schools Budget Explorer.
          Written from a user's perspective — whether you're a parent attending Town Meeting for the
          first time, a School Committee member, or a journalist doing background research.
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          {TOC_ITEMS.map(item => (
            <NavPill key={item.id} href={`#${item.id}`} label={item.label} />
          ))}
        </div>
      </div>

      {/* Collapsible TOC for mobile */}
      <div className="lg:hidden">
        <button
          onClick={() => setTocOpen(o => !o)}
          className="flex items-center gap-2 text-sm font-medium text-gray-600 hover:text-gray-900"
        >
          <span>{tocOpen ? '▾' : '▸'}</span>
          Table of Contents
        </button>
        {tocOpen && (
          <ol className="mt-2 ml-4 space-y-1 text-sm text-blue-600">
            {TOC_ITEMS.map((item, i) => (
              <li key={item.id}>
                <a href={`#${item.id}`} className="hover:underline">
                  {i + 1}. {item.label}
                </a>
              </li>
            ))}
          </ol>
        )}
      </div>

      {/* ─ 1. Overview ─────────────────────────────────────────────────────────── */}
      <DocSection
        id="overview"
        title="1. What This Tool Is"
        subtitle="Purpose, data source, and scope"
      >
        <p>
          The <strong>Lunenburg Public Schools Budget Explorer</strong> is an interactive web app that
          turns the district's annual budget spreadsheet — a dense Excel file with hundreds of rows —
          into something navigable, searchable, and understandable.
        </p>
        <p>
          It is designed for anyone who wants to understand how Lunenburg Public Schools spends money:
          parents, taxpayers, journalists, School Committee members, town officials, and students. No
          accounting background is needed to use it, although this documentation explains the underlying
          data structures for those who want to go deeper.
        </p>

        <SubSection title="What it shows">
          <ul className="list-disc pl-5 space-y-1 text-gray-700">
            <li>
              <strong>Multiple fiscal years</strong> side by side — typically four years of actuals plus
              the current proposed budget.
            </li>
            <li>
              <strong>Every line item</strong> in the district's budget, organized by department and
              spending category.
            </li>
            <li>
              <strong>Year-over-year changes</strong> as dollar amounts and percentages, with anomaly
              detection to surface the largest shifts automatically.
            </li>
            <li>
              <strong>Prop 2½ context</strong> — how the proposed budget relates to the legal tax
              limit and whether an override vote is needed.
            </li>
          </ul>
        </SubSection>

        <SubSection title="What it does not show">
          <ul className="list-disc pl-5 space-y-1 text-gray-700">
            <li>
              <strong>Individual employee salaries.</strong> The budget shows department-level salary
              totals only. Specific salary data for public employees is available through a Massachusetts
              public records request.
            </li>
            <li>
              <strong>Revenue sources.</strong> This app shows how money is <em>spent</em>, not where
              it comes from (property taxes, Chapter 70 state aid, federal grants, etc.).
            </li>
            <li>
              <strong>Real-time data.</strong> The data reflects what was loaded at build time from the
              official budget spreadsheet. It is a snapshot, not a live feed.
            </li>
          </ul>
        </SubSection>

        <Callout kind="note" title="Data source">
          All figures come directly from the district's official budget Excel file. The app parses the
          spreadsheet at startup — no values are hardcoded or editable by the app itself. If you spot a
          number that looks wrong, the source spreadsheet is authoritative.
        </Callout>
      </DocSection>

      {/* ─ 2. Navigation ────────────────────────────────────────────────────────── */}
      <DocSection
        id="navigation"
        title="2. Navigating the App"
        subtitle="What each section of the sidebar does"
      >
        <p>
          The sidebar on the left (or the hamburger menu on mobile) lists every major section. Here's
          what each one is for:
        </p>

        <div className="not-prose space-y-4">
          {[
            {
              route: '/',
              label: 'Insights',
              icon: '💡',
              summary: 'The default landing page.',
              detail:
                'Shows auto-generated narrative summaries, anomaly flags (unexpected cost spikes or cuts), Prop 2½ context, and school-by-school impact. Good starting point for understanding the budget story without reading every line.',
            },
            {
              route: '/departments',
              label: 'Departments & Schools',
              icon: '🏫',
              summary: 'Per-department line item tables.',
              detail:
                'Breaks the budget into 18 departments organized by school building, program, and staff role. Each department has a detailed table showing every expense and salary line item with year-over-year comparison.',
            },
            {
              route: '/yoy',
              label: 'Year-Over-Year Analysis',
              icon: '📈',
              summary: 'Historical trends across all years.',
              detail:
                'Shows how the budget has changed at each fiscal-year transition. Identifies patterns such as sustained multi-year growth in a category, large one-time spikes, and share shifts (a category growing faster than the overall budget).',
            },
            {
              route: '/flow',
              label: 'Prop 2½ & Override Calculator',
              icon: '⚖️',
              summary: 'Step-by-step tax levy analysis.',
              detail:
                "Walks through Massachusetts's Prop 2½ formula to show the maximum amount the district can raise from local property taxes, how much the proposed budget exceeds (or fits within) that cap, and what an override vote would authorize.",
            },
            {
              route: '/overview',
              label: 'Budget Breakdown',
              icon: '🗺️',
              summary: 'Visual overview of the whole budget.',
              detail:
                'An interactive treemap sized by spending, a category bar chart, a trend line across years, and a summary table. Best for getting a visual sense of proportions and trends.',
            },
            {
              route: '/compare',
              label: 'Compare Years',
              icon: '↔️',
              summary: 'Line-by-line side-by-side comparison.',
              detail:
                'Shows every budget group with its value in the primary year and compare year, sortable by absolute change or percent change. Good for finding every line that moved significantly.',
            },
            {
              route: '/search',
              label: 'Search Line Items',
              icon: '🔎',
              summary: 'Full-text search across all budget rows.',
              detail:
                'Type any keyword — a department name, a description fragment, an account code — to find matching line items across expenses and salaries for all years.',
            },
            {
              route: '/guide',
              label: 'How to Read This Budget',
              icon: '📖',
              summary: 'Plain-English guide to the budget spreadsheet.',
              detail:
                'Explains account codes, the two-section structure (expenses vs. salaries), what fiscal years mean, and tips for using this explorer. Written for a first-time reader.',
            },
          ].map(item => (
            <div key={item.route} className="flex gap-4 rounded-lg border border-gray-100 p-4 hover:border-gray-200 transition-colors">
              <span className="text-2xl flex-shrink-0">{item.icon}</span>
              <div className="min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <p className="font-semibold text-gray-900">{item.label}</p>
                  <code className="text-xs text-gray-400 font-mono bg-gray-50 px-1.5 py-0.5 rounded">
                    /#/{item.route.replace('/', '') || ''}
                  </code>
                </div>
                <p className="text-gray-500 text-xs mt-0.5">{item.summary}</p>
                <p className="text-gray-700 text-sm mt-1">{item.detail}</p>
              </div>
            </div>
          ))}
        </div>

        <Callout kind="tip" title="Which page to start with?">
          <strong>First-timers:</strong> go to Insights for the narrative, then Budget Breakdown for
          visuals. <strong>School Committee members:</strong> Departments & Schools for line-item
          details, then Compare Years for a sorted list of changes. <strong>Town Meeting voters:</strong>{' '}
          Insights and the Prop 2½ Calculator.
        </Callout>
      </DocSection>

      {/* ─ 3. Global Controls ───────────────────────────────────────────────────── */}
      <DocSection
        id="global-controls"
        title="3. Global Controls"
        subtitle="The top bar and filters that apply everywhere"
      >
        <p>
          The top bar (above the main content on every page) contains controls that affect the entire
          app. These are global — changing them updates every chart, table, and number site-wide.
        </p>

        <SubSection title="Primary Year">
          <p>
            The <strong>Primary Year</strong> dropdown sets which fiscal year is treated as "current."
            Most numbers and charts display this year's values by default. It defaults to the most
            recent year in the dataset (usually the proposed budget year).
          </p>
          <Callout kind="tip">
            If you want to analyze a past year's budget, change the Primary Year to that year. All
            pages will update to show that year as the focal point.
          </Callout>
        </SubSection>

        <SubSection title="Compare Year">
          <p>
            The <strong>Compare Year</strong> dropdown sets the baseline for all percentage-change
            calculations. It defaults to the year immediately before the Primary Year. The delta
            badges (red/green percentages) always show the change from Compare Year to Primary Year.
          </p>
          <p>
            You can compare any two years — for example, set Primary to FY27 and Compare to FY24 to
            see a three-year swing.
          </p>
        </SubSection>

        <SubSection title="Section Filter (Expenses / Salaries / Both)">
          <p>
            The budget is split into two major sections. The toggle controls which section is
            displayed:
          </p>
          <div className="space-y-2">
            <Term word="Expenses">
              Non-salary operating costs: supplies, contracts, utilities, software, equipment,
              transportation, insurance, and anything else that isn't a person's compensation.
            </Term>
            <Term word="Salaries">
              All employee compensation: teachers, administrators, paraprofessionals, custodians,
              coaches, secretaries, and any other staff paid through the school budget.
            </Term>
            <Term word="Both">
              Shows totals that combine expenses and salaries, giving a complete picture of each
              department's full cost.
            </Term>
          </div>
          <Callout kind="note">
            Salaries typically represent 75–80% of the total budget. When looking at "where does
            the money go," switching to <strong>Both</strong> gives the most accurate picture.
          </Callout>
        </SubSection>

        <SubSection title="Category Filter">
          <p>
            The category filter limits the view to specific spending categories. The seven categories
            are determined by the first digit of each account code:
          </p>
          <div className="not-prose overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 text-left">
                  <th className="py-2 pr-4 text-xs text-gray-400 font-semibold uppercase tracking-wide">Code</th>
                  <th className="py-2 pr-4 text-xs text-gray-400 font-semibold uppercase tracking-wide">Category</th>
                  <th className="py-2 text-xs text-gray-400 font-semibold uppercase tracking-wide">Typical items</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {[
                  ['1', 'Administration', 'School Committee, superintendent office, finance, HR, legal'],
                  ['2', 'Instructional', 'Classroom teachers, curriculum, library, academic departments'],
                  ['3', 'Student Services', 'Guidance, health, special education, attendance, psychology'],
                  ['4', 'Facilities', 'Custodians, maintenance, utilities, grounds, building costs'],
                  ['5', 'Fixed Costs', 'Retirement assessments, insurance, debt service, benefits'],
                  ['7', 'Capital', 'Equipment and large one-time purchases above a dollar threshold'],
                  ['9', 'Tuitions', 'Out-of-district placements, vocational school assessments'],
                ].map(([code, cat, items]) => (
                  <tr key={code}>
                    <td className="py-2 pr-4 font-mono font-bold text-gray-800">{code}</td>
                    <td className="py-2 pr-4 font-semibold text-gray-800">{cat}</td>
                    <td className="py-2 text-gray-500">{items}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-2">
            When multiple categories are selected, the app shows data for all of them. Deselecting
            all categories resets to showing everything (same as selecting all).
          </p>
        </SubSection>

        <Callout kind="info" title="Filters are global and URL-encoded">
          All filter state (primary year, compare year, section, categories) is encoded in the URL.
          This means you can bookmark or share a link and the recipient will see the exact same
          filters you had set. See <a href="#sharing" className="underline">Sharing & URLs</a> for details.
        </Callout>
      </DocSection>

      {/* ─ 4. Insights ──────────────────────────────────────────────────────────── */}
      <DocSection
        id="insights"
        title="4. Insights Page"
        subtitle="Auto-generated budget analysis and narrative"
      >
        <p>
          The Insights page (<PageLink to="/" label="/" />) is the default landing page and the best
          place to start if you want a plain-English summary of the budget. It is generated
          automatically by analyzing the data — no human writes these summaries.
        </p>

        <SubSection title="Budget Story">
          <p>
            The top section generates one or two paragraphs contextualizing the proposed budget. It
            typically covers:
          </p>
          <ul className="list-disc pl-5 space-y-1">
            <li>Total proposed spending and the year-over-year change</li>
            <li>Whether the budget requires an override vote under Prop 2½</li>
            <li>The dominant cost driver (usually salaries)</li>
            <li>Any historically unusual patterns in the data</li>
          </ul>
        </SubSection>

        <SubSection title="Prop 2½ Banner">
          <p>
            If the proposed budget exceeds the Prop 2½ tax levy limit, a prominent banner explains
            the gap and whether an override vote is needed. Clicking it takes you to the full{' '}
            <PageLink to="/flow" label="Prop 2½ Calculator" />.
          </p>
        </SubSection>

        <SubSection title="Anomalies">
          <p>
            The anomaly engine scans every line item and flags these types of changes automatically:
          </p>
          <div className="space-y-3">
            <Term word="New line item">
              A budget line that exists in the primary year but had no funding in the compare year.
              Indicates a genuinely new program, position, or expense.
            </Term>
            <Term word="Eliminated line item">
              A budget line that was funded in the compare year but has $0 or is absent in the
              primary year. May mean a program was cut or a position was eliminated.
            </Term>
            <Term word="Spike">
              A line item that grew by more than 50% <em>and</em> added more than $15,000. Filters
              out small-dollar noise — a line going from $100 to $200 is not flagged even though
              it's a 100% increase.
            </Term>
            <Term word="Sharp cut">
              A line item that fell by more than 40% <em>and</em> lost more than $10,000.
              Significant reductions that may indicate service changes.
            </Term>
          </div>
          <p>
            Each anomaly is rated <strong>high</strong>, <strong>medium</strong>, or{' '}
            <strong>low</strong> severity based on dollar magnitude and percentage change. Click any
            anomaly to navigate to the relevant line item or drill-down page.
          </p>
        </SubSection>

        <SubSection title="Patterns">
          <p>
            Beyond single-year anomalies, the pattern engine looks across all available fiscal years:
          </p>
          <div className="space-y-2">
            <Term word="Sustained growth">
              A category or department that has grown in every fiscal-year transition shown in the
              data. Signals a structural upward trend, not a one-time bump.
            </Term>
            <Term word="Sustained cuts">
              A category that has fallen in every transition — a structural decline.
            </Term>
            <Term word="Budget share shift">
              A category whose share of the total budget has grown or shrunk significantly over
              time, even if its absolute dollars went up (because everything goes up with inflation).
            </Term>
            <Term word="Restoration">
              A line item that was cut in a prior year and then restored to near its original level.
              Often seen after one-time budget pressures resolve.
            </Term>
          </div>
        </SubSection>

        <SubSection title="School Impact">
          <p>
            A per-building breakdown showing how the budget change (Primary vs. Compare year) breaks
            out across the four school buildings: Primary School, Elementary School, Middle School,
            and High School. Includes the top specific increases and decreases for each building.
          </p>
        </SubSection>

        <Callout kind="warn" title="Automated analysis has limits">
          The Insights page is generated by algorithms, not by humans with contextual knowledge.
          A "spike" might reflect a planned capital purchase, not an error. An "eliminated" line
          might have been merged into another account code. Always verify anomalies against the
          district's budget narrative documents.
        </Callout>
      </DocSection>

      {/* ─ 5. Budget Breakdown ──────────────────────────────────────────────────── */}
      <DocSection
        id="budget-breakdown"
        title="5. Budget Breakdown"
        subtitle="Charts and tables for the full district view"
      >
        <p>
          The Budget Breakdown page (<PageLink to="/overview" label="/overview" />) shows the
          entire budget visually. It has four components:
        </p>

        <SubSection title="Spending Map (Treemap)">
          <p>
            A rectangular treemap where each tile represents a budget group (department/program). Tile
            size is proportional to dollar amount — bigger tile = more money.
          </p>
          <p>Tiles are color-coded by spending category (the seven codes from the category filter).</p>
          <ul className="list-disc pl-5 space-y-1">
            <li>
              <strong>Hover</strong> a tile to see the department name, total, and percent of budget.
            </li>
            <li>
              <strong>Click</strong> a tile to navigate to that department's drill-down page.
            </li>
          </ul>
          <Callout kind="tip">
            The treemap responds to the global Section filter. Switch to "Salaries only" to see how
            staff costs are distributed, or "Expenses only" to see operating costs.
          </Callout>
        </SubSection>

        <SubSection title="Category Bar Chart">
          <p>
            A horizontal bar chart showing total spending per category for the Primary Year. Bars are
            sorted by value (largest on top). Each bar shows the dollar total and — on hover — the
            compare-year value and change.
          </p>
        </SubSection>

        <SubSection title="Budget Trend Line">
          <p>
            A line chart showing the district's total budget across all fiscal years in the dataset.
            The proposed year is visually distinguished from actuals (typically shown with a dashed
            line or different marker).
          </p>
          <p>
            This gives you a quick sense of the budget's growth trajectory over the available history.
          </p>
        </SubSection>

        <SubSection title="Summary Table">
          <p>
            A table listing every budget group with columns for each fiscal year. You can:
          </p>
          <ul className="list-disc pl-5 space-y-1">
            <li>Click a row to go to that group's drill-down detail page.</li>
            <li>Sort by any column header.</li>
            <li>See the delta badge (% change between Primary and Compare years) in the last column.</li>
          </ul>
        </SubSection>
      </DocSection>

      {/* ─ 6. Departments & Schools ─────────────────────────────────────────────── */}
      <DocSection
        id="departments"
        title="6. Departments & Schools"
        subtitle="Per-building and per-program budget breakdown"
      >
        <p>
          The Departments & Schools page (<PageLink to="/departments" label="/departments" />) organizes
          the budget into 18 named departments across three groups. This is the best page for understanding
          what each school or program costs.
        </p>

        <SubSection title="Department Groups">
          <div className="space-y-3">
            <div className="rounded-lg border border-gray-200 p-4">
              <p className="font-semibold text-gray-900 mb-1">Schools (4 buildings)</p>
              <p className="text-gray-600 text-sm">
                Primary School, Elementary School, Middle School, High School. These capture costs
                attributable to each building — classroom instruction, building-specific support staff,
                and operating expenses. Costs that span multiple buildings (district-wide programs)
                appear in Programs instead.
              </p>
            </div>
            <div className="rounded-lg border border-gray-200 p-4">
              <p className="font-semibold text-gray-900 mb-1">Programs (9 district-wide services)</p>
              <p className="text-gray-600 text-sm">
                Special Education, Athletics & Activities, Music & Performing Arts, Health Services,
                Transportation, Technology, Facilities & Operations, Benefits & Insurance, and
                Contracted Services. These cross building lines and are tracked as district functions.
              </p>
            </div>
            <div className="rounded-lg border border-gray-200 p-4">
              <p className="font-semibold text-gray-900 mb-1">Staff Roles (5 role types)</p>
              <p className="text-gray-600 text-sm">
                Administration, Guidance & Student Support, Classroom Teachers, Paraprofessionals,
                School Nurses, Librarians, Substitutes, Coaches & Advisors. These cut across buildings
                and programs to show how much is spent on each type of staff district-wide.
              </p>
            </div>
          </div>
        </SubSection>

        <SubSection title="Department Cards">
          <p>
            Each department appears as a card with:
          </p>
          <ul className="list-disc pl-5 space-y-1">
            <li>Total budget for the Primary Year</li>
            <li>Dollar and percent change vs. the Compare Year</li>
            <li>A line item table showing every expense and salary row in that department</li>
            <li>A CSV export button for that department's data</li>
          </ul>
          <Callout kind="note">
            The department groupings are derived by matching budget account codes and description
            keywords — they're the app's best interpretation of how line items map to departments.
            Some line items may appear in more than one department view if their descriptions are
            ambiguous. The source of truth is always the raw line item data in Compare Years or Search.
          </Callout>
        </SubSection>

        <SubSection title="District % Column">
          <p>
            Each department card table includes a "District %" column showing what fraction of the
            total district budget that line item represents. This helps identify which individual
            expenses are large in an absolute sense, even within a small department.
          </p>
        </SubSection>

        <SubSection title="Screenshot-Friendly Tables">
          <p>
            The department tables have a clean layout designed for screenshots — useful for sharing
            at public meetings or in presentations. The table caption includes the department name,
            year, and change summary.
          </p>
        </SubSection>
      </DocSection>

      {/* ─ 7. YOY Analysis ──────────────────────────────────────────────────────── */}
      <DocSection
        id="yoy"
        title="7. Year-Over-Year Analysis"
        subtitle="Historical trends and multi-year patterns"
      >
        <p>
          The YOY Analysis page (<PageLink to="/yoy" label="/yoy" />) focuses specifically on how
          the budget has evolved across all fiscal year transitions in the dataset — not just the
          most recent one.
        </p>

        <SubSection title="Transition Summary Cards">
          <p>
            For each fiscal-year transition (e.g., FY24→FY25, FY25→FY26, FY26→FY27), a summary card
            shows:
          </p>
          <ul className="list-disc pl-5 space-y-1">
            <li>Total budget change in dollars and percent</li>
            <li>Biggest category increases and decreases</li>
            <li>Number of new line items, eliminations, spikes, and cuts in that transition</li>
          </ul>
        </SubSection>

        <SubSection title="Patterns Detected">
          <p>
            The analysis engine looks at all transitions together and flags categories or departments
            that show consistent behavior:
          </p>
          <ul className="list-disc pl-5 space-y-1">
            <li>
              <strong>Consistent growth</strong>: grew in every transition, suggesting ongoing program
              expansion or structural cost increases.
            </li>
            <li>
              <strong>Consistent cuts</strong>: fell in every transition, which may reflect deliberate
              downsizing or enrollment decline.
            </li>
            <li>
              <strong>Share shifts</strong>: a category growing faster than the total budget, causing
              it to consume an increasing fraction of overall spending.
            </li>
          </ul>
        </SubSection>

        <SubSection title="Cost Drivers">
          <p>
            A ranked list of the departments or line items responsible for the most cumulative dollar
            growth across the dataset's history. This identifies structural cost pressure vs. one-time
            changes.
          </p>
        </SubSection>

        <Callout kind="info">
          The YOY page is most useful when the dataset contains at least three years of actuals (four
          or more is ideal). With only two years, there's only one transition and patterns cannot be
          detected. The app adapts gracefully — it will show as much analysis as the data supports.
        </Callout>
      </DocSection>

      {/* ─ 8. Prop 2½ ───────────────────────────────────────────────────────────── */}
      <DocSection
        id="flow"
        title="8. Prop 2½ & Override Calculator"
        subtitle="Understanding the tax levy limit and override analysis"
      >
        <p>
          The Prop 2½ Calculator (<PageLink to="/flow" label="/flow" />) walks through the statutory
          formula that limits how much Massachusetts municipalities can raise through property taxes.
          This is the single most important constraint on the school budget.
        </p>

        <SubSection title="What Prop 2½ Is">
          <p>
            Massachusetts General Laws Chapter 59, §21C (known as "Proposition 2½") limits the total
            property tax levy a town can assess each year. The key rules:
          </p>
          <ul className="list-disc pl-5 space-y-1">
            <li>
              The levy may increase by no more than 2.5% per year (the "2½ limit"), plus an allowance
              for new growth (newly built or improved taxable property).
            </li>
            <li>
              The levy may never exceed 2.5% of the total assessed value of all taxable property (the
              "levy ceiling").
            </li>
            <li>
              A town may vote to temporarily or permanently exceed the limit through an{' '}
              <strong>override</strong> (operating expenses) or <strong>exclusion</strong> (capital
              debt). Overrides require a simple majority at a special election.
            </li>
          </ul>
        </SubSection>

        <SubSection title="Step-by-Step Breakdown">
          <p>The calculator shows the following steps:</p>
          <ol className="list-decimal pl-5 space-y-2">
            <li>
              <strong>Prior Year Levy Base:</strong> What the town assessed last year from property
              taxes (school + municipal).
            </li>
            <li>
              <strong>+2.5% Automatic Increase:</strong> The statutory annual growth allowed without
              a vote.
            </li>
            <li>
              <strong>+New Growth:</strong> Additional levy capacity from new construction and
              improvements.
            </li>
            <li>
              <strong>= Levy Limit:</strong> The maximum the town can assess this year without an
              override.
            </li>
            <li>
              <strong>School Committee Request:</strong> What the School Committee has proposed.
            </li>
            <li>
              <strong>Gap / Override Amount:</strong> If the request exceeds the levy limit, this
              is the dollar amount that requires an override vote.
            </li>
          </ol>
        </SubSection>

        <SubSection title="Free Cash Adjustments">
          <p>
            If the district is using "free cash" (unspent prior-year funds) to offset the budget,
            this appears as a one-time credit. Free cash reduces the amount that needs to be raised
            from taxes but is not a recurring source of funds — it cannot be relied upon year after
            year.
          </p>
        </SubSection>

        <Callout kind="warn" title="Complexity and context">
          The Prop 2½ analysis is computed from the budget data available in the spreadsheet.
          Real-world levy calculations involve additional municipal data (assessed value, new growth
          estimates, debt exclusions) that may not be fully reflected. Treat the calculator as an
          illustration, not a certified financial statement. For official figures, refer to the Town
          Manager's budget message or the Board of Assessors.
        </Callout>
      </DocSection>

      {/* ─ 9. Compare Years ─────────────────────────────────────────────────────── */}
      <DocSection
        id="compare"
        title="9. Compare Years"
        subtitle="Side-by-side line item comparison with sorting and filtering"
      >
        <p>
          The Compare Years page (<PageLink to="/compare" label="/compare" />) is the most granular
          view of budget changes. It shows every department group side by side for the Primary and
          Compare years, with the ability to sort and filter.
        </p>

        <SubSection title="Table Columns">
          <div className="space-y-2">
            <Term word="Department / Group">
              The budget group name. Clicking navigates to the drill-down page for that group, showing
              all its individual line items.
            </Term>
            <Term word="Compare Year Value">
              Total spending by this group in the Compare year.
            </Term>
            <Term word="Primary Year Value">
              Total spending by this group in the Primary year.
            </Term>
            <Term word="Change ($)">
              Dollar difference (Primary minus Compare). Positive = increase, negative = decrease.
            </Term>
            <Term word="Change (%)">
              Percentage difference. Shown with a color-coded badge: red for increases, green for
              decreases.
            </Term>
          </div>
        </SubSection>

        <SubSection title="Sorting">
          <p>
            Click any column header to sort. The most useful sorts for budget analysis:
          </p>
          <ul className="list-disc pl-5 space-y-1">
            <li>
              <strong>Sort by Change ($) descending</strong>: Find the biggest dollar increases first.
              Good for identifying what's driving budget growth.
            </li>
            <li>
              <strong>Sort by Change (%) descending</strong>: Find the largest proportional increases.
              Good for catching small-but-fast-growing items.
            </li>
            <li>
              <strong>Sort by Primary Year descending</strong>: See the largest absolute cost centers.
            </li>
          </ul>
        </SubSection>

        <SubSection title="Filters">
          <p>
            The global Section and Category filters from the top bar apply here. You can narrow to
            just salaries in the Instructional category, for example, to see how teacher pay has
            changed across departments.
          </p>
        </SubSection>

        <SubSection title="Pagination">
          <p>
            The table shows a fixed number of rows per page. Use the page controls at the bottom
            to navigate. The current sort and filter settings are preserved across pages.
          </p>
        </SubSection>
      </DocSection>

      {/* ─ 10. Search ───────────────────────────────────────────────────────────── */}
      <DocSection
        id="search"
        title="10. Search Line Items"
        subtitle="Full-text search across all budget rows"
      >
        <p>
          The Search page (<PageLink to="/search" label="/search" />) lets you search the full text
          of every line item description and account code in the budget.
        </p>

        <SubSection title="How to search">
          <p>Type any keyword into the search box. The results update as you type. You can search for:</p>
          <ul className="list-disc pl-5 space-y-1">
            <li>A person's role: <code className="bg-gray-100 px-1 rounded font-mono">custodian</code></li>
            <li>A subject area: <code className="bg-gray-100 px-1 rounded font-mono">special education</code></li>
            <li>A vendor or contract type: <code className="bg-gray-100 px-1 rounded font-mono">tuition</code></li>
            <li>A specific account code: <code className="bg-gray-100 px-1 rounded font-mono">2305</code></li>
            <li>A partial description: <code className="bg-gray-100 px-1 rounded font-mono">tech</code> matches
              "Technology", "Technical", "Technician", etc.
            </li>
          </ul>
        </SubSection>

        <SubSection title="Search results">
          <p>
            Results show the line item description, its account code group, section (expenses vs.
            salaries), and values for all fiscal years. Clicking a result navigates to the
            individual line item detail page.
          </p>
        </SubSection>

        <SubSection title="Search scope">
          <p>
            Search covers both the Expenses and Salaries sections simultaneously. The global Section
            filter does not affect Search — you'll always see all matching items regardless of filter
            state. This makes Search useful for finding items when you're not sure which section they
            appear in.
          </p>
        </SubSection>

        <Callout kind="tip">
          The search query is also stored in the URL, so you can share a link to a specific search.
          For example, bookmark the URL after searching "transportation" to quickly revisit all
          transportation-related line items.
        </Callout>
      </DocSection>

      {/* ─ 11. Drill-Down Pages ─────────────────────────────────────────────────── */}
      <DocSection
        id="drilldown"
        title="11. Drill-Down Pages"
        subtitle="Category and line item detail views"
      >
        <p>
          Several pages throughout the app link to drill-down views for deeper inspection. There are
          two types:
        </p>

        <SubSection title="Category Drill-Down (/category/:code)">
          <p>
            Shows all line items in a given spending category (1–9). Accessible by clicking a tile in
            the Budget Breakdown treemap or a row in the Summary Table.
          </p>
          <p>
            The page shows the category's total spending across years, then lists every budget group
            within that category, and finally every individual line item. This is useful for
            understanding all the detail behind, say, "Instructional spending" or "Fixed Costs."
          </p>
        </SubSection>

        <SubSection title="Line Item Detail (/item/:id)">
          <p>
            Shows a single budget line item's history across all fiscal years. Accessible by clicking
            a row in Search results, the Compare Years table, or within a Category Drill-Down.
          </p>
          <p>The detail page shows:</p>
          <ul className="list-disc pl-5 space-y-1">
            <li>The line item's description and account code</li>
            <li>Its parent group and spending category</li>
            <li>Values for every fiscal year in the dataset</li>
            <li>A mini trend chart of its history</li>
            <li>The percent change between each consecutive pair of years</li>
          </ul>
        </SubSection>

        <Callout kind="note">
          Line item IDs in the URL are derived from the Excel row number and section. If the budget
          spreadsheet is updated and rows shift, old line-item URLs may not resolve correctly. The
          app handles this gracefully and will show an error message if an item isn't found.
        </Callout>
      </DocSection>

      {/* ─ 12. Export ───────────────────────────────────────────────────────────── */}
      <DocSection
        id="export"
        title="12. Exporting Data"
        subtitle="Downloading budget data for external analysis"
      >
        <p>
          You can export budget data to CSV or Excel format from several places in the app. Exports
          always include all fiscal years in the dataset, not just the currently selected Primary Year.
        </p>

        <SubSection title="Where to find Export buttons">
          <ul className="list-disc pl-5 space-y-1">
            <li>
              <strong>Departments & Schools</strong>: Each department card has an Export button that
              downloads just that department's line items.
            </li>
            <li>
              <strong>Compare Years</strong>: Export the full comparison table as shown (respecting
              current sort and filter).
            </li>
            <li>
              <strong>Budget Breakdown Summary Table</strong>: Export all budget group totals.
            </li>
          </ul>
        </SubSection>

        <SubSection title="Export formats">
          <div className="space-y-2">
            <Term word="CSV (.csv)">
              Comma-separated values. Opens in Excel, Google Sheets, Numbers, or any data tool.
              Best for importing into other systems or further analysis.
            </Term>
            <Term word="Excel (.xlsx)">
              Native Excel format with basic formatting. Best for sharing with people who will open
              the file in Microsoft Excel.
            </Term>
          </div>
        </SubSection>

        <SubSection title="What's included">
          <p>Exported files include:</p>
          <ul className="list-disc pl-5 space-y-1">
            <li>Account code / budget code</li>
            <li>Line item description</li>
            <li>Section (expenses or salaries)</li>
            <li>Spending category code and label</li>
            <li>Values for every fiscal year in the dataset</li>
            <li>Dollar change and percent change between Primary and Compare years</li>
          </ul>
        </SubSection>

        <Callout kind="tip">
          If you want to build a custom chart or analysis, export from Compare Years with the
          section and category filters set to show exactly what you need, then import into your
          spreadsheet tool. The exported column structure is consistent and well-suited for pivot
          tables.
        </Callout>
      </DocSection>

      {/* ─ 13. Sharing ──────────────────────────────────────────────────────────── */}
      <DocSection
        id="sharing"
        title="13. Sharing & URLs"
        subtitle="How filter state is encoded in the URL for bookmarking and sharing"
      >
        <p>
          Every filter setting you apply is automatically saved into the URL. This means you can
          share a link with a colleague or bookmark a specific view, and the exact same data will
          appear when the URL is opened.
        </p>

        <SubSection title="URL structure">
          <p>
            The app uses <strong>hash-based routing</strong> (URLs contain a <code className="bg-gray-100 px-1 rounded font-mono">#</code>
            symbol before the path). This is intentional: hash URLs work without a backend server,
            making the app hostable on simple static hosting like Netlify.
          </p>
          <p>
            The full URL structure is:
          </p>
          <div className="bg-gray-50 rounded-lg p-3 font-mono text-xs text-gray-600 overflow-x-auto">
            https://[host]/#/[page]?primary=fy27&compare=fy26&section=both&categories=1,2,3
          </div>
        </SubSection>

        <SubSection title="URL parameters">
          <div className="not-prose overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 text-left">
                  <th className="py-2 pr-4 text-xs text-gray-400 font-semibold uppercase tracking-wide">Parameter</th>
                  <th className="py-2 pr-4 text-xs text-gray-400 font-semibold uppercase tracking-wide">Values</th>
                  <th className="py-2 text-xs text-gray-400 font-semibold uppercase tracking-wide">Example</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {[
                  ['primary', 'Fiscal year key', 'primary=fy27'],
                  ['compare', 'Fiscal year key', 'compare=fy26'],
                  ['section', '"expenses", "salaries", or "both"', 'section=salaries'],
                  ['categories', 'Comma-separated category codes', 'categories=1,2,3'],
                  ['search', 'Search query string', 'search=transportation'],
                ].map(([param, vals, ex]) => (
                  <tr key={param}>
                    <td className="py-2 pr-4 font-mono text-gray-800">{param}</td>
                    <td className="py-2 pr-4 text-gray-600">{vals}</td>
                    <td className="py-2 font-mono text-xs text-gray-400">{ex}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SubSection>

        <SubSection title="How to share a specific view">
          <ol className="list-decimal pl-5 space-y-1">
            <li>Set your filters (primary year, compare year, section, categories) in the top bar.</li>
            <li>Navigate to the page you want to share.</li>
            <li>Copy the URL from your browser's address bar.</li>
            <li>Share the URL. The recipient will see the exact same filters and page.</li>
          </ol>
        </SubSection>

        <Callout kind="note">
          Because the app is a static site, shared URLs will reflect the data as it was at build time.
          If the site is updated with new budget data, old URLs will still work but will now show
          the new data with the old filter settings.
        </Callout>
      </DocSection>

      {/* ─ 14. Data Model ───────────────────────────────────────────────────────── */}
      <DocSection
        id="data-model"
        title="14. Data Model Deep Dive"
        subtitle="How the budget spreadsheet is parsed and structured"
      >
        <p>
          This section is for technical users who want to understand exactly how the app processes
          the source Excel file and represents the data internally.
        </p>

        <SubSection title="Data loading">
          <p>
            On first load, the app fetches <code className="bg-gray-100 px-1 rounded font-mono">./data/budget.xlsx</code>{' '}
            and parses it in the browser using the{' '}
            <code className="bg-gray-100 px-1 rounded font-mono">xlsx</code> library (SheetJS). No
            data is sent to a server. A supplemental{' '}
            <code className="bg-gray-100 px-1 rounded font-mono">./data/supplemental.csv</code> may
            also be loaded; it fails gracefully if absent.
          </p>
        </SubSection>

        <SubSection title="Year column discovery">
          <p>
            The parser scans the first 12 rows of the spreadsheet looking for cells that match the
            pattern <code className="bg-gray-100 px-1 rounded font-mono">{'FY\\d{2,4}'}</code> (e.g.,
            "FY25", "FY2025"). This allows the app to work with any number of fiscal years without
            hardcoding column positions. The row immediately below the year header provides the
            sub-label ("Actuals", "Proposed", etc.). The last discovered year column is marked as{' '}
            <code className="bg-gray-100 px-1 rounded font-mono">isProjected: true</code>.
          </p>
        </SubSection>

        <SubSection title="Section boundary detection">
          <p>
            The parser looks for specific markers in column A:
          </p>
          <ul className="list-disc pl-5 space-y-1 font-mono text-xs">
            <li>"DISTRICT EXPENSES" — marks the start of the expenses section</li>
            <li>"DISTRICT SALARIES" — marks the start of the salaries section</li>
            <li>"TOTAL SALARIES" — marks the end of the salaries section</li>
          </ul>
          <p>
            If these markers are absent, the parser falls back to safe defaults.
          </p>
        </SubSection>

        <SubSection title="Line item parsing rules">
          <ul className="list-disc pl-5 space-y-1">
            <li>
              <strong>Column A</strong> contains the budget code (4-digit number). If column A is
              empty for a row, that row is a detail line item under the previous group header.
            </li>
            <li>
              <strong>Column B</strong> contains the description text.
            </li>
            <li>
              <strong>Year columns</strong> contain numeric values (or null for blank cells).
            </li>
            <li>
              <strong>Merged cells</strong> are handled via a merge map — the top-left cell's value
              is propagated to all merged siblings before parsing begins.
            </li>
            <li>
              <strong>TOTAL rows</strong> and section-header rows (containing "DISTRICT" or
              "TOTAL") are skipped — they're computed summaries, not raw line items.
            </li>
          </ul>
        </SubSection>

        <SubSection title="Category code assignment">
          <p>
            The spending category is derived from the <strong>first digit</strong> of the budget
            code. Code 2305 → category 2 (Instructional). This is a Massachusetts standard for
            school accounting (DESE Chart of Accounts).
          </p>
        </SubSection>

        <SubSection title="Group aggregation">
          <p>
            After parsing, line items are aggregated into{' '}
            <code className="bg-gray-100 px-1 rounded font-mono">BudgetGroup</code> objects. Each
            group's totals are the sum of its member line items (not the header row value, which is
            redundant and excluded to avoid double-counting).
          </p>
        </SubSection>

        <SubSection title="Zustand store">
          <p>
            Parsed data is stored in a Zustand state store with the following key slices:
          </p>
          <ul className="list-disc pl-5 space-y-1 font-mono text-xs text-gray-600">
            <li>data: BudgetData | null</li>
            <li>primaryYear: FiscalYear</li>
            <li>compareYear: FiscalYear</li>
            <li>activeSection: 'expenses' | 'salaries' | 'both'</li>
            <li>activeCategories: CategoryCode[]</li>
            <li>searchQuery: string</li>
          </ul>
          <p className="mt-2">
            Filter state is bidirectionally synced to the URL via the{' '}
            <code className="bg-gray-100 px-1 rounded font-mono">useUrlState</code> hook: changes to
            the store update the URL, and on page load, the URL is read to restore store state.
          </p>
        </SubSection>

        <SubSection title="Insights engine">
          <p>
            The insights engine (<code className="bg-gray-100 px-1 rounded font-mono">data/insights.ts</code>,
            ~1,500 lines) computes all anomalies, patterns, Prop 2½ analysis, and narrative text
            client-side on every render of the Insights page. It uses{' '}
            <code className="bg-gray-100 px-1 rounded font-mono">useMemo</code> to avoid recomputing
            when the data hasn't changed.
          </p>
        </SubSection>
      </DocSection>

      {/* ─ API: useBudgetStore ───────────────────────────────────────────────────── */}
      <DocSection
        id="api-store"
        title="16. API Reference: useBudgetStore"
        subtitle="The central Zustand store — all app state lives here"
      >
        <p>
          <code className="bg-gray-100 px-1.5 py-0.5 rounded font-mono text-sm">useBudgetStore</code> is
          the single source of truth for all budget data and filter state. It is a{' '}
          <a href="https://github.com/pmndrs/zustand" className="underline text-blue-600">Zustand</a> store,
          which means any component can subscribe to it and will re-render only when the slice it uses
          changes. It is importable from anywhere in the app:
        </p>

        <FnHeader name="useBudgetStore" signature="() → BudgetStore" />
        <CodeBlock>
          <Cm c="// Import anywhere in the component tree" />{'\n'}
          <K c="import" /> {'{ useBudgetStore } '}<K c="from" /> <S c="'../store/budgetStore'" />{'\n\n'}
          <K c="function" /> <Fn c="MyComponent" />{'() {'}{'\n'}
          {'  '}<K c="const" /> {'{ data, primaryYear, setPrimaryYear } = '}<Fn c="useBudgetStore" />{'()'}{'\n'}
          {'  '}<Cm c="// data is null until the spreadsheet finishes loading" />{'\n'}
          {'  '}<K c="if" /> {'(!data) '}<K c="return" /> {'<'}<T c="LoadingSpinner" /> {'/>'}{'\n'}
          {'  '}<K c="return" /> {'<div>{formatDollar(data.grandTotals[primaryYear])}</div>'}{'\n'}
          {'}'}
        </CodeBlock>

        <SubSection title="State properties">
          <ParamTable params={[
            { name: 'data', type: 'BudgetData | null', required: true, desc: 'The fully parsed budget. null until loadData() resolves.' },
            { name: 'loading', type: 'boolean', required: true, desc: 'True while the spreadsheet is being fetched and parsed.' },
            { name: 'error', type: 'string | null', required: true, desc: 'Error message if loadData() threw. null on success.' },
            { name: 'years', type: 'YearColumn[]', required: true, desc: 'Discovered fiscal year columns, in chronological order. Derived from data.' },
            { name: 'primaryYear', type: 'FiscalYear', required: true, desc: 'The currently selected "current" year (e.g. "fy27"). Synced to URL.' },
            { name: 'compareYear', type: 'FiscalYear', required: true, desc: 'The baseline year for delta calculations. Synced to URL.' },
            { name: 'activeSection', type: "'expenses' | 'salaries' | 'both'", required: true, desc: 'Which budget section to display. Synced to URL.' },
            { name: 'activeCategories', type: 'CategoryCode[]', required: true, desc: 'Category filter. Empty array means all categories are shown.' },
            { name: 'searchQuery', type: 'string', required: true, desc: 'Full-text search string. Synced to URL.' },
          ]} />
        </SubSection>

        <SubSection title="Actions">
          <ParamTable params={[
            { name: 'loadData', type: '(url: string) => Promise<void>', required: true, desc: 'Fetches and parses the budget spreadsheet. Sets loading/error state. Called once on mount via useBudgetData hook.' },
            { name: 'setPrimaryYear', type: '(y: FiscalYear) => void', required: true, desc: 'Updates the primary year. Triggers re-render of all subscribed components.' },
            { name: 'setCompareYear', type: '(y: FiscalYear) => void', required: true, desc: 'Updates the compare year baseline.' },
            { name: 'setActiveSection', type: "(s: 'expenses' | 'salaries' | 'both') => void", required: true, desc: 'Changes the section filter globally.' },
            { name: 'toggleCategory', type: '(c: CategoryCode) => void', required: true, desc: 'Adds or removes a category from the active filter. Idempotent — toggling a category already in the list removes it.' },
            { name: 'setSearchQuery', type: '(q: string) => void', required: true, desc: 'Updates the search query string.' },
            { name: 'resetFilters', type: '() => void', required: true, desc: 'Resets primaryYear, compareYear, activeSection, activeCategories, and searchQuery to their defaults.' },
          ]} />
        </SubSection>

        <SubSection title="Selector pattern (performance optimization)">
          <p>
            Pass a selector function to <code className="bg-gray-100 px-1 rounded font-mono text-xs">useBudgetStore</code> to
            subscribe to only a slice of state. This avoids unnecessary re-renders when other parts of
            the store change:
          </p>
          <CodeBlock>
            <Cm c="// ✓ Only re-renders when primaryYear changes" />{'\n'}
            <K c="const" /> {'primaryYear = '}<Fn c="useBudgetStore" />{'(s => s.primaryYear)'}{'\n\n'}
            <Cm c="// ✓ Only re-renders when data or primaryYear changes" />{'\n'}
            <K c="const" /> {'{ data, primaryYear } = '}<Fn c="useBudgetStore" />{'(s => ({\n'}
            {'  data: s.data,\n'}
            {'  primaryYear: s.primaryYear,\n'}
            {'}))'}{'\n\n'}
            <Cm c="// ✗ Re-renders on any store change (avoid for heavy components)" />{'\n'}
            <K c="const" /> {'store = '}<Fn c="useBudgetStore" />{'()'}
          </CodeBlock>
        </SubSection>

        <Callout kind="note" title="URL synchronization">
          Filter state (<code className="font-mono text-xs">primaryYear</code>, <code className="font-mono text-xs">compareYear</code>,{' '}
          <code className="font-mono text-xs">activeSection</code>, <code className="font-mono text-xs">activeCategories</code>,{' '}
          <code className="font-mono text-xs">searchQuery</code>) is bidirectionally synced to the URL
          hash by the <code className="font-mono text-xs">useUrlState</code> hook, which is mounted
          once inside <code className="font-mono text-xs">AppShell</code>. Calling any setter
          automatically updates the URL within the same tick.
        </Callout>
      </DocSection>

      {/* ─ API: parseBudgetFile ──────────────────────────────────────────────────── */}
      <DocSection
        id="api-parser"
        title="17. API Reference: parseBudgetFile"
        subtitle="The Excel ingestion pipeline — turns a spreadsheet URL into structured data"
      >
        <p>
          The parser is the foundation of the entire app. It fetches an Excel file, locates year
          columns dynamically, identifies section boundaries, resolves merged cells, and returns a
          clean <code className="bg-gray-100 px-1 rounded font-mono text-xs">BudgetData</code> object
          ready for rendering. It runs entirely in the browser — no server-side processing.
        </p>

        <FnHeader name="parseBudgetFile" signature="(url: string) → Promise<BudgetData>" />
        <CodeBlock>
          <K c="async function" /> <Fn c="parseBudgetFile" />{'('}<Kw2 c="url" />{': '}<T c="string"  />{'): '}<T c="Promise" />{'<'}<T c="BudgetData" />{'>'}{'\n\n'}
          <Cm c="// Usage — called once in useBudgetStore.loadData()" />{'\n'}
          <K c="const" /> {'data = '}<K c="await" /> <Fn c="parseBudgetFile" />{'('}<S c="'./data/budget.xlsx'" />{')'}{'\n'}
          <Cm c="// → BudgetData with lineItems, groups, grandTotals, years, ..." />
        </CodeBlock>

        <SubSection title="Parameters">
          <ParamTable params={[
            { name: 'url', type: 'string', required: true, desc: 'URL to the .xlsx file. Relative paths work fine in a browser context (e.g. "./data/budget.xlsx"). The file is fetched with a standard HTTP GET.' },
          ]} />
        </SubSection>

        <ReturnBox
          type="Promise<BudgetData>"
          desc="Resolves with a fully structured BudgetData object. Rejects with an Error if the fetch fails or if the sheet cannot be parsed. See the Type Reference section for the full BudgetData shape."
        />

        <SubSection title="What the parser does — in order">
          <CodeBlock>
            <Cm c="Step 1 — Fetch & decode" />{'\n'}
            <Fn c="fetch" />{'(url) → ArrayBuffer → '}<Fn c="XLSX.read" />{'(buffer)  '}<Cm c="// SheetJS" />{'\n\n'}
            <Cm c="Step 2 — Year column discovery (scans first 12 rows)" />{'\n'}
            <Fn c="discoverYearColumns" />{'(rawRows)  '}<Cm c="// finds FY\\d{2,4} headers" />{'\n'}
            <Cm c="// → [{ key:'fy24', short:'FY24', label:'FY24 Actuals', col:2, isProjected:false }, ...]" />{'\n\n'}
            <Cm c="Step 3 — Section boundary detection" />{'\n'}
            <Cm c="// Looks for 'DISTRICT EXPENSES' and 'DISTRICT SALARIES' in col A" />{'\n'}
            <Cm c="// Falls back to safe row offsets if markers are absent" />{'\n\n'}
            <Cm c="Step 4 — Merge cell resolution" />{'\n'}
            <Fn c="buildMergeMap" />{'(sheet)  '}<Cm c="// propagates top-left cell value to all merged siblings" />{'\n\n'}
            <Cm c="Step 5 — Line item parsing" />{'\n'}
            <Cm c="// Iterates rows; col A = budget code, col B = description" />{'\n'}
            <Cm c="// Skips TOTAL / DISTRICT header rows" />{'\n'}
            <Cm c="// Groups assigned top-down from last seen 4-digit code" />{'\n\n'}
            <Cm c="Step 6 — Group aggregation" />{'\n'}
            <Cm c="// Sums line item values per year per group (header rows excluded)" />{'\n\n'}
            <Cm c="Step 7 — Grand total calculation & free cash scan" />{'\n'}
            <Cm c="// Scans entire sheet for 'FREE CASH' label (any column)" />{'\n\n'}
            <Cm c="Step 8 — Supplemental CSV load (optional)" />{'\n'}
            <Fn c="fetch" />{'('}<S c="'./data/supplemental.csv'" />{')'}<Cm c="  // fails gracefully if 404" />
          </CodeBlock>
        </SubSection>

        <SubSection title="Parse warnings">
          <p>
            Non-fatal issues are collected in{' '}
            <code className="bg-gray-100 px-1 rounded font-mono text-xs">BudgetData.parseWarnings</code> and
            logged to the browser console under the prefix{' '}
            <code className="bg-gray-100 px-1 rounded font-mono text-xs">[BudgetParser]</code>. Common warnings:
          </p>
          <ul className="list-disc pl-5 space-y-1 text-gray-700">
            <li>Year column discovered with no sub-label (label defaults to the short name)</li>
            <li>Supplemental CSV missing or unparseable (data loads normally without it)</li>
            <li>Row with a budget code that doesn't match a known 4-digit pattern</li>
          </ul>
        </SubSection>

        <Callout kind="warn" title="Spreadsheet structure assumptions">
          The parser makes a few structural assumptions: budget code in column A, description in
          column B, year data in columns to the right. If the district ever changes this layout,
          the <code className="font-mono text-xs">COL_BUDGET_CODE</code> and{' '}
          <code className="font-mono text-xs">COL_DESCRIPTION</code> constants at the top of{' '}
          <code className="font-mono text-xs">parser.ts</code> need updating. Year columns are
          always discovered dynamically and require no changes for new fiscal years.
        </Callout>
      </DocSection>

      {/* ─ API: Transforms ───────────────────────────────────────────────────────── */}
      <DocSection
        id="api-transforms"
        title="18. API Reference: Data Transforms"
        subtitle="Pure functions that reshape BudgetData into chart- and table-ready structures"
      >
        <p>
          All chart and table data is built by pure transformation functions in{' '}
          <code className="bg-gray-100 px-1 rounded font-mono text-xs">data/transforms.ts</code>. They
          take raw <code className="bg-gray-100 px-1 rounded font-mono text-xs">BudgetData</code> slices
          and return typed arrays ready to pass to Recharts components or table renderers. Because they
          are pure, they can be memoized cheaply with <code className="bg-gray-100 px-1 rounded font-mono text-xs">useMemo</code>.
        </p>

        {/* formatDollar */}
        <div className="space-y-2">
          <FnHeader name="formatDollar" signature="(value: number) → string" />
          <CodeBlock>
            <K c="function" /> <Fn c="formatDollar" />{'('}<Kw2 c="value" />{': '}<T c="number" />{'): '}<T c="string" />{'\n\n'}
            <Fn c="formatDollar" />(<Num c="1_234_567" />)   <Cm c="// → '$1.23M'" />{'\n'}
            <Fn c="formatDollar" />(<Num c="45_600" />)      <Cm c="// → '$45.6K'" />{'\n'}
            <Fn c="formatDollar" />(<Num c="892" />)         <Cm c="// → '$892'" />{'\n'}
            <Fn c="formatDollar" />(<Num c="-50_000" />)     <Cm c="// → '-$50.0K'  (preserves sign)" />
          </CodeBlock>
          <p className="text-sm text-gray-600">
            Scale-adaptive formatter used in all dollar displays. Thresholds: ≥$1M → millions with
            2 decimal places; ≥$1K → thousands with 1 decimal place; below $1K → whole dollars.
          </p>
        </div>

        {/* formatDollarShort */}
        <div className="space-y-2">
          <FnHeader name="formatDollarShort" signature="(value: number) → string" />
          <CodeBlock>
            <K c="function" /> <Fn c="formatDollarShort" />{'('}<Kw2 c="value" />{': '}<T c="number" />{'): '}<T c="string" />{'\n\n'}
            <Fn c="formatDollarShort" />(<Num c="1_234_567" />)  <Cm c="// → '$1.2M'  (1 decimal vs 2)" />{'\n'}
            <Fn c="formatDollarShort" />(<Num c="45_600" />)     <Cm c="// → '$46K'   (0 decimals vs 1)" />
          </CodeBlock>
          <p className="text-sm text-gray-600">
            Compact variant used in chart axis labels and badges where horizontal space is tight.
            Produces shorter strings at the cost of precision.
          </p>
        </div>

        {/* formatPct */}
        <div className="space-y-2">
          <FnHeader name="formatPct" signature="(value: number | null) → string" />
          <CodeBlock>
            <K c="function" /> <Fn c="formatPct" />{'('}<Kw2 c="value" />{': '}<T c="number" />{' | '}<T c="null" />{'): '}<T c="string" />{'\n\n'}
            <Fn c="formatPct" />(<Num c="0.125" />)   <Cm c="// → '+12.5%'" />{'\n'}
            <Fn c="formatPct" />(<Num c="-0.032" />)  <Cm c="// → '-3.2%'" />{'\n'}
            <Fn c="formatPct" />(<K c="null" />)      <Cm c="// → 'N/A'  (e.g. new item with no prior year)" />
          </CodeBlock>
          <p className="text-sm text-gray-600">
            Always includes a <code className="bg-gray-100 px-1 rounded font-mono text-xs">+</code> prefix
            for positive values. Returns <code className="bg-gray-100 px-1 rounded font-mono text-xs">'N/A'</code> for null
            (division by zero when the prior year had $0).
          </p>
        </div>

        {/* buildTreemapData */}
        <div className="space-y-2">
          <FnHeader name="buildTreemapData" signature="(groups, year, section?, activeCats?, years?) → TreemapCategory[]" />
          <CodeBlock>
            <K c="function" /> <Fn c="buildTreemapData" />{'('}{'\n'}
            {'  '}<Kw2 c="groups" />{':      '}<T c="BudgetGroup" />{'[],'}{'\n'}
            {'  '}<Kw2 c="year" />{':        '}<T c="FiscalYear" />{','}{'\n'}
            {'  '}<Kw2 c="section" />{':     '}<T c="Section" />{' | '}<S c="'both'" />{' = '}<S c="'both'" />{','}{'\n'}
            {'  '}<Kw2 c="activeCats" />{':  '}<T c="CategoryCode" />{'[] = [],'}{'\n'}
            {'  '}<Kw2 c="years" />{':       '}<T c="YearColumn" />{'[] = [],'}{'\n'}
            {'): '}<T c="TreemapCategory" />{'[]'}{'\n\n'}
            <Cm c="// Each TreemapCategory = one color group in the treemap" />{'\n'}
            <Cm c="// Each TreemapLeaf     = one budget group tile" />{'\n'}
            <Cm c="// Tiles with size ≤ 0 are excluded automatically" />{'\n'}
            <Cm c="// Result sorted by category total (largest first)" />
          </CodeBlock>
          <ReturnBox
            type="TreemapCategory[]"
            desc="Array of category nodes, each containing a children array of group leaves. Categories with no visible groups (all filtered out or zero-value) are omitted. Pass directly to a Recharts <Treemap data={...} /> prop."
          />
        </div>

        {/* buildCategoryBarData */}
        <div className="space-y-2">
          <FnHeader name="buildCategoryBarData" signature="(groups, section?, years?) → CategoryBarDatum[]" />
          <CodeBlock>
            <K c="function" /> <Fn c="buildCategoryBarData" />{'('}{'\n'}
            {'  '}<Kw2 c="groups" />{':   '}<T c="BudgetGroup" />{'[],'}{'\n'}
            {'  '}<Kw2 c="section" />{':  '}<T c="Section" />{' | '}<S c="'both'" />{' = '}<S c="'both'" />{','}{'\n'}
            {'  '}<Kw2 c="years" />{':    '}<T c="YearColumn" />{'[] = [],'}{'\n'}
            {'): '}<T c="CategoryBarDatum" />{'[]'}{'\n\n'}
            <Cm c="// CategoryBarDatum = { category, categoryCode, compare, primary, compareLabel, primaryLabel }" />{'\n'}
            <Cm c="// Result sorted by primary value (largest first)" />
          </CodeBlock>
          <p className="text-sm text-gray-600">
            Aggregates all groups by their category code, summing both the primary and compare year
            totals. Intended for the horizontal bar chart on the Budget Breakdown page.
          </p>
        </div>

        {/* buildTrendData */}
        <div className="space-y-2">
          <FnHeader name="buildTrendData" signature="(source, years?) → TrendDatum[]" />
          <CodeBlock>
            <K c="function" /> <Fn c="buildTrendData" />{'('}{'\n'}
            {'  '}<Kw2 c="source" />{': '}<T c="BudgetGroup" />{' | '}{`{ totals: `}<T c="Record" />{`<`}<T c="FiscalYear" />{', '}<T c="number" />{`> }`}{' | '}<K c="null" />{','}{'\n'}
            {'  '}<Kw2 c="years" />{':  '}<T c="YearColumn" />{'[] = [],'}{'\n'}
            {'): '}<T c="TrendDatum" />{'[]'}{'\n\n'}
            <Cm c="// TrendDatum = { year: 'FY27', fy: 'fy27', value: number, isProjected: boolean }" />{'\n\n'}
            <Cm c="// Pass grandTotals to chart the entire district:" />{'\n'}
            <Fn c="buildTrendData" />{'({ totals: data.grandTotals }, data.years)'}{'\n\n'}
            <Cm c="// Or a specific group:" />{'\n'}
            <Fn c="buildTrendData" />{"(data.groups.find(g => g.code === "}<S c="'2305'" />{")', data.years)"}
          </CodeBlock>
          <ReturnBox
            type="TrendDatum[]"
            desc="One entry per fiscal year. isProjected: true on the last entry (proposed budget year). The Recharts LineChart component can use isProjected to visually distinguish actuals from estimates."
          />
        </div>

        {/* buildComparisonData */}
        <div className="space-y-2">
          <FnHeader name="buildComparisonData" signature="(groups, yearA, yearB, section?) → ComparisonRow[]" />
          <CodeBlock>
            <K c="function" /> <Fn c="buildComparisonData" />{'('}{'\n'}
            {'  '}<Kw2 c="groups" />{':   '}<T c="BudgetGroup" />{'[],'}{'\n'}
            {'  '}<Kw2 c="yearA" />{':    '}<T c="FiscalYear" />{',  '}<Cm c="// compare (baseline)" />{'\n'}
            {'  '}<Kw2 c="yearB" />{':    '}<T c="FiscalYear" />{',  '}<Cm c="// primary (current)" />{'\n'}
            {'  '}<Kw2 c="section" />{':  '}<T c="Section" />{' | '}<S c="'both'" />{' = '}<S c="'both'" />{','}{'\n'}
            {'): '}<T c="ComparisonRow" />{'[]'}{'\n\n'}
            <Cm c="// ComparisonRow = { code, label, categoryLabel, section, yearA, yearB, delta, pctChange }" />{'\n'}
            <Cm c="// pctChange = null when yearA === 0 (division guard)" />{'\n'}
            <Cm c="// Result sorted by |delta| descending (largest absolute change first)" />
          </CodeBlock>
          <p className="text-sm text-gray-600">
            Group-level comparison. Powers the Compare Years page table. Note parameter order:
            <code className="bg-gray-100 px-1 rounded font-mono text-xs ml-1">yearA</code> is the baseline
            (compare year) and <code className="bg-gray-100 px-1 rounded font-mono text-xs">yearB</code> is
            the target (primary year). Delta = <code className="bg-gray-100 px-1 rounded font-mono text-xs">yearB − yearA</code>.
          </p>
        </div>

        {/* buildLineItemComparisonData */}
        <div className="space-y-2">
          <FnHeader name="buildLineItemComparisonData" signature="(items, yearA, yearB, section?, activeCats?) → LineItemComparisonRow[]" />
          <CodeBlock>
            <K c="function" /> <Fn c="buildLineItemComparisonData" />{'('}{'\n'}
            {'  '}<Kw2 c="items" />{':       '}<T c="LineItem" />{'[],'}{'\n'}
            {'  '}<Kw2 c="yearA" />{':       '}<T c="FiscalYear" />{','}{'\n'}
            {'  '}<Kw2 c="yearB" />{':       '}<T c="FiscalYear" />{','}{'\n'}
            {'  '}<Kw2 c="section" />{':     '}<T c="Section" />{' | '}<S c="'both'" />{' = '}<S c="'both'" />{','}{'\n'}
            {'  '}<Kw2 c="activeCats" />{':  '}<T c="CategoryCode" />{'[] = [],'}{'\n'}
            {'): '}<T c="LineItemComparisonRow" />{'[]'}{'\n\n'}
            <Cm c="// Excludes isGroupHeader rows and section === 'summary' rows" />{'\n'}
            <Cm c="// yearA/yearB values can be null (new or eliminated items)" />{'\n'}
            <Cm c="// delta treats null as 0: new item → delta = yearB, eliminated → delta = -yearA" />
          </CodeBlock>
          <ReturnBox
            type="LineItemComparisonRow[]"
            desc="Line-item-level comparison, sorted by absolute delta. Finer-grained than buildComparisonData (which operates on groups). Use this to find specific budget lines that changed, rather than department-level totals."
          />
        </div>

        {/* searchLineItems */}
        <div className="space-y-2">
          <FnHeader name="searchLineItems" signature="(items, query, section?, activeCats?) → LineItem[]" />
          <CodeBlock>
            <K c="function" /> <Fn c="searchLineItems" />{'('}{'\n'}
            {'  '}<Kw2 c="items" />{':       '}<T c="LineItem" />{'[],'}{'\n'}
            {'  '}<Kw2 c="query" />{':       '}<T c="string" />{','}{'\n'}
            {'  '}<Kw2 c="section" />{':     '}<T c="Section" />{' | '}<S c="'both'" />{' = '}<S c="'both'" />{','}{'\n'}
            {'  '}<Kw2 c="activeCats" />{':  '}<T c="CategoryCode" />{'[] = [],'}{'\n'}
            {'): '}<T c="LineItem" />{'[]'}{'\n\n'}
            <Cm c="// Match logic: case-insensitive substring on description OR budgetCode" />{'\n'}
            <Cm c="// Empty query returns all items (after section/category filtering)" />{'\n'}
            <Cm c="// Section 'summary' rows are always excluded" />{'\n\n'}
            <Fn c="searchLineItems" />{'(data.lineItems, '}<S c="'custodian'" />{', '}<S c="'salaries'" />{')'}
            <Cm c="  // → all salary lines mentioning 'custodian'" />
          </CodeBlock>
        </div>
      </DocSection>

      {/* ─ API: Insights Engine ──────────────────────────────────────────────────── */}
      <DocSection
        id="api-insights"
        title="19. API Reference: Insights Engine"
        subtitle="Automated narrative generation and anomaly detection"
      >
        <p>
          The insights engine is the largest module in the app (~1,500 lines,{' '}
          <code className="bg-gray-100 px-1 rounded font-mono text-xs">data/insights.ts</code>).
          It exports several pure functions that compute structured analysis objects from{' '}
          <code className="bg-gray-100 px-1 rounded font-mono text-xs">BudgetData</code>. All are called
          inside <code className="bg-gray-100 px-1 rounded font-mono text-xs">useMemo</code> on the
          Insights page to avoid repeated computation.
        </p>

        {/* computeBudgetStory */}
        <div className="space-y-2">
          <FnHeader name="computeBudgetStory" signature="(data, primaryYear, compareYear) → BudgetStory" />
          <CodeBlock>
            <K c="function" /> <Fn c="computeBudgetStory" />{'('}{'\n'}
            {'  '}<Kw2 c="data" />{':         '}<T c="BudgetData" />{','}{'\n'}
            {'  '}<Kw2 c="primaryYear" />{':  '}<T c="FiscalYear" />{','}{'\n'}
            {'  '}<Kw2 c="compareYear" />{':  '}<T c="FiscalYear" />{','}{'\n'}
            {'): '}<T c="BudgetStory" />{'\n\n'}
            <Cm c="// BudgetStory = {" />{'\n'}
            <Cm c="//   paragraphs:    string[]   // ready-to-render narrative text" />{'\n'}
            <Cm c="//   primaryLabel:  string     // e.g. 'FY27 Proposed'" />{'\n'}
            <Cm c="//   compareLabel:  string     // e.g. 'FY26 Budget'" />{'\n'}
            <Cm c="// }" />
          </CodeBlock>
          <p className="text-sm text-gray-600">
            Generates 2–4 plain-English paragraphs summarizing the budget. The narrative includes:
            total spending and change, salary/expense split, which categories grew most, whether the
            budget exceeds Prop 2½ limits, and a comparison to the historical average growth rate.
          </p>
        </div>

        {/* Anomaly detection — thresholds callout */}
        <SubSection title="Anomaly detection thresholds">
          <p>The anomaly engine applies these specific thresholds. All are constants in the source:</p>
          <CodeBlock>
            <Cm c="// ── Spike detection ──────────────────────────────────────" />{'\n'}
            <K c="const" /> {'SPIKE_PCT_THRESHOLD  = '}<Num c="0.50" />{'   '}<Cm c="// must grow > 50%" />{'\n'}
            <K c="const" /> {'SPIKE_ABS_THRESHOLD  = '}<Num c="15_000" />{'  '}<Cm c="// AND add > $15,000" />{'\n\n'}
            <Cm c="// ── Sharp cut detection ──────────────────────────────────" />{'\n'}
            <K c="const" /> {'CUT_PCT_THRESHOLD    = '}<Num c="0.40" />{'   '}<Cm c="// must fall > 40%" />{'\n'}
            <K c="const" /> {'CUT_ABS_THRESHOLD    = '}<Num c="10_000" />{'  '}<Cm c="// AND lose > $10,000" />{'\n\n'}
            <Cm c="// ── Severity classification ──────────────────────────────" />{'\n'}
            <Cm c="// high:   |delta| > $100,000  or  |pctChange| > 1.0" />{'\n'}
            <Cm c="// medium: |delta| > $25,000   or  |pctChange| > 0.5" />{'\n'}
            <Cm c="// low:    anything above the spike/cut thresholds" />
          </CodeBlock>
          <Callout kind="note">
            The dual-threshold approach (both a percentage AND a dollar floor) prevents noise. A
            line item going from $10 to $20 is a 100% increase but not a budget anomaly. Conversely,
            a line going from $500K to $490K is only a −2% change but represents $10K — not flagged
            because the percent is below the cut threshold.
          </Callout>
        </SubSection>

        <SubSection title="Pattern detection logic">
          <CodeBlock>
            <Cm c="// Sustained growth: category grew in every transition" />{'\n'}
            <K c="const" /> {'transitions = years.map((y, i) => '}<Cm c="/* fy23→fy24, fy24→fy25, ... */" />{')'}{'\n'}
            <K c="const" /> {'isSustained = transitions.'}<Fn c="every" />{'(t => t.delta > '}<Num c="0" />{')'}{'\n\n'}
            <Cm c="// Share shift: category's share of total changed by > 1 percentage point" />{'\n'}
            <K c="const" /> {'shareA = catTotalA / grandTotalA'}{'\n'}
            <K c="const" /> {'shareB = catTotalB / grandTotalB'}{'\n'}
            <K c="const" /> {'hasShift = '}<Fn c="Math.abs" />{'(shareB - shareA) > '}<Num c="0.01" />{'  '}<Cm c="// >1pp" />
          </CodeBlock>
        </SubSection>
      </DocSection>

      {/* ─ API: Type Reference ───────────────────────────────────────────────────── */}
      <DocSection
        id="api-types"
        title="20. API Reference: Core Types"
        subtitle="TypeScript interfaces that define the shape of all budget data"
      >
        <p>
          All types live in <code className="bg-gray-100 px-1 rounded font-mono text-xs">data/types.ts</code>.
          Understanding these interfaces is the key to working with any part of the app.
        </p>

        <div className="space-y-4">
          <div className="space-y-1">
            <p className="font-semibold text-gray-900 font-mono text-sm">LineItem</p>
            <CodeBlock>
              <K c="interface" /> <T c="LineItem" />{' {'}{'\n'}
              {'  '}<Kw2 c="id" />{':              '}<T c="string" />{'         '}<Cm c="// '{section}-row-{rawRow}'" />{'\n'}
              {'  '}<Kw2 c="budgetCode" />{':      '}<T c="string" />{' | '}<K c="null" />{'  '}<Cm c="// '1110 - School Committee' or null (detail rows)" />{'\n'}
              {'  '}<Kw2 c="description" />{':     '}<T c="string" />{'         '}<Cm c="// text from col B" />{'\n'}
              {'  '}<Kw2 c="section" />{':         '}<T c="Section" />{'        '}<Cm c="// 'expenses' | 'salaries' | 'summary'" />{'\n'}
              {'  '}<Kw2 c="categoryCode" />{':    '}<T c="CategoryCode" />{' | '}<K c="null" />{'  '}<Cm c="// first digit of budgetCode" />{'\n'}
              {'  '}<Kw2 c="isGroupHeader" />{':   '}<T c="boolean" />{'        '}<Cm c="// true if this row names a department" />{'\n'}
              {'  '}<Kw2 c="parentCode" />{':      '}<T c="string" />{' | '}<K c="null" />{'  '}<Cm c="// budgetCode of the containing group" />{'\n'}
              {'  '}<Kw2 c="values" />{':          '}<T c="Record" />{'<'}<T c="FiscalYear" />{', '}<T c="number" />{' | '}<K c="null" />{'>  '}<Cm c="// one entry per year" />{'\n'}
              {'  '}<Kw2 c="pctChange" />{':       '}<T c="number" />{' | '}<K c="null" />{'  '}<Cm c="// (penultimate → final) ÷ penultimate" />{'\n'}
              {'  '}<Kw2 c="rawRow" />{':          '}<T c="number" />{'         '}<Cm c="// 0-indexed Excel row" />{'\n'}
              {'}'}
            </CodeBlock>
          </div>

          <div className="space-y-1">
            <p className="font-semibold text-gray-900 font-mono text-sm">BudgetGroup</p>
            <CodeBlock>
              <K c="interface" /> <T c="BudgetGroup" />{' {'}{'\n'}
              {'  '}<Kw2 c="code" />{':          '}<T c="string" />{'        '}<Cm c="// '2305'" />{'\n'}
              {'  '}<Kw2 c="label" />{':         '}<T c="string" />{'        '}<Cm c="// '2305 - Library Services'" />{'\n'}
              {'  '}<Kw2 c="section" />{':       '}<T c="Section" />{'       '}<Cm c="// 'expenses' | 'salaries'" />{'\n'}
              {'  '}<Kw2 c="categoryCode" />{':  '}<T c="CategoryCode" />{' | '}<K c="null" />{'\n'}
              {'  '}<Kw2 c="lineItems" />{':     '}<T c="LineItem" />{'[]'}{'\n'}
              {'  '}<Kw2 c="totals" />{':        '}<T c="Record" />{'<'}<T c="FiscalYear" />{', '}<T c="number" />{'>  '}<Cm c="// sum of member lineItems (no header row)" />{'\n'}
              {'}'}
            </CodeBlock>
          </div>

          <div className="space-y-1">
            <p className="font-semibold text-gray-900 font-mono text-sm">YearColumn</p>
            <CodeBlock>
              <K c="interface" /> <T c="YearColumn" />{' {'}{'\n'}
              {'  '}<Kw2 c="key" />{':          '}<T c="FiscalYear" />{'  '}<Cm c="// 'fy27'  (used as Record key)" />{'\n'}
              {'  '}<Kw2 c="short" />{':        '}<T c="string" />{'      '}<Cm c="// 'FY27'" />{'\n'}
              {'  '}<Kw2 c="label" />{':        '}<T c="string" />{'      '}<Cm c="// 'FY27 Proposed'" />{'\n'}
              {'  '}<Kw2 c="col" />{':          '}<T c="number" />{'      '}<Cm c="// 0-based Excel column index" />{'\n'}
              {'  '}<Kw2 c="isProjected" />{':  '}<T c="boolean" />{'     '}<Cm c="// true only for the last (proposed) year" />{'\n'}
              {'}'}
            </CodeBlock>
          </div>

          <div className="space-y-1">
            <p className="font-semibold text-gray-900 font-mono text-sm">BudgetData</p>
            <CodeBlock>
              <K c="interface" /> <T c="BudgetData" />{' {'}{'\n'}
              {'  '}<Kw2 c="lineItems" />{':      '}<T c="LineItem" />{'[]'}{'\n'}
              {'  '}<Kw2 c="groups" />{':         '}<T c="BudgetGroup" />{'[]'}{'\n'}
              {'  '}<Kw2 c="grandTotals" />{':    '}<T c="Record" />{'<'}<T c="FiscalYear" />{', '}<T c="number" />{'>   '}<Cm c="// sum across all groups & sections" />{'\n'}
              {'  '}<Kw2 c="sections" />{':       { expenses: '}<T c="LineItem" />{'[], salaries: '}<T c="LineItem" />{'[] }'}{'\n'}
              {'  '}<Kw2 c="years" />{':          '}<T c="YearColumn" />{'[]'}{'\n'}
              {'  '}<Kw2 c="freeCash" />{':       '}<T c="Partial" />{'<'}<T c="Record" />{'<'}<T c="FiscalYear" />{', '}<T c="number" />{'>>'}<Cm c="  // one-time offsets" />{'\n'}
              {'  '}<Kw2 c="supplemental" />{':   '}<T c="SupplementalRow" />{'[]'}{'\n'}
              {'  '}<Kw2 c="parseWarnings" />{':  '}<T c="string" />{'[]'}{'\n'}
              {'}'}
            </CodeBlock>
          </div>

          <div className="space-y-1">
            <p className="font-semibold text-gray-900 font-mono text-sm">Primitive types</p>
            <CodeBlock>
              <K c="type" /> <T c="FiscalYear" />{' = '}<T c="string" />{'  '}<Cm c="// opaque string, e.g. 'fy27'. Enforce via YearColumn.key." />{'\n'}
              <K c="type" /> <T c="Section" />{' = '}<S c="'expenses'" />{' | '}<S c="'salaries'" />{' | '}<S c="'summary'" />{'\n'}
              <K c="type" /> <T c="CategoryCode" />{' = '}<S c="'1'" />{' | '}<S c="'2'" />{' | '}<S c="'3'" />{' | '}<S c="'4'" />{' | '}<S c="'5'" />{' | '}<S c="'7'" />{' | '}<S c="'9'" />
            </CodeBlock>
            <Callout kind="tip">
              <code className="font-mono text-xs">FiscalYear</code> is typed as{' '}
              <code className="font-mono text-xs">string</code> rather than a union because the
              year values are discovered at runtime from the spreadsheet — they can't be enumerated
              at compile time. Always source year keys from{' '}
              <code className="font-mono text-xs">data.years.map(y =&gt; y.key)</code> rather than
              hardcoding <code className="font-mono text-xs">'fy27'</code>.
            </Callout>
          </div>
        </div>
      </DocSection>

      {/* ─ 21. Glossary ─────────────────────────────────────────────────────────── */}
      <DocSection
        id="glossary"
        title="21. Glossary"
        subtitle="Key terms used throughout the app and documentation"
      >
        <div className="space-y-3">
          <Term word="Account Code">
            A 4-digit number identifying a specific budget group (e.g., 2305 = Library Services).
            The first digit is the spending category; the remaining three digits identify the
            department or program.
          </Term>
          <Term word="Actuals">
            The final, audited spending for a completed fiscal year. The books are closed; this
            number will not change.
          </Term>
          <Term word="Budget Group">
            A named collection of line items under the same account code prefix (e.g., all lines
            under "2305 – Library Services").
          </Term>
          <Term word="Chapter 70">
            Massachusetts state education aid formula. Funds flow from the state to cities and towns
            based on enrollment, local income, and assessed property values.
          </Term>
          <Term word="Compare Year">
            The baseline fiscal year used for calculating percentage changes. Set in the top bar.
            Defaults to the year before the Primary Year.
          </Term>
          <Term word="Delta Badge">
            The red or green percentage shown next to values throughout the app. Red = increase
            (costs went up); green = decrease (costs went down). Note: from a taxpayer perspective,
            red means spending more; from a school perspective, green may mean a cut to programs.
          </Term>
          <Term word="DESE">
            Massachusetts Department of Elementary and Secondary Education. Sets accounting
            standards for Massachusetts public school budgets, including the account code system
            used here.
          </Term>
          <Term word="District Expenses">
            The non-salary section of the budget. Everything that isn't a person's compensation.
          </Term>
          <Term word="District Salaries">
            The salary section of the budget. All employee compensation.
          </Term>
          <Term word="Fiscal Year (FY)">
            Massachusetts school budgets run July 1 through June 30. FY27 = July 1, 2026 through
            June 30, 2027. The September 2026 school year is funded by the FY27 budget.
          </Term>
          <Term word="Free Cash">
            Unspent and uncollected funds from a prior fiscal year, certified by the state. Can be
            used as a one-time budget offset but is not a recurring revenue source.
          </Term>
          <Term word="Grand Total">
            The sum of all line items across all budget groups and both sections (expenses +
            salaries). This is the total proposed or actual district budget.
          </Term>
          <Term word="Group Header">
            The bold row in a budget table that names the department or program (e.g., "2305 –
            Library Services"). Its dollar value in the spreadsheet equals the sum of the
            detail rows below it; the app sums the detail rows independently.
          </Term>
          <Term word="Line Item">
            A single row in the budget spreadsheet, representing one type of expense or one
            salary category within a department.
          </Term>
          <Term word="Override">
            A voter-approved authorization for a municipality to permanently exceed the Prop 2½
            annual levy limit. Requires a simple majority at a special election.
          </Term>
          <Term word="Primary Year">
            The focal fiscal year for most charts and tables. Set in the top bar. Defaults to the
            most recent year (usually the proposed budget).
          </Term>
          <Term word="Proposed Budget">
            The amount the School Committee is requesting for the upcoming fiscal year. This number
            is subject to change through Town Meeting and collective bargaining.
          </Term>
          <Term word="Prop 2½">
            Shorthand for Massachusetts Proposition 2½ (M.G.L. Ch. 59, §21C). A voter-approved
            1980 ballot initiative that limits annual property tax increases to 2.5% of the prior
            levy (plus new growth), and caps total taxes at 2.5% of assessed value.
          </Term>
          <Term word="Spending Category">
            One of seven broad groupings defined by the first digit of the account code:
            Administration (1), Instructional (2), Student Services (3), Facilities (4),
            Fixed Costs (5), Capital (7), Tuitions (9).
          </Term>
          <Term word="Supplemental Data">
            Optional additional data loaded from supplemental.csv. May include notes, custom
            department mappings, or corrections. The app works normally if this file is absent.
          </Term>
          <Term word="Town Meeting">
            The annual legislative meeting of Lunenburg voters where the town budget, including the
            school assessment, is voted on. The school budget does not take effect until Town Meeting
            approves the overall town budget.
          </Term>
          <Term word="Treemap">
            A chart type where rectangles are sized proportionally to the values they represent.
            Used in the Budget Breakdown page to show spending distribution at a glance.
          </Term>
        </div>
      </DocSection>

      {/* Footer */}
      <div className="border-t border-gray-200 pt-6 text-xs text-gray-400 space-y-1">
        <p>
          This documentation page is not linked from the main navigation. Access it at{' '}
          <code className="bg-gray-100 px-1 rounded font-mono">/#/user-docs</code>.
        </p>
        <p>
          Documentation written by Claude Code based on analysis of the source code and data model.
          If anything is inaccurate, the source of truth is the codebase itself.
        </p>
      </div>
    </div>
  )
}
