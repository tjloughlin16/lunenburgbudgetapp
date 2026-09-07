#!/usr/bin/env python3
"""What the annual reports contain that we have NOT read, or have read and not checked.

    python3 scripts/build_extraction_gaps.py
    python3 scripts/build_extraction_gaps.py --check

Writes `notes/reference/EXTRACTION-GAPS.md`.

WHY THIS EXISTS

TJ asked the question this file answers, and he asked it for a good reason: the special
revenue schedule sat for days marked `check failed` on every one of its fifteen years, and
the label was correct, published, and completely inert. Nobody had put the extract next to
the page. When somebody finally did, the pages turned out to be pristine and the whole year
reconciled to the penny on the first attempt.

So the honest question is not "is there a gap" but **"what else looks like that"** — and a
count nobody maintains is the only kind that stays true. Every figure here is read from the
database at build time.

THE THREE KINDS OF GAP, WHICH ARE NOT THE SAME THING

  NOT READ        the reports contain a table and no dataset holds it. Visible only by
                  comparing the survey against the datasets, which nothing did before.
  READ, UNCHECKED `no check` — extracted from a table that prints no total to verify
                  against. Not doubtful; simply unverifiable by arithmetic.
  READ, FAILING   `check failed` — extracted, and the columns do not sum to the total the
                  report prints. THIS is the category that misleads, because it looks like
                  a property of the data and is usually a property of the instrument.

The third is where special revenue lived. It is the one to work through first.
"""

import argparse
import collections
import json
import os
import sqlite3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
OUT = os.path.join(ROOT, 'notes', 'reference', 'EXTRACTION-GAPS.md')
# The same figures, for the page that states them to a resident rather than to a reader of
# this repository. Published as a static file so /what-we-cannot-answer spends no D1 read
# budget, and emitted HERE rather than recomputed in TSX: two implementations of one count
# is two counts, and they disagree on the day one of them is edited.
JSON_OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'extraction-gaps.json')

# Which dataset holds each family the page survey found. `None` means the survey found the
# table in the reports and nothing was ever built to read it -- which is the finding, so it
# is declared here rather than inferred from a name that happens not to match.
FAMILY = {
    'appropriations': 'report_appropriations',
    'capital_project': 'report_capital_projects',
    'debt': 'report_debt',
    'receipts': 'annual_report_receipts',
    'special_revenue': 'special_revenue_funds',
    'trust_funds': 'report_trust_funds',
    'valuation': 'report_valuation',
    'payroll': 'report_gross_wages',
    'staff_roster': 'staff_roster_entries',
    'school_report': 'report_enrollment_mcas',
    'enterprise': None,
    'tax_rate': None,
    'town_meeting': None,
    'balance_sheet': None,
}

# What each never-extracted family is, and why its absence costs something. Module level so
# the Markdown and the published JSON carry one text rather than two.
NOTE = {
    'enterprise': 'The four enterprise funds — water, sewer, solid waste, PEG access. '
                  'CLAUDE.md calls these the **control case**: they are the part of '
                  'the town where money in and money out CAN be traced, which is what '
                  'proves the general fund’s opacity is a property of a general '
                  'fund rather than sloppy record-keeping. Fifteen years of them are '
                  'unread.',
    'town_meeting': 'What Town Meeting actually voted, article by article. The '
                    'appropriation is the OUTPUT of these votes, and the archive '
                    'currently holds the output and not the decision.',
    'balance_sheet': 'The combining balance sheet — what the town HOLDS, against the '
                     'flow tables the archive already has. `pdf_tables.py` names this '
                     'page specifically as one where plain extraction mode wins and '
                     'layout mode recovers zero of its 61 money tokens.',
    'tax_rate': 'The tax rate by class and year. Small, and it is the number every '
                'resident actually feels.',
}


