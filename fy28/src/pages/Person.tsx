import { useEffect, useState } from 'react'
import { ReportShell, Body, H2, Stat } from '../components/report'

/* ONE PAGE PER NAME, at /people/<slug>. Payload: scripts/build_people.py.
 *
 * TJ, 26 October 2026: *"when i search for PEOPLE in the search bar, and i click on them,
 * it just brings me to the org chart. i am expecting each person gets their own page"* --
 * what they held, when the rosters print them, their votes, the documents naming them,
 * contact if the publisher prints it, and the chart they sit in.
 *
 * EVERY FIGURE HERE IS A COUNT OF PRINTINGS, NOT OF EVENTS. A roster is a snapshot,
 * undated within its year. "First printed" is not a start date, "not printed" is not a
 * departure, and the page never says either (rule 7).
 *
 * EMPLOYEE PAGES CARRY NOINDEX and are not in the sitemap (TJ, 26 October 2026). The
 * payload's `indexed` decides: true only for a name that holds or held a public office. */

type Year = { fy: string; url: string | null; label: string; section: string }
type Position = { unit: string; subunit: string; role: string; unit_kind: string; years: Year[] }
type Service = {
  unit: string; unit_kind: string; published: string[]; printed: string[]
  first: string; last: string; not_printed_inside: string[]; rosters_inside: number
  before_archive: boolean; on_latest: boolean; chart_url: string
  /** Years this body prints a possibly-same name instead: { fy: name }. */
  printed_as_other: Record<string, string>
}
type Seat = { fy: string; post: string; kind: string; section: string; term_expires: string; note: string; url: string | null }
type Chair = { fy: string; body: string; title: string; url: string | null }
type Vote = {
  date: string; board: string; board_slug: string; role: 'moved' | 'seconded'
  as_printed: string; motion: string; outcome: string; procedural: boolean; url: string | null
}
/** A printed form that is not a page's own address. */
type Alias = { printed: string; alias_of?: string; name?: string; not_a_person?: boolean; chart_url?: string }
type SitRow = { person: string; role: string; tier: string; status: string; slug: string; me: boolean }
type Page = {
  slug: string; name: string; spellings: string[]; indexed: boolean; kinds: string[]
  latest: { fy: string; role: string; unit: string; subunit: string; unit_kind: string; directory: boolean }
  contact: { email: string; title: string; school: string; fetched: string; publisher: string; source_url: string } | null
  positions: Position[]
  service: Service[]
  seats: Seat[]
  chairs: Chair[]
  votes: null | {
    moved: number; seconded: number; meetings: number; as_printed: string[]
    by_board: { board: string; board_slug: string; moved: number; seconded: number; meetings: number; first: string; last: string }[]
    recent: Vote[]
  }
  named: { count: number; corpus: number; first: string | null; last: string | null
    recent: { board: string; board_slug: string; date: string; kind: string; url: string }[] }
  sits: { unit: string; subunit: string; fy: string; total: number; rows: SitRow[]
    others_by_tier: Record<string, number>; chart_url: string }
  possibly_same: { slug: string; name: string }[]
}

/** /people/<slug>, or null. */
export function personSlugFromPath(pathname: string): string | null {
  const m = /^\/people\/([a-z0-9-]+)\/?$/.exec(pathname.toLowerCase())
  return m ? m[1] : null
}

/** The address of a name as printed: build_people.py's slug_for(). Keep the two identical.
 *  A printed form that is not its page's own address (`A dam Burney`, `Stevenson, Warren`)
 *  has an alias file there, which this page follows. */
export const personSlug = (name: string) =>
  name.split(/\s+/).filter(Boolean).join(' ').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '')

// FY2027 in the org charts is not a roster: it is the two staff directories, fetched in
// September 2026. Called by what it is.
const fyLabel = (fy: string) => (fy === '2027' ? 'Sept 2026 directory' : `FY${fy}`)
const fyShort = (fy: string) => (fy === '2027' ? 'Sep 26' : `’${fy.slice(2)}`)

const KIND: Record<string, string> = {
  board: 'board or committee', officer: 'appointed post', department: 'town staff', school: 'school staff',
}
const BAND: Record<string, string> = {
  '0': 'Heads the body', '1': 'Deputy and assistant', '2': 'Supervisors, ranked posts and the clerk',
  '3': 'Members, seats and staff', '4': 'Associate, honorary, ex officio and non-voting',
}

