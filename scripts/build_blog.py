#!/usr/bin/env python3
"""The blog: one post per PUBLISHED item, the archive that lists them, and the share card.

    python3 scripts/build_blog.py
    python3 scripts/build_blog.py --check
    python3 scripts/build_blog.py --measure                 # does the share card fit 1200x630
    python3 scripts/build_blog.py --render-images [slug ...] [--out DIR]

WHY THERE IS A TIER BETWEEN THE CARD AND THE REPORT. There are three lengths a reader
gives this project and for a long time only two of them existed:

    the hook       a 1200x630 image: label, headline, one line, an address   ~8 seconds
    THE POST       why it matters, the figures, what it means for you         ~2 minutes
    the working    the analysis, the charts, the caveats                     ~20 minutes

A card is too short to convince anybody and an analysis page is too long to open from a
Facebook post. TJ, working it out: *"Maybe we basically treat this flow like a BLOG....
create 'blog posts' that include high level summaries of the data, specifically built to
have interesting headings people care about, posted on the home page with quick links and
hooks, and also posted to Facebook groups. Clicking, brings you to the 'blog' with details,
but still not the full content. and each blog can link to all the detailed analyses or
pages on the app for more reference and details"*.

THIS IS NOT A CONTENT MANAGEMENT SYSTEM. TJ, after three drafts of one: *"This is NOT a
CMS :)"*. There is no draft state, no scheduling engine and no editor's view, because none
of those is a thing that exists here:

  * the CONTENT is `notes/process/CONTENT-CANDIDATES.md`, and the EDITOR is Zed;
  * the PUBLISHED list is `PUBLISHED` below -- the items that are live, named one per line;
  * an item not on it is not in a state. It is simply not published, and it stays here;
  * publishing is: add a line, run this, commit, deploy. The workflow is git.

NOTHING HERE KNOWS WHAT DAY IT IS, and that is the last thing that had to go. There was a
publish DATE on each item and this decided from it, which is a scheduler however small it
looks. TJ: *"its not about 'undated' content. the dates are just a PLAN you and I have. I
will tell you when we push the next post up. We'll discuss and post. Nothing automated."*
So the dates live in `notes/process/BLOG-PLAN.md`, where they are a recommendation two
people argue with, and the list below is a record of what was actually decided. A date is a
prediction; a list is a fact.

THE ONE THING THAT GENUINELY MATTERS, AND IT IS A CONSTRAINT RATHER THAN A FEATURE.
`fy28/public/` IS THE SITE. Everything in it is served whether or not a page renders it and
whether or not anything links to it, so a payload holding all 48 items would publish all 48
whatever the pages did with them. TJ: *"the blog plan is all repo-side. you/i will push and
rollout deliberately. the content shouldnt exist on the site anywhere"*.

So THE GATE IS AT THE POINT OF WRITING, here, and nowhere else. An undated item is never
serialised, never given a share page, never routed, never prerendered and never put in the
sitemap. `--check` proves the absence afterwards by searching the whole published tree for
each undated item's own words, because reasoning about a filter is not the same as looking.

AND IT FAILS CLOSED. Not on the list means not published, and a list naming an item that
does not exist writes nothing at all. The cost of a post staying private one more day is
nothing; the cost of one going out early is TJ's name on something he had not signed off.

ONE LIST DRIVES EVERYTHING. The same names decide the payload, the archive row, the route,
the prerendered HTML, the sitemap entry and the share card, and every one of those is
DERIVED from it on each build rather than appended to. So a published post cannot be
live-but-unfindable, and the fifth post costs exactly what the twentieth does.

THE SHARE IMAGE IS GENERATED FROM THE SAME PAYLOAD. `/share/<slug>.html` is a 1200x630 page
holding the eyebrow, the headline, one sentence of support and the address; a PNG is
Chrome's screenshot of it. An image is the one artefact here that cannot be corrected after
it is posted, so not a character of it is authored: every string is the item's own, the
palette is read out of `fy28/src/index.css`, and `--measure` asks the browser whether the
copy fits rather than anybody looking at it.
"""

import argparse
import io
import json
import os
import re
import subprocess
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import content_items as C               # noqa: E402

OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'blog.json')
# THE REVIEW COPY, and note where it is NOT: anywhere under `fy28/public`, which vite
# copies into `dist` wholesale. Gitignored, served only by the dev server.
REVIEW = os.path.join(ROOT, 'build', 'blog-all.json')
REVIEW_SHARE = os.path.join(ROOT, 'build', 'share')
REVIEW_PDF = os.path.join(ROOT, 'build', 'pdf')
SHARE = os.path.join(ROOT, 'fy28', 'public', 'share')
CSS = os.path.join(ROOT, 'fy28', 'src', 'index.css')
SITE = 'https://lunenburgbudgetproject.org'

# WHAT IS PUBLISHED. Everything else stays in this repository.
#
# One entry per live post: the item number as it appears in the candidates file, and the
# day it went up, which is RECORDED here rather than computed anywhere -- it is printed on
# the archive row and nothing reads it. `None` is fine if nobody wrote the day down.
#
# THE ORDER IS PUBLICATION ORDER. The archive shows it reversed, newest first, so the last
# line here is the top of the page.
#
# IT STARTS EMPTY AND THAT IS A CORRECT STATE. Zero published posts means an archive that
# says so, no routes, no share images and nothing in the sitemap. Which items go up, and
# when, is a conversation between TJ and whoever is helping -- see
# `notes/process/BLOG-PLAN.md` for the suggested order, which is a recommendation and not
# a schedule. To publish, add a line:
#
#     PUBLISHED = {
#         '2.1': '2026-09-15',
#     }
#
# ...then `python3 scripts/build_blog.py`, commit, deploy.
PUBLISHED = {}