def collect(c):
    """Every figure this file states, computed once.

    The Markdown below and the JSON the site reads are two renderings of THIS, so there is
    no arithmetic in either of them to drift apart."""
    stat = {}
    for (t,) in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
        cols = {d[1] for d in c.execute('PRAGMA table_info("%s")' % t)}
        if 'status' not in cols:
            continue
        got = {r['status']: r['n'] for r in
               c.execute('SELECT status, COUNT(*) n FROM "%s" GROUP BY status' % t)}
        if sum(got.values()):
            stat[t] = (got.get('checked', 0), got.get('check failed', 0),
                       got.get('no check', 0))
    tot = [sum(x) for x in zip(*stat.values())]

    fams = collections.Counter()
    figrows = collections.Counter()
    for r in c.execute('SELECT [table] f, figure_rows n FROM annual_report_contents'):
        fams[r['f']] += 1
        try:
            figrows[r['f']] += int(r['n'] or 0)
        except (TypeError, ValueError):
            pass
    missing = sorted(((f, fams[f], figrows[f]) for f in fams if FAMILY.get(f) is None),
                     key=lambda x: -x[2])

    d = {
        'about': 'What the annual reports contain that we have not read, or have read and '
                 'not checked against a total the report itself prints. Generated by '
                 'scripts/build_extraction_gaps.py; the long form is '
                 'notes/reference/EXTRACTION-GAPS.md.',
        'checked': tot[0], 'checkFailed': tot[1], 'noCheck': tot[2], 'rows': sum(tot),
        'datasets': [
            {'dataset': t, 'checked': ok, 'checkFailed': bad, 'noCheck': none,
             # True where NOT ONE row of the dataset has been recomputed against a printed
             # total. It is the ⚠ in the Markdown table and it is the whole finding.
             'nothingChecked': ok == 0}
            for t, (ok, bad, none) in sorted(stat.items(), key=lambda kv: -sum(kv[1]))],
        'neverExtracted': [
            {'family': f, 'years': n, 'figureRows': rr, 'dataset': None,
             'whyItMatters': NOTE.get(f)}
            for f, n, rr in missing],
        'neverExtractedRows': sum(x[2] for x in missing),
        'catalogued': c.execute('SELECT COUNT(*) FROM annual_report_catalogue').fetchone()[0],
        'readIntoADataset': c.execute('SELECT COUNT(*) FROM annual_report_contents').fetchone()[0],
        'byDifficulty': [
            {'judgement': r['extractable'] or '(unstated)', 'tables': r['n'],
             'rows': r['rr'] or 0}
            for r in c.execute("""SELECT extractable, COUNT(*) n,
                                         SUM(CAST(approx_rows AS INT)) rr
                                  FROM annual_report_catalogue GROUP BY extractable
                                  ORDER BY n DESC""")],
    }
    if not d['datasets'] or not d['neverExtracted']:
        # A join that matches nothing looks exactly like data that is absent, and an empty
        # gap page would read as "no gaps" — the one thing this file must never say wrongly.
        raise SystemExit('build_extraction_gaps: the database returned no datasets or no '
                         'never-extracted families. That is a broken query, not an archive '
                         'with nothing missing.')
    return d


