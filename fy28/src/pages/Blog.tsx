import { useState } from 'react'
import type { Tab } from '../routes'
import { abs } from '../lib/abs'
import { blogSlugFromPath } from '../routes'
import { ReportShell, useReport, H2, Body, MoreReports } from '../components/report'
import { Inline } from '../lib/inline'

const TAB: Tab = 'blog'
const DATA = '/data/blog.json'

/** THE MIDDLE TIER, AND THE READER'S SURFACE. A card is too short to convince anybody; a
 *  report is too long to open from a Facebook post.
 *
 *  THREE LENGTHS, AND ONLY TWO OF THEM EXISTED. TJ, working it out: *"Maybe we basically
 *  treat this flow like a BLOG.... create 'blog posts' that include high level summaries
 *  of the data, specifically built to have interesting headings people care about, posted
 *  on the home page with quick links and hooks, and also posted to Facebook groups.
 *  Clicking, brings you to the 'blog' with details, but still not the full content. and
 *  each blog can link to all the detailed analyses or pages on the app for more reference
 *  and details"*.
 *
 *      the hook       a 1200x630 image and the words above it       ~8 seconds
 *      THE POST       why it matters, the figures, what it means    ~2 minutes
 *      the working    the analysis, the charts, the caveats        ~20 minutes
 *
 *  EVERYTHING ON THIS PAGE IS ADDRESSED TO A RESIDENT, and that is a rule rather than a
 *  tone. TJ: *"I want /blog to be what the readers would see if these things were posted.
 *  But you mixed the EDITORIAL content here of speaking to ME. That needs to be entirely
 *  separate."* He was right: the page was telling readers how many posts were written and
 *  not published, which is us talking to ourselves on somebody else's page.
 *
 *  So nothing here mentions the candidates file, the four formats, an item number, a
 *  character budget, a draft, or a count of what is not here. A reader does not know this
 *  project has 48 candidates and must not be able to tell. With nothing published the
 *  archive is simply a blog with no posts yet.
 *
 *  `PostPage` IS THE POST, AND IT IS THE SAME OBJECT ON BOTH SURFACES. `/blog-drafts`
 *  renders this exact component -- not a preview of it -- so that what TJ reviews is
 *  byte for byte what a reader gets. Anything the drafts page needs to say about an item
 *  lives in that page's frame AROUND this, visibly outside it. The test: cover the frame
 *  with your thumb and what is left is the reader's post.
 *
 *  WHAT IT CARRIES THAT LOOKS LIKE APPARATUS AND IS NOT. The must-carry notes, under
 *  *What this does not show*. Those are rule 7 caveats -- a definitional break in a
 *  series, a stage-matched comparison -- and they belong to the finding rather than to our
 *  process. A reader needs them. Everything else editorial is gone.
 *
 *  NOTHING HERE IS TYPED. `/data/blog.json` is generated from
 *  `notes/process/CONTENT-CANDIDATES.md`, and it holds only the posts somebody decided to
 *  publish. A post is the one artefact this project makes that cannot be corrected once it
 *  has been shared, so it has exactly one home and every rendering follows it. */

type Link = { href: string; label: string }
type Impact = { who: string; text: string }
type Myth = { myth: string; mechanism: string }

export type Facebook = {
  text: string
  lines: string[]
  hook: string
  flags: string[]
  source: string | null
  visible: number
  chars: number
  link: string
}

export type Post = {
  id: string
  n: string
  slug: string
  title: string
  format: string
  label: string
  headline: string
  support: string
  impacts: Impact[]
  takeaway: string
  myth: Myth | null
  must_carry: string[]
  vintage: number | null
  vintage_from: string | null
  vintage_span: [number, number] | null
  epistemic: 'measured' | 'hypothesis'
  conclusions: string[]
  links: Link[]
  unrouted: string[]
  href: string
  /** The day it went up, RECORDED in the generator's published list. Nothing computes
   *  from it; it prints on the archive row. `null` if nobody wrote it down. */
  went_up: string | null
  published: boolean
  share: { html: string; width: number; height: number }
  reading: { words: number; minutes: number }
  /** THE WORDS THAT GO IN THE BOX ABOVE THE IMAGE, composed from the item's own
   *  sentences. It is NEVER rendered inside a post -- see /blog-drafts, which is the only
   *  place it appears. A reader meets it on Facebook, not here. */
  facebook: Facebook
}

