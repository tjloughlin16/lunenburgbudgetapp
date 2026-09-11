import { useState } from 'react'
import { useReport } from '../components/report'
import { PostPage, longDate, type BlogPayload, type Post } from './Blog'

/** THE REVIEW SURFACE. Local only. Never built, never deployed, never on the site.
 *
 *  TJ: *"So we mixed 2 things again. I want /blog to be what the readers would see if
 *  these things were posted. But you mixed the EDITORIAL content here of speaking to ME.
 *  That needs to be entirely separate. Like a blog-drafts or something. this is so i can
 *  review the blog format and style and flow, then the blogs themselves for style and
 *  flow. And then the editorials need to show me what the facebook posts would be for each
 *  blog."*
 *
 *  THREE JOBS, IN THAT ORDER.
 *
 *   1. Review the FORMAT -- does a post work as a post. So each one is rendered by the
 *      same `PostPage` a reader gets, at full width, not in a preview box.
 *   2. Review the POSTS. All of them, in the candidates file's own order, with a jump list.
 *   3. See what the FACEBOOK POST would be. That is a third artefact -- the image plus the
 *      words above it -- and it is the thing that actually gets read. It sits BESIDE the
 *      post here and appears nowhere inside it.
 *
 *  THE FRAME IS OUTSIDE THE POST, ALWAYS. Item number, format, whether it is up, the
 *  composed Facebook text and its flags -- all of that is in this page's chrome. Cover the
 *  chrome with your thumb and what is left is byte for byte what a reader gets. That is
 *  the whole reason this page exists: a preview carrying extra material is a preview of
 *  the wrong thing.
 *
 *  HOW IT STAYS OFF THE SITE. Three independent guarantees, because one is a promise and
 *  three is a property:
 *
 *   - it is not a `Tab`, so it is in no route table, no sitemap and no prerender;
 *   - App.tsx renders it only inside `import.meta.env.DEV`, which is replaced with `false`
 *     and eliminated from the production bundle;
 *   - its content comes from `/data/blog-all.json`, which lives in gitignored `build/` and
 *     is served only by a dev-server middleware that contributes nothing to a build.
 *
 *  And `scripts/build_blog.py --check` greps the whole of `fy28/public` and `fy28/dist`
 *  for every unpublished post's address on every run, because reasoning about three
 *  guarantees is not the same as looking. */

export function BlogDrafts() {
  const { d } = useReport<BlogPayload>('blog-all.json')
  const [only, setOnly] = useState('all')

  if (!d) {
    return (
      <div className="mx-auto max-w-3xl px-5 py-16">
        <h1 className="text-3xl font-bold tracking-tight">Nothing to review yet</h1>
        <p className="mt-4 text-[15px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          Run <code className="px-1 py-0.5 rounded" style={{ background: 'var(--surface-3)' }}>
            python3 scripts/build_blog.py --all</code> and reload. It writes{' '}
          <code>build/blog-all.json</code> and the share cards beside it, both gitignored.
        </p>
      </div>
    )
  }

  const formats = Array.from(new Set(d.posts.map(p => p.format)))
  const shown = only === 'all' ? d.posts : d.posts.filter(p => p.format === only)
  const flagged = d.posts.filter(p => p.facebook.flags.length).length
  const blank = d.posts.filter(p => !p.facebook.text).length

  return (
    <div className="pb-24">
      <div className="mx-auto max-w-6xl px-5 pt-12">
        <p className="text-xs font-semibold uppercase tracking-widest"
          style={{ color: 'var(--status-warning)' }}>Not the site &mdash; local review only</p>
        <h1 className="text-4xl font-bold tracking-tight mt-3">Posts for review</h1>
        <p className="mt-4 text-[15px] leading-relaxed max-w-2xl"
          style={{ color: 'var(--text-secondary)' }}>
          Every post as a reader would see it, with the Facebook post that would carry it
          above each one. None of this is on the deployed site: this page does not exist
          there, and neither does the file it reads.
        </p>

        <div className="grid gap-3 mt-8 sm:grid-cols-4">
          <Metric v={String(d.counts.prepared)} u="written" />
          <Metric v={String(d.counts.published)} u="up on the site" />
          <Metric v={String(flagged)} u="Facebook posts flagged"
            tone={flagged ? 'var(--status-warning)' : undefined} />
          <Metric v={String(blank)} u="with no Facebook post"
            tone={blank ? 'var(--status-bad)' : undefined} />
        </div>

        <div className="flex flex-wrap items-center gap-1.5 mt-8">
          <Pill on={only === 'all'} onClick={() => setOnly('all')}>
            All {d.posts.length}
          </Pill>
          {formats.map(f => (
            <Pill key={f} on={only === f} onClick={() => setOnly(f)}>
              {d.posts.find(p => p.format === f)?.label}{' '}
              {d.posts.filter(p => p.format === f).length}
            </Pill>
          ))}
        </div>

        {/* Bulk open and close. The jump list below scrolls to an item but cannot OPEN it
            now that the items are collapsed, so without these a link in that list would
            land on a closed row and look broken. Plain DOM rather than state: `<details>`
            already owns its own open flag, and mirroring it into React would give two
            sources of truth for one boolean. */}
        <div className="flex flex-wrap items-center gap-3 mt-6 text-[12.5px]">
          <button type="button" className="underline"
            style={{ color: 'var(--series-cost)' }}
            onClick={() => document.querySelectorAll<HTMLDetailsElement>('details[id^="draft-"]')
              .forEach(el => { el.open = true })}>
            open all
          </button>
          <button type="button" className="underline"
            style={{ color: 'var(--series-cost)' }}
            onClick={() => document.querySelectorAll<HTMLDetailsElement>('details[id^="draft-"]')
              .forEach(el => { el.open = false })}>
            close all
          </button>
          <span style={{ color: 'var(--text-muted)' }}>
            or click a row to open one
          </span>
        </div>

        <ol className="grid gap-1 mt-6 sm:grid-cols-2">
          {shown.map(p => (
            <li key={p.slug} className="text-[13px] leading-snug">
              <a href={`#draft-${p.id}`} className="underline"
                style={{ color: 'var(--series-cost)' }}
                onClick={() => {
                  const el = document.getElementById(`draft-${p.id}`)
                  if (el instanceof HTMLDetailsElement) el.open = true
                }}>
                <span className="tnum" style={{ color: 'var(--text-muted)' }}>{p.n}</span>{' '}
                {p.title}
              </a>
              {p.facebook.flags.length ? (
                <span className="ml-1.5" style={{ color: 'var(--status-warning)' }}>&#9679;</span>
              ) : null}
            </li>
          ))}
        </ol>
      </div>

      {shown.map(p => <Draft key={p.slug} p={p} />)}
    </div>
  )
}

