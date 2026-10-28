#!/usr/bin/env python3
"""Is a scanned report complete and in order? Read off its own page numbers, lists and index.

The older annual reports are scans of paper copies. A page can be lost, shuffled or doubled
before it ever reached the scanner, and nothing downstream would notice: a missing page of
wages is just fewer wages. So before any figure is checked, the scan is checked against
three things the report says about itself (PLAN-ANNUAL-REPORT-PIPELINE.md section 8):

  1. FOLIOS. Each page's printed number: a bare number alone on its row in a margin band.
     A number mid-page is not a folio -- the 2000 report prints a vote count of 132 on two
     pages, and its page 132 is missing. Printed = PDF + an offset; every page off that
     line, every duplicate, every skipped number and every page without one is reported.
  2. RUNS THAT MUST CONTINUE. An alphabetical column (wages, staff) or the town meeting's
     ARTICLE numbers carried across a page break. A break there is a missing or misplaced
     page even where the folio is unreadable.
  3. THE INDEX AGAINST THE BODY. The report's own index says where each section starts and
     ends; check the heading is on that page and that every page it names exists.

No model, no network: Textract's line positions only (build/textract/out/<stem>.lines.tsv).
Each finding has a class:

  issue  the scan disagrees with itself: a page missing, out of place, or doubled
  check  a run or a heading that does not continue where it should; worth a look
  note   what the instrument could not read (no folio, no index found) -- a statement
         about THIS SCRIPT, never about the town (rule 13c)

    python3 scripts/page_integrity.py                  # every Textract output
    python3 scripts/page_integrity.py "2000 Annual Town Report"
    python3 scripts/page_integrity.py --json STEM      # the findings as JSON
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import archive_storage  # noqa: E402

OUT = ROOT / 'build' / 'textract' / 'out'
CACHE = ROOT / 'build' / 'textract' / 'cache'

BAND = 0.08          # a margin band: the outer 8% of the page, on any side
FOLIO = re.compile(r'^[-–—\s]*(?:page\s+)?(\d{1,3})[-–—.\s]*$', re.I)
SPEC = re.compile(r'^\d{1,3}(?:\s*[-–]\s*\d{1,3})?(?:\s*,\s*\d{1,3}(?:\s*[-–]\s*\d{1,3})?)*$')
NAME = re.compile(r"^(?:[A-Z]\.?\s+)?([A-Z][A-Za-z'\-]{2,})$")
ARTICLE = re.compile(r'^ARTICLE\s*(\d+)?\b')
ARTICLE_NO = re.compile(r'^(\d{1,3})\.')
STOP = {'the', 'and', 'of', 'see', 'separate', 'pamphlet', 'for', 'town'}

MIN_RUN = 10         # an alphabetical column needs this many names to count as a list
SORTED = 0.85        # ...and this share of its neighbours in order


@dataclass
class Line:
    page: int
    left: float
    top: float
    width: float
    height: float
    text: str

    @property
    def bottom(self):
        return self.top + self.height

    @property
    def right(self):
        return self.left + self.width


@dataclass
class Finding:
    kind: str          # issue | check | note
    check: str         # folio_gap, out_of_place, duplicate_folio, no_folio, run_break, ...
    pages: list        # PDF pages it concerns
    detail: str


@dataclass
class Report:
    stem: str
    pdf_pages: list                  # the pages Textract was sent
    sha256: str | None = None
    total: int | None = None         # pages in the PDF, if we hold it
    offset: int | None = None
    folios: dict = field(default_factory=dict)        # pdf page -> printed number
    findings: list = field(default_factory=list)
    blank: list = field(default_factory=list)         # sent, and no text came back

    @property
    def pages_ok(self):
        return not any(f.kind == 'issue' for f in self.findings)

    def add(self, kind, check, pages, detail):
        self.findings.append(Finding(kind, check, sorted(pages), detail))


def read_lines(path):
    pages = defaultdict(list)
    with open(path, newline='') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            pages[int(r['page'])].append(Line(int(r['page']), float(r['left']), float(r['top']),
                                              float(r['width']), float(r['height']), r['text'].strip()))
    return dict(sorted(pages.items()))


def overlaps(a0, a1, b0, b1):
    """Two spans share at least half of the shorter one. A tall rotated header word that
    grazes a folio's row by a hair is not on that row."""
    return min(a1, b1) - max(a0, b0) > 0.5 * min(a1 - a0, b1 - b0)


