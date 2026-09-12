import { useEffect, useState } from 'react'
import { abs } from '../lib/abs'
import { useReport } from '../components/report'
import { Inline } from '../lib/inline'
import { type BlogPayload } from './Blog'
import type { Area, Tab } from '../routes'
import { AREA_HOME, AREA_LABEL } from '../routes'

/** The front page: the top-level doors and nothing else.
 *
 *  For its whole life the root served the walkthrough, which made this site one corridor —
 *  the right shape when the only thing here was an argument about FY28, and the wrong shape
 *  now that the archive behind it has grown into documents, datasets and a queryable API.
 *
 *  IT SHOWS ONLY THE TOP LEVEL, and that took three attempts to get right.
 *
 *  The first version had a paragraph per door and two lines under every link. The second
 *  cut the prose but kept the links, so the page still listed eighteen destinations — a
 *  chooser with a sitemap stapled to it, which is the same failure in a smaller font. TJ:
 *  "too many buttons... ONLY show the top level subpages."
 *
 *  A chooser is a fork in a road, not a directory. Its whole job is one decision, and every
 *  extra target on the page is a decision it did not ask for. What is inside an area is the
 *  area's business — the header bar draws it the moment you are in one.
 *
 *  Two rules that are easy to break on a landing page of all places:
 *
 *   - **No figure is typed into this copy.** This is where "3,877 documents" gets written
 *     down once and quietly stops being true. (CLAUDE.md rule 2.)
 *   - **A door describes what exists.** "The money" carried a `Being built` flag while its
 *     front page said so too; it now opens on a real page that hands over five published
 *     reference documents and the list of what the records cannot answer, so the flag came
 *     off. A door may promise only what is behind it. (Rule 7: an intention is not an
 *     outcome.)
 */

/** `quiet` marks a door that is not for a resident. It is smaller and in the muted
 *  colour rather than the brand one, so the eye sorts it out of the set of three before
 *  reading it — the three above are choices about the town, and this one is plumbing. */
const DOORS: { area: Area; who: string; note?: string; quiet?: boolean
  /** A door that opens a generated FILE rather than a route.
   *
   *  NOTHING USES THIS NOW, and it is kept because the reasoning is worth having when the
   *  next area has no front page. `The database` had this set to `/reference/schema.html`,
   *  because that document — every table, with a live query box — was a better greeting
   *  than the rate register it opened before, which answers a question about athletic fees
   *  to somebody who came for a database. It was still a front page whose first click left
   *  the app, and the four other reference documents behind that door were reachable from
   *  nowhere. `pages/Database` is the route now, and the schema page is the first thing on
   *  it. */
  href?: string }[] = [
  { area: 'crisis', who: 'Why the budget keeps breaking, and what would fix it' },
  { area: 'money', who: 'Where every dollar comes from, and where the trail goes cold' },
  // Split out of `money` on 8 September at TJ's suggestion. The money door had grown
  // thirteen tabs behind it, which is a sitemap rather than an area. Named for the FORM
  // and not the subject -- it was `School analysis` for an hour, which would have made
  // the town-side reports homeless the moment one was written.
  { area: 'analyses', who: 'The reports: staffing, athletics, fees, and what each one cannot say' },
  { area: 'data', who: 'Every table, the whole file, and how to check a figure' },
  { area: 'agents', who: 'Pointing an assistant at this, or you are one',
    quiet: true },
]