/** One item: the frame, the Facebook post, then the post itself untouched.
 *
 *  COLLAPSED BY DEFAULT. TJ, reviewing: "its too much to scroll. But i like this format.
 *  FB post. Metadata. Blog post. I just need those collapsible so i can focus." Forty-eight
 *  items each carrying a feed mock, a share card and a full post is a page nobody can hold
 *  a judgement in -- and the judgement is the whole point of this surface.
 *
 *  The summary carries everything needed to CHOOSE which to open: number, format, state,
 *  slug, the title, and whether the Facebook post is flagged. `<details>` rather than React
 *  state on purpose -- the browser keeps the open ones open across a hot reload, which
 *  matters when the thing being edited is the copy this page renders. */
function Draft({ p }: { p: Post }) {
  return (
    <details id={`draft-${p.id}`} className="mt-8 pt-6 group"
      style={{ borderTop: '3px solid var(--grid)' }}>
      <summary className="mx-auto max-w-6xl px-5 cursor-pointer list-none
                          flex flex-wrap items-baseline gap-x-3 gap-y-1
                          hover:opacity-80">
        <span className="text-[13px] tnum select-none"
          style={{ color: 'var(--text-muted)' }}>
          <span className="group-open:hidden">&#9656;</span>
          <span className="hidden group-open:inline">&#9662;</span>
        </span>
        <span className="text-[15px] font-bold tnum">{p.n}</span>
        <span className="text-[14px] font-semibold">{p.title}</span>
        <span className="text-[11px] font-semibold uppercase tracking-widest"
          style={{ color: 'var(--text-muted)' }}>{p.label}</span>
        {p.facebook?.flags?.length ? (
          <span className="text-[11px] font-semibold uppercase tracking-widest"
            style={{ color: 'var(--status-warning)' }}>
            fb &times;{p.facebook.flags.length}
          </span>
        ) : null}
      </summary>
      <div className="mx-auto max-w-6xl px-5 mt-6">
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <span className="text-[15px] font-bold tnum">{p.n}</span>
          <span className="text-[11px] font-semibold uppercase tracking-widest"
            style={{ color: 'var(--text-muted)' }}>{p.label}</span>
          <span className="text-[11px] font-semibold uppercase tracking-widest"
            style={{ color: p.published ? 'var(--status-good)' : 'var(--status-warning)' }}>
            {p.published ? `up ${p.went_up ? longDate(p.went_up) : ''}` : 'not published'}
          </span>
          <span className="text-[12.5px]" style={{ color: 'var(--text-muted)' }}>
            /blog/{p.slug}
          </span>
        </div>

        <div className="mt-6 max-w-[440px]">
          <FacebookPost p={p} />
        </div>

        <p className="text-[11px] font-semibold uppercase tracking-widest mt-10"
          style={{ color: 'var(--text-muted)' }}>
          What the click gets &mdash; exactly as a reader sees it
        </p>
        <p className="text-[12.5px] leading-snug mt-1.5 max-w-2xl"
          style={{ color: 'var(--text-muted)' }}>
          Nothing below is added for review. It is the same component the site renders, and
          the PDF is the same again.
        </p>
      </div>

      {/* THE POST. Not wrapped, not previewed, not annotated. */}
      <div style={{ background: 'var(--surface-2)' }} className="mt-6">
        <PostPage p={p} />
      </div>
    </details>
  )
}