def document(stem, read):
    """The Textract cache this output came from, the pages SENT to Textract (a page sent and
    returning no text is blank, not unread), and the PDF's page count if we hold the file.

    The output is named for the PDF it was read from, the cache for its sha256; the cache
    whose pages cover the output's is the one."""
    best = None
    for d in CACHE.iterdir() if CACHE.exists() else ():
        sent = sorted({int(f.name[1:4]) for f in d.glob('p*-*.json')})
        if read <= set(sent) and (best is None or len(sent) < len(best[1])):
            best = (d.name, sent)
    if best is None:
        return None, sorted(read), None
    sha, sent = best
    total = None
    for row in archive_storage.read_manifest().values():
        if row['sha256'] == sha:
            path = Path(archive_storage.local_path(row['key']))
            if path.exists():
                import pypdfium2
                total = len(pypdfium2.PdfDocument(str(path)))
            break
    return sha, sent, total


# ---- 1. folios ---------------------------------------------------------------------------

def folio_candidates(lines):
    """Bare numbers in a margin band, ALONE on their row (or column, in a side band).

    Alone is what tells a folio from an index entry or a table cell that happens to sit
    near the edge: the 2000 index prints `Zoning Board of Appeals ... 36` in the bottom
    band, with its label on the same row."""
    out = []
    for ln in lines:
        m = FOLIO.match(ln.text)
        if not m:
            continue
        if ln.top < BAND or ln.bottom > 1 - BAND:
            alone = not any(o is not ln and overlaps(ln.top, ln.bottom, o.top, o.bottom) for o in lines)
        elif ln.right < BAND or ln.left > 1 - BAND:
            alone = not any(o is not ln and overlaps(ln.left, ln.right, o.left, o.right) for o in lines)
        else:
            continue
        if alone:
            out.append((int(m.group(1)), ln))
    return out


def read_folios(rep, pages):
    cands = {p: folio_candidates(ls) for p, ls in pages.items()}
    single = [n - p for p, c in cands.items() if len(c) == 1 for n, _ in c]
    if not single:
        rep.add('note', 'no_folios_read', [], 'no page number was read on any page')
        return
    rep.offset = Counter(single).most_common(1)[0][0]
    for p, c in cands.items():
        if not c:
            continue
        fit = [n for n, _ in c if n - p == rep.offset]
        # several candidates: the one on the document's own line, else the one nearest an edge
        rep.folios[p] = fit[0] if fit else min(c, key=lambda nl: min(nl[1].top, 1 - nl[1].bottom))[0]


def check_folios(rep):
    f = rep.folios
    if not f:
        return
    numbered = sorted(f)
    first, last = numbered[0], numbered[-1]

    # a page whose number disagrees with BOTH neighbours, which agree with each other: one
    # page out of place (or one folio misread -- the detail says which numbers are where)
    outliers = set()
    for i in range(1, len(numbered) - 1):
        a, p, b = numbered[i - 1], numbered[i], numbered[i + 1]
        if f[a] - a == f[b] - b != f[p] - p:
            outliers.add(p)
            expect = p + f[a] - a
            where = [q for q in numbered if q != p and f[q] == f[p]]
            also = f'; printed {f[p]} is also on PDF {where[0]}' if where else ''
            rep.add('issue', 'out_of_place', [p],
                    f'PDF {p} carries printed {f[p]}; its neighbours put it at {expect}{also}')

    seen = defaultdict(list)
    for p in numbered:
        seen[f[p]].append(p)
    for n, ps in sorted(seen.items()):
        if len(ps) > 1:
            rep.add('issue', 'duplicate_folio', ps, f'printed {n} is on PDF {", ".join(map(str, ps))}')

    run = [p for p in numbered if p not in outliers]
    for a, b in zip(run, run[1:]):
        dp, dn = b - a, f[b] - f[a]
        if dn == dp or dn == 0:          # in step; a repeat is reported as a duplicate above
            continue
        if dn > dp:
            gone = dn - dp
            nums = list(range(f[a] + 1, f[b])) if dp == 1 else None
            what = (f'printed {nums[0]}' if nums and len(nums) == 1 else
                    f'printed {nums[0]}-{nums[-1]}' if nums else f'{gone} printed page(s)')
            rep.add('issue', 'folio_gap', [a, b],
                    f'PDF {a} is printed {f[a]} and PDF {b} is printed {f[b]}: {what} not in the file')
        elif dn < 0:
            rep.add('issue', 'folio_backwards', [a, b],
                    f'PDF {a} is printed {f[a]} and PDF {b} is printed {f[b]}')
        else:
            rep.add('issue', 'extra_pages', [a, b],
                    f'{dp - dn} more PDF page(s) between printed {f[a]} and {f[b]} than the numbers allow')

    gaps = [p for p in rep.pdf_pages if first < p < last and p not in f]
    gaps = [p for p in gaps if p not in rep.blank]
    for p in gaps:
        rep.add('note', 'no_folio', [p], f'PDF {p}: no page number read; its neighbours put it at {p + rep.offset}')
    front = [p for p in rep.pdf_pages if p < first]
    back = [p for p in rep.pdf_pages if p > last]
    if front:
        rep.add('note', 'unnumbered_front', front, f'PDF {front[0]}-{front[-1]} carry no number (front matter)')
    if back:
        rep.add('note', 'unnumbered_back', back, f'PDF {back[0]}-{back[-1]} carry no number after printed {f[last]}')