export function Home({ onJump }: { onJump: (t: Tab) => void }) {
  return (
    <div className="mx-auto max-w-3xl px-5 pb-20">
      <header className="pt-10 pb-6">
        <h1 className="text-[27px] sm:text-4xl font-bold tracking-tight leading-[1.1]">
          The <span style={{ color: 'var(--brand)' }}>Lunenburg</span> Budget Project
        </h1>
        <p className="mt-2.5 text-[15px] leading-snug"
          style={{ color: 'var(--text-secondary)' }}>
          An independent tool for residents. Pick your depth.
        </p>
        {/* THE SEARCH BOX, ON THE FRONT PAGE. TJ, 11 September, on seeing /search: "We
            need to put an indicator on the home page that users can search." The
            indicator is the box itself: a text field is the one affordance on the web
            that needs no label, and a sentence saying "you can search" would be weaker
            than the thing. It is not a door -- it goes to nowhere in particular -- so it
            sits with the header, above the set, and stays narrow. */}
        <form className="mt-4 flex gap-2"
          onSubmit={e => {
            e.preventDefault()
            const q = (new FormData(e.currentTarget).get('q') as string || '').trim()
            window.location.assign('/search' + (q ? '?q=' + encodeURIComponent(q) : ''))
          }}>
          <input name="q" type="search" aria-label="Search everything this project holds"
            placeholder="Search the budgets, the minutes, the meetings…"
            className="flex-1 min-w-0 px-3 py-2 text-[15px] rounded-lg border"
            style={{ background: 'var(--surface-2)', borderColor: 'var(--grid)',
                     color: 'var(--text-primary)' }} />
          <button type="submit" className="px-3.5 py-2 text-sm font-semibold rounded-lg shrink-0"
            style={{ background: 'var(--series-cost)', color: '#fff' }}>Search</button>
        </form>
        {/* THE WEEK, one line. The doors are places to read; this is the calendar — what is
            coming and what just appeared. A resident who came for tonight's agenda should
            not have to guess which door hides it. */}
        <p className="mt-3 text-[13px]">
          <button onClick={() => onJump('thisweek')} className="underline font-semibold"
            style={{ color: 'var(--series-cost)' }}>This week in town &rarr;</button>
          <span style={{ color: 'var(--text-muted)' }}> meetings coming up, minutes and recordings just posted</span>
        </p>
      </header>

      {/* One column, always. The rows are the whole page on a phone; two columns would
          pair them off and stop the set reading as a list. The row is the hit target, not
          the words in it. The count is deliberately not written into the prose here or in
          the comment above — it was "four" until it was five, which is rule 2 arriving in
          a doc comment. */}
      {/* TWO COLUMNS AT A LAPTOP WIDTH. TJ asked for this twice — "This should be a new
          column or something on the home page that gives them another way in", "an easier
          door" — and then, seeing it as a section underneath everything: "at the bottom
          and inline is NOT going to work".
          The earlier argument against a column was that it would make the posts a PEER of
          the doors. They are a peer. A chooser assumes you already know what you want; the
          post is for the larger number of people who do not. On a phone it stacks with the
          doors first, because somebody who came back on purpose should not scroll past an
          article to reach them. */}
      <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_20rem] lg:items-start">
      <div>
      <div className="grid gap-2.5">
        {DOORS.map(d => d.href ? (
          <a key={d.area} href={abs(d.href)}
            className="card px-4 py-4 text-left w-full min-h-[64px] block
                       transition-opacity hover:opacity-90">
            <span className="text-[17px] font-bold leading-tight block">
              {AREA_LABEL[d.area]}
            </span>
            <span className="block text-[13.5px] mt-1 leading-snug"
              style={{ color: 'var(--text-muted)' }}>{d.who}</span>
          </a>
        ) : (
          <button key={d.area} onClick={() => onJump(AREA_HOME[d.area])}
            className={'card text-left w-full transition-opacity hover:opacity-90 ' +
              (d.quiet ? 'px-4 py-3 min-h-[52px] mt-1.5' : 'px-4 py-4 min-h-[64px]')}
            style={d.quiet ? { background: 'transparent' } : undefined}>
            <span className="flex items-baseline gap-2 flex-wrap">
              <span className={d.quiet
                ? 'text-[14.5px] font-bold leading-tight'
                : 'text-[17px] font-bold leading-tight'}
                style={d.quiet ? { color: 'var(--text-secondary)' } : undefined}>
                {AREA_LABEL[d.area]}
              </span>
              {d.note && (
                <span className="text-[10.5px] font-semibold uppercase tracking-wider"
                  style={{ color: 'var(--status-warning)' }}>{d.note}</span>
              )}
            </span>
            <span className={d.quiet
              ? 'block text-[12.5px] mt-0.5 leading-snug'
              : 'block text-[13.5px] mt-1 leading-snug'}
              style={{ color: 'var(--text-muted)' }}>{d.who}</span>
          </button>
        ))}
      </div>

      {/* A FIFTH THING, and deliberately not a fifth DOOR.
          This page is four choices and that took three attempts to get right — TJ:
          "too many buttons... ONLY show the top level subpages." A door is a place to
          go and read; this is an invitation to say something, which is a different act.
          So it sits under the set, smaller and quieter, where it reads as an offer
          rather than as a fifth option competing with the four. */}
      <button onClick={() => onJump('askus')}
        className="mt-5 w-full text-left px-4 py-3 min-h-[44px] rounded-lg
                   transition-opacity hover:opacity-80"
        style={{ border: '1px dashed var(--grid)', background: 'transparent' }}>
        <span className="text-[14.5px] font-bold" style={{ color: 'var(--series-cost)' }}>
          Ask us a question &rarr;
        </span>
        <span className="block text-[12.5px] mt-0.5 leading-snug"
          style={{ color: 'var(--text-muted)' }}>
          About the budget, or anything on this site. A person reads every one.
        </span>
      </button>

      {/* A SECOND WAY IN, AND IT IS NOT A FIFTH DOOR EITHER.
          The doors stay, all of them, and they stay ABOVE this. TJ: "we have to keep the
          current 'doors' we have. This should be a new column or something on the home
          page that gives them another way in" -- and "an easier door".

          THE ARGUMENT, because the docstring at the top of this file argues hard against
          adding targets and that argument still stands for the doors. A chooser assumes
          somebody already knows what they want; every door on this page is a place to go
          and read, and a reader who does not yet have a question cannot pick one. A CARD
          is the other half: it gives somebody a reason to want something. Both belong,
          and they are different acts, so they are not in the same set -- the doors are a
          decision and this is an offer.

          WHY IT IS BELOW AND NOT BESIDE. A column next to the doors would make the two
          sets peers and reinstate exactly the "too many buttons" failure the docstring
          records. Under them, behind a rule, the page is still four choices; a reader who
          knew what they wanted has already left, and a reader who did not scrolls into
          the thing that was built for them.

          AND IT IS ONE POST, NOT FORTY-EIGHT CARDS. It was three cards, chosen by a
          rule; it is now the newest PUBLISHED post, because a card is eight seconds and
          cannot convince anybody on its own -- see pages/Blog.tsx for the three lengths.
          The rule that replaced the old one is smaller and harder: nothing unpublished
          reaches the front page. */}
      </div>
      <div className="lg:sticky lg:top-4"><HomeLatest /></div>
      </div>

      {/* The "the walkthrough moved" note was here and is gone. It explained a
          change to somebody who had not seen the old page and could not have missed it,
          on the one page whose job is to be four choices. Every old address still
          resolves — `walk`, `walkthrough`, `start` and `start-here` are all aliases —
          so nobody arrives at a dead link and needs telling. */}

    </div>
  )
}

