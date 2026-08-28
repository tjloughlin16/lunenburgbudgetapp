"""Out-of-district tuition, budget by budget, back through the mirrored budget documents.

The model escalates this line at 8% a year and nothing supports that number: the citation
says only "our estimate", and the back-test flags it as the worst-calibrated assumption in
the model -- assumed 8.0%, observed -22.5%. Three budget years is not enough to do better.
The archive now holds the district's whole budget page back to FY18, and those documents
carry lines 9300 and 9400, so a longer budget-to-budget series is available.

**Two hazards, and the second one is worse.**

First, every one of these documents prints five or six columns side by side and most of
them are ACTUAL spending. A series built by taking "the last number on the row" would
silently mix actuals with budgets -- rule 1, the error that put a special education
escalator 1.5 points too high.

Second, and this is the one that only appears once you look: **a fiscal year does not have
one budget figure for this line.** It has several, at different stages, and they are far
apart. Collaborative tuitions for FY25 were proposed at $369,415 in April 2024 and
approved at $460,952 that June. FY26 was approved at $782,867 in March 2025 and reported
as a final budget of $302,663 a year later -- a 61% revision inside the year.

So "the FY25 budget" is ambiguous, and a series that takes whichever figure each document
happens to lead with is not a trend. It is a walk across stages. This script therefore
records the STAGE of every observation and compares only like with like.

So nothing here is positional. Each document states its own columns:

    FY15   FY16   FY17   FY18   FY19     FY20
    Actual Actual Actual Actual Budgeted Proposed

The script reads that header, maps each position to a fiscal year AND a kind, and keeps
only the positions the document itself calls a budget. Where a document does not state its
columns, it is skipped and said so, rather than guessed at.

    python3 scripts/extract_tuition_history.py
"""
import os, re, sys, glob, csv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXT = os.path.join(ROOT, 'sources/district-budget-page/text')
DATA = os.path.join(ROOT, 'sources/data')

# The line groups worth a history, each summed from the district's own line names.
#
# Out-of-district tuition came first, because the model escalated it at 8% on no basis at
# all. The other two are here because the rate that replaced it rests on them: the
# in-district rate assumes the FY27 jump in aides was a step rather than the start of a
# climb, and it prices the bus contract off a single year. Both are assumptions the
# archive can now test, and an assumption that can be tested and has not been is just an
# assumption somebody has decided not to look at.
GROUPS = {
    'ood-tuition': dict(
        out='ood-tuition-history.csv',
        what='out-of-district tuition',
        parts={
            'private': re.compile(r'^Special Ed Tuitions?/Private\b', re.I),
            'collaborative': re.compile(r'^Collaborative Tuitions?\b', re.I),
        }),
    'paraprofessionals': dict(
        out='sped-para-history.csv',
        what='special education paraprofessionals',
        parts={
            school.lower().replace('.', ''): re.compile(
                rf'^{re.escape(school)}\s+Special Ed(?:ucation)? Paraprofessionals?\*{{0,3}}',
                re.I)
            for school in ('P.S.', 'E.S.', 'M.S.', 'H.S.', 'ACE')
        }),
    'sped-transport': dict(
        out='sped-transport-history.csv',
        what='special education transportation',
        parts={
            'system': re.compile(r'^Special Ed(?:ucation)? Transportation\b', re.I),
        }),
}

YEARS = re.compile(r'\bFY\s?(\d{2})\b')
# What the document calls each column. Only the budget kinds are kept. The layout is
# always a row of fiscal years followed by a row of column kinds, and both rows usually
# carry one extra trailing column -- "%", "increase", "Increase/Decrease" -- which is a
# computed change rather than a year, so the kinds are truncated to the number of years.
# "FINAL BUDGET" first, so it is read as one kind rather than as Final then Budget --
# the FY27 documents label their prior-year column that way and it is the settled figure.
KINDS = re.compile(r'\b(FINAL BUDGET|Actuals|Actual|Budgeted|Budget|Proposed|Requested|'
                   r'Recommended|Recommend|Adopted|Final|Approved)\b', re.I)
BUDGET_KINDS = {'budgeted', 'budget', 'final budget', 'proposed', 'requested',
                'recommended', 'recommend', 'adopted', 'final', 'approved'}
NUM = re.compile(r'\(?\$?\s?(\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?\)?')


def money(tok):
    return float(tok.replace(',', ''))


