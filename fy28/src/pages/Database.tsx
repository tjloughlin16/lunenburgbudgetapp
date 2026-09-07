import { abs } from '../lib/abs'
import { useEffect, useState } from 'react'
import type { Tab } from '../routes'
import { LABEL } from '../routes'

/** The front door to "The database".
 *
 *  This area had no front page. Its door on the home page pointed straight at
 *  `/reference/schema.html` — a good document and a bad door, because the first click a
 *  visitor made left the app, and the four reference pages filed alongside it were
 *  reachable by nobody. The pattern here is `pages/Money.tsx`, one area over, for the same
 *  reason: five documents were already published, generated and `--check`ed, and findable
 *  only by somebody who knew the filename.
 *
 *  WHAT THIS PAGE IS FOR. The crisis pages make an argument; this area exists so a resident
 *  or a reporter can go and check a number in it without reading the argument at all. So
 *  the page is a set of addresses and the shortest honest description of each, and it makes
 *  no claim about the budget.
 *
 *  THE FRAMING IS DELIBERATELY MODEST. The CSVs are the source of truth and the database is
 *  a derived read model, rebuilt from scratch on every run — nothing is ever edited in it,
 *  because a row in a database has no address, no publisher filename and no sha256. That is
 *  notes/reference/SCHEMA.md's rule and it is the reason this page says "check any figure"
 *  rather than anything that sounds like an official record. It is our rendering of what the
 *  town published, and rule 13 says to quote the source rather than the rendering — which is
 *  why /sources is on this page and not in a footer.
 *
 *  NOT ONE FIGURE IS TYPED HERE (CLAUDE.md rule 2). Everything arrives at runtime from two
 *  generated static files — no D1 read budget is spent by opening this page:
 *
 *    /data/reference.json   written by scripts/build_reference_pages.py. The reference
 *                           documents, each with the `door` it belongs to, its `tier`, its
 *                           size, the scripts that regenerate it, and a one-line `about`.
 *                           The descriptions shown are those, not a second set written
 *                           here — a second set is a second thing to go stale.
 *    /api/schema.json       written by scripts/build_api.py from the database itself. Only
 *                           the download size is read from it, and it is the database's own
 *                           account of its own size.
 *
 *  Each of the five documents behind this door was read before this shipped.
 *
 *  A FILTER THAT MATCHES NOTHING LOOKS EXACTLY LIKE DATA THAT IS ABSENT, so an empty list
 *  says so out loud rather than rendering as a gap. */

type RefPage = {
  name: string; title: string; about: string; url: string; format: string
  door: string; tier: string; bytes: number; generators: string[]
}
type RefIndex = { about: string; caveat: string; pages: RefPage[] }

/** Only the download block is read. A table COUNT is deliberately not taken from here:
 *  `tables` and `otherTables` are two objects that partition the documented from the
 *  undocumented, and their sum is not the number the schema page prints — that page counts
 *  what is in the file. Two counts of "the tables" differing by two on adjacent pages is
 *  exactly the kind of derived figure rule 13 is about, so this page states none and links
 *  the page whose business it is. */
type Schema = { download?: { url: string; bytes: number; format: string } }

const DOOR = 'the data'

const kb = (n: number) => (n >= 1e6 ? `${(n / 1e6).toFixed(1)} MB` : `${Math.round(n / 1024)} KB`)

function H2({ children }: { children: React.ReactNode }) {
  return <h2 className="text-2xl font-bold tracking-tight mt-14 mb-3 max-w-3xl">{children}</h2>
}

function Body({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[15px] leading-relaxed max-w-2xl mt-3"
      style={{ color: 'var(--text-secondary)' }}>{children}</p>
  )
}

/** One document, as a row. The whole row is the target, and the arrow is the affordance —
 *  the same treatment as the money door, because a row that looks like a link and is not
 *  one is the defect that put the arrow there in the first place. */
