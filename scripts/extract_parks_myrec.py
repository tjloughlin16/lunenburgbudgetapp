"""The Parks & Recreation registration system's two FY2025 sales reports, as data.

    python3 scripts/extract_parks_myrec.py           # write sources/data/parks-myrec-sales-fy2025.csv
    python3 scripts/extract_parks_myrec.py --check   # ...and fail if it no longer reproduces

Two one-page printouts from MyRec (lunenburgma.myrec.com), the system the department
sells programme places and beach passes through, obtained by records request in August
2025: the Program Sales Report and the Membership Sales Report, both for 1 July 2024 to
30 June 2025. Rule 13a: a system printed these, so they are evidence of what MyRec
recorded -- which is registrations and the fees attached to them, not what reached the
town's books (fund 1500, Park Revolving, is on the town's special-revenue report).

The text layer of the programme report drops its header row, so the six columns are
named from the rendered page, and every figure is checked against the TOTALS line each
report prints: three counts and three amounts, to the cent, or nothing is written.
"""
import argparse
import csv
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = {
    'program': 'sources/town-ledgers/account-details/parks-program-financials-fy2025-myrec.pdf',
    'membership': 'sources/town-ledgers/account-details/parks-membership-sales-fy2025-myrec.pdf',
}
OUT = os.path.join(ROOT, 'sources', 'data', 'parks-myrec-sales-fy2025.csv')
FIELDS = ['report', 'fy', 'program', 'res_count', 'nonres_count', 'total_count', 'res_total', 'nonres_total', 'total', 'document']

# The Membership report's text layer prints the totals row without a label and the
# programme names on separate lines from their figures, so both are read from the
# rendered page rather than parsed; the page is one table each and the values are
# checked against the printed totals below.
PROGRAM = [
    ("2024 Lunenburg's Great Cardboard Boat Race", 3, 4, 7, 0.00, 0.00, 0.00),
    ('BEST Soccer', 16, 11, 27, 3040.00, 2090.00, 5130.00),
    ('BEST Soccer- Summer Clinic', 1, 0, 1, -190.00, 0.00, -190.00),
    ('COUCH TO 5K', 8, 0, 8, 280.00, 0.00, 280.00),
    ('Game Time Training Basketball Clinic', 1, 2, 3, -160.00, -320.00, -480.00),
    ('Gentle Flow Yoga', 4, 12, 16, 0.00, 0.00, 0.00),
    ('MA Sports Leagues School Vacation Programs', 30, 14, 44, 4600.00, 2000.00, 6600.00),
    ('NRWA Summertime Eco-Adventures', 4, 0, 4, 0.00, 0.00, 0.00),
    ('Science Heroes', 15, 15, 30, 0.00, 0.00, 0.00),
    ('SNAPOLOGY-STEM PROGRAMS', 49, 59, 108, 6501.00, 10559.50, 17060.50),
    ('SWIM LESSONS 2024', 19, 1, 20, 360.00, 0.00, 360.00),
    ('SWIM LESSONS 2025', 98, 47, 145, 2310.00, 1170.00, 3480.00),
    ('The Painted Goat- Adult and Youth Workshops!', 13, 8, 21, 570.00, 405.00, 975.00),
    ('Thursday Night Volleyball- Advanced', 12, 19, 31, 480.00, 780.00, 1260.00),
    ('Thursday- Intermediate Pickleball', 7, 28, 35, 160.00, 1120.00, 1280.00),
    ('Wednesday Afternoon Pickleball', 27, 71, 98, 600.00, 2130.00, 2730.00),
    ('Wildlife Encounters- Junior Zookeepers', 30, 22, 52, 280.00, 190.00, 470.00),
]
PROGRAM_TOTALS = (337, 313, 650, 18831.00, 20124.50, 38955.50)
MEMBERSHIP = [
    ('2024 BEACH PASSES', 26, 3, 29, 1509.00, 175.00, 1684.00),
    ('2024 SEASON PASS-FAMILY ADD ON $5', 1, 3, 4, 5.00, 15.00, 20.00),
    ('2025 BEACH PASSES', 60, 71, 131, 3466.00, 3614.00, 7080.00),
    ('LUNENBURG EMPLOYEE MEMBERSHIP', 0, 0, 0, 0.00, 44.00, 44.00),
]
MEMBERSHIP_TOTALS = (87, 77, 164, 4980.00, 3848.00, 8828.00)


def text(path):
    import pypdf
    return '\n'.join(p.extract_text() for p in pypdf.PdfReader(os.path.join(ROOT, path)).pages)


def check_rows(name, rows, totals, path):
    """Every figure typed above must appear in the document's own text layer, and the
    columns must foot to the totals the report prints."""
    t = text(path).replace(',', '')
    for r in rows:
        for v in r[1:]:
            s = ('%d' % v) if isinstance(v, int) else ('-$%.2f' % -v if v < 0 else '$%.2f' % v)
            if s not in t:
                raise SystemExit('%s: %r for %r is not in the document text' % (name, s, r[0]))
    for i, tot in enumerate(totals):
        got = round(sum(r[i + 1] for r in rows), 2)
        if abs(got - tot) > 0.005:
            raise SystemExit('%s: column %d sums to %s, report prints %s' % (name, i + 1, got, tot))
        s = ('%d' % tot) if isinstance(tot, int) else '$%.2f' % tot
        # The programme report's text layer carries neither its header row nor its
        # TOTALS row (pypdf gets the body only); those were read from the rendered page,
        # so only the membership report's totals can be asserted against the text.
        if name == 'membership' and s not in t:
            raise SystemExit('%s: printed total %r is not in the document text' % (name, s))
    for r in rows:
        if r[1] + r[2] != r[3] or abs(r[4] + r[5] - r[6]) > 0.005:
            raise SystemExit('%s: %r does not foot across' % (name, r[0]))


def build():
    check_rows('program', PROGRAM, PROGRAM_TOTALS, DOCS['program'])
    check_rows('membership', MEMBERSHIP, MEMBERSHIP_TOTALS, DOCS['membership'])
    out = []
    for rep, rows in (('program', PROGRAM), ('membership', MEMBERSHIP)):
        for r in rows:
            out.append(dict(report=rep, fy=2025, program=r[0], res_count=r[1], nonres_count=r[2], total_count=r[3],
                            res_total='%.2f' % r[4], nonres_total='%.2f' % r[5], total='%.2f' % r[6], document=DOCS[rep]))
    return out


def render(rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator='\n')
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    s = render(build())
    if a.check:
        if not os.path.exists(OUT) or open(OUT, encoding='utf-8').read() != s:
            raise SystemExit('%s is stale' % os.path.relpath(OUT, ROOT))
        print('parks-myrec-sales-fy2025.csv reproduces: %d rows, both reports tie to their printed totals' % (s.count('\n') - 1))
        return
    open(OUT, 'w', encoding='utf-8').write(s)
    print('wrote %s: %d rows' % (os.path.relpath(OUT, ROOT), s.count('\n') - 1))


if __name__ == '__main__':
    main()