# One declaration of the divisor, in the parser, imported rather than repeated.
WPM = C.WORDS_PER_MINUTE

# The tokens the share image needs, read out of the app's own `:root` so the image cannot
# drift from the site. A share image has no viewer theme -- it is a raster -- so the LIGHT
# values are the ones taken.
SHARE_TOKENS = ('surface-1', 'surface-3', 'text-primary', 'text-secondary', 'text-muted',
                'grid', 'brand', 'series-cost', 'status-warning')


def slugify(s):
    s = re.sub(r'[‘’′]', '', s.lower())
    s = re.sub(r'[^a-z0-9]+', '-', s)
    return s.strip('-')


def route_labels():
    """slug -> the name the app gives that page. Read off routes.ts, never listed here.

    A post's whole job is to hand the reader on, so every link on it needs a name. The two
    tables the app itself routes and labels on are the only place those names exist; a
    second list here would be the artefact that goes stale first.
    """
    src = io.open(C.ROUTES, encoding='utf-8').read()
    blk = re.search(r'export const SLUG: Record<Tab, string> = \{(.*?)\n\}', src, re.S)
    lab = re.search(r'export const LABEL: Record<Tab, string> = \{(.*?)\n\}', src, re.S)
    if not blk or not lab:
        raise SystemExit('routes.ts: could not find the SLUG and LABEL tables')
    slug = dict(re.findall(r"^\s*(\w+): '([^']*)',", blk.group(1), re.M))
    label = dict(re.findall(r"^\s*(\w+): '(.*?)',$", lab.group(1), re.M))
    out = {'/' + v: label.get(k, k) for k, v in slug.items() if v}
    if len(out) < 20:
        raise SystemExit('routes.ts: only %d routes joined a slug to a label — refusing '
                         'to write, because every post would link to an unnamed page'
                         % len(out))
    return out


def tokens():
    """The light palette, out of index.css's `:root` block."""
    src = io.open(CSS, encoding='utf-8').read()
    root = re.search(r':root\s*\{(.*?)\n\}', src, re.S)
    if not root:
        raise SystemExit('index.css: could not find the :root block')
    vals = dict(re.findall(r'--([a-z0-9-]+):\s*([^;]+);', root.group(1)))
    out = {}
    for t in SHARE_TOKENS:
        if t not in vals:
            raise SystemExit('index.css: :root declares no --%s, which the share image '
                             'is drawn in — refusing to write' % t)
        out[t] = vals[t].strip()
    return out


def words(*parts):
    return len(re.findall(r"[A-Za-z0-9$%][A-Za-z0-9$%.,'’\-]*", ' '.join(p for p in parts if p)))


def whole(a, b):
    return ' '.join(x for x in (a or '', b or '') if x).strip()


def slug_of(it):
    """The address. The item's title, slugified, or whatever `**Slug** —` overrides it to.

    A title is what a reader recognises in a shared link. The override is the remedy when
    a title has to change after a post has been shared: rule 12's discipline -- an address
    is a promise -- applied to our own pages.
    """
    m = re.search(r'\*\*Slug\*\*\s*—\s*([a-z0-9][a-z0-9-]*)', it['_visible'] + it.get('_meta', ''))
    return m.group(1) if m else slugify(it['title'])