function PageRow({ p }: { p: RefPage }) {
  return (
    <a href={abs(p.url)} className="card block px-4 py-4 min-h-[44px] transition-opacity hover:opacity-90">
      <span className="flex items-baseline gap-2 flex-wrap">
        <span className="text-[16px] font-bold leading-tight"
          style={{ color: 'var(--series-cost)' }}>{p.title} &rarr;</span>
        <span className="text-[10.5px] font-semibold uppercase tracking-wider tnum"
          style={{ color: 'var(--text-muted)' }}>{p.format} · {kb(p.bytes)}</span>
      </span>
      <span className="block text-[13.5px] mt-1.5 leading-snug"
        style={{ color: 'var(--text-secondary)' }}>{p.about}</span>
      <span className="block text-[11.5px] mt-2" style={{ color: 'var(--text-muted)' }}>
        {p.generators.length
          ? <>regenerated by {p.generators.map((g, i) => (
            <span key={g}>{i > 0 ? ', ' : ''}<code>{g}</code></span>))}</>
          : 'hand-written — nothing regenerates it, so nothing will tell it when the data moves'}
      </span>
    </a>
  )
}

/** The machine-readable addresses. Four, not forty: this is a door, and the full list of
 *  every endpoint is already a page of its own (`/agents`), linked at the bottom. The
 *  `note` is what the address IS; the one quantity in them is read at runtime. */
function Route({ href, name, note }: { href: string; name: string; note: React.ReactNode }) {
  return (
    <a href={abs(href)} className="card block px-4 py-3 min-h-[44px] transition-opacity hover:opacity-90">
      <code className="text-[14px] font-bold leading-tight"
        style={{ color: 'var(--series-cost)' }}>{name}</code>
      <span className="block text-[12.5px] mt-0.5 leading-snug"
        style={{ color: 'var(--text-secondary)' }}>{note}</span>
    </a>
  )
}