def db():
    if not os.path.exists(DB):
        raise SystemExit(f'{DB} missing. Run: python3 scripts/build_db.py')
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def render(d):
    L = []
    a = L.append
    a('# What we have not read, and what we have read without checking\n')
    a('**Generated by `scripts/build_extraction_gaps.py`. Do not edit.**\n')

    # ---------- status across every extract
    tot = [d['checked'], d['checkFailed'], d['noCheck']]
    total = d['rows']

    a(f'## The headline: **{tot[0]:,} of {total:,} extracted rows are checked**\n')
    a(f'Checked means the extract was recomputed against a total the report itself prints '
      f'and agreed with it. {tot[1]:,} rows come from a table whose columns do **not** sum '
      f'to its printed total; {tot[2]:,} come from a table that prints no total to check '
      f'against.\n')
    a('| dataset | checked | check failed | no check |')
    a('|---|---:|---:|---:|')
    for r in d['datasets']:
        mark = ' ⚠' if r['nothingChecked'] else ''
        a(f'| `{r["dataset"]}`{mark} | {r["checked"]:,} | {r["checkFailed"]:,} '
          f'| {r["noCheck"]:,} |')
    a(f'| **total** | **{tot[0]:,}** | **{tot[1]:,}** | **{tot[2]:,}** |')
    a('\n⚠ marks a dataset where **nothing** is checked.\n')

    # ---------- families surveyed and never extracted
    a('\n## Surveyed in every report, and never extracted at all\n')
    missing = [(r['family'], r['years'], r['figureRows']) for r in d['neverExtracted']]
    a('These were found by reading all sixteen annual reports page by page, counted, and '
      'recorded in `annual_report_contents`. **No dataset holds any of them.** They are '
      'mentioned in `extraction_plan`, so this is work not done rather than work '
      'considered and declined.\n')
    a('| family | years it appears in | figure rows counted | dataset |')
    a('|---|---:|---:|---|')
    for f, n, rr in missing:
        a(f'| `{f}` | {n} | {rr:,} | **none** |')
    a(f'| **total** | | **{d["neverExtractedRows"]:,}** | |')

    a('\nWhat each one is, and why it matters here:\n')
    for f, _, _ in missing:
        if NOTE.get(f):
            a(f'- **`{f}`** — {NOTE[f]}')

    # ---------- catalogue vs contents
    n_cat = d['catalogued']
    n_read = d['readIntoADataset']
    a(f'\n## The wider count\n')
    a(f'`annual_report_catalogue` holds **{n_cat:,}** tables found by reading the reports '
      f'end to end. `annual_report_contents` records **{n_read:,}** that have been read '
      f'into a dataset. The catalogue is a list of what EXISTS and the difference is not '
      f'all loss — many catalogued rows are the same table across pages, and some are '
      f'prose. But it is not nothing either, and nothing had ever compared the two.\n')
    a('| how hard the survey judged it | tables | rows |')
    a('|---|---:|---:|')
    for r in d['byDifficulty']:
        a(f'| {r["judgement"]} | {r["tables"]:,} | {r["rows"]:,} |')

    # ---------- the lesson
    a('\n## Why this went unnoticed, which is the part worth keeping\n')
    a('The special revenue schedule was extracted, catalogued, loaded into the database '
      'and published — carrying the label `0 checked / 2,058 failed`. Everything worked. '
      'Four things then had to line up for fifteen years of data to sit unusable:\n')
    a('1. **`status` did its job, and that was the problem.** The rule is that nothing may '
      'be aggregated without splitting on it, so the bad data was never quietly used. But '
      'SAFE and FIXED are different, and a well-behaved status column lets a gap sit '
      'forever because nothing ever breaks.\n')
    a('2. **Nobody asked why it failed.** `v1: 6,355,758.65 vs printed 6,414,742.67` reads '
      'like messy data. It was 99% correct data with a handful of dropped cells.\n')
    a('3. **The extractor had been crashing**, so it could not be re-run to investigate — '
      'and it was not in `check_generated.py`, so the crash itself was invisible.\n')
    a('4. **Two OCR products, only one with anything in it.** The plain text layer for '
      'those pages holds 21 characters, the page number. The `--boxes` geometry had the '
      'real content. Anyone spot-checking the obvious file would have concluded the pages '
      'were blank scans.\n')
    a('> The thing that broke it open was looking at the page. Rule 13 says quote the '
      'source rather than your rendering of it, and this project had applied that to '
      'every figure except the ones an instrument had already given up on.\n')
    return '\n'.join(L) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    d = collect(db())
    fresh = render(d)
    blob = json.dumps(d, indent=1, ensure_ascii=False) + '\n'
    rel = os.path.relpath(OUT, ROOT)
    jrel = os.path.relpath(JSON_OUT, ROOT)
    if args.check:
        for path, want, name in ((OUT, fresh, rel), (JSON_OUT, blob, jrel)):
            if not os.path.exists(path):
                raise SystemExit(f'{name} does not exist. Run without --check.')
            if open(path, encoding='utf-8').read() != want:
                raise SystemExit(f'STALE: {name} no longer reproduces.\n'
                                 f'  Run: python3 scripts/build_extraction_gaps.py')
        print(f'ok: {rel} and {jrel} still reproduce')
        return
    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write(fresh)
    with open(JSON_OUT, 'w', encoding='utf-8') as fh:
        fh.write(blob)
    print(f'wrote {rel} ({len(fresh):,} bytes) and {jrel} ({len(blob):,} bytes)')


if __name__ == '__main__':
    main()