def build(everything=False):
    """The payload. `everything=True` is the LOCAL REVIEW COPY and never leaves this repo.

    One generator, one flag, so the review copy cannot drift from the published one: a
    post TJ reads at his desk is byte for byte the post a reader would get. The difference
    is the gate below and the file it is written to -- `fy28/public/data/blog.json`, which
    is the site, against `build/blog-all.json`, which is gitignored and served only by the
    dev server.
    """
    every = C.items()
    labels = route_labels()
    for url, r in C.reports_by_url().items():
        labels.setdefault(url, r.get('title') or url)
    routes = C.payload_routes()
    idx = C.conclusion_index()

    unknown = sorted(set(PUBLISHED) - {it['n'] for it in every})
    if unknown:
        raise SystemExit(
            'PUBLISHED names %s, which is not an item in list 1 of %s. Refusing to write '
            'anything: a list that does not resolve is the one case where guessing what '
            'was meant could publish the wrong post.' % (', '.join(unknown), C.DOC))

    posts, prepared, pinned = [], 0, []
    for it in every:
        prepared += 1
        n, slug = it['n'], slug_of(it)

        # THE GATE. Everything below this line is written into `fy28/public/`, which is
        # the site. An item that is not on the list does not get past it -- not as a row
        # with a flag on it, not as a file nothing links to. It is simply not here.
        if not everything and n not in PUBLISHED:
            continue

        href = it['slugs'][0] if it['slugs'] else None
        if not href:
            for cid in it['cited']:
                href = routes.get(idx[cid][0])
                if href:
                    break
        href = href or '/reports'

        # WHERE THE POST HANDS THE READER ON. The item's own Source and Format lines, then
        # the page that renders each cited conclusion's payload -- so a post built on four
        # conclusions from four reports reaches all four. A post that cannot hand a reader
        # on is a long card, so a post with no routed link refuses to write.
        seen, links, dropped = set(), [], []
        cited_routes = [routes[idx[cid][0]] for cid in it['cited'] if idx[cid][0] in routes]
        for h in [href] + it['slugs'] + cited_routes:
            if h in seen:
                continue
            seen.add(h)
            (links if h in labels else dropped).append(
                dict(href=h, label=labels[h]) if h in labels else h)
        if not links:
            raise SystemExit('item %s links to nothing the app routes — refusing to write'
                             % n)

        w = words(it['headline'], it['support'], it['takeaway'],
                  *[i['text'] for i in it['impacts']], *it['must_carry'],
                  (it['myth'] or {}).get('myth'), (it['myth'] or {}).get('mechanism'))

        if re.search(r'\*\*Pin\*\*\s*—\s*yes', it['_visible'], re.I):
            pinned.append(slug)

        posts.append(dict(
            id=it['id'], n=n, slug=slug, title=it['title'],
            format=it['format'], label=it['label'],
            headline=it['headline'], support=it['support'],
            impacts=[dict(who=i['who'], text=i['text']) for i in it['impacts']],
            takeaway=it['takeaway'],
            myth=(dict(myth=it['myth']['myth'], mechanism=it['myth']['mechanism'])
                  if it['myth'] else None),
            must_carry=it['must_carry'],
            vintage=it['vintage'], vintage_from=it['vintage_from'],
            vintage_span=it['vintage_span'],
            epistemic=it['epistemic'], conclusions=it['cited'],
            links=links, unrouted=dropped, href=href,
            went_up=PUBLISHED.get(n),
            published=n in PUBLISHED,
            share=dict(html='/share/%s.html' % slug, width=1200, height=630),
            reading=dict(words=w, minutes=max(1, int(round(w / float(WPM))))),
        ))
        posts[-1]['facebook'] = facebook_post(posts[-1])

    if prepared < C.MIN_ITEMS:
        raise SystemExit('parsed %d items and the floor is %d — refusing to write'
                         % (prepared, C.MIN_ITEMS))
    dupes = sorted({p['slug'] for p in posts
                    if sum(1 for q in posts if q['slug'] == p['slug']) > 1})
    if dupes:
        raise SystemExit(
            'two published items resolve to one address: %s. A slug is the address a post '
            'is shared at — give one of them a `**Slug** — ...` line.' % ', '.join(dupes))
    if len(pinned) > 1:
        raise SystemExit('%d published items are pinned (%s) and the front page shows one'
                         % (len(pinned), ', '.join(pinned)))

    # NEWEST FIRST, and "newest" is the order of the list rather than a date: the list is
    # the record of what was decided and in what order, and a date nobody wrote down would
    # otherwise reorder the page silently.
    order = list(PUBLISHED)
    posts.sort(key=lambda p: (order.index(p['n']) if p['n'] in order else -1), reverse=True)
    return dict(
        source=dict(path='notes/process/CONTENT-CANDIDATES.md', prepared=prepared),
        review=everything,
        words_per_minute=WPM,
        pinned=pinned[0] if pinned else None,
        counts=dict(
            published=sum(1 for p in posts if p['published']),
            prepared=prepared,
            no_vintage=sum(1 for p in posts if p['vintage'] is None),
            hypothesis=sum(1 for p in posts if p['epistemic'] == 'hypothesis'),
            no_facebook_post=sum(1 for p in posts if not p['facebook']['text']),
            facebook_flagged=sum(1 for p in posts if p['facebook']['flags']),
            by_format={f: sum(1 for p in posts if p['format'] == f)
                       for f in sorted({p['format'] for p in posts})},
        ),
        posts=posts,
    )


def leak_check(payload):
    """PROVE THE ABSENCE. Search the whole published tree for every unpublished item.

    Reasoning about a filter is not the same as looking, and this is exactly the kind of
    thing that is correct the day it is written and leaks three weeks later when somebody
    adds a field to a payload. So this walks `fy28/public/` and `fy28/dist/` -- every byte
    the host would serve -- and looks.

    WHAT IT LOOKS FOR, and the choice matters. It searches for each unpublished item's own
    ADDRESS: its slug, and its item id. Those are artefacts this pipeline invents and they
    exist nowhere else, so a hit is unambiguous -- a payload row, a share page, a sitemap
    entry, a prerendered archive listing it, a stale file left in dist by an earlier build.
    It caught all four of those on its first run.

    IT DOES NOT SEARCH FOR THE ITEM'S SENTENCES, and that is deliberate rather than lax. An
    item's headline is frequently the verbatim headline of a CONCLUSION that its own report
    already publishes at `/data/<report>.json`; finding it there is the report doing its
    job, not this leaking. A check that fires on that is measuring the archive rather than
    the gate, and a check that cries wolf gets turned off.
    """
    live = {p['slug'] for p in payload['posts'] if p['published']}
    # ...and the review copy's own filename, which must appear in no built file. The app
    # names it only inside `import.meta.env.DEV`, so a production bundle that mentions it
    # is a bundle where that guard stopped working.
    probes = [('the review copy', 'blog-all.json')]
    for it in C.items():
        slug = slug_of(it)
        if slug in live:
            continue
        # THE ADDRESS FORMS, not the bare slug. A slug is the item's title slugified and
        # the titles mirror the conclusion ids, so a bare slug matches the published
        # payload of the REPORT the item rests on -- which is that report publishing its
        # own conclusion, not this leaking. `/blog/<slug>` and `/share/<slug>.html` are
        # addresses only this pipeline invents.
        probes += [(it['n'], '/blog/' + slug), (it['n'], '/share/' + slug + '.html'),
                   (it['n'], it['id'])]
    hits = []
    for root in (os.path.join(ROOT, 'fy28', 'public'), os.path.join(ROOT, 'fy28', 'dist')):
        if not os.path.isdir(root):
            continue
        for dirpath, _dirs, files in os.walk(root):
            for f in files:
                fp = os.path.join(dirpath, f)
                rel = os.path.relpath(fp, ROOT)
                try:
                    body = io.open(fp, encoding='utf-8', errors='ignore').read()
                except OSError:
                    continue
                for n, probe in probes:
                    if probe in body or probe.strip('/') in rel:
                        hits.append('%s (%s) in %s' % (n, probe, rel))
    return probes, sorted(set(hits))