export function Database({ onJump }: { onJump: (t: Tab) => void }) {
  const [ref, setRef] = useState<RefIndex | null>(null)
  const [schema, setSchema] = useState<Schema | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    let live = true
    const get = (u: string) =>
      fetch(u).then(r => (r.ok ? r.json() : Promise.reject(new Error(`${u}: HTTP ${r.status}`))))
    Promise.all([get('/data/reference.json'), get('/api/schema.json')])
      .then(([r, s]) => { if (live) { setRef(r); setSchema(s) } })
      .catch(e => { if (live) setErr(String(e)) })
    return () => { live = false }
  }, [])

  const pages = (ref?.pages ?? []).filter(p => p.door === DOOR)
  const primary = pages.filter(p => p.tier === 'primary')
  const secondary = pages.filter(p => p.tier !== 'primary')

  const dbBytes = schema?.download?.bytes

  return (
    <div className="mx-auto max-w-6xl px-5 pt-14 pb-16">
      <p className="text-xs font-semibold uppercase tracking-widest mb-3"
        style={{ color: 'var(--text-muted)' }}>The database</p>
      <h1 className="text-4xl sm:text-5xl font-bold tracking-tight leading-[1.05] max-w-3xl">
        Check any figure on this site
      </h1>
      <p className="mt-5 text-lg leading-relaxed max-w-2xl"
        style={{ color: 'var(--text-secondary)' }}>
        Everything this project computes comes out of one SQLite file, and that file is
        public. You can browse it table by table, query it in the page, ask it a question
        over the web with no key and no account, or download the whole thing.
      </p>

      <Body>
        It is not an official record and it is not the town&rsquo;s system. The source of
        truth is a set of CSVs read out of documents the town, the district and the state
        published; the database is a <strong>derived read model</strong>, rebuilt from
        scratch every time, and nothing is ever edited inside it &mdash; a row in a database
        has no address, no publisher&rsquo;s filename and no sha256, and those are what make
        a figure checkable.
      </Body>
      <Body>
        So the useful claim is narrow, and it is the one this area exists for: every number
        we publish can be traced back to a document somebody else published, and you can do
        that yourself without asking us.
      </Body>

      {err && (
        <div className="card p-5 mt-10" style={{ borderLeft: '4px solid var(--status-warning)' }}>
          <p className="text-[15px] font-bold mb-1">This page&rsquo;s index did not load</p>
          <p className="text-[13.5px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            {err}. The documents themselves are still at <code>/reference/</code> and the
            database&rsquo;s own description at <code>/api/schema</code>.
          </p>
        </div>
      )}

      <H2>Start here</H2>
      <Body>{ref ? ref.caveat : 'Loading the published reference index…'}</Body>
      <div className="grid gap-2.5 mt-6">
        {primary.map(p => <PageRow key={p.name} p={p} />)}
      </div>

      {secondary.length > 0 && (
        <>
          <p className="text-[11px] font-semibold uppercase tracking-widest mt-9 mb-3"
            style={{ color: 'var(--text-muted)' }}>What can and cannot be joined</p>
          <div className="grid gap-2">
            {secondary.map(p => (
              <a key={p.name} href={abs(p.url)}
                className="card block px-4 py-3 min-h-[44px] transition-opacity
                           hover:opacity-90">
                <span className="text-[14px] font-bold leading-tight"
                  style={{ color: 'var(--series-cost)' }}>{p.title} &rarr;</span>
                <span className="block text-[12.5px] mt-0.5 leading-snug"
                  style={{ color: 'var(--text-secondary)' }}>{p.about}</span>
              </a>
            ))}
          </div>
        </>
      )}
      {ref && !pages.length && (
        <p className="text-[13.5px] mt-4" style={{ color: 'var(--status-warning)' }}>
          The reference index loaded and no page in it is filed under &ldquo;{DOOR}&rdquo;.
          That is a broken filter, not an empty shelf &mdash; see{' '}
          <code>scripts/build_reference_pages.py</code>.
        </p>
      )}

      <H2>If you would rather have the file</H2>
      <Body>
        Read-only, open to anybody, no key. The two discovery documents describe the rest,
        including the four ways to get a confident wrong answer out of this data.
      </Body>
      <div className="grid gap-2 mt-6 sm:grid-cols-2">
        <Route href={abs('/api/index')} name="/api/index"
          note="What exists, as JSON. The map a program should fetch first." />
        <Route href={abs('/api/schema')} name="/api/schema"
          note="Every table and view, what each is for, and the four ways to get a confident wrong answer." />
        <Route href={abs('/data/lunenburg.db')} name="/data/lunenburg.db"
          note={<>The whole database, SQLite{dbBytes ? ` — ${kb(dbBytes)}` : ''}. The same file
            every figure on this site comes from.</>} />
        <Route href={abs('/data/archive-manifest.csv')} name="/data/archive-manifest.csv"
          note="Every document in the archive: its address, the publisher's own filename, and a sha256." />
      </div>
      <p className="text-xs leading-relaxed mt-4" style={{ color: 'var(--text-muted)' }}>
        Every other machine-readable address is listed on{' '}
        <button onClick={() => onJump('agents')} className="underline"
          style={{ color: 'var(--text-secondary)' }}>{LABEL.agents}</button>.
      </p>

      <H2>The documents themselves</H2>
      <Body>
        This database holds <em>figures we extracted</em>. It does not hold the PDFs,
        spreadsheets and workbooks they were extracted from &mdash; those are the archive,
        and they are the thing to check when you do not believe a number, because they were
        written by the town and the district rather than by us.
      </Body>
      <div className="grid gap-2 mt-6">
        <button onClick={() => onJump('sources')}
          className="card block px-4 py-4 min-h-[44px] text-left w-full transition-opacity
                     hover:opacity-90">
          <span className="text-[16px] font-bold leading-tight"
            style={{ color: 'var(--series-cost)' }}>{LABEL.sources} &rarr;</span>
          <span className="block text-[13.5px] mt-1.5 leading-snug"
            style={{ color: 'var(--text-secondary)' }}>
            Every document behind every figure &mdash; where it came from, the filename its
            publisher gave it, our copy, and a hash of both.
          </span>
        </button>
      </div>
    </div>
  )
}
