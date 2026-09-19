#!/usr/bin/env python3
"""WHAT TOWN MEETING ACTUALLY DID, from the Town Clerk's own record in the annual reports.

    python3 scripts/extract_town_meeting_votes.py --fy 2025
    python3 scripts/extract_town_meeting_votes.py --all
    python3 scripts/extract_town_meeting_votes.py --check

WHY THIS EXISTS. Town Meeting is the town's legislative body and every thread ends there --
Kids Kingdom, the fourth fire shift and the solid-waste enterprise fund were all settled on
one Saturday in May 2026. **The town publishes no results document.** There is a warrant
(the questions) and a legal notice, and then nothing until the annual report carries the
Clerk's record of the proceedings about a year later.

That record has been in this archive the whole time. `annual-report-contents.csv` catalogues
a `town_meeting` section in EVERY report FY2011-FY2025, with page ranges -- and marks it
`(not tabular)`, "votes and articles -- prose, not a table", which is why no extractor ever
ran on it. The same reason the placement counts went unread for fifteen years: prose with no
heading naming it.

WHAT IT PRODUCES, and what it does not. One row per article per Town Meeting: the article
number, what it was about, the outcome as the Clerk printed it, and the Finance Committee
and Select Board recommendations where the report carries them. The `quote` column holds the
Clerk's own sentence, VERBATIM, and `--check` fails if it is not in the source page.

TWO RECORDS OF ONE VOTE, and they are merged, not averaged. TJ, 19 September 2026: "the
votes follow the same pattern for town meeting. We accept the transcript version, then when
we get the official version we merge." So:

  * OUR minutes of the recording (`sources/data/recording-minutes/town-meeting/`) are what
    we have CONTEMPORANEOUSLY, written from machine captions. A caption model hears
    "fifteen hundred", "$1,500" and "$50" alike, and rule 13a calls that a derived thing.
  * THIS is the official record, printed by the Clerk, and it supersedes -- it does not
    average with, and it does not silently overwrite. Where the two disagree the
    disagreement is the finding, which is `reconcile_minutes.py`'s existing pattern.

The lag is the whole problem and it points the wrong way for anybody tracking a live
matter: this route covers everything up to the last published annual report and nothing
since. FY2025 is the newest. The 2 May 2026 Annual Town Meeting is not in it.
"""
import argparse
import collections
import csv
import datetime as dt
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from write_recording_minutes import NODE22   # noqa: E402

CONTENTS = os.path.join(ROOT, 'sources', 'data', 'annual-report-contents.csv')
CATALOGUE = os.path.join(ROOT, 'sources', 'data', 'annual-report-catalogue.csv')
TEXT_DIR = os.path.join(ROOT, 'sources', 'town-annual-reports', 'text')
OUT = os.path.join(ROOT, 'sources', 'data', 'town-meeting-votes.csv')
MODEL = 'sonnet'

COLS = ['fy', 'meeting', 'meeting_date', 'article', 'subject', 'result',
        'amount_as_printed', 'fincom', 'select_board', 'quote', 'page',
        'source_doc', 'extracted_by', 'extracted_at']