/** WHAT THE POST WOULD LOOK LIKE IN A FEED.
 *
 *  Drawn as a post rather than listed as fields, because the question is whether it stops
 *  a scroll, and that is not a question anybody can answer from a text box. The image is
 *  the real 1200x630 share card in an iframe, scaled -- the same file that would be
 *  uploaded, not a mock of it.
 *
 *  THE TEXT IS COMPOSED, NEVER WRITTEN. `scripts/build_blog.py` takes whole sentences out
 *  of the item's own takeaway, and where an item yields nothing short enough to open with
 *  it leaves the post EMPTY and says why. A filler sentence would hide the editorial
 *  problem this page exists to surface. */
function FacebookPost({ p }: { p: Post }) {
  const fb = p.facebook
  return (
    <div>
      <p className="text-[11px] font-semibold uppercase tracking-widest mb-2"
        style={{ color: 'var(--text-muted)' }}>The Facebook post</p>
      <div className="rounded-lg overflow-hidden"
        style={{ border: '1px solid var(--grid)', background: 'var(--surface-1)' }}>
        <div className="flex items-center gap-2 px-3 pt-3">
          <span className="inline-block rounded-full"
            style={{ width: 32, height: 32, background: 'var(--brand)' }} />
          <span>
            <span className="block text-[13px] font-semibold leading-tight">
              The Lunenburg Budget Project
            </span>
            <span className="block text-[11px]" style={{ color: 'var(--text-muted)' }}>
              Just now &middot; Public
            </span>
          </span>
        </div>

        {fb.text ? (
          <p className="px-3 pt-2.5 pb-3 text-[13.5px] leading-snug whitespace-pre-wrap">
            <span>{fb.text.slice(0, fb.visible)}</span>
            {fb.chars > fb.visible ? (
              <>
                <span style={{ color: 'var(--text-secondary)' }}>
                  {fb.text.slice(fb.visible)}
                </span>
                <span className="block text-[12px] font-semibold mt-1"
                  style={{ color: 'var(--status-warning)' }}>
                  &uarr; everything after the first {fb.visible} characters is behind
                  &ldquo;See more&rdquo;
                </span>
              </>
            ) : null}
            <span className="block mt-2" style={{ color: 'var(--series-cost)' }}>
              {fb.link}
            </span>
          </p>
        ) : (
          <p className="px-3 pt-2.5 pb-3 text-[13.5px] leading-snug"
            style={{ color: 'var(--status-bad)' }}>
            No post could be composed from this item&rsquo;s own words. Nothing has been
            invented to fill the gap.
          </p>
        )}

        {/* The real card, at 1200x630, scaled to the column. */}
        <div className="relative" style={{ width: '100%', paddingTop: '52.5%',
          borderTop: '1px solid var(--grid)', overflow: 'hidden' }}>
          <iframe title={`share card for ${p.slug}`} src={p.share.html} scrolling="no"
            style={{ position: 'absolute', top: 0, left: 0, width: 1200, height: 630,
              border: 0, transformOrigin: 'top left' }}
            ref={el => {
              if (!el || !el.parentElement) return
              const s = el.parentElement.clientWidth / 1200
              el.style.transform = `scale(${s})`
            }} />
        </div>
        <div className="px-3 py-2" style={{ background: 'var(--surface-3)' }}>
          <span className="block text-[10.5px] uppercase tracking-wider"
            style={{ color: 'var(--text-muted)' }}>lunenburgbudgetproject.org</span>
          <span className="block text-[13px] font-semibold leading-tight mt-0.5">
            {p.title}
          </span>
        </div>
      </div>

      <p className="text-[12px] mt-2" style={{ color: 'var(--text-muted)' }}>
        {fb.chars} characters
        {fb.source ? ` · composed from the ${fb.source}` : ''}
      </p>
      {fb.flags.length ? (
        <ul className="mt-2 grid gap-1.5">
          {fb.flags.map((f, i) => (
            <li key={i} className="text-[12.5px] leading-snug pl-3"
              style={{ color: 'var(--text-secondary)',
                borderLeft: '2px solid var(--status-warning)' }}>{f}</li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}

function Metric({ v, u, tone }: { v: string; u: string; tone?: string }) {
  return (
    <div className="card p-3.5">
      <span className="text-2xl font-bold tnum" style={tone ? { color: tone } : undefined}>
        {v}
      </span>
      <span className="block text-[12.5px] mt-0.5" style={{ color: 'var(--text-muted)' }}>
        {u}
      </span>
    </div>
  )
}

function Pill({ on, onClick, children }: {
  on: boolean; onClick: () => void; children: React.ReactNode
}) {
  return (
    <button type="button" onClick={onClick} aria-pressed={on}
      className="text-[12.5px] font-semibold px-2.5 py-1.5 rounded min-h-[32px]"
      style={on
        ? { background: 'var(--surface-3)', color: 'var(--text-primary)' }
        : { color: 'var(--text-muted)', border: '1px solid var(--grid)' }}>
      {children}
    </button>
  )
}
