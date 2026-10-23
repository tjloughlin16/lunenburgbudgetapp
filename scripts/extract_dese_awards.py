#!/usr/bin/env python3
"""DESE's competitive grant awards, one row per recipient, off DESE's own award documents.

    python3 scripts/extract_dese_awards.py           # write sources/data/dese-competitive-awards.csv
    python3 scripts/extract_dese_awards.py --check   # rebuild; fail if it differs

Reads the award documents fetch_dese_awards.py landed under sources/state-dese/awards/fy<YYYY>/
(the working copy of each, which is the newest version). Every one is a Word file DESE
publishes under the heading *Competitive Awards*: a header block --

    FY2026 Student Opportunity Act Evidence-Based Practice Grant   Fund Code: 0117
    Funds Allocated: $1,000,000 (State Trust)
    Number of Proposals Received: 25
    Number of Proposals Recommended: 10

-- and ONE table, `Recipients | Amounts`. A row with no amount is a heading inside the table
(`Goal 1`, `Fund Code 527S Summer Programming | -`) and is not a recipient.

WHAT IS CHECKED. DESE prints no total under the table, so a document cannot be footed on its
own face. What it does print is `Funds Allocated` and `Number of Proposals Recommended`, and
both are written beside every row with what the table actually holds (`recipients_sum`,
`recipients_n`), so a reader sees where they differ. They are not refused when they differ:
DESE allocates a pot and may award less than it (fund code 412A: $500,000 allocated, $166,028
requested), and one proposal can be several rows (0646 prints sites). A document whose table
cannot be found, or whose header carries no fund code, IS refused.

WHO A RECIPIENT IS. DESE prints a recipient as it was written on the application -- `Acton-
Boxborough`, `Acton Boxborough`, `Arlington Public Schools`, `Public Schools of Brookline`,
`Brockton High School`. The match to a district is BY NAME, because the documents carry no
code, and it is deliberately narrow: the printed name and DESE's own district name (off the
allocation pages, sources/data/dese-entitlement-allocations.csv) are put through ONE
normalisation -- case, apostrophes, `&`, hyphens and spaces, and a trailing `Public Schools`,
`Public School District`, `Regional School District`, `School District` or `(District)` -- and
must then be IDENTICAL. Nothing fuzzy. A school (`Brockton High School`), a collaborative or a
non-profit is left UNATTRIBUTED, with `match` blank, never guessed onto a district.

AND AN UNATTRIBUTED ROW MAY NOT HIDE A DISTRICT THE COMPARISON NEEDS. For every district the
grant comparison names (build_grant_comparison_topics.py), any unattributed recipient whose
printed text contains that district's name is listed in REVIEWED below with what it is, or
this refuses to write. A school of a comparison district is that district's award: DESE names
the grantee school, and the district is the legal recipient.
"""
import argparse
import csv
import hashlib
import html
import io
import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, 'sources', 'state-dese', 'awards')
ALLOC = os.path.join(ROOT, 'sources', 'data', 'dese-entitlement-allocations.csv')
INDEX = os.path.join(ROOT, 'sources', 'state-dese', 'index.csv')
OUT = os.path.join(ROOT, 'sources', 'data', 'dese-competitive-awards.csv')
FIELDS = ['fy', 'fund_code', 'program', 'funding', 'funds_allocated', 'proposals_received',
          'proposals_recommended', 'recipients_n', 'recipients_sum', 'recipient', 'amount',
          'joint', 'district', 'district_code', 'match', 'source_url', 'our_copy', 'sha256']

# Recipients that NAME a comparison district without being its district name, read by eye on
# 23 October 2026 and attributed here with the reason. Keyed (fy, fund code, printed name);
# the value is (district codes, why). No codes means read and NOT a district's award. A joint
# application names several districts and prints ONE amount: each gets a row with `joint`
# saying how many share it, so a sum over districts must divide or it counts the money twice.
# Codes are DESE's, off the allocation pages: 0735 North Middlesex, 0153 Leominster, 0174
# Maynard, 0616 Ayer Shirley, 0281 Springfield, 0332 West Springfield, 0086 Easthampton,
# 0450 Hilltown Cooperative Charter.
REVIEWED = {
    (2026, '0199', 'North Middlesex RSD'): (['0735'], 'RSD is regional school district'),
    (2026, '0213', 'Nashoba Learning Group, Inc.'): ([], 'a private special education school, '
                                                         'not the Nashoba district'),
    (2026, '0215', 'Springfield + West Springfield + Easthampton'):
        (['0281', '0332', '0086'], 'a joint application of three districts'),
    (2026, '0335', 'Hilltown Coop Charter Public School (Easthampton)*'):
        (['0450'], 'a charter school, its own district; Easthampton is its town'),
    (2026, '0426', 'Leominster High School'): (['0153'], "the district's high school"),
    (2026, '0426', 'Maynard High School'): (['0174'], "the district's high school"),
    (2026, '0589', 'Springfield (with West Springfield and Easthampton)'):
        (['0281', '0332', '0086'], 'a joint application of three districts'),
}