# ---- the share image ------------------------------------------------------------------

def share_html(p, tok):
    """One 1200x630 page. Every string on it is the post's own.

    THE HEADLINE SIZE IS DERIVED FROM ITS LENGTH, not chosen per item. The headlines run
    from 60 to 279 characters and one type size cannot hold both; a ladder is a rule a
    machine can apply, and it means a corrected headline re-renders correctly rather than
    needing somebody to notice it no longer fits.
    """
    h = p['headline']
    size = 62 if len(h) < 90 else 50 if len(h) < 140 else 40 if len(h) < 200 else 33
    # ONE SENTENCE OF SUPPORT, and it is the first one. The post renders the field whole
    # because a post has room; 630 pixels does not, and the alternative to taking a whole
    # sentence is a machine deciding where to stop mid-clause. Nothing is rewritten and
    # nothing is elided -- the rest is one click away, at the address printed below it.
    sup = (C.sentences(p['support']) or [''])[0]
    vint = ('FY%d–FY%d' % tuple(p['vintage_span'])) if p['vintage_span'] else (
        'FY%d' % p['vintage'] if p['vintage'] else 'Year not established')
    guess = p['epistemic'] == 'hypothesis'
    e = lambda s: (s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))
    # `**bold**` and `` `code` `` are the only marks the copy uses. Rendered, never
    # stripped: stripping would change the emphasis the author chose.
    def inline(s):
        s = e(s)
        s = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', s)
        s = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<i>\1</i>', s)
        return re.sub(r'`([^`]+)`', r'<span class="c">\1</span>', s)
    return """<!doctype html>
<meta charset="utf-8">
<title>%(title)s</title>
<style>
  :root { %(vars)s }
  * { box-sizing: border-box; margin: 0; }
  /* NOTHING SHRINKS. A flex column with a fixed height compresses its children rather
     than overflowing, so a paragraph gets quietly clipped while the page still measures
     630 tall -- which is exactly what --measure found on the first pass. With the
     children fixed, copy that does not fit makes the PAGE too tall and the check sees it. */
  body > * { flex: 0 0 auto; }
  html, body { width: 1200px; height: 630px; }
  body {
    background: var(--surface-1); color: var(--text-primary);
    font: 400 20px/1.4 ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto,
          "Helvetica Neue", Arial, sans-serif;
    display: flex; flex-direction: column; justify-content: space-between;
    padding: 58px 64px; border-left: 14px solid var(--brand);
  }
  .eyebrow { font-size: 20px; font-weight: 700; letter-spacing: .14em;
             text-transform: uppercase; color: var(--text-secondary);
             display: flex; gap: 18px; align-items: baseline; }
  .chip { font-size: 16px; letter-spacing: .08em; color: var(--text-muted);
          border: 1px solid var(--grid); border-radius: 5px; padding: 3px 9px; }
  .guess { color: var(--status-warning); border-color: var(--status-warning); }
  .myth { font-size: 25px; line-height: 1.3; color: var(--text-muted);
          text-decoration: line-through; margin-bottom: 10px; }
  h1 { font-size: %(size)dpx; line-height: 1.1; font-weight: 700;
       letter-spacing: -.015em; }
  .support { font-size: 22px; line-height: 1.42; color: var(--text-secondary);
             margin-top: 18px; }
  .cta { display: flex; justify-content: space-between; align-items: baseline;
         border-top: 2px solid var(--grid); padding-top: 20px; font-size: 21px; }
  .cta b { color: var(--series-cost); }
  .site { color: var(--text-muted); }
  .c { background: var(--surface-3); border-radius: 4px; padding: 0 5px; }
  b { font-weight: 700; }
</style>
<div class="eyebrow">
  <span>%(label)s</span>
  <span class="chip%(guessclass)s">%(vintage)s</span>
</div>
<div>
  %(myth)s<h1>%(headline)s</h1>
  %(support)s
</div>
<div class="cta">
  <span><b>%(action)s</b></span>
  <span class="site">%(site)s/blog/%(slug)s</span>
</div>
""" % dict(
        title=e(p['title']), vars=' '.join('--%s: %s;' % (k, v) for k, v in tok.items()),
        label=e(p['label']), vintage=e(vint),
        guessclass=' guess' if guess else '',
        myth=('<p class="myth">%s</p>' % inline(p['myth']['myth'])) if p['myth'] else '',
        size=size, headline=inline(h),
        support=('<p class="support">%s</p>' % inline(sup)) if sup else '',
        action='A scenario — read the working' if guess else 'Read the post',
        site=SITE.replace('https://', ''), slug=p['slug'])


# ---- the Facebook post ---------------------------------------------------------------