SYSTEM = """You read the TOWN MEETING PROCEEDINGS printed in a Massachusetts town's annual report, and extract one record per ARTICLE voted.

The Town Clerk writes these as prose. A typical article reads:

  ARTICLE 6: To see if the Town will vote to transfer from available funds, all sums of money necessary to amend the amounts voted for the Town's FY 2025 Budget ... or take any other action relative thereto. UNANIMOUS VOICE VOTE to PASS OVER Article 6. Finance Committee and Select Board recommend Approval to pass over Article 6.

Rules:
- One record per article. If the same article number appears under two different Town Meetings in the report (an Annual and a Special), that is two records.
- `meeting` is 'annual' or 'special'. `meeting_date` is the date of that Town Meeting as printed, YYYY-MM-DD, or null if the section does not state it.
- `subject`: what the article was about, in one plain clause under 120 characters, in your own words. Not the full article text.
- `result`: exactly one of passed, failed, passed_over, indefinitely_postponed, withdrawn, amended_and_passed, no_action, unclear. Use 'unclear' when the printed text does not say -- never guess.
- `amount_as_printed`: the sum the article appropriates or transfers, copied EXACTLY as printed ("$325,000", "$1,558,447.62"). Null if no sum is stated. Do not compute, convert or total anything.
- `fincom` and `select_board`: what each body recommended, as printed -- 'Approval', 'Disapproval', 'No recommendation', or null if the report does not say for this article. These are often printed together in one sentence for both bodies; in that case record the same value for each.
- `quote`: the Clerk's OWN sentence recording the outcome, copied VERBATIM and exactly, including capitalisation and punctuation. This is checked character-for-character against the source and a paraphrase is a failure. Keep it under 300 characters; if the sentence is longer, STOP COPYING mid-sentence. Do not add a full stop, an ellipsis, a bracket or any other mark the source does not have at that point, and do not close the sentence for tidiness -- an added '.' where the report prints ',' fails the check on an otherwise perfect quote. Copy, never finish.
- `page`: the ===PAGE N=== marker the article's outcome falls under, as an integer.
- Text may come from OCR and be garbled. If an article's outcome cannot be read, still emit the record with result 'unclear' and quote whatever the outcome sentence renders as.
- Do NOT include: the warrant's articles where no outcome is printed, election results, committee reports, or anything outside the Town Meeting proceedings.
- If the pages contain no Town Meeting proceedings at all, return an empty list."""

SCHEMA = {
    'type': 'object',
    'properties': {
        'articles': {'type': 'array', 'items': {'type': 'object', 'properties': {
            'meeting': {'type': 'string', 'enum': ['annual', 'special']},
            'meeting_date': {'type': ['string', 'null']},
            'article': {'type': 'string'},
            'subject': {'type': 'string'},
            'result': {'type': 'string', 'enum': ['passed', 'failed', 'passed_over',
                                                  'indefinitely_postponed', 'withdrawn',
                                                  'amended_and_passed', 'no_action', 'unclear']},
            'amount_as_printed': {'type': ['string', 'null']},
            'fincom': {'type': ['string', 'null']},
            'select_board': {'type': ['string', 'null']},
            'quote': {'type': 'string'},
            'page': {'type': ['integer', 'null']},
        }, 'required': ['meeting', 'meeting_date', 'article', 'subject', 'result',
                        'amount_as_printed', 'fincom', 'select_board', 'quote', 'page']}},
    },
    'required': ['articles'],
}


def pages_of(text):
    """The report split on its own ===PAGE N=== markers, as {page number: text}."""
    out, cur, buf = {}, None, []
    for line in text.splitlines():
        m = re.match(r'^===PAGE (\d+)===', line)
        if m:
            if cur is not None:
                out[cur] = '\n'.join(buf)
            cur, buf = int(m.group(1)), []
        else:
            buf.append(line)
    if cur is not None:
        out[cur] = '\n'.join(buf)
    return out


def catalogued_pages(fy):
    """The page range the contents catalogue gives for this year's town_meeting section."""
    for r in csv.DictReader(open(CONTENTS, encoding='utf-8')):
        if r['fy'] == str(fy) and r['table'] == 'town_meeting':
            out = []
            for part in (r['pages'] or '').split(','):
                part = part.strip()
                if '-' in part:
                    a, b = part.split('-', 1)
                    out.extend(range(int(a), int(b) + 1))
                elif part:
                    out.append(int(part))
            return sorted(set(out))
    return []


ARTICLE_RE = re.compile(r'^\s*ARTICLE\s+\d+\s*:', re.I | re.M)


def report_text(fy):
    """The report's extracted text. The catalogue names the file; the year is in the name."""
    for r in csv.DictReader(open(CATALOGUE, encoding='utf-8')):
        if r.get('fy') == str(fy):
            for k in ('text_path', 'text', 'path'):
                p = r.get(k) or ''
                if p.endswith('.txt'):
                    full = os.path.join(ROOT, p)
                    if os.path.exists(full):
                        return full
    hits = [f for f in os.listdir(TEXT_DIR) if re.search(r'fy[- ]?%s\b' % fy, f, re.I)]
    if len(hits) == 1:
        return os.path.join(TEXT_DIR, hits[0])
    raise SystemExit('cannot find one annual-report text for FY%s (found %r)' % (fy, hits))