def columns(lines, i):
    """The column layout in force at line i, as [(fy, kind), ...].

    Read from the document's own two header rows rather than assumed from position. If
    the two rows cannot be lined up, this returns None and the caller skips the line --
    a guessed column is how actual spending gets into a budget series.
    """
    for j in range(i, max(-1, i - 400), -1):
        ys = YEARS.findall(lines[j])
        if len(ys) < 2:
            continue
        for k in range(j + 1, min(len(lines), j + 3)):
            ks = [m.group(1).lower() for m in KINDS.finditer(lines[k])]
            if len(ks) >= len(ys):
                return [(2000 + int(y), kind)
                        for y, kind in zip(ys, ks[:len(ys)])]
        return None
    return None


# Which stage of the budget a column represents. A year passes through several and they
# are not close together, so a series has to hold one of these constant.
#
#   proposed  what the superintendent or the town manager put forward for the coming year
#   settled   what that year's budget came to be, as reported once the year is in the past
#
# The settled figure is the one worth projecting on: it is what the district actually
# operated under, and it is the stage the FY27 workbook uses for its own prior-year
# columns. It can only be read from a document published in a LATER year, which is why
# this script reads each document for what it says about years other than its own.
def stage_of(fy, kind, doc_year):
    if doc_year is not None and fy < doc_year:
        return 'settled'
    return 'proposed'


DOC_YEAR = re.compile(r'\bFY\s?(\d{2})\b')


def document_year(lines):
    """The year a document is about, from its own title block."""
    head = ' '.join(lines[:6])
    m = DOC_YEAR.search(head)
    return 2000 + int(m.group(1)) if m else None


def scan(path, parts):
    lines = open(path, encoding='utf-8', errors='replace').read().split('\n')
    dy = document_year(lines)
    out = []
    for i, ln in enumerate(lines):
        for key, pat in parts.items():
            if not pat.match(ln.strip()):
                continue
            cols = columns(lines, i)
            if not cols:
                continue
            nums = [money(m.group(1)) for m in NUM.finditer(ln)]
            if len(nums) < len(cols):
                continue
            for (fy, kind), v in zip(cols, nums[:len(cols)]):
                if kind in BUDGET_KINDS:
                    out.append(dict(fy=fy, line=key, kind=kind, value=v,
                                    stage=stage_of(fy, kind, dy),
                                    doc=os.path.basename(path), docYear=dy))
    return out


def run(name, spec):
    obs = []
    for path in sorted(glob.glob(os.path.join(TEXT, '*.txt'))):
        obs += scan(path, spec['parts'])

    def pick(fy, line, stage):
        vals = [o for o in obs if o['fy'] == fy and o['line'] == line
                and o['stage'] == stage]
        if not vals:
            return None, False
        # A later document reporting the same settled year has had longer to stop moving.
        vals.sort(key=lambda o: (o['docYear'] or 0), reverse=True)
        return vals[0]['value'], len({v['value'] for v in vals}) > 1

    years = sorted({o['fy'] for o in obs})
    parts = list(spec['parts'])
    print(f"\n{spec['what'].upper()} — budget columns only, one stage at a time")
    print(f"{'FY':<6}{'settled':>14}{'proposed':>14}   parts present")
    rows = []
    for fy in years:
        cell, vals = {}, {}
        for stage in ('settled', 'proposed'):
            got = {k: pick(fy, k, stage) for k in parts}
            have = [k for k in parts if got[k][0] is not None]
            # A partial year is not a total. Summing three of five schools and calling it
            # the line is how a series acquires a fake collapse.
            total = sum(got[k][0] for k in have) if len(have) == len(parts) else None
            vals[stage] = dict(total=total, parts={k: got[k][0] for k in have},
                               disagree=any(got[k][1] for k in have), have=len(have))
            cell[stage] = f"{total:,.0f}" + ('*' if vals[stage]['disagree'] else '') \
                if total is not None else f'({len(have)}/{len(parts)})'
        print(f"FY{fy % 100:<4}{cell['settled']:>14}{cell['proposed']:>14}")
        rows.append((fy, vals))

    out = os.path.join(DATA, spec['out'])
    with open(out, 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['fy', 'stage'] + parts + ['total', 'documents_disagree'])
        for fy, vals in rows:
            for stage, v in vals.items():
                if v['total'] is None:
                    continue
                w.writerow([fy, stage] + [f"{v['parts'].get(k, 0):.0f}" for k in parts]
                           + [f"{v['total']:.0f}", int(v['disagree'])])
    print(f"wrote {out}")
    return rows


def main():
    print('Budget history from the mirrored district budget documents.')
    print('Budget columns only. Stage held constant. * = documents disagree at that '
          'stage; the latest is used.')
    for name, spec in GROUPS.items():
        run(name, spec)


if __name__ == '__main__':
    main()