SUFFIX = re.compile(r'\s+(public schools|public school district|regional school district|'
                    r'school district|\(district\))$')


def fail(msg):
    raise SystemExit('extract_dese_awards: ' + msg)


def norm(s):
    s = html.unescape(s).replace('’', "'").replace('‘', "'").replace('&', ' and ')
    s = re.sub(r'[\s\-–—]+', ' ', s).strip().lower()
    s = re.sub(r'^public schools of\s+', '', s)
    prev = None
    while prev != s:
        prev, s = s, SUFFIX.sub('', s).strip()
    return s


def districts():
    """{normalised name: {code}} off the allocation pages, every spelling DESE printed, and
    {code: the spelling DESE printed most often} to name it by."""
    import collections
    out, seen = {}, collections.defaultdict(collections.Counter)
    for r in csv.DictReader(open(ALLOC, encoding='utf-8', newline='')):
        if r['district_code']:
            out.setdefault(norm(r['district']), set()).add(r['district_code'])
            seen[r['district_code']][r['district']] += 1
    return out, {c: n.most_common(1)[0][0] for c, n in seen.items()}


def money(s):
    s = s.replace(' ', ' ')
    m = re.search(r'\$?\s*([\d,]+(?:\.\d\d)?)', s)
    if not m or not re.search(r'\d', m.group(1)):
        return None
    return float(m.group(1).replace(',', ''))


def cell_text(xml):
    xml = re.sub(r'<w:tab/>', ' ', xml)
    xml = re.sub(r'</w:p>', '\n', xml)
    t = html.unescape(re.sub(r'<[^>]+>', '', xml))
    return re.sub(r'[ \t]+', ' ', t).strip()


def read_doc(path):
    x = zipfile.ZipFile(path).read('word/document.xml').decode('utf-8')
    tables = re.findall(r'<w:tbl>.*?</w:tbl>', x, re.S)
    head = cell_text(re.sub(r'<w:tbl>.*?</w:tbl>', '\n', x, flags=re.S))
    flat = ' '.join(head.split())
    rec = None
    for t in tables:
        trs = [[cell_text(c) for c in re.findall(r'<w:tc>.*?</w:tc>', tr, re.S)]
               for tr in re.findall(r'<w:tr[ >].*?</w:tr>', t, re.S)]
        if trs and len(trs[0]) >= 2 and trs[0][0].lower().rstrip().endswith('recipients'):
            rec = trs
    if rec is None:
        fail('%s: no Recipients | Amounts table' % os.path.relpath(path, ROOT))
    m = re.search(r'^(FY\s?\d{2,4}:?\s*.*?)\s*-?\s*Fund Code:?\s*([0-9A-Za-z/\- ]+?)\s+Funds Allocated', flat)
    if not m:
        fail('%s: no program and fund code in the header' % os.path.relpath(path, ROOT))
    program = re.sub(r'^FY\s?\d{2,4}:?\s*', '', m.group(1)).strip()
    alloc = re.search(r'Funds Allocated:?\s*\$\s*([\d,]+(?:\.\d\d)?)\s*(\([^)]*\))?', flat)
    rcv = re.search(r'Number of Proposals Received:?\s*(\d+)', flat)
    rec_n = re.search(r'Number of Proposals Recommended:?\s*(\d+)', flat)
    rows = []
    for r in rec[1:]:
        name, amt = ' '.join(r[0].split()), money(r[-1])
        if not name or amt is None:
            continue
        rows.append((name, amt))
    if not rows:
        fail('%s: the recipients table has no rows with an amount' % os.path.relpath(path, ROOT))
    return dict(program=program,
                funding=(alloc.group(2) or '').strip('()') if alloc else '',
                funds_allocated=alloc.group(1).replace(',', '') if alloc else '',
                proposals_received=rcv.group(1) if rcv else '',
                proposals_recommended=rec_n.group(1) if rec_n else '', rows=rows)