/** THE NEWEST PUBLISHED POST, and the offer that stands when there is not one yet.
 *
 *  WHAT CHANGED AND WHY. This used to draw three CARDS, chosen by a rule: the most
 *  recently changed new finding, the first myth, the first did-you-know that fitted. All
 *  three were items nobody had decided to publish, and the front page of a public tool is
 *  not where unreviewed copy belongs. So it shows the newest post that is actually up --
 *  and the payload it reads holds nothing else.
 *
 *  A PIN, BECAUSE THE NEWEST IS NOT ALWAYS THE ONE THAT MATTERS THIS WEEK. An item may
 *  carry `**Pin** — yes` in the candidates file and it takes this slot. A pin promotes a
 *  post that is already up; it does not put one up, and a pin on an unpublished item is
 *  simply not there to find.
 *
 *  AND NOTHING RATHER THAN A PLACEHOLDER. With nothing published there is no post and
 *  none is invented -- the section draws its heading and the one line under it, and that
 *  is TJ's actual request here: *"we have to keep the current 'doors' we have. This
 *  should be a new column or something on the home page that gives them another way in"*,
 *  *"an easier door"*.
 *
 *  IT RENDERS NOTHING UNTIL THE PAYLOAD ARRIVES. The front page is four doors and an
 *  offer; an error box where the offer was would be a worse front page than one without
 *  it, and there is no fallback copy to show because there is no copy here (rule 2). */