function longDate(iso: string) {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
}

/** noindex for as long as the page is mounted -- the employee pages. */
function useNoIndex(on: boolean) {
  useEffect(() => {
    if (!on) return
    const m = document.createElement('meta')
    m.name = 'robots'
    m.content = 'noindex'
    document.head.appendChild(m)
    return () => { m.remove() }
  }, [on])
}

const link = { color: 'var(--series-cost)' }
const muted = { color: 'var(--text-muted)' }
const th = 'text-left text-[11px] font-semibold uppercase tracking-wider py-2 pr-4'
const td = 'py-2 pr-4 align-top'

/** One strip per body: a cell for every roster the body published, filled where it
 *  prints the name. The shape of a career, drawn in printings rather than in dates. */
function Strip({ s }: { s: Service }) {
  const printed = new Set(s.printed)
  return (
    <div className="flex flex-wrap gap-1 mt-2" role="list" aria-label={`Rosters of ${s.unit}`}>
      {s.published.map(fy => {
        const on = printed.has(fy)
        const other = s.printed_as_other[fy]
        return (
          <div key={fy} role="listitem" className="text-center" style={{ width: 38 }}
            title={`${fyLabel(fy)}: ${on ? 'printed' : other ? `printed as ${other}` : 'not printed'}`}>
            <div style={{
              height: 18, borderRadius: 3,
              background: on ? 'var(--fund-school)' : other
                ? 'repeating-linear-gradient(135deg, var(--fund-school) 0 3px, transparent 3px 6px)' : 'transparent',
              border: on || other ? 'none' : '1px dashed var(--grid)',
            }} />
            <div className="text-[10.5px] mt-0.5 tnum" style={muted}>{fyShort(fy)}</div>
          </div>
        )
      })}
    </div>
  )
}