def catalogued():
    return {r['local']: r for r in csv.DictReader(open(INDEX, encoding='utf-8'))}


def fmt_amt(v):
    return ('%d' % v) if float(v).is_integer() else ('%.2f' % v)


def extract():
    names, label = districts()
    cat = catalogued()
    out = []
    for d in sorted(os.listdir(DOCS)):
        if not re.fullmatch(r'fy\d{4}', d):
            continue
        fy = int(d[2:])
        for f in sorted(os.listdir(os.path.join(DOCS, d))):
            if not f.lower().endswith('.docx'):
                continue
            path = os.path.join(DOCS, d, f)
            local = os.path.relpath(path, ROOT)
            c = cat.get(local)
            if not c:
                fail('%s is not catalogued in sources/state-dese/index.csv' % local)
            blob = open(path, 'rb').read()
            sha = hashlib.sha256(blob).hexdigest()
            if c['sha256'] != sha:
                fail('%s: catalogue sha256 is stale' % local)
            doc = read_doc(path)
            code = f.rsplit('.', 1)[0]
            total = sum(a for _, a in doc['rows'])
            for name, amt in doc['rows']:
                hit = names.get(norm(name), set())
                if len(hit) > 1:
                    hit = set()                  # a name DESE gives two codes: never guessed
                got = [(c0, 'name') for c0 in hit]
                rv = REVIEWED.get((fy, code, name))
                if rv is not None:
                    got = [(c0, 'reviewed: ' + rv[1]) for c0 in rv[0]] or [('', 'reviewed: ' + rv[1])]
                for dc, how in got or [('', '')]:
                    out.append(dict(
                        fy=fy, fund_code=code, program=doc['program'], funding=doc['funding'],
                        funds_allocated=doc['funds_allocated'],
                        proposals_received=doc['proposals_received'],
                        proposals_recommended=doc['proposals_recommended'],
                        recipients_n=len(doc['rows']), recipients_sum=fmt_amt(total),
                        recipient=name, amount=fmt_amt(amt), joint=len(got) if got else 1,
                        district=label.get(dc, ''), district_code=dc, match=how,
                        source_url=c['upstream'], our_copy='/docs/' + local[len('sources/'):],
                        sha256=sha))
    if not out:
        fail('no award documents held -- run fetch_dese_awards.py')
    return out


def guard(rows):
    """No unattributed recipient may carry the name of a district the comparison needs."""
    sys.path.insert(0, os.path.join(ROOT, 'scripts'))
    import build_grant_comparison_topics as G
    D = G.load()
    want = [m['name'] for m in D['members'].values()] + [G.LUN]
    bad = []
    for r in rows:
        if r['match']:
            continue
        low = norm(r['recipient'])
        for w in want:
            base = norm(w)
            if re.search(r'\b%s\b' % re.escape(base), low):
                bad.append('FY%s %s %r names %s and is unattributed -- read it and add it to '
                           'REVIEWED' % (r['fy'], r['fund_code'], r['recipient'], w))
    return bad


def render(rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, FIELDS, lineterminator='\n')
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    rows = extract()
    bad = guard(rows)
    if bad:
        print('\n'.join(bad), file=sys.stderr)
        return 1
    text = render(rows)
    n_docs = len({(r['fy'], r['fund_code']) for r in rows})
    n_dist = sum(1 for r in rows if r['district_code'])
    if a.check:
        if not os.path.exists(OUT) or open(OUT, encoding='utf-8').read() != text:
            print('STALE %s' % os.path.relpath(OUT, ROOT), file=sys.stderr)
            return 1
        print('dese competitive awards: current (%d documents, %d rows, %d attributed to a '
              'district)' % (n_docs, len(rows), n_dist))
        return 0
    tmp = OUT + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)
    os.replace(tmp, OUT)
    print('wrote %s: %d documents, %d recipient rows, %d attributed to a district by name, %d not'
          % (os.path.relpath(OUT, ROOT), n_docs, len(rows), n_dist, len(rows) - n_dist))
    return 0


if __name__ == '__main__':
    sys.exit(main())