def slice_for(fy):
    """THE PAGES THE ARTICLES ARE ON -- the catalogue's range UNION the pages that actually
    print an `ARTICLE n:` heading. The catalogue is a reading of the report and it is not
    always complete: FY2025 prints articles on pages 138, 140 and 143, and the catalogued
    range does not name them. A join that silently drops three pages of votes looks exactly
    like three pages of votes that were never held."""
    path = report_text(fy)
    text = open(path, encoding='utf-8', errors='replace').read()
    pages = pages_of(text)
    catalogued = set(catalogued_pages(fy))
    found = {n for n, t in pages.items() if ARTICLE_RE.search(t)}
    want = sorted(catalogued & set(pages) | found)
    return path, pages, want, sorted(found - catalogued), sorted(catalogued - found)


def extract(fy, verbose=True):
    path, pages, want, extra, missing = slice_for(fy)
    if not want:
        print('FY%s: no town-meeting pages found' % fy)
        return []
    body = '\n\n'.join('===PAGE %d===\n%s' % (n, pages[n]) for n in want)
    if verbose:
        print('FY%s: %d pages (%s), %d chars%s'
              % (fy, len(want), os.path.basename(path), len(body),
                 '; %d pages print articles the catalogue does not name: %s'
                 % (len(extra), extra[:8]) if extra else ''))
    env = dict(os.environ, PATH=NODE22 + os.pathsep + os.environ.get('PATH', ''))
    r = subprocess.run(['claude', '-p', '--tools', '', '--model', MODEL,
                        '--system-prompt', SYSTEM,
                        '--json-schema', json.dumps(SCHEMA),
                        '--output-format', 'json', '--max-budget-usd', '2'],
                       input='Annual report FY%s, Town Meeting proceedings:\n\n%s' % (fy, body),
                       capture_output=True, text=True, env=env, timeout=1800)
    if r.returncode != 0:
        raise SystemExit('claude failed on FY%s:\n%s' % (fy, (r.stdout + r.stderr)[-2000:]))
    res = json.loads(r.stdout)
    body_out = res.get('structured_output') or res.get('result')
    if isinstance(body_out, str):
        body_out = json.loads(body_out)
    arts = (body_out or {}).get('articles') or []
    now = dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    rel = os.path.relpath(path, ROOT)
    rows = []
    for a in arts:
        rows.append({'fy': fy, 'meeting': a['meeting'], 'meeting_date': a.get('meeting_date') or '',
                     'article': a['article'], 'subject': a['subject'], 'result': a['result'],
                     'amount_as_printed': a.get('amount_as_printed') or '',
                     'fincom': a.get('fincom') or '', 'select_board': a.get('select_board') or '',
                     'quote': a['quote'], 'page': a.get('page') or '',
                     'source_doc': rel, 'extracted_by': MODEL, 'extracted_at': now})
    if verbose:
        print('  %d articles, cost $%s' % (len(rows), res.get('total_cost_usd')))
    return rows


# TYPOGRAPHIC VARIANTS OF THE SAME CHARACTER, folded before comparing. The PDF extractor
# renders the report's curly quotes and dashes as U+201C/201D/2018/2019/2013/2014; a model
# transcribing the same sentence writes the ASCII ones. Eleven of FY2025's forty-nine
# quotes differed from the report in nothing else -- "School Department," against
# “School Department,”. This is not a relaxation of rule 13: the character IS the same
# character, and the check still requires every other one to match exactly.
FOLD = {'\u201c': '"', '\u201d': '"', '\u2018': "'", '\u2019': "'",
        '\u2013': '-', '\u2014': '-', '\u00a0': ' ', '\u2032': "'", '\u2033': '"'}