function HomeLatest() {
  const { d } = useReport<BlogPayload>('blog.json')
  // IN DEV ONLY, fall back to the drafts payload so the section can be SEEN with real
  // content before anything is published. TJ: "whats going to show on the homepage when we
  // post blogs? Id like to see how it looks". `import.meta.env.DEV` is replaced with
  // `false` in the production bundle, so this branch and the fetch inside it are
  // eliminated -- an unpublished post cannot reach a built page through here.
  // `useReport` prefixes `/data/`, so the drafts payload is fetched directly. The whole
  // branch is eliminated from the production bundle by `import.meta.env.DEV`.
  const [draft, setDraft] = useState<BlogPayload | null>(null)
  useEffect(() => {
    if (!import.meta.env.DEV) return
    let live = true
    fetch('/blog-all.json').then(r => (r.ok ? r.json() : null))
      .then(j => { if (live) setDraft(j) }).catch(() => {})
    return () => { live = false }
  }, [])
  if (!d) return null
  const live = d.posts.filter(p => p.published)
  let post = live.find(p => p.slug === d.pinned) ?? live[0] ?? null
  let preview = false
  if (!post && import.meta.env.DEV && draft?.posts?.length) {
    post = draft.posts[0]
    preview = true
  }

  // NOTHING PUBLISHED MEANS NOTHING ON THE PAGE -- not a heading over an empty space.
  // A section that announces itself and then shows nothing reads as broken, and TJ read it
  // exactly that way: "we need to cut the 'worth knowing' section on the home page. i think
  // thats stale." It was not stale; it was empty, which looks the same and is worse,
  // because it is the front page telling a stranger that something here is not working.
  if (!post) return null

  return (
    <section className="mt-10 pt-8" style={{ borderTop: '1px solid var(--grid)' }}>
      {preview ? (
        <p className="text-[11px] font-semibold uppercase tracking-widest mb-2"
          style={{ color: 'var(--status-warning)' }}>
          Local preview &mdash; nothing is published; this is draft {post.n}
        </p>
      ) : null}
      <h2 className="text-[17px] font-bold tracking-tight">Latest articles</h2>
      <p className="text-[13.5px] mt-1 leading-snug" style={{ color: 'var(--text-muted)' }}>
        One finding at a time, in about two minutes, with the report behind it.
      </p>

      {post ? (
        <a href={`/blog/${post.slug}`}
          className="card block p-5 mt-4 transition-opacity hover:opacity-90">
          <span className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <span className="text-[11px] font-semibold uppercase tracking-widest"
              style={{ color: 'var(--text-secondary)' }}>{post.label}</span>
            <span className="text-[12.5px]" style={{ color: 'var(--text-muted)' }}>
              {post.reading.minutes} min read
            </span>
            {post.vintage === null ? (
              <span className="text-[12.5px]" style={{ color: 'var(--status-bad)' }}>
                Year not established
              </span>
            ) : (
              <span className="text-[12.5px]" style={{ color: 'var(--text-muted)' }}>
                {post.vintage_span
                  ? `FY${post.vintage_span[0]}\u2013FY${post.vintage_span[1]}`
                  : `FY${post.vintage}`}
              </span>
            )}
          </span>
          <span className="block text-[19px] font-bold leading-snug mt-2">
            <Inline text={post.headline} />
          </span>
          {post.support ? (
            <span className="block text-[14px] leading-snug mt-2"
              style={{ color: 'var(--text-secondary)' }}>
              <Inline text={post.support.split('. ')[0] + '.'} />
            </span>
          ) : null}
          <span className="block text-[13.5px] font-semibold mt-3"
            style={{ color: 'var(--series-cost)' }}>Read the post &rarr;</span>
        </a>
      ) : null}

      {d.counts.published > 1 ? (
        <p className="text-[13.5px] font-semibold mt-4">
          <a className="underline" style={{ color: 'var(--series-cost)' }} href="/blog">
            All {d.counts.published} &rarr;
          </a>
        </p>
      ) : null}
    </section>
  )
}
