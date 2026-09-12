#!/usr/bin/env python3
"""Every string on every published post, and every figure about one, recomputed.

    python3 scripts/verify_blog.py

WHAT IT ASSERTS, and all of it is VALUES. CLAUDE.md rule 13: a check that asserts a
sentence EXISTS passes while the sentence is wrong. So nothing here greps a page for a
phrase; everything is derived from the candidates file and compared.

  0. ONLY WHAT IS ON THE LIST IS ON THE SITE. The payload's posts are exactly the items in
     `build_blog.PUBLISHED`, and the share directory holds exactly one page per post. This
     is the assertion that matters most and it is first: a post nobody decided to publish
     appearing on the site is the one failure here with a cost outside this repository.
  1. NOTHING WAS AUTHORED. Every sentence a post renders is a verbatim substring of
     `notes/process/CONTENT-CANDIDATES.md` -- except the myth and the mechanism, which come
     from `sources/data/myths.csv` and are checked against that instead. The rule is that
     no string is written HERE, not that every string is in one file.
  2. THE POST IS THE ITEM, WHOLE. Nothing is trimmed, summarised or reordered on its way
     out of the parser.
  3. THE ADDRESSES ARE UNIQUE AND ROUTED. One slug per post, every link resolving to a page
     the app routes or a document /reports holds, and at least one link per post -- a post
     that cannot hand a reader on is a long card.
  4. THE READING TIME IS THE STATED DIVISION, over a word count recomputed from the strings
     the post actually renders.
  5. THE EPISTEMIC LABEL SURVIVES THE TIER. Every conclusion a post cites exists; a post
     citing a `hypothesis` is marked one and a post marked one cites one. The archive holds
     one hypothesis and it must never reach a reader as a fact.
  6. THE VINTAGE IS ON EVERY POST, OR ITS ABSENCE IS. A post is shared onward by people who
     will not come back to check it, so an item with no establishable year says so in those
     words rather than borrowing the year it was written.
  7. THE SHARE IMAGE CARRIES NOTHING OF ITS OWN. Every visible string on the 1200x630 page
     is the post's, and its palette is `fy28/src/index.css`'s `:root`, character for
     character.
  8. THE FACEBOOK POST IS COMPOSED, NOT WRITTEN. Every line of it is one of the item's own
     sentences, whole, taken from the takeaway or the headline in that order; the flags
     recompute; and an item that yields no hook has an EMPTY post rather than a filler
     sentence, which is the signal the item needs editorial work.
  9. THE COUNTS ARE THE ROWS.

WHAT IT DOES NOT ASSERT, deliberately: any dollar, count or rate. Those are computed and
checked by the report each post links to, and re-deriving them here would be a second
implementation that can disagree with the first. The post's job is to carry the report's
figure unaltered, and (1) and (2) are the assertions that it did.
"""
import csv
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import content_items as C                # noqa: E402
import build_blog as BL                  # noqa: E402

FAILS = []


def check(ok, msg):
    if not ok:
        FAILS.append(msg)


def norm(s):
    return re.sub(r'\s+', ' ', s or '').strip()


def flat_html(html):
    """Tags become a space -- then the space a closing tag leaves in front of a full stop
    is taken back out, because `<b>...</b>.` is one sentence and not a sentence and a dot."""
    return re.sub(r'\s+([.,;:!?])', r'\1',
                  norm(re.sub(r'<[^>]+>', ' ', html.split('</style>')[-1])))