# THE PAGE BREAK IS OUR INSTRUMENT, AND IT SITS INSIDE THE SENTENCE. The Clerk's sentences
# run across pages, so the extracted text interrupts them with the PDF's printed page
# footer and then our own ===PAGE n=== marker -- "...Abstain 1) to 137 ===PAGE 142===
# accept the provisions of...". A model quoting the sentence quotes the sentence. Rule 13:
# an instrument that reformats before you see it is part of the finding, so the marker and
# the footer number immediately before it come out before anything is compared.
# TWO LITERAL-ANCHORED PASSES, NOT ONE PATTERN THAT LEADS WITH `\s*`.
#
# This was `\s*\d{0,4}\s*===PAGE \d+===\s*`, and it CATASTROPHICALLY BACKTRACKS. Two
# unbounded `\s*` either side of an optional number means that at every position inside a
# whitespace run the engine tries every way of splitting that run before failing to find
# the literal -- and an OCR'd annual report is mostly whitespace. On the 648 KB FY2018
# report it did not finish in three hours, and because it hung AFTER the year's rows were
# written the backfill looked like it was still working. A hang that leaves correct data
# behind is the worst kind: nothing is wrong except that nothing is happening.
#
# Both replacements below start with something fixed -- a literal, or a line start -- so
# the engine has one place to try per position instead of hundreds.
PAGE_MARKER = re.compile(r'===PAGE \d+===')
# A line holding nothing but one to four digits is the printed page number, which the
# extractor lifts out of the page header or footer into the middle of the Clerk's sentence.
PAGE_NUMBER = re.compile(r'(?m)^[ \t]*\d{1,4}[ \t]*$')


def norm(s):
    s = PAGE_NUMBER.sub(' ', PAGE_MARKER.sub(' ', s or ''))
    for a, b in FOLD.items():
        s = s.replace(a, b)
    # WHITESPACE AND HYPHENATION ARE THE EXTRACTOR'S. THE CHARACTER SEQUENCE IS THE CLERK'S.
    # One quantity, four renderings, all from the same report:
    #   "VOTED (Yes -243, No -9, Abstain -6, Total -258)"   a space before each hyphen
    #   "VOTED (Yes-320, No-31, Abstain-1, Total-352)"      no spaces
    #   "to re - authorize the revolving funds"             spaces around it
    #   "to replace the cur-\nrent Salary Schedule"          a word wrapped across a line
    # A reader sees one sentence; a model transcribing it writes one sentence; and the two
    # differ in nothing but spacing and hyphens. So the comparison is made on the character
    # sequence with whitespace and hyphens removed from BOTH sides.
    #
    # THIS DOES NOT WEAKEN THE CHECK IN THE WAY THAT MATTERS. Every letter, digit and mark
    # must still appear, in order: a fabricated tally fails, a paraphrase fails, a
    # reordered clause fails, an article's quote taken from a neighbouring article fails.
    # What it stops failing on is the one thing the Clerk did not write.
    return re.sub(r'[\s-]+', '', s)


# `ARTICLE 6:` in the FY2025 report and `ARTICLE 6.` in FY2024 -- the Clerk's own
# punctuation changes between years, and requiring the colon found 6 headings in a report
# that prints 26 articles. A heading regex that silently matches almost nothing turns
# every row into a failure and reads exactly like the extraction being wrong.
ART_HEAD = re.compile(r'^[ \t]*ARTICLE[ \t]+(\d+)[ \t]*[:.]', re.I | re.M)


def article_spans(raw):
    """THE TEXT THAT BELONGS TO EACH ARTICLE -- from its own heading to the next one.

    A quote can be perfectly verbatim and still be filed against the wrong article. The
    report prints forty in a row and every one opens `VOTED (Yes-n, No-n, ...)`, so a check
    that asks only *is this sentence somewhere in the document* passes on all of them --
    the compensating-error shape CLAUDE.md warns about, a check with no power to fail. It
    was not hypothetical: two FY2024 rows anchored on a NEIGHBOURING article's vote line
    and the document-wide check was happy with both.

    Only a line-anchored `ARTICLE n:` opens a span. An article NAMED inside another
    article's text -- "amend the vote of Article 33 of the May 6, 2006 Annual Town Meeting"
    -- is a reference, not a heading, and must not open one.
    """
    heads = [(m.start(), m.group(1)) for m in ART_HEAD.finditer(raw)]
    spans = collections.defaultdict(list)
    for i, (pos, num) in enumerate(heads):
        end = heads[i + 1][0] if i + 1 < len(heads) else len(raw)
        spans[num].append(norm(raw[pos:end]))
    return spans


