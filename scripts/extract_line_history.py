"""Every budget line the district's documents print, budget and actual, year by year.

`extract_budget_history.py` pulls named groups -- the paras, the buses, the totals. This
pulls EVERYTHING: each row of each table, keyed by the district's own label for it, with
each column mapped to the fiscal year and kind the document states in its own header.

What it is for. The totals say the district lands within half a percent of its budget most
years. That is a statement about the sum, and a sum can be quiet while everything inside it
is loud -- which is exactly what analyses/budget-vs-actual.md claims about FY25. With one
year you cannot tell a line that always misses from a line that missed once. With eight you
can.

Two things this inherits from the group extractor, and both matter:

  * nothing is taken by position. Each document states its columns and the header is read.
  * a fiscal year does not have one budget figure, so the STAGE is recorded and only like
    is compared with like.

And one thing it adds: labels drift. "M.S. Specl Ed Resourse Rm Tchrs" and "M.S. Specl Ed
Resource Rm Teacher" are the same line in different years, so labels are normalised before
matching -- lowercased, punctuation dropped, and the district's own abbreviations folded
together. Where normalisation cannot decide, the line simply does not match across years
and is dropped rather than guessed at.

    python3 scripts/extract_line_history.py
"""
import os, re, csv, sys, glob, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXT = os.path.join(ROOT, 'sources/district-budget-page/text')
OUT = os.path.join(ROOT, 'sources/data/line-history.csv')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib.util
_spec = importlib.util.spec_from_file_location(
    'ebh', os.path.join(ROOT, 'scripts/extract_budget_history.py'))
ebh = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ebh)

# A data row is a label followed by numbers. Split at the first digit or dollar sign
# rather than matched with one regex: a pattern with a lazy label and a repeating number
# group backtracks catastrophically on the handful of rows that are nearly-but-not-quite
# a data row, and there are six thousand rows to get through.
FIRST_NUM = re.compile(r'[\d$(]')


def split_row(t):
    """(label, numbers-part) for a data row, or None."""
    m = FIRST_NUM.search(t)
    if not m or m.start() < 4:
        return None
    label = t[:m.start()].strip()
    if len(label) < 3 or not label[0].isalpha():
        return None
    return label, t[m.start():]
GROUP_HEADER = re.compile(r'^\d{4}\s*-\s')
SKIP = re.compile(r'^(TOTAL|Total|DESCRIPTION|FY\d)', re.I)

# The district's own abbreviations, folded so the same line matches itself across years.
ABBREV = [
    (r'\bspecl\b|\bspecil\b|\bspeci\b|\bspecial\b', 'special'),
    (r'\bed\b|\beduc\b|\beducation\b', 'ed'),
    (r'\btchrs?\b|\bteachers?\b|\bteach\b|\btea\b', 'teacher'),
    (r'\brsourse\b|\bresourse\b|\bresource\b', 'resource'),
    (r'\brm\b|\broom\b', 'rm'),
    (r'\bparaprofessionals?\b|\bparas?\b', 'para'),
    (r'\bpathologists?\b|\bpathigsts\b|\bpathlgsts\b|\bpathologis\b|\bpathologi\b', 'pathologist'),
    (r'\bsubs?\b|\bsubstitutes?\b', 'sub'),
    (r'\bmater\b|\bmaterials?\b', 'materials'),
    (r'\bsupt\b|\bsuperintendent\b', 'supt'),
    (r'\bsvcs?\b|\bservices?\b|\bser\b', 'services'),
    (r'\bcont\b|\bcontracted\b|\bcontrctd\b', 'contracted'),
    (r'\bps\b|\bprimary\b', 'ps'), (r'\bes\b|\belementary\b', 'es'),
    (r'\bms\b|\bmiddle\b', 'ms'), (r'\bhs\b|\bhigh\b', 'hs'),
]


def norm(label):
    s = label.lower().strip().rstrip('*.')
    s = re.sub(r'[^a-z0-9 ]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    for pat, rep in ABBREV:
        s = re.sub(pat, rep, s)
    return re.sub(r'\s+', ' ', s).strip()


def layouts(lines):
    """The column layout in force at every line, computed once per document.

    The group extractor walks backwards from each row to find its header, which is fine
    for six lines and quadratic for six thousand. Here the headers are found once and
    carried forward, which is the same answer and roughly a thousand times less work.
    """
    out = [None] * len(lines)
    cur = None
    for i, ln in enumerate(lines):
        ys = ebh.YEARS.findall(ln)
        if len(ys) >= 2:
            for k in range(i + 1, min(len(lines), i + 3)):
                ks = [m.group(1).lower() for m in ebh.KINDS.finditer(lines[k])]
                if len(ks) >= len(ys):
                    cur = [(2000 + int(y), kind)
                           for y, kind in zip(ys, ks[:len(ys)])]
                    break
        out[i] = cur
    return out


def scan(path):
    lines = open(path, encoding='utf-8', errors='replace').read().split('\n')
    dy = ebh.document_year(lines)
    lay = layouts(lines)
    out = []
    for i, ln in enumerate(lines):
        t = ln.strip()
        if not t or SKIP.match(t) or GROUP_HEADER.match(t):
            continue
        parsed = split_row(t)
        if not parsed:
            continue
        label, rest = parsed
        cols = lay[i]
        if not cols:
            continue
        nums = [ebh.money(x.group(1)) for x in ebh.NUM.finditer(rest)]
        if len(nums) < len(cols):
            continue
        for (fy, kind), v in zip(cols, nums[:len(cols)]):
            if kind in ebh.BUDGET_KINDS:
                stage = ebh.stage_of(fy, kind, dy)
            elif kind in ebh.ACTUAL_KINDS:
                stage = 'actual'
            else:
                continue
            out.append(dict(fy=fy, label=label, key=norm(label), stage=stage, value=v,
                            doc=os.path.basename(path), docYear=dy))
    return out


def main():
    obs = []
    for path in sorted(glob.glob(os.path.join(TEXT, '*.txt'))):
        obs += scan(path)
    print(f'{len(obs):,} observations from {len({o["doc"] for o in obs})} documents')

    # Collapse to one figure per (line, year, stage): later documents win, and a
    # disagreement is recorded rather than averaged away.
    best, disagree = {}, set()
    for o in sorted(obs, key=lambda x: (x['docYear'] or 0)):
        k = (o['key'], o['fy'], o['stage'])
        if k in best and abs(best[k]['value'] - o['value']) > 1:
            disagree.add(k)
        best[k] = o

    keys = sorted({k[0] for k in best})
    print(f'{len(keys):,} distinct lines after normalising labels')
    print(f'{len(disagree):,} (line, year, stage) cells where documents disagree')

    with open(OUT, 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['key', 'label', 'fy', 'stage', 'value', 'documents_disagree', 'source'])
        for (key, fy, stage), o in sorted(best.items()):
            w.writerow([key, o['label'], fy, stage, f"{o['value']:.0f}",
                        int((key, fy, stage) in disagree), o['doc']])
    print(f'wrote {OUT}')

    pairs = [(k, fy) for (k, fy, st) in best if st == 'actual'
             and (k, fy, 'settled') in best]
    print(f'{len(pairs):,} line-years with both a settled budget and an actual')
    yrs = collections.Counter(fy for _, fy in pairs)
    print('   by year: ' + ', '.join(f'FY{fy%100} {n}' for fy, n in sorted(yrs.items())))


if __name__ == '__main__':
    main()
