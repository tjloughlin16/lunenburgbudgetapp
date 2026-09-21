#!/usr/bin/env python3
"""Who held every town post, board by board, out of the annual report's personnel listing.

TJ, 21 September 2026, after I reported that the annual reports carry no organisational
charts: *"org charts DO exist in annual reports... its not called an org chart. its
personell listing for each department and board"*. He was right. I had grepped for
`organizational chart`, found nothing in five years, and reported my matcher's failure as
a fact about the town -- rule 13c, for the sixth time -- when the thing itself runs to
nine or ten pages in every book under ELECTED OFFICIALS and APPOINTED OFFICIALS, and was
already catalogued in our own extraction plan with per-year notes I had not read.

**WHY THIS IS WORTH READING.** A budget line that falls is not a cut, and a cut is a
service reduction. The nearest published thing to a service level is who the town employs
and appoints, and the wage list stopped naming departments after FY2016. This listing did
not stop: it names every board, every appointed post and every holder, with the year their
term runs out, for every year we hold.

**THE HEADING STATES THE BOARD'S SIZE, so the page checks itself.** `COUNCIL ON AGING-(11
members) 3 year term` is followed by eleven names. That is an identity the document states
about itself, exactly like a printed grand total, and it is the difference between reading
this listing and guessing at it: eighteen to twenty headings a year carry one. A board
whose names do not come to its stated size is reported rather than published.

**AND THE FORMAT IS NOT THE SAME EVERY YEAR** -- TJ again, before a line of this was
written: *"just make sure you dont assume this format is the same for every year"*.
FY2022 and FY2023 open the listing on page 7; FY2025 on page 10. FY2023 began adding
`-appointed 9/2023` notes after a name. So the page range is discovered from the headings
rather than hardcoded, and a year that produces no `(N members)` heading at all is refused
rather than trusted, because that is the signature of a layout this does not understand.

    python3 scripts/extract_personnel.py            # every year it can find
    python3 scripts/extract_personnel.py --check    # ...and fail if a stated size disagrees
"""

import argparse
import collections
import csv
import glob
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = os.path.join(ROOT, 'sources', 'town-budget', 'pages')
OUT = os.path.join(ROOT, 'sources', 'data', 'town-personnel.csv')

SECTION = re.compile(r'^(ELECTED|APPOINTED)\s+OFFICIALS\b', re.I)
SIZE = re.compile(r'\(\s*(?:no less than \d+ and no more than\s*)?(\d+)\s*members?\s*\)', re.I)
TERM = re.compile(r'[-–]\s*(20\d\d)\s*$')
APPOINTED_NOTE = re.compile(r'[-–]\s*(appointed|resigned|retired|deceased|term|vacan)', re.I)
PAGENO = re.compile(r'^\d{1,3}$')


def raw_pages(path):
    """{page: [line, ...]} with the `  12|` gutter taken off and COLUMNS PRESERVED."""
    page, out = None, collections.defaultdict(list)
    for raw in open(path, encoding='utf-8', errors='replace'):
        m = re.match(r'^===PAGE (\d+)===', raw)
        if m:
            page = int(m.group(1))
            continue
        if page is not None:
            out[page].append(re.sub(r'^\s*\d+\|', '', raw.rstrip('\n')))
    return out


def split_columns(lines):
    """One stream per printed COLUMN, with the gutter MEASURED off the page.

    Two or three of the nine listing pages in every year are set in two columns, and a
    line-based reader runs them together: FY2022 page 9 prints `ANIMAL CONTROL OFFICER`
    beside `ANIMAL INSPECTOR`, and read as one line it is one post with the wrong name and
    two people's worth of names beneath it. `FINANCE COMMITTEE (7 members)` came out with
    ZERO members that way -- its seven names were in the other column.

    The gutter is not guessed. Take the share of lines blank at each character position,
    and a run of six or more positions blank on 97% of them, away from the margins, is the
    gap between columns. Rule 13b for a page with no boxes: measure it, do not tune a
    constant. A page with no such run is one column and is left alone.
    """
    body = [l for l in lines if l.strip()]
    if len(body) < 6:
        return [lines]
    width = max(len(l) for l in body)
    blank = [sum(1 for l in body if i >= len(l) or l[i] == ' ') / len(body)
             for i in range(width)]
    runs, cur = [], 0
    for i, f in enumerate(blank + [0.0]):
        if f >= 0.97:
            cur += 1
            continue
        if cur >= 6 and width * 0.25 < i - cur / 2 < width * 0.75:
            runs.append(i - cur)
        cur = 0
    if not runs:
        return [lines]
    cuts = [0] + runs + [width]
    return [[l[a:b] for l in lines] for a, b in zip(cuts, cuts[1:])]