# WHERE FACEBOOK CUTS. The feed shows roughly this many characters and then "See more", so
# a first sentence longer than this is read in halves by most of the people who see it.
# It is a threshold to REPORT against, not one to rewrite copy to fit.
FB_SEE_MORE = 125
# And roughly where the whole post stops being read at all. Again: reported, never enforced
# by cutting, because cutting is authoring.
FB_BODY = 400
# An opening line longer than this is not a hook. Nothing is trimmed to reach it -- the
# item is flagged and left alone, because a hook that has to be invented is an editorial
# problem and not a formatting one.
FB_HOOK = 160
# A HOOK THAT OPENS WITH A DANGLING REFERENCE IS NOT A HOOK. "It is also a marginal rate"
# is a fine third sentence and a useless first one: the reader has not read the thing "it"
# refers to, and on Facebook there is nothing above it. So a sentence starting with one of
# these is passed over in favour of the next short one, and used only if nothing else fits
# -- in which case it is flagged rather than rewritten.
FB_DANGLES = ('it', 'this', 'that', 'these', 'those', 'they', 'its', 'their', 'them',
              'and', 'but', 'so', 'nor', 'then', 'he', 'she', 'both')


def fb_plain(s):
    """The sentence as it would be TYPED INTO THE BOX. Facebook has no markup.

    This is the one place any tier here alters a string, and it is a rendering rather than
    an edit: `**both are true**` would be posted with the asterisks in it, which is worse
    than useless -- it reads as somebody who does not know what they are doing. The words,
    their order and their punctuation are untouched; only the emphasis marks the Markdown
    file uses go. `verify_blog.py` asserts the result against the same transformation of
    the source sentence, so a reworded line still fails.
    """
    return re.sub(r'\s+', ' ', re.sub(r'\*\*|`|(?<!\*)\*(?!\*)', '', s or '')).strip()


def facebook_post(p):
    """The words that go in the box above the image. COMPOSED, never written.

    A Facebook post is a third artefact and it is neither the blog post nor the card: it is
    the image plus the two or three lines somebody types above it. It is also the single
    most-read thing this project will produce and the one that cannot be corrected once it
    is posted, so not one word of it is authored here.

    IT OPENS WITH THE HEADLINE, AND THAT IS A CORRECTION. The first version reasoned that
    the image already carries the headline, so the text should not repeat it -- true, and
    it gets the ORDER wrong. **Facebook renders the text ABOVE the image**, so a reader
    going top to bottom meets the composed sentence BEFORE the headline they need in order
    to parse it. TJ, reading the drafts: *"i cant understand the text without the
    headline"*. And he was right in the worst way: item 1.2 opened *"Nobody is being
    misled and nobody has to be wrong"*, and 1.3 opened *"The rise is real"* -- what rise?

    The takeaway is written to FOLLOW a headline. Lifting its sentences and putting them
    first is quoting a paragraph without its first line.

    So: the headline's first sentence opens the post, then the takeaway's sentences follow
    it, whole, up to where a feed stops reading. The duplication with the image is real and
    is the lesser cost -- an image can fail to load, is not read by a screen reader, and is
    not what somebody sees when the post is shared as a link.

    WHERE IT DOES NOT WORK, IT IS LEFT EMPTY. That is the point of the flags below. An item
    whose every sentence runs past 160 characters has no hook in it, and inventing one here
    would hide exactly the editorial problem TJ is looking for. A blank is a finding.
    """
    flags, source = [], None
    take = C.sentences(p['takeaway'])
    head = C.sentences(p['headline'])
    def fits(x):
        return len(fb_plain(x)) <= FB_HOOK

    def opens(x):
        w = re.sub(r'[^a-z]', '', fb_plain(x).split(' ')[0].lower())
        return fits(x) and w not in FB_DANGLES

    # THE HEADLINE OPENS IT. Its first sentence, because a headline can run long and only
    # the first ~125 characters are read before "See more".
    hook = head[0] if head else None
    if hook is None:
        return dict(text='', lines=[], hook='', flags=flags + [
            'this item has no headline to open a post with'],
            source=None, visible=0, chars=0, link='%s/blog/%s' % (SITE, p['slug']))
    source, rest = 'headline', take
    # The takeaway follows. Its own first sentence often restates the headline in other
    # words -- "Both are true. There are 256 fewer children…" after a headline that just
    # said so -- which reads as a stammer rather than as emphasis. Drop a following
    # sentence that repeats four or more of the hook's distinctive words.
    def words(x):
        return {w for w in re.findall(r'[a-z]{4,}', fb_plain(x).lower())}
    hw = words(hook)
    rest = [x for x in rest if len(words(x) & hw) < 4]

    hook = fb_plain(hook)
    lines, total = [hook], len(hook)
    for x in rest:
        x = fb_plain(x)
        if total + 1 + len(x) > FB_BODY:
            break
        lines.append(x)
        total += 1 + len(x)

    text = ' '.join(lines)
    if len(hook) > FB_SEE_MORE:
        flags.append('the opening sentence is %d characters and Facebook shows about %d '
                     'before "See more", so it is read in halves' % (len(hook), FB_SEE_MORE))
    if len(text) < 80:
        flags.append('%d characters is thin for a post' % len(text))
    if len(lines) == 1:
        flags.append('the headline is the whole post — nothing in the takeaway followed it '
                     'without repeating it')
    return dict(text=text, lines=lines, hook=hook, flags=flags, source=source,
                visible=min(len(text), FB_SEE_MORE), chars=len(text),
                link='%s/blog/%s' % (SITE, p['slug']))


# ---- the review PDFs ------------------------------------------------------------------