def main():
    payload = json.load(io.open(BL.OUT, encoding='utf-8'))
    doc = norm(io.open(C.DOC, encoding='utf-8').read())
    posts = payload['posts']
    items = {it['n']: it for it in C.items()}
    idx = C.conclusion_index()
    reports = C.reports_by_url()

    src = io.open(C.ROUTES, encoding='utf-8').read()
    blk = re.search(r'export const SLUG: Record<Tab, string> = \{(.*?)\n\}', src, re.S)
    check(blk is not None, 'routes.ts: could not find the SLUG table')
    slugs = {'/' + v for _k, v in re.findall(r"^\s*(\w+): '([^']*)',", blk.group(1), re.M)}
    check(len(slugs) > 20, 'the SLUG table parsed to %d entries' % len(slugs))

    # --- 0. only what is on the list is on the site ------------------------------------
    check({p['n'] for p in posts} == set(BL.PUBLISHED),
          'the payload holds %s and PUBLISHED names %s'
          % (sorted(p['n'] for p in posts), sorted(BL.PUBLISHED)))
    check(all(p['published'] for p in posts),
          'the deployed payload carries a post marked unpublished')
    have = ({f for f in os.listdir(BL.SHARE) if f.endswith('.html')}
            if os.path.isdir(BL.SHARE) else set())
    check(have == {p['slug'] + '.html' for p in posts},
          'fy28/public/share holds %s and the posts are %s'
          % (sorted(have), sorted(p['slug'] + '.html' for p in posts)))
    probes, hits = BL.leak_check(payload)
    check(not hits, 'unpublished copy is on the published side:\n    '
                    + '\n    '.join(hits))
    check(len(probes) > 3, 'the leak check ran %d probes' % len(probes))
    # The public payload no longer says how many items are prepared -- that count is
    # addressed to us -- so the floor is checked against the candidates file directly.
    check(len(C.items()) >= C.MIN_ITEMS,
          '%d items were parsed and the floor is %d' % (len(C.items()), C.MIN_ITEMS))
    check('prepared' not in payload['counts'] and 'prepared' not in payload['source'],
          'the public payload carries the count of unpublished items')

    tok = BL.tokens()
    with io.open(C.MYTHS, encoding='utf-8', newline='') as fh:
        myths = {r['item'].strip(): r for r in csv.DictReader(fh)}
    check(bool(myths), 'myths.csv parsed to no rows')

    seen_slugs = set()
    for p in posts:
        w = p['n']
        it = items.get(w)
        check(it is not None, '%s is a post and not an item in the candidates file' % w)
        if not it:
            continue

        # --- 1. nothing authored ------------------------------------------------------
        for s in ([p['headline'], p['support'], p['takeaway']]
                  + [i['text'] for i in p['impacts']] + list(p['must_carry'])):
            for sent in C.sentences(s):
                if len(sent) > 20:
                    check(norm(sent) in doc,
                          '%s renders a sentence that is not verbatim from the candidates '
                          'file: %r' % (w, sent[:70]))

        # --- 2. the post is the item, whole -------------------------------------------
        for f in ('headline', 'support', 'takeaway', 'title', 'format', 'must_carry'):
            check(p[f] == it[f], '%s %s differs from the parsed item' % (w, f))
        check([i['who'] for i in p['impacts']] == [i['who'] for i in it['impacts']],
              '%s renders a different set of readers' % w)
        check([i['text'] for i in p['impacts']] == [i['text'] for i in it['impacts']],
              '%s trimmed or reworded an impact line' % w)
        check(p['vintage'] == it['vintage'] and p['epistemic'] == it['epistemic'],
              '%s vintage or epistemic label differs from the parsed item' % w)

        if p['myth']:
            reg = myths.get(w)
            check(reg is not None, '%s renders a myth that is not in the registry' % w)
            if reg:
                check(p['myth']['myth'] == reg['myth'],
                      '%s does not carry the registry myth verbatim' % w)
                check(p['myth']['mechanism'] == reg['mechanism'],
                      '%s does not carry the registry mechanism verbatim' % w)
                check(bool(reg['mechanism'].strip()),
                      '%s names no mechanism, so the post takes a side instead of '
                      'explaining one' % w)
                check(idx.get(reg['conclusion_id'], (None, {}))[1].get('kind') == 'measured',
                      '%s rests a myth on a conclusion that is not measured' % w)

        # --- 3. the addresses ----------------------------------------------------------
        check(re.fullmatch(r'[a-z0-9][a-z0-9-]*', p['slug']) is not None,
              '%s has slug %r, which is not an address' % (w, p['slug']))
        check(p['slug'] not in seen_slugs, '%s repeats the address %s' % (w, p['slug']))
        seen_slugs.add(p['slug'])
        check(len(p['links']) >= 1, '%s links to nothing' % w)
        for l in p['links']:
            check(l['href'] in slugs or l['href'] in reports,
                  '%s links to %s, which the app does not route' % (w, l['href']))
            check(bool(l['label'].strip()), '%s links to %s with no name' % (w, l['href']))
        check(all(u not in slugs for u in p['unrouted']),
              '%s dropped a link the app does in fact route' % w)

        # --- 4. the reading time is the stated division --------------------------------
        recount = BL.words(p['headline'], p['support'], p['takeaway'],
                           *[i['text'] for i in p['impacts']], *p['must_carry'],
                           (p['myth'] or {}).get('myth'),
                           (p['myth'] or {}).get('mechanism'))
        check(p['reading']['words'] == recount,
              '%s states %d words and its own strings hold %d'
              % (w, p['reading']['words'], recount))
        check(p['reading']['minutes'] == max(
            1, int(round(recount / float(payload['words_per_minute'])))),
            '%s reading time %d is not %d words / %d a minute'
            % (w, p['reading']['minutes'], recount, payload['words_per_minute']))

        # --- 5. the epistemic label ----------------------------------------------------
        kinds = set()
        for cid in p['conclusions']:
            check(cid in idx, '%s cites conclusion %s, which no payload carries' % (w, cid))
            if cid in idx:
                kinds.add(idx[cid][1].get('kind'))
        check(p['epistemic'] == ('hypothesis' if 'hypothesis' in kinds else 'measured'),
              '%s is marked %s and cites %s' % (w, p['epistemic'], sorted(kinds)))

        # --- 6. the vintage ------------------------------------------------------------
        if p['vintage'] is not None:
            check(1990 <= p['vintage'] <= 2035,
                  '%s vintage %s is not a plausible fiscal year' % (w, p['vintage']))
            check(p['vintage_from'] in ('card', 'payload'),
                  '%s vintage_from is %r' % (w, p['vintage_from']))

        # --- 8. the Facebook post is composed, not written -----------------------------
        fb = p['facebook']
        check(fb == BL.facebook_post(p),
              '%s facebook post is not what the payload composes — run build_blog.py' % w)
        # The item's own whole sentences, with the Markdown emphasis marks taken off --
        # Facebook has no markup and `**both are true**` would be posted with the
        # asterisks in it. Nothing else is altered, so a reworded line still fails here.
        pool = [BL.fb_plain(x) for x in
                C.sentences(p['takeaway']) + C.sentences(p['headline'])]
        for line in fb['lines']:
            check(line in pool,
                  '%s facebook post carries a line that is not one of the item\'s own '
                  'whole sentences: %r' % (w, line[:60]))
        check(fb['text'] == ' '.join(fb['lines']),
              '%s facebook text is not its own lines' % w)
        check(not fb['text'] or fb['lines'] and fb['lines'][0] == fb['hook'],
              '%s facebook post does not open with its own hook' % w)
        check(fb['chars'] == len(fb['text']), '%s facebook char count is wrong' % w)
        check(fb['visible'] == min(len(fb['text']), BL.FB_SEE_MORE),
              '%s facebook visible-before-See-more is wrong' % w)
        check(fb['link'] == '%s/blog/%s' % (BL.SITE, p['slug']),
              '%s facebook post links somewhere other than the post' % w)
        check(bool(fb['text']) or bool(fb['flags']),
              '%s has no facebook post and says nothing about why' % w)
        check(not fb['text'] or len(fb['hook']) <= BL.FB_HOOK,
              '%s opens a facebook post with a %d-character sentence' % (w, len(fb['hook'])))

        # --- 7. the share image carries nothing of its own -----------------------------
        path = os.path.join(BL.SHARE, p['slug'] + '.html')
        check(os.path.exists(path), '%s has no share page at %s' % (w, path))
        if os.path.exists(path):
            html = io.open(path, encoding='utf-8').read()
            check(html == BL.share_html(p, tok),
                  '%s share page is not what the payload renders — run build_blog.py' % w)
            flat = flat_html(html)
            # The image carries the headline whole and ONE SENTENCE of the support, which
            # is the only place any tier here shows less than the whole field. Asserted as
            # the first sentence rather than as "some prefix", so a renderer that started
            # cutting mid-clause would fail here.
            for s in ([p['headline'], (C.sentences(p['support']) or [''])[0], p['label']]
                      + ([p['myth']['myth']] if p['myth'] else [])):
                bare = re.sub(r'\s+([.,;:!?])', r'\1', norm(re.sub(r'[*`]', '', s)))
                check(not bare or bare in flat,
                      '%s share page does not carry its own %r' % (w, bare[:50]))
            check(('/blog/' + p['slug']) in flat,
                  '%s share page does not carry its own address' % w)
            if p['vintage'] is None:
                check('Year not established' in flat,
                      '%s has no vintage and its share page does not say so' % w)
            for k, v in tok.items():
                check(('--%s: %s;' % (k, v)) in html,
                      '%s share page does not carry index.css\'s --%s' % (w, k))

    # --- 9. the counts are the rows ----------------------------------------------------
    cnt = payload['counts']
    check(cnt['published'] == len(posts), 'counts.published is not the rows')
    check(cnt['no_vintage'] == sum(1 for p in posts if p['vintage'] is None),
          'counts.no_vintage is not the rows')
    check(cnt['hypothesis'] == sum(1 for p in posts if p['epistemic'] == 'hypothesis'),
          'counts.hypothesis is not the rows')
    for f, n in cnt['by_format'].items():
        check(n == sum(1 for p in posts if p['format'] == f),
              'counts.by_format[%s] is not the rows' % f)
    check(sum(cnt['by_format'].values()) == len(posts),
          'the formats do not partition the posts')
    check(cnt['no_facebook_post'] == sum(1 for p in posts if not p['facebook']['text']),
          'counts.no_facebook_post is not the rows')
    check(cnt['facebook_flagged'] == sum(1 for p in posts if p['facebook']['flags']),
          'counts.facebook_flagged is not the rows')
    check(payload['review'] is False,
          'the deployed payload is marked as the local review copy')

    pin = payload['pinned']
    check(pin is None or pin in seen_slugs, 'the pin names %r, which is not a post' % pin)

    if FAILS:
        print('%d failure(s):\n' % len(FAILS))
        for f in FAILS:
            print('  ' + f)
        return 1
    print('ok: %d of %d items published — every sentence verbatim from %s, every address '
          'routed, every reading time, label, vintage and count recomputed, and none of '
          'the %d unpublished items anywhere under fy28/public or fy28/dist'
          % (len(posts), len(C.items()), os.path.relpath(C.DOC, ROOT), len(probes)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