def lines_of(path):
    """(page, section, text) in READING ORDER: each column of each page, top to bottom.

    THE REPORT ALREADY SAYS WHETHER A POST IS ELECTED OR APPOINTED, and I threw it away.
    The listing is printed in two sections with a running header on every page -- ELECTED
    OFFICIALS, then APPOINTED OFFICIALS -- and I was matching that header only to skip it.

    TJ, on being told we could not tell how these posts are filled: *"its not OUR
    classification. its theirs."* and *"we KNOW the select board is elected. We know the
    finance committted is appointed. we know the superintendent of shcools is hired."* He
    is right twice over: it is a known fact about how the town works, and the town prints
    it. Inventing an `our_kind` column for it was hedging about something the document
    states on every single page.
    """
    for page, lines in sorted(raw_pages(path).items()):
        head = next((l.strip() for l in lines if l.strip()), '')
        m = SECTION.match(head)
        section = m.group(1).lower() if m else ''
        for col in split_columns(lines):
            for t in col:
                if t.strip():
                    yield page, section, t.strip()


TERMLEN = re.compile(r'\b\d+\s*year\s*term\b', re.I)


def is_heading(t):
    """A POST says how it is constituted. A PERSON does not.

    The first version of this tested CASE -- capitals are a post, title case is a person --
    and TJ had already warned that the format is not the same every year. It is not: the
    APPOINTED pages print `INSPECTOR OF WIRING`, and the ELECTED pages print `Board of
    Assessors - (3 members) 3 year term`, so a case test reads an entire page of the
    listing as one long list of people under no post at all.

    What every heading carries, in both styles and all four years, is its own constitution:
    `(3 members)`, `3 year term`, or both. That is the same kind of signal as a printed
    total -- the document saying what it is about to show -- and it does not care how the
    year chose to set the type. Capitals stay as a second test, because a single-holder
    post like `DPW DIRECTOR` has no membership to state.

    It also makes `Associate Members—(2) 2 year term` a post in its own right, which is
    what it is: the Agricultural Commission states five members and lists four plus two
    associates, and reading the associates into the commission was what made it nine.
    """
    if SIZE.search(t) or TERMLEN.search(t):
        return True
    head = post_name(t)
    letters = [c for c in head if c.isalpha()]
    if len(letters) < 3:
        return False
    upper = sum(1 for c in letters if c.isupper()) / len(letters)
    return upper > 0.85 and bool(re.search(r'[A-Z]{3}', head))


def post_name(t):
    return re.sub(r'\s+', ' ', TERMLEN.sub('', SIZE.sub('', t))).strip(' -–,()')


def listing_pages(path):
    """The pages of the listing itself, found from its RUNNING HEADER.

    `ELECTED OFFICIALS` and `APPOINTED OFFICIALS` are printed at the top of every page of
    the listing and nowhere else -- except the contents page, which names them in a list
    of sections. So the test is not that the words appear on the page, it is that they are
    the FIRST thing on it. Taking any page that mentions them pulled in the contents page
    and then, because the range was filled in between, twenty pages of departmental prose:
    FY2022 came out with 1,104 people in a nine-page listing.
    """
    first, pages = {}, set()
    for page, _sec, t in lines_of(path):
        first.setdefault(page, t)
    for page, t in first.items():
        if SECTION.match(t):
            pages.add(page)
    return pages


def close_post(rows, post, stated, seen, problems, fy):
    """Stamp every row of the post just finished with what its own heading proves.

    THREE STATES, NEVER TWO, for the same reason the annual-report extracts have three:
    `checked` where the heading states a size and that many people are named; `check
    failed` where it states one and a different number are named; `no check` where the
    heading states no size at all, which is most single-holder posts and is not a doubt
    about the reading. Nothing may be counted without splitting on this column -- a board
    listing six people against five seats is usually a mid-year replacement printed beside
    the person it replaced, and summing it as six inflates the town.
    """
    if not post:
        return
    state = ('no check' if stated is None
             else 'checked' if seen == stated else 'check failed')
    for r in rows:
        if r['post'] == post and r['fy'] == fy and not r['size_check']:
            r['size_check'] = state
    if state == 'check failed':
        problems.append(f'FY{fy} {post}: states {stated} members, {seen} named')