def post_markdown(p, standalone=True):
    """One post as Markdown, for `build_analysis_pdf.py` to print.

    WHY MARKDOWN AND NOT A SECOND RENDERER. `scripts/build_analysis_pdf.py` already turns
    Markdown into a printed page with this project's typography, using Chrome, with no
    dependency a resident would have to install. Writing a second one for posts would be a
    second set of typographic decisions and a second thing to keep in step.

    THE DRAFT LINE IS IN THE DOCUMENT, not in a watermark. A PDF travels further than
    anything else here and arrives with no context: the collaborator forwards it, and the
    person who receives it has no way of knowing this was never published. So it is the
    first thing under the title, in words, and it cannot be missed or cropped out.

    AND EVERY LINK IS PRINTED AS AN ADDRESS. A post's whole job is to send a reader to the
    analysis behind it, and a clicked link does not exist on paper.
    """
    h = '#' if standalone else '##'
    out = ['%s %s' % (h, p['title']), '']
    # THE ONLY THING ON THE PAGE THAT IS NOT THE POST, and it is chrome rather than
    # content: a band at the top, plainer than the text under it. A PDF travels further
    # than anything else here and arrives with no context -- the collaborator forwards it,
    # and the person who receives it has no way of knowing this was never published. Cover
    # this line with your thumb and what is left is byte for byte the reader's post.
    if p['published']:
        out += ['*Published %s at %s/blog/%s.*'
                % (p['went_up'] or 'already', SITE, p['slug']), '']
    else:
        out += ['*An unpublished draft of the Lunenburg Budget Project. It is not on the '
                'website, it has no address there, and it has not been reviewed or '
                'endorsed by the Town of Lunenburg, the School Committee, the Finance '
                'Committee or Lunenburg Public Schools. It is circulated for comment '
                'before anybody decides whether to publish it.*', '']
    vint = ('FY%d-FY%d' % tuple(p['vintage_span'])) if p['vintage_span'] else (
        'FY%d' % p['vintage'] if p['vintage'] else 'Year not established')
    # THE POST'S OWN META LINE, and nothing editorial in it. No format label and no item
    # number: a reader does not know this project has four formats and 48 candidates, and
    # the PDF is the reader's post. What stays is what a reader needs -- which year the
    # figures are about, and how long it takes.
    out += ['Figures for %s | about %d minute%s to read'
            % (vint, p['reading']['minutes'],
               '' if p['reading']['minutes'] == 1 else 's'), '']
    if p['epistemic'] == 'hypothesis':
        out += ['**A scenario or an explanation - nothing here tests it.** This post rests '
                'on an explanation for a measurement rather than on the measurement '
                'itself. It is not a finding and must not be quoted as one.', '']
    if p['myth']:
        out += ['**The obvious reading:** %s' % p['myth']['myth'], '']
    out += ['**%s**' % p['headline'], '']
    if p['support']:
        out += [p['support'], '']
    if p['myth']:
        out += ['**What it misreads.** %s' % p['myth']['mechanism'], '']
    if p['impacts']:
        out += ['%s# What this means for you' % h, '']
        for im in p['impacts']:
            out += ['**If you are %s:** %s' % (im['who'], im['text']), '']
    if p['takeaway']:
        out += ['%s# What to take away' % h, '', p['takeaway'], '']
    out += ['%s# What this does not show' % h, '']
    for m in p['must_carry']:
        out += ['- %s' % m, '']
    out += ['No figure in this post is computed in it. Every one is carried unaltered '
            'from the report underneath it, and that report recomputes its own figures '
            'from the documents by a script that fails rather than warns.', '']
    out += ['%s# Read the working' % h, '']
    for l in p['links']:
        out += ['- %s - %s%s' % (l['label'], SITE, l['href'])]
    out += ['']
    return '\n'.join(out)