def check(rows=None, verbose=True):
    """EVERY QUOTE, VERBATIM, IN THE PAGE IT CLAIMS. Rule 13: a check must assert the value,
    not the prose around it -- so this does not test that a row exists, it tests that the
    Clerk's sentence is really in the Clerk's report."""
    rows = rows if rows is not None else list(csv.DictReader(open(OUT, encoding='utf-8')))
    cache, spans, bad, soft, misfiled, nohead, ok = {}, {}, [], [], [], [], 0
    for r in rows:
        doc = r['source_doc']
        if doc not in cache:
            raw = open(os.path.join(ROOT, doc), encoding='utf-8', errors='replace').read()
            cache[doc], spans[doc] = norm(raw), article_spans(raw)
        q = norm(r['quote'])
        mine = spans[doc].get(re.sub(r'\D', '', r['article'])) or []
        # THREE OUTCOMES, AND TWO OF THEM ARE NOT THE SAME THING -- the split the annual-report
        # datasets already use (`checked` / `check failed` / `no check`). Where this article's
        # heading cannot be located in the report, the strong check CANNOT BE RUN: the quote is
        # verified against the document instead, and the row is reported as unlocatable rather
        # than counted as either a pass or a failure. Calling an unrunnable check a failure is
        # how a reader concludes the extraction is broken when the heading regex is.
        if q and not mine:
            (nohead if q in cache[doc] else bad).append(r)
        elif q and any(q in sp for sp in mine):
            ok += 1
        # VERBATIM, BUT UNDER SOMEBODY ELSE'S HEADING. The sentence is the Clerk's; the
        # article it is filed against is not the one it was printed under. Counted and named
        # separately, because it is a different defect from a quote that is not in the
        # report at all -- and it is the one a document-wide check cannot see.
        elif q and q in cache[doc]:
            misfiled.append(r)
        # ONE NAMED ALLOWANCE, and only one: a quote truncated mid-sentence that the model
        # closed with a mark the report does not print there. The substance is verbatim and
        # the last character is not. It is counted separately and printed, never folded into
        # `ok` -- a check that quietly forgives is a check with no power to fail.
        elif q and q.rstrip('.…') and any(q.rstrip('.…') in sp for sp in mine):
            soft.append(r)
        else:
            bad.append(r)
    if verbose:
        print('%d of %d quotes verbatim UNDER THEIR OWN ARTICLE HEADING%s%s%s'
              % (ok, len(rows),
                 '; %d more but for a closing mark the report does not print' % len(soft) if soft else '',
                 '; %d under another heading' % len(misfiled) if misfiled else '',
                 '; %d whose heading could not be located, verified against the document only'
                 % len(nohead) if nohead else ''))
        for r in misfiled[:10]:
            print('  WRONG ARTICLE  FY%s %s article %s: verbatim in the report, but not under '
                  'this heading: %r' % (r['fy'], r['meeting'], r['article'], r['quote'][:95]))
        for r in bad[:10]:
            print('  NOT FOUND  FY%s %s article %s: %r' % (r['fy'], r['meeting'], r['article'], r['quote'][:110]))
    return ok, bad + misfiled, soft


def write(rows):
    have = []
    if os.path.exists(OUT):
        have = [r for r in csv.DictReader(open(OUT, encoding='utf-8'))]
    fys = {str(r['fy']) for r in rows}
    have = [r for r in have if str(r['fy']) not in fys]
    allr = sorted(have + rows, key=lambda r: (str(r['fy']), r['meeting'],
                                              int(re.sub(r'\D', '', r['article']) or 0)))
    with open(OUT, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        for r in allr:
            w.writerow({c: r.get(c, '') for c in COLS})
    print('wrote %s — %d rows over %d years'
          % (os.path.relpath(OUT, ROOT), len(allr), len({r['fy'] for r in allr})))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fy', type=int)
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    if a.check:
        ok, bad, soft = check()
        raise SystemExit(1 if bad else 0)
    fys = [a.fy] if a.fy else sorted({int(r['fy']) for r in csv.DictReader(open(CONTENTS, encoding='utf-8'))
                                      if r['table'] == 'town_meeting'})
    if not a.fy and not a.all:
        raise SystemExit('give --fy YYYY or --all (%d years catalogued: %s)' % (len(fys), fys))
    rows = []
    for fy in fys:
        rows += extract(fy)
    if rows:
        write(rows)
        check(rows)


if __name__ == '__main__':
    main()