export type BlogPayload = {
  source: { path: string; prepared: number }
  review: boolean
  words_per_minute: number
  pinned: string | null
  counts: {
    published: number
    prepared: number
    no_vintage: number
    hypothesis: number
    no_facebook_post: number
    facebook_flagged: number
    by_format: Record<string, number>
  }
  posts: Post[]
}

export const longDate = (iso: string) =>
  new Date(iso + 'T12:00:00Z').toLocaleDateString('en-GB',
    { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' })

export function Blog() {
  const slug = blogSlugFromPath(window.location.pathname)
  const { d, err } = useReport<BlogPayload>('blog.json')
  if (slug) return <OnePost slug={slug} d={d} err={err} />
  return <Archive d={d} err={err} />
}

/* ---- one post ------------------------------------------------------------ */

function OnePost({ slug, d, err }: { slug: string; d: BlogPayload | null; err: string | null }) {
  const p = d ? d.posts.find(x => x.slug === slug) ?? null : null

  if (d && !p) {
    return (
      <ReportShell tab={TAB} title="No post at this address"
        standfirst="Every post is listed on the blog." dataUrl={DATA}>
        <Body>
          The address <code>/blog/{slug}</code> names no post. The blog is{' '}
          <a className="underline" style={{ color: 'var(--series-cost)' }}
            href="/blog">here</a>.
        </Body>
        <MoreReports here={TAB} />
      </ReportShell>
    )
  }
  if (!p) {
    return <ReportShell tab={TAB} title="A post" err={err} loading={!d && !err}
      dataUrl={DATA} />
  }
  return <PostPage p={p} />
}

/** THE POST A READER GETS. Used by /blog and, unchanged, by /blog-drafts.
 *
 *  Rule 7a: it opens with the finding. The only thing above it is the hypothesis banner,
 *  which is rule 7a's own exception -- a warning that changes whether a reader should
 *  trust what follows. */
export function PostPage({ p }: { p: Post }) {
  return (
    <ReportShell
      tab={TAB}
      kicker="The blog"
      title={p.title}
      dataUrl={DATA}
      meta={<PostMeta p={p} />}
    >
      {p.epistemic === 'hypothesis' ? (
        <div className="card p-4 mt-8"
          style={{ borderLeft: '4px solid var(--status-warning)' }}>
          <p className="text-[11px] font-semibold uppercase tracking-widest"
            style={{ color: 'var(--status-warning)' }}>
            A scenario or an explanation &mdash; nothing here tests it
          </p>
          <p className="text-[13.5px] leading-relaxed mt-1"
            style={{ color: 'var(--text-secondary)' }}>
            This post rests on an explanation for a measurement rather than on the
            measurement itself. It is not a finding and must not be quoted as one.
          </p>
        </div>
      ) : null}

      {/* THE FINDING, FIRST. The myth above it where there is one -- struck, because a
          correction reads as nonsense without the thing being corrected. */}
      {p.myth ? (
        <p className="text-[19px] sm:text-[21px] leading-snug mt-9 line-through max-w-3xl"
          style={{ color: 'var(--text-muted)' }}>
          <Inline text={p.myth.myth} />
        </p>
      ) : null}
      <p className={'text-[21px] sm:text-[26px] font-bold leading-tight max-w-3xl ' +
        (p.myth ? 'mt-3' : 'mt-9')}>
        <Inline text={p.headline} />
      </p>

      {p.support ? (
        <p className="text-[16px] leading-relaxed max-w-3xl mt-5"
          style={{ color: 'var(--text-secondary)' }}>
          <Inline text={p.support} />
        </p>
      ) : null}

      {p.myth ? (
        <div className="card p-4 mt-6 max-w-3xl">
          <p className="text-[10.5px] font-semibold uppercase tracking-widest"
            style={{ color: 'var(--text-muted)' }}>What it misreads</p>
          <p className="text-[14.5px] leading-relaxed mt-1.5"
            style={{ color: 'var(--text-secondary)' }}>
            <Inline text={p.myth.mechanism} />
          </p>
        </div>
      ) : null}

      {/* WHAT IT MEANS FOR YOU. All of them at once, deliberately: TJ's model is that a
          resident seeing what the School Committee is being told about the same finding is
          a FEATURE rather than a leak. */}
      {p.impacts.length ? (
        <>
          <H2 id="you">What this means for you</H2>
          <div className="grid gap-3 mt-5 max-w-3xl">
            {p.impacts.map(im => (
              <div key={im.who} className="card p-4 avoid-break">
                <p className="text-[11px] font-semibold uppercase tracking-widest"
                  style={{ color: 'var(--text-muted)' }}>If you are {im.who}</p>
                <p className="text-[14.5px] leading-relaxed mt-1.5"
                  style={{ color: 'var(--text-secondary)' }}>
                  <Inline text={im.text} />
                </p>
              </div>
            ))}
          </div>
        </>
      ) : null}

      {p.takeaway ? (
        <>
          <H2 id="takeaway">What to take away</H2>
          <p className="text-[16px] leading-relaxed max-w-3xl mt-5"
            style={{ color: 'var(--text-secondary)' }}>
            <Inline text={p.takeaway} />
          </p>
        </>
      ) : null}

      {/* WHAT IT DOES NOT SHOW. Rule 7's other half, and a section rather than a footnote:
          a measurement and an explanation for it are never set in one voice here, and a
          short piece written to persuade is the cheapest place to get that wrong. */}
      <H2 id="limits">What this does not show</H2>
      {p.must_carry.length ? (
        <ul className="grid gap-3 mt-5 max-w-3xl">
          {p.must_carry.map((m, i) => (
            <li key={i} className="text-[14.5px] leading-relaxed pl-4"
              style={{ color: 'var(--text-secondary)',
                borderLeft: '2px solid var(--status-warning)' }}>
              <Inline text={m} />
            </li>
          ))}
        </ul>
      ) : null}
      <Body>
        No figure on this page is computed here. Every one of them is carried unaltered
        from the report underneath it, and that report recomputes its own figures from the
        documents by a script that fails rather than warns. This post is a summary of a
        finding; it is not the finding, and it is not an official document.
      </Body>

      <H2 id="working">Read the working</H2>
      <Body>
        The full version &mdash; the series, the charts, the method and everything this
        summary leaves out.
      </Body>
      <div className="grid gap-2 mt-4 sm:grid-cols-2 max-w-3xl">
        {p.links.map(l => (
          <a key={l.href} href={l.href}
            className="card block p-3.5 min-h-[44px] text-[14px] font-semibold
                       leading-snug transition-opacity hover:opacity-90"
            style={{ color: 'var(--series-cost)' }}>
            {l.label} &rarr;
            {/* The address, on paper only. A link is dead in print, and a reader of a
                printed post has to be able to type it. Screen readers of the same page see
                the link and not the URL, so the two documents stay the same document. */}
            <span className="print-only block font-normal text-[12px] mt-0.5"
              style={{ color: 'var(--text-muted)' }}>
              lunenburgbudgetproject.org{l.href}
            </span>
          </a>
        ))}
      </div>

      <MoreReports here={TAB} />
    </ReportShell>
  )
}

/** The year the figures are about, and how long it takes to read. Beside the title.
 *
 *  WHAT YEAR is not decoration. A figure that is right today is wrong in three years, and
 *  a post is shared onward by people who will not come back to check it. A post whose
 *  vintage could not be established says so in those words rather than borrowing the year
 *  it was written. */
function PostMeta({ p }: { p: Post }) {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2 mt-4 text-[12.5px]"
      style={{ color: 'var(--text-muted)' }}>
      <span style={p.vintage === null ? { color: 'var(--status-bad)' } : undefined}>
        {p.vintage === null ? 'Year not established'
          : p.vintage_span ? `Figures for FY${p.vintage_span[0]}–FY${p.vintage_span[1]}`
            : `Figures for FY${p.vintage}`}
      </span>
      <span>About {p.reading.minutes} {p.reading.minutes === 1 ? 'minute' : 'minutes'} to read</span>
      {p.published && p.went_up ? <span>Published {longDate(p.went_up)}</span> : null}
    </div>
  )
}

/* ---- the archive --------------------------------------------------------- */

/** Newest first, so nothing has to be caught the day it goes out.
 *
 *  TJ: *"there needs to be a way to see the 'historical' blog posts. Like the list with
 *  dates and such"*, and the reason -- *"In case people missed it"*. Somebody who joins a
 *  Facebook group in November has to be able to read back through what they missed. */
function Archive({ d, err }: { d: BlogPayload | null; err: string | null }) {
  const [n, setN] = useState(12)
  const rows = d ? d.posts : []

  return (
    <ReportShell
      tab={TAB}
      title="The blog"
      standfirst="One finding at a time, in about two minutes, with the report behind every one."
      err={err}
      loading={!d && !err}
      dataUrl={DATA}
    >
      {d ? (
        <>
          {rows.length ? (
            <>
              <div className="grid gap-3 mt-9">
                {rows.slice(0, n).map(p => <Row key={p.slug} p={p} />)}
              </div>
              {n < rows.length ? (
                <button type="button" onClick={() => setN(v => v + 12)}
                  className="card px-4 py-3 min-h-[44px] mt-4 text-[13.5px] font-semibold
                             no-print transition-opacity hover:opacity-90"
                  style={{ color: 'var(--series-cost)' }}>
                  Older posts &rarr;
                </button>
              ) : null}
            </>
          ) : (
            <div className="card p-5 mt-9 max-w-3xl">
              <p className="text-[16px] font-bold">No posts yet.</p>
              <p className="text-[14px] leading-relaxed mt-2"
                style={{ color: 'var(--text-secondary)' }}>
                The first one will be here. In the meantime the reports these are drawn
                from are at{' '}
                <a className="underline" style={{ color: 'var(--series-cost)' }}
                  href="/reports">reports</a>, and you can{' '}
                <a className="underline" style={{ color: 'var(--series-cost)' }}
                  href="/ask-a-question">ask us a question</a> about any of it.
              </p>
            </div>
          )}

          <H2 id="what">What a post is</H2>
          <Body>
            A post is one finding, in about two minutes: what it is, what it means for you,
            and what it does not show. It is the middle of three lengths &mdash; shorter
            than the analysis it rests on, longer than anything that fits in a picture.
          </Body>
          <Body>
            No figure is computed on a post. Every one is carried unaltered from the report
            underneath it, and that report recomputes its own figures from the documents by
            a script that fails rather than warns. Every post ends in the links out, which
            is the point of it.
          </Body>
          <Body>
            Nothing here is an official document. It is written by the Lunenburg Budget
            Project, an independent tool for residents, and it has not been reviewed or
            endorsed by the Town of Lunenburg, the School Committee, the Finance Committee
            or Lunenburg Public Schools.
          </Body>

          <p className="text-[13.5px] leading-relaxed max-w-2xl mt-8 no-print"
            style={{ color: 'var(--text-muted)' }}>
            The reports underneath these posts are indexed at{' '}
            <a className="underline" style={{ color: 'var(--series-cost)' }}
              href="/reports">reports</a>. The rows this page is drawn from are published
            at{' '}
            <a className="underline" style={{ color: 'var(--series-cost)' }}
              href={abs(DATA)}>{DATA}</a>.
          </p>

          <MoreReports here={TAB} />
        </>
      ) : null}
    </ReportShell>
  )
}

/** One row: the date, how long it takes, the title and the finding. */
function Row({ p }: { p: Post }) {
  return (
    <a href={`/blog/${p.slug}`}
      className="card block p-4 avoid-break transition-opacity hover:opacity-90">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="text-[12.5px] tnum" style={{ color: 'var(--text-muted)' }}>
          {p.went_up ? longDate(p.went_up) : ''}
        </span>
        <span className="text-[12.5px]" style={{ color: 'var(--text-muted)' }}>
          {p.reading.minutes} min
        </span>
      </div>
      <p className="text-[16px] font-bold leading-snug mt-1.5"
        style={{ color: 'var(--series-cost)' }}>{p.title} &rarr;</p>
      <p className="text-[14px] leading-snug mt-1.5" style={{ color: 'var(--text-secondary)' }}>
        <Inline text={p.headline} />
      </p>
    </a>
  )
}