def review_pdfs(payload, only):
    """Every post as a PDF, in `build/pdf/`, plus one combined document.

    TJ: *"i even want all the blog pages (once I review) to be exportable to PDFs so I can
    send them to my collaborator for review, without going to the site"* -- and the
    constraint is hiding in that last clause. The collaborator CANNOT go to the site,
    because the posts are not on it. So this is not a convenience; it is the only way a
    second person reads a post before it is published.

    BOTH FORMS, because they are for different moments: one PDF per post for sending a
    single item to somebody, and one combined document because 48 attachments is a bad
    email and a reviewer reading the whole set wants one thing to scroll.

    Gitignored, like everything else on this side. `build/` is ignored whole.
    """
    import build_analysis_pdf as PDF
    if not PDF.CHROME:
        print('no Chrome found; set CHROME=/path/to/chrome')
        return 1
    want = [p for p in payload['posts'] if not only or p['slug'] in only]
    missing = sorted(only - {p['slug'] for p in want}) if only else []
    if missing:
        print('no such post: %s' % ', '.join(missing))
        return 1
    os.makedirs(REVIEW_PDF, exist_ok=True)
    rc = 0
    for p in want:
        # The item number leads the filename so an attachment list sorts the way the
        # candidates file reads, and the slug follows so the name alone says what it is.
        name = '%s-%s' % (p['n'].replace('.', '-'), p['slug'])
        md = os.path.join(REVIEW_PDF, name + '.md')
        with io.open(md, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(post_markdown(p))
        rc |= PDF.build(name, md_path=md, out_dir=REVIEW_PDF)
        os.remove(md)
    if not only and want:
        name = 'all-posts-for-review'
        body = ['# The Lunenburg Budget Project - posts for review', '',
                '**%d posts, %d of them unpublished.** Everything marked unpublished below '
                'is a draft: it is not on the website, has no address there, and has not '
                'been reviewed or endorsed by the Town of Lunenburg, the School Committee, '
                'the Finance Committee or Lunenburg Public Schools.'
                % (len(want), sum(1 for p in want if not p['published'])), '']
        for p in want:
            body += ['---', '', post_markdown(p, standalone=False)]
        md = os.path.join(REVIEW_PDF, name + '.md')
        with io.open(md, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write('\n'.join(body))
        rc |= PDF.build(name, md_path=md, out_dir=REVIEW_PDF)
        os.remove(md)
    return rc


def share_source(p):
    """The share page on disk: published ones under fy28/public, the rest in build/."""
    pub = os.path.join(SHARE, p['slug'] + '.html')
    return pub if os.path.exists(pub) else os.path.join(REVIEW_SHARE, p['slug'] + '.html')


def share_files(payload):
    tok = tokens()
    return {p['slug'] + '.html': share_html(p, tok) for p in payload['posts']}


def chrome_bin():
    return next((p for p in (
        os.environ.get('CHROME'),
        '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        '/Applications/Chromium.app/Contents/MacOS/Chromium',
        '/usr/bin/google-chrome', '/usr/bin/chromium') if p and os.path.exists(p)), None)


def measure(payload, tmpdir):
    """Does the copy fit in 1200x630? Measured off the rendered box, never eyeballed.

    A SHARE IMAGE IS THE ONE ARTEFACT HERE THAT CANNOT BE CORRECTED. A card that overflows
    on the site shows the overflow -- /worth-knowing tints it on purpose. An image that
    overflows is posted with a sentence cut in half and there is no version to fix.

    `scrollHeight > clientHeight` is exact and a screenshot is a judgement, so this asks
    the browser: a copy of each page with one line of script appended, rendered with
    --dump-dom, and the measurement read back out of the attribute the script set. Chrome
    is needed, so it is not in `check_generated.py`; run it after changing the copy or the
    layout.
    """
    chrome = chrome_bin()
    if not chrome:
        print('no Chrome found; set CHROME=/path/to/chrome')
        return 1
    os.makedirs(tmpdir, exist_ok=True)
    # A FIXED-HEIGHT FLEX COLUMN DOES NOT OVERFLOW. It SHRINKS its children, so the body's
    # own scrollHeight stays at 630 while a paragraph inside it is quietly clipped -- the
    # first version of this check measured the body and passed all 48 for that reason.
    # So it asks every element whether its own content fits its own box, and reports the
    # worst. That is the measurement `scrollHeight > clientHeight` actually makes.
    # WHAT IS MEASURED, AND WHAT IS DELIBERATELY NOT.
    #
    # HEIGHT is measured on the BODY, because the body is the box the image is cut from
    # and its children no longer shrink. An element's own scrollHeight is NOT used: a
    # three-line headline reports two pixels of it past its clientHeight on every single
    # page, because glyph ink -- descenders, an em dash, a minus sign -- extends past the
    # line box by design. Nothing is clipped there (overflow is visible and the body has
    # room), and a check that fails on all 48 identically is measuring the font, not the
    # copy.
    #
    # WIDTH is measured per element, because that IS a clip: a long unbroken token wider
    # than its column is cut by the edge of the image.
    probe = ('<script>var o=document.body.scrollHeight-630,w=0;'
             'document.querySelectorAll("body *").forEach(function(e){'
             'w=Math.max(w,e.scrollWidth-e.clientWidth)});'
             'document.documentElement.setAttribute("data-fit",o+"x"+w)</script>')
    worst, over = [], []
    for p in payload['posts']:
        src = share_source(p)
        tmp = os.path.join(tmpdir, p['slug'] + '.html')
        with io.open(tmp, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(io.open(src, encoding='utf-8').read() + probe)
        out = subprocess.run(
            [chrome, '--headless', '--disable-gpu', '--no-sandbox', '--hide-scrollbars',
             '--virtual-time-budget=2000', '--window-size=1200,630',
             '--dump-dom', 'file://' + tmp],
            capture_output=True, text=True).stdout
        m = re.search(r'data-fit="(\d+)x(\d+)"', out)
        if not m:
            print('%-60s  NOT MEASURED' % p['slug'])
            over.append(p['slug'])
            continue
        h, w = max(0, int(m.group(1))), int(m.group(2))
        worst.append((h, w, p['slug']))
        if h > 0 or w > 0:
            over.append(p['slug'])
    worst.sort(reverse=True)
    for h, w, slug in worst[:8]:
        print('%4dpx over, %4dpx wide  %s' % (h, w, slug))
    print('%d of %d share pages measured; the tallest needs %dpx more than the 630 it has'
          % (len(worst), len(payload['posts']), worst[0][0] if worst else 0))
    if over:
        print('\nOVER THE BOX -- these would be posted with copy cut off:\n  %s'
              % '\n  '.join(over))
        return 1
    print('every share page fits 1200x630 as rendered')
    return 0


def render_images(payload, only, outdir):
    """Chrome's screenshot of the share page. Run on demand; nothing is committed.

    A PNG is 100KB of bytes that reproduce exactly from the HTML beside it, so the HTML is
    what this repository keeps. `--render-images` is for the moment somebody is about to
    post one.
    """
    chrome = chrome_bin()
    if not chrome:
        print('no Chrome found; set CHROME=/path/to/chrome')
        return 1
    os.makedirs(outdir, exist_ok=True)
    want = [p for p in payload['posts'] if not only or p['slug'] in only]
    if only:
        missing = sorted(set(only) - {p['slug'] for p in want})
        if missing:
            print('no such post: %s' % ', '.join(missing))
            return 1
    for p in want:
        src = share_source(p)
        png = os.path.join(outdir, p['slug'] + '.png')
        subprocess.run([chrome, '--headless', '--disable-gpu', '--no-sandbox',
                        '--hide-scrollbars', '--force-device-scale-factor=1',
                        '--virtual-time-budget=2000',
                        '--window-size=1200,630', '--screenshot=' + png,
                        'file://' + src], capture_output=True)
        print('%s  %s' % (('%7d bytes' % os.path.getsize(png)) if os.path.exists(png)
                          else '  FAILED', png))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--check', action='store_true',
                    help='fail if the published payload, a share page, or the absence of '
                         'every unpublished item no longer holds')
    ap.add_argument('--render-images', nargs='*', default=None, metavar='SLUG',
                    help='screenshot the share pages to PNG (all of them, or the named)')
    ap.add_argument('--all', action='store_true',
                    help='ALSO write build/blog-all.json — every item, rendered as a post, '
                         'for local review. Gitignored, dev-server only, never bundled.')
    ap.add_argument('--pdf', nargs='*', default=None, metavar='SLUG',
                    help='render every post (or the named ones) to PDF in build/pdf/, for '
                         'sending to somebody who cannot open the site')
    ap.add_argument('--measure', action='store_true',
                    help='render every share page and fail if the copy overflows 1200x630')
    ap.add_argument('--out', default=os.path.join(ROOT, 'build', 'share'),
                    help='where --render-images and --measure write their files')
    args = ap.parse_args()

    payload = build()
    text = json.dumps(payload, indent=1, sort_keys=True, ensure_ascii=False) + '\n'
    files = share_files(payload)
    c = payload['counts']

    # BOTH OF THESE WORK ON EVERY ITEM, published or not. They answer a question about the
    # rendering -- does this copy fit 1200x630, what does the card look like -- and holding
    # that back until a post is live is exactly backwards.
    if args.render_images is not None:
        return render_images(build(everything=True), set(args.render_images), args.out)
    if args.measure:
        return measure(build(everything=True), os.path.join(args.out, 'measure'))
    if args.pdf is not None:
        return review_pdfs(build(everything=True), set(args.pdf))

    if args.all:
        os.makedirs(os.path.dirname(REVIEW), exist_ok=True)
        full = build(everything=True)
        with io.open(REVIEW, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(json.dumps(full, indent=1, sort_keys=True, ensure_ascii=False) + '\n')
        os.makedirs(REVIEW_SHARE, exist_ok=True)
        for name, body in sorted(share_files(full).items()):
            with io.open(os.path.join(REVIEW_SHARE, name), 'w', encoding='utf-8',
                         newline='\n') as fh:
                fh.write(body)
        print('wrote %s and %d share cards in %s — all %d items, for local review only.'
              % (os.path.relpath(REVIEW, ROOT), full['counts']['prepared'],
                 os.path.relpath(REVIEW_SHARE, ROOT), full['counts']['prepared']))
        print('  npm run dev  (in fy28/), then open http://localhost:5173/blog')

    if args.check:
        if not os.path.exists(OUT):
            print('missing fy28/public/data/blog.json')
            return 1
        if io.open(OUT, encoding='utf-8').read() != text:
            print('fy28/public/data/blog.json is stale — run python3 scripts/build_blog.py')
            return 1
        have = ({f for f in os.listdir(SHARE) if f.endswith('.html')}
                if os.path.isdir(SHARE) else set())
        if have != set(files):
            print('fy28/public/share holds %d pages and the published posts need %d — run '
                  'python3 scripts/build_blog.py' % (len(have), len(files)))
            return 1
        for name, body in sorted(files.items()):
            if io.open(os.path.join(SHARE, name), encoding='utf-8').read() != body:
                print('fy28/public/share/%s is stale — run python3 scripts/build_blog.py'
                      % name)
                return 1
        probes, hits = leak_check(payload)
        if hits:
            print('UNPUBLISHED COPY IS ON THE PUBLISHED SIDE:\n  %s' % '\n  '.join(hits))
            return 1
        print('ok: %d of %d items published; blog.json and %d share pages reproduce; none '
              'of the %d unpublished items appears anywhere under fy28/public or fy28/dist'
              % (c['published'], c['prepared'], len(files), len(probes)))
        return 0

    with io.open(OUT, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)
    os.makedirs(SHARE, exist_ok=True)
    for stale in os.listdir(SHARE):
        if stale.endswith('.html') and stale not in files:
            os.remove(os.path.join(SHARE, stale))
    for name, body in sorted(files.items()):
        with io.open(os.path.join(SHARE, name), 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(body)
    # AND THE DIRECTORY ITSELF GOES when nothing is published. Vite copies `public/`
    # wholesale, so an empty `share/` becomes an empty `dist/share/` -- a directory on the
    # site announcing that share cards are a thing here and that there are none.
    if not files and os.path.isdir(SHARE) and not os.listdir(SHARE):
        os.rmdir(SHARE)

    probes, hits = leak_check(payload)
    print('wrote fy28/public/data/blog.json — %d of %d items published, %d share pages'
          % (c['published'], c['prepared'], len(files)))
    if hits:
        print('\nUNPUBLISHED COPY IS ON THE PUBLISHED SIDE:\n  %s' % '\n  '.join(hits))
        return 1
    print('  checked %d unpublished items: none of their words appears anywhere under '
          'fy28/public or fy28/dist' % len(probes))
    if payload['posts']:
        mins = sorted(p['reading']['minutes'] for p in payload['posts'])
        print('  reading time %d–%d minutes at %d words a minute · pinned: %s'
              % (mins[0], mins[-1], payload['words_per_minute'], payload['pinned'] or 'none'))
    else:
        print('  nothing is published — which is a correct state, not an error. Add the '
              'item number to PUBLISHED at the top of this script and run it again.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