# ---- 2. runs that must continue ------------------------------------------------------------

def name_columns(lines):
    """Alphabetical columns on a page: [(x, [names top to bottom])]."""
    hits = sorted((ln.left, ln.top, m.group(1).lower()) for ln in lines
                  if BAND < ln.top < 1 - BAND and (m := NAME.match(ln.text)))
    # a column is a chain of left edges no more than 2.5% apart: `W Nelson` starts an
    # initial's width to the left of `Salo`, and both are the surname column
    cols, prev = [], None
    for left, top, name in hits:
        if prev is None or left - prev > 0.025:
            cols.append([])
        cols[-1].append((left, top, name))
        prev = left
    out = []
    for col in cols:
        names = [n for _, _, n in sorted(col, key=lambda c: c[1])]
        if len(set(names)) < MIN_RUN:      # `MAX` forty times down a step column is not a list
            continue
        ordered = sum(a[:2] <= b[:2] for a, b in zip(names, names[1:])) / (len(names) - 1)
        if ordered >= SORTED:
            out.append((statistics.median(c[0] for c in col), names))
    return out


def check_name_runs(rep, pages):
    cols = {p: name_columns(ls) for p, ls in pages.items()}
    order = list(pages)
    for a, b in zip(order, order[1:]):
        for xa, na in cols[a]:
            match = [nb for xb, nb in cols[b] if abs(xa - xb) <= 0.05]
            if not match:
                continue
            last, first = na[-1], match[0][0]
            # a list may restart at A (a second list); going back to mid-alphabet may not
            if first[:2] < last[:2] and first[0] != 'a':
                rep.add('check', 'run_break', [a, b],
                        f'the alphabetical list ends PDF {a} at "{last.title()}" and resumes PDF {b} '
                        f'at "{first.title()}"')
    end = order[-1]
    for _, names in cols[end] if whole(rep) else ():
        rep.add('note', 'run_reaches_end', [end],
                f'an alphabetical list runs to the last page of the file, ending at "{names[-1].title()}"')


def articles(lines):
    """ARTICLE numbers on a page, top to bottom. The number may be a separate line on the row."""
    out = []
    for ln in lines:
        m = ARTICLE.match(ln.text)
        if not m:
            continue
        n = m.group(1)
        if n is None:
            row = sorted((o for o in lines if o is not ln and o.left > ln.left
                          and overlaps(ln.top, ln.bottom, o.top, o.bottom)), key=lambda o: o.left)
            m2 = ARTICLE_NO.match(row[0].text) if row else None
            n = m2.group(1) if m2 else None
        if n is not None:
            out.append((ln.top, int(n)))
    return [n for _, n in sorted(out)]


def check_articles(rep, pages):
    seq = [(p, articles(ls)) for p, ls in pages.items()]
    seq = [(p, ns) for p, ns in seq if ns]
    for (a, na), (b, nb) in zip(seq, seq[1:]):
        last, first = na[-1], nb[0]
        if first == last + 1 or first == 1:
            continue
        if first > last + 1:
            gone = f'ARTICLE {last + 1}' if first == last + 2 else f'ARTICLES {last + 1}-{first - 1}'
            rep.add('check', 'article_gap', [a, b],
                    f'PDF {a} ends at ARTICLE {last} and PDF {b} starts at ARTICLE {first}: '
                    f'{gone} not read in between')
        else:
            rep.add('check', 'article_backwards', [a, b],
                    f'PDF {a} ends at ARTICLE {last} and PDF {b} starts at ARTICLE {first}')


# ---- 3. the index against the body ---------------------------------------------------------

def rows(lines):
    """Lines grouped into printed rows by vertical overlap, each left to right."""
    out = []
    for ln in sorted(lines, key=lambda l: l.top):
        for r in out:
            if overlaps(ln.top, ln.bottom, r[0].top, r[0].bottom):
                r.append(ln)
                break
        else:
            out.append([ln])
    return [sorted(r, key=lambda l: l.left) for r in out]


def spec_pages(spec):
    """'95-99, 112-119' -> [(95, 99), (112, 119)]."""
    out = []
    for part in spec.split(','):
        ends = [int(x) for x in re.split(r'[-–]', part.strip())]
        out.append((ends[0], ends[-1]))
    return out