def read_year(fy, path):
    rows, problems = [], []
    keep = listing_pages(path)
    if not keep:
        return [], []
    post, stated, seen, kind = None, None, 0, ''
    order = 0
    for page, section, t in lines_of(path):
        if page not in keep:
            continue
        if PAGENO.match(t) or SECTION.match(t):
            continue
        if is_heading(t):
            close_post(rows, post, stated, seen, problems, fy)
            m = SIZE.search(t)
            # A POST THAT STATES A MEMBERSHIP IS A BOARD SEAT; one that does not is an
            # OFFICER. That is the document's own distinction -- `Board of Assessors - (3
            # members) 3 year term` against `DPW DIRECTOR` -- and it is the only one here
            # that is read rather than assumed. It is NOT paid against unpaid: this listing
            # never says what anybody is paid, and the wage list stopped naming departments
            # after FY2016, so any split on salary would be us inventing one. Rule 7.
            kind = 'board seat' if (m or TERMLEN.search(t)) else 'officer'
            # elected + board seat -> a seat the voters fill.
            # appointed + board seat -> a seat the Select Board fills: a volunteer member.
            # appointed + officer   -> a post somebody is HIRED into: the Town Manager,
            #                          the DPW Director, the Superintendent's office.
            # All three are the town's own distinction, read off the section header and
            # off whether the post states a membership.
            post, stated, seen = post_name(t), int(m.group(1)) if m else None, 0
            continue
        if not post:
            continue
        kind = kind if post else ''
        # A person. The term year and any note travel with them, never into the name.
        term = TERM.search(t)
        note = ''
        name = t
        if term:
            name = t[:term.start()].strip(' -–')
        elif APPOINTED_NOTE.search(t):
            i = APPOINTED_NOTE.search(t).start()
            name, note = t[:i].strip(' -–'), t[i:].strip(' -–')
        if len(re.findall(r'[A-Za-z]', name)) < 3:
            continue
        seen += 1
        order += 1
        rows.append({'fy': fy, 'page': page, 'order': order, 'post': post,
                     'section': section, 'kind': kind, 'stated_members': stated if stated is not None else '',
                     'person': re.sub(r'\s+', ' ', name),
                     'term_expires': term.group(1) if term else '', 'note': note,
                     'size_check': ''})
    close_post(rows, post, stated, seen, problems, fy)
    return rows, problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--since', type=int, default=2022)
    args = ap.parse_args()

    rows, problems, refused = [], [], []
    for path in sorted(glob.glob(os.path.join(PAGES, 'FY*.ocr.txt'))):
        m = re.search(r'FY(\d{4})\.ocr', path)
        if not m or int(m.group(1)) < args.since:
            continue
        fy = int(m.group(1))
        got, probs = read_year(fy, path)
        # A YEAR WITH NO STATED SIZE ANYWHERE IS A LAYOUT WE DO NOT UNDERSTAND, not a year
        # with no boards. Every year read so far prints eighteen to twenty of them.
        if not any(r['stated_members'] for r in got):
            refused.append(f'FY{fy}: no `(N members)` heading found — layout not recognised')
            continue
        rows += got
        problems += probs

    by_fy = collections.Counter(r['fy'] for r in rows)
    posts = collections.Counter(fy for fy, _ in {(r['fy'], r['post']) for r in rows})
    checked = sum(1 for r in rows if r['stated_members'])
    print(f'{len(rows)} people across {len(by_fy)} years')
    for fy in sorted(by_fy):
        print(f'  FY{fy}: {by_fy[fy]:4} people in {posts[fy]:3} posts')
    print(f'  {checked} of {len(rows)} sit under a post that states its own size')
    for r in refused:
        print(f'  REFUSED {r}')
    for p in problems[:14]:
        print(f'  MISMATCH {p}')
    if len(problems) > 14:
        print(f'  ...and {len(problems) - 14} more')

    state = collections.Counter(r['size_check'] for r in rows)
    kinds = collections.Counter(f"{r['section']} {r['kind']}" for r in rows)
    print('  by check: ' + ', '.join(f'{v} {k}' for k, v in state.most_common()))
    print('  by kind : ' + ', '.join(f'{v} {k}' for k, v in kinds.most_common()))
    if args.check and refused:
        raise SystemExit(1)
    with open(OUT, 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=['fy', 'page', 'order', 'post', 'kind',
                                           'section', 'stated_members', 'person',
                                           'term_expires', 'note', 'size_check'])
        w.writeheader()
        w.writerows(rows)
    print(f'wrote {os.path.relpath(OUT, ROOT)}')


if __name__ == '__main__':
    main()