export function Person() {
  const [slug, setSlug] = useState(() => personSlugFromPath(window.location.pathname))
  const [p, setP] = useState<Page | null>(null)
  const [stray, setStray] = useState<Alias | null>(null)
  const [err, setErr] = useState<string | null>(null)
  useEffect(() => {
    if (!slug) return
    fetch(`/data/people/${slug}.json`)
      .then(r => { if (!r.ok) throw new Error(`no page for /people/${slug}`); return r.json() })
      .then((j: Page & Alias) => {
        // Another printing of somebody's name: go to their page, and say so there.
        if (j.alias_of) {
          window.history.replaceState(null, '', `/people/${j.alias_of}`)
          setStray(j)
          setSlug(j.alias_of)
        } else if (j.not_a_person) setStray(j)
        else setP(j)
      })
      .catch(e => setErr(String(e.message || e)))
  }, [slug])
  useNoIndex(Boolean((p && !p.indexed) || stray?.not_a_person))

  if (stray?.not_a_person) {
    return (
      <ReportShell title="Not a person" noPrint>
        <Body>The org chart prints &ldquo;{stray.printed}&rdquo; where a name goes. It names no person, or holds
          several, so it has no page. <a className="underline" style={link} href={stray.chart_url}>The chart it is printed in</a>.</Body>
      </ReportShell>
    )
  }

  if (err || !slug) {
    return (
      <ReportShell title="No such person" noPrint>
        <Body>Nobody on the org charts has the address <code>{window.location.pathname}</code>.
          Search for a name at <a className="underline" style={link} href="/search?type=people">/search</a>,
          or browse the <a className="underline" style={link} href="/org-charts">org charts</a>.</Body>
      </ReportShell>
    )
  }
  if (!p) return <ReportShell title="" loading />

  const L = p.latest
  const where = L.subunit ? `${L.subunit}, ${L.unit}` : L.unit
  // ACROSS EVERY BODY THE NAME IS PRINTED IN, not only the latest: a Select Board member
  // printed from FY2020 sat on the Conservation Commission from FY2016.
  const first = p.service.reduce((m, s) => (s.first < m ? s.first : m), p.service[0].first)
  const last = p.service.reduce((m, s) => (s.last > m ? s.last : m), p.service[0].last)
  const firstIn = p.service.filter(s => s.first === first)
  const lastIn = p.service.filter(s => s.last === last)
  // The September 2026 directories are FY2027 -- the fiscal year began in July -- so the
  // span is ordinary arithmetic on fiscal years.
  const span = Number(last) - Number(first) + 1
  // Years after the latest printing that print a possibly-same spelling instead.
  const later = lastIn.flatMap(s => Object.entries(s.printed_as_other)).filter(([fy]) => fy > last).sort()
  const role = L.role ? L.role[0].toUpperCase() + L.role.slice(1) : 'Listed'

  return (
    <ReportShell title={p.name} kicker="Person" dataUrl={`/data/people/${p.slug}.json`}
      standfirst={<>{role}, {where} &mdash; as of the {L.directory
        ? 'September 2026 staff directory' : `FY${L.fy} annual town report`}.</>}
      meta={
        <div className="mt-3 text-[13.5px] leading-relaxed max-w-2xl" style={{ color: 'var(--text-secondary)' }}>
          {p.contact && (
            <p><a className="underline" style={link} href={`mailto:${p.contact.email}`}>{p.contact.email}</a>
              <span style={muted}> &middot; as printed in the <a className="underline" href={p.contact.source_url}>{p.contact.publisher}</a>, {longDate(p.contact.fetched)}</span></p>
          )}
          {p.possibly_same.length > 0 && (
            <p className="mt-1">Possibly the same person as{' '}
              {p.possibly_same.map((a, i) => <span key={a.slug}>{i ? ', ' : ''}<a className="underline" style={link} href={`/people/${a.slug}`}>{a.name}</a></span>)}
              <span style={muted}> &mdash; a name printed two ways. Nothing here proves it is one person or two.</span></p>
          )}
          {p.spellings.length > 0 && (
            <p className="mt-1" style={muted}>Printed as {p.spellings.join(' · ')}.</p>
          )}
        </div>
      }>

      <div className="flex flex-wrap gap-x-10 gap-y-5 mt-8">
        <Stat value={fyLabel(first)}>first roster to print the name &mdash; {firstIn.map(s => s.unit).join(', ')}{firstIn.some(s => s.before_archive) ? '; the earliest held, so it may go back further' : ''}</Stat>
        <Stat value={fyLabel(last)}>latest listing &mdash; {lastIn.map(s => s.unit).join(', ')}{lastIn.some(s => s.on_latest) ? ', the newest published'
          : later.length ? `; printed since as “${later[0][1]}”, up to ${fyLabel(later[later.length - 1][0])}`
          : ', which has published since without the name'}</Stat>
        <Stat value={span === 1 ? '1 year' : `${span} years`}>from the first roster that prints the name to the latest, inclusive, across {p.service.length === 1 ? 'one body' : `${p.service.length} bodies`}</Stat>
        {p.votes && <Stat value={String(p.votes.moved + p.votes.seconded)}>motions moved or seconded, at {p.votes.meetings} meetings, in the town&rsquo;s minutes</Stat>}
        {p.named.count > 0 && <Stat value={String(p.named.count)}>town documents print the full name, of {p.named.corpus.toLocaleString()} searched</Stat>}
      </div>
      <Body>A roster is a snapshot, undated within its year. The first year that prints a name is not a start date, and a year that omits it
        is not a departure &mdash; it is a year the town did not print it.</Body>

      <H2 id="where">Where they sit</H2>
      <div className="card p-4 mt-2 max-w-2xl">
        <p className="text-[13px] font-semibold">{p.sits.subunit ? `${p.sits.subunit} · ` : ''}{p.sits.unit} &middot; {fyLabel(p.sits.fy)}</p>
        {(['0', '1', '2', '3', '4'] as const).map(t => {
          const rs = p.sits.rows.filter(r => r.tier === t)
          const more = p.sits.others_by_tier[t] ?? 0
          if (!rs.length && !more) return null
          return (
            <div key={t} className="mt-3" style={{ marginLeft: Number(t) * 14 }}>
              <p className="text-[11px] font-semibold uppercase tracking-wider" style={muted}>{BAND[t]}</p>
              <ul className="mt-1 text-[14px] leading-snug">
                {rs.map((r, i) => (
                  <li key={i} className="py-0.5" style={r.me ? { fontWeight: 700 } : undefined}>
                    {r.me
                      ? <span style={{ background: 'var(--surface-2, rgba(0,0,0,.06))', padding: '1px 5px', borderRadius: 4 }}>{r.person}</span>
                      : r.slug ? <a className="underline" style={link} href={`/people/${r.slug}`}>{r.person}</a>
                      : <span style={muted}>{r.person || (r.status === 'vacant' ? 'vacant' : 'unnamed post')}</span>}
                    <span style={muted}> &mdash; {r.role || 'listed'}</span>
                  </li>
                ))}
                {more > 0 && <li className="py-0.5" style={muted}>and {more} more in this band</li>}
              </ul>
            </div>
          )
        })}
        <p className="text-[12.5px] mt-4"><a className="underline" style={link} href={p.sits.chart_url}>The whole chart, with {p.name} marked &rarr;</a></p>
      </div>

      <H2 id="service">Rosters that print the name</H2>
      {p.service.map(s => (
        <div key={s.unit} className="mt-5 max-w-3xl">
          <p className="text-[15px] font-bold">{s.unit} <span className="font-normal text-[13px]" style={muted}>&middot; {KIND[s.unit_kind] ?? s.unit_kind}</span></p>
          <Strip s={s} />
          <p className="text-[13.5px] mt-2 leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            Printed in {s.printed.length} of the {s.rosters_inside} rosters from {fyLabel(s.first)} to {fyLabel(s.last)}.
            {Object.keys(s.printed_as_other).length > 0 && <> Printed as {[...new Set(Object.values(s.printed_as_other))].map(n => `“${n}”`).join(', ')} in {Object.keys(s.printed_as_other).map(fyLabel).join(', ')} (hatched).</>}
            {s.not_printed_inside.filter(y => !s.printed_as_other[y]).length > 0 && <> Not printed in {s.not_printed_inside.filter(y => !s.printed_as_other[y]).map(fyLabel).join(', ')}.</>}
            {s.before_archive && <> {fyLabel(s.first)} is the earliest roster held for this body.</>}
            {' '}<a className="underline" style={link} href={s.chart_url}>Chart</a>
          </p>
        </div>
      ))}

      <H2 id="positions">Positions held</H2>
      <div className="overflow-x-auto max-w-4xl">
        <table className="w-full text-[13.5px]">
          <thead><tr style={{ borderBottom: '1px solid var(--grid)', ...muted }}>
            <th className={th}>Role</th><th className={th}>Where</th><th className={th}>Years printed</th></tr></thead>
          <tbody>
            {p.positions.map((x, i) => (
              <tr key={i} style={{ borderBottom: '1px solid var(--grid)' }}>
                <td className={td}>{x.role}</td>
                <td className={td}>{x.subunit ? `${x.subunit}, ` : ''}{x.unit}</td>
                <td className={td + ' tnum'}>
                  {x.years.map((y, j) => <span key={y.fy}>{j ? ', ' : ''}{y.url
                    ? <a className="underline" style={link} href={y.url} title={y.label}>{fyLabel(y.fy)}</a>
                    : <span title={y.label}>{fyLabel(y.fy)}</span>}</span>)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {p.seats.length > 0 && (<>
        <H2 id="seats">Seats and terms</H2>
        <div className="overflow-x-auto max-w-4xl">
          <table className="w-full text-[13.5px]">
            <thead><tr style={{ borderBottom: '1px solid var(--grid)', ...muted }}>
              <th className={th}>Report</th><th className={th}>Seat</th><th className={th}>Elected or appointed</th><th className={th}>Term expires</th><th className={th}>Note</th></tr></thead>
            <tbody>
              {p.seats.map((s, i) => (
                <tr key={i} style={{ borderBottom: '1px solid var(--grid)' }}>
                  <td className={td + ' tnum'}>{s.url ? <a className="underline" style={link} href={s.url}>FY{s.fy}</a> : `FY${s.fy}`}</td>
                  <td className={td}>{s.post}</td>
                  <td className={td}>{s.section || '—'}</td>
                  <td className={td + ' tnum'}>{s.term_expires || '—'}</td>
                  <td className={td}>{s.note}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </>)}

      {p.chairs.length > 0 && (<>
        <H2 id="chair">Chair and officer roles</H2>
        <ul className="mt-2 text-[14px] leading-relaxed max-w-2xl">
          {p.chairs.map((c, i) => (
            <li key={i}>{c.title}, {c.body} &mdash; {c.url ? <a className="underline" style={link} href={c.url}>FY{c.fy} report</a> : `FY${c.fy}`}</li>
          ))}
        </ul>
      </>)}

      {p.votes && (<>
        <H2 id="votes">Motions moved and seconded</H2>
        <div className="flex flex-wrap gap-3 mt-2">
          {p.votes.by_board.map(b => (
            <div key={b.board_slug} className="card p-3.5" style={{ minWidth: 220 }}>
              <a className="text-[14px] font-bold underline" style={link} href={`/boards/${b.board_slug}/votes`}>{b.board}</a>
              <p className="text-[13px] mt-1" style={{ color: 'var(--text-secondary)' }}>
                moved {b.moved}, seconded {b.seconded}, at {b.meetings} meetings</p>
              <p className="text-[12px]" style={muted}>{longDate(b.first)} &ndash; {longDate(b.last)}</p>
            </div>
          ))}
        </div>
        <div className="overflow-x-auto max-w-5xl mt-4">
          <table className="w-full text-[13.5px]">
            <thead><tr style={{ borderBottom: '1px solid var(--grid)', ...muted }}>
              <th className={th}>Date</th><th className={th}>Board</th><th className={th}></th><th className={th}>Motion</th><th className={th}>Outcome</th></tr></thead>
            <tbody>
              {p.votes.recent.map((v, i) => (
                <tr key={i} style={{ borderBottom: '1px solid var(--grid)' }}>
                  <td className={td + ' whitespace-nowrap tnum'}>{v.url ? <a className="underline" style={link} href={v.url}>{longDate(v.date)}</a> : longDate(v.date)}</td>
                  <td className={td}>{v.board}</td>
                  <td className={td}>{v.role}</td>
                  <td className={td}>{v.motion}</td>
                  <td className={td}>{v.outcome}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <Body>The minutes print a mover as {p.votes.as_printed.slice(0, 4).map(s => `“${s}”`).join(', ')}{p.votes.as_printed.length > 4 ? ' and other forms' : ''}, not as a person.
          Matching that to {p.name} is ours: the surname and first initial against the members this board&rsquo;s roster prints within a year of the meeting,
          and only where exactly one member fits. The latest {p.votes.recent.length} are listed; every vote is on the board&rsquo;s own votes page.</Body>
      </>)}

      <H2 id="named">Named in the town&rsquo;s documents</H2>
      {p.named.count > 0 ? (<>
        <Body>{p.named.count} of the {p.named.corpus.toLocaleString()} minutes, agendas and other documents the town published print &ldquo;{p.name}&rdquo; in full,
          from {longDate(p.named.first!)} to {longDate(p.named.last!)}. That is a floor: minutes mostly print &ldquo;Mr.&rdquo; or &ldquo;Ms.&rdquo; and a surname.</Body>
        <ul className="mt-3 text-[13.5px] leading-relaxed max-w-3xl">
          {p.named.recent.map((d, i) => (
            <li key={i}><a className="underline" style={link} href={d.url}>{longDate(d.date)}</a> &middot; {d.board} <span style={muted}>{d.kind}</span></li>
          ))}
        </ul>
      </>) : (
        <Body>None of the {p.named.corpus.toLocaleString()} documents the town published prints &ldquo;{p.name}&rdquo; in full. Minutes mostly print a surname, so this does not mean the name never appears.</Body>
      )}
      <p className="text-[13.5px] mt-3"><a className="underline" style={link}
        href={`/search?${new URLSearchParams({ q: `"${p.name}"` })}`}>Search everything for &ldquo;{p.name}&rdquo; &rarr;</a></p>

      <H2 id="not-shown">What this page does not show</H2>
      <ul className="list-disc pl-5 mt-2 text-[14px] leading-relaxed max-w-2xl" style={{ color: 'var(--text-secondary)' }}>
        <li>A start or end date. The town&rsquo;s rosters are annual and undated within the year.</li>
        <li>Pay, hours or which fund pays the post. Rosters print a name and a title only.</li>
        <li>That one name is one person. Two people with this name in two bodies or two decades would share this page.</li>
        <li>Why a name stops appearing. A move, a leave, a retirement and a roster that left somebody off all look the same.</li>
      </ul>
    </ReportShell>
  )
}