def read_index(lines):
    entries = []
    for r in rows(lines):
        if len(r) < 2 or not SPEC.match(r[-1].text) or r[-1].left < 0.5:
            continue
        title = ' '.join(l.text for l in r[:-1])
        if re.search(r'[A-Za-z]{3}', title):
            entries.append((title, spec_pages(r[-1].text)))
    return entries


def words(text):
    return {w for w in re.findall(r'[a-z]{3,}', text.lower()) if w not in STOP}


def check_index(rep, pages):
    numbered = sorted(rep.folios)
    # the index lives in the front matter or at the back
    where = [p for p in pages if not numbered or p < numbered[0] or p > numbered[-1]] or []
    index = []
    for p in where:
        e = read_index(pages[p])
        if len(e) >= 8:
            index.append((p, e))
    if not index:
        rep.add('note', 'no_index_read', [], 'no index page was read in the unnumbered pages')
        return
    by_printed = {n: p for p, n in rep.folios.items()}
    top = max(rep.folios.values()) if rep.folios else None
    page_words = {p: words(' '.join(l.text for l in ls)) for p, ls in pages.items()}
    for ip, entries in index:
        missing = set()
        for title, spans in entries:
            for lo, hi in spans:
                gone = [n for n in range(lo, hi + 1) if n not in by_printed
                        and not (rep.offset is not None and n - rep.offset in pages
                                 and n - rep.offset not in rep.folios)]
                if gone and whole(rep):
                    missing.update(gone)
                    rep.add('issue', 'index_page_absent', [ip],
                            f'the index puts "{title}" at {lo}-{hi}; no page in the file carries printed '
                            + ', '.join(map(str, gone)))
            want = words(title)
            lo = spans[0][0]
            p = by_printed.get(lo) or (lo - rep.offset if rep.offset is not None else None)
            if not want or p not in pages:
                continue
            if len(want & page_words[p]) / len(want) >= 0.5:
                continue
            near = [q for q in range(p - 3, p + 4) if q in pages and q != p
                    and len(want & page_words[q]) / len(want) >= 0.5]
            if near:
                rep.add('check', 'index_heading_elsewhere', [p, near[0]],
                        f'the index puts "{title}" at printed {lo} (PDF {p}); its words are on PDF {near[0]}')
            else:
                rep.add('note', 'index_heading_unmatched', [p],
                        f'"{title}" (printed {lo}, PDF {p}): its words were not read on that page or near it')
        if top is not None and missing and max(missing) > top and whole(rep):
            rep.add('issue', 'pages_after_last', [], f'the index names printed pages up to {max(missing)}; '
                    f'the last page in the file is printed {top}')


# ---- the run -------------------------------------------------------------------------------

def check(path, sent=None, total=None):
    """`sent` and `total` default to what the Textract cache and the archive say; a test
    passes them for a document it has doctored."""
    pages = read_lines(path)
    stem = Path(path).name.removesuffix('.lines.tsv')
    sha = None
    if sent is None:
        sha, sent, total = document(stem, set(pages))
    rep = Report(stem=stem, pdf_pages=sent, sha256=sha, total=total)
    rep.blank = [p for p in sent if p not in pages]
    if rep.blank:
        rep.add('note', 'blank', rep.blank, 'no text read: PDF ' + ', '.join(map(str, rep.blank)))
    read_folios(rep, pages)
    check_folios(rep)
    check_name_runs(rep, pages)
    check_articles(rep, pages)
    check_index(rep, pages)
    return rep


def whole(rep):
    """Was every page of the PDF read? Only then can a gap at the edges be a finding."""
    return rep.total is not None and rep.pdf_pages == list(range(1, rep.total + 1))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('stems', nargs='*', help='Textract output stems (default: all)')
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args(argv)
    paths = [OUT / f'{s}.lines.tsv' for s in args.stems] or sorted(OUT.glob('*.lines.tsv'))
    reports = []
    for path in paths:
        if not path.exists():
            sys.exit(f'no Textract output: {path}')
        rep = check(path)
        reports.append(rep)
        if args.json:
            continue
        span = ('every page' if whole(rep) else
                f'of {rep.total}' if rep.total else 'PDF not held, page count unknown')
        offs = f'printed = PDF {rep.offset:+d}' if rep.offset is not None else 'no folios'
        print(f'{rep.stem}: {len(rep.pdf_pages)} pages read ({span}), {len(rep.folios)} numbered, '
              f'{offs} -- ' + ('pages_ok' if rep.pages_ok else 'PAGES NOT OK'))
        if not whole(rep):
            print('  (not every page was read: only what was read is checked)')
        for f in rep.findings:
            print(f'  {f.kind:<5} {f.check:<24} {f.detail}')
    if args.json:
        print(json.dumps([{**asdict(r), 'pages_ok': r.pages_ok} for r in reports], indent=1))


if __name__ == '__main__':
    main()
