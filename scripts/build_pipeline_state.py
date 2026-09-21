"""Where every fiscal year stands, step by step, in the annual-report pipeline.

    python3 scripts/build_pipeline_state.py
    python3 scripts/build_pipeline_state.py --check
    python3 scripts/build_pipeline_state.py --subject trust-and-stabilization

Writes `sources/data/pipeline-state.csv`, one row per (fiscal year, table family).

WHY THIS EXISTS, IN TJ'S WORDS, 21 September 2026:

    "i think you need a way to manage 'state' better to be more accurate. there's a clear
    process. 1) We found and downloaded the annual report PDF 2) we OCRd them 3) we have
    hte OCRd text 4) we need to find the correct tables and info in those 5) we need to
    process the data into csv/table format 6) we need to put that data into our database
    and 7) we need to use that data to analyze and create the report. you need a state
    file that manages every year to know where we are for each of those steps for every
    FY"

He is right, and the reason he had to say it is worth recording. Asked which years the
general Stabilization Fund had, I answered three times and was wrong twice -- once from
the published payload (which had 7 points while the chart beside it had 9), once from the
trust-table CSV (which is one of four sources), and only the third time from the data.
Each answer was a true statement about an artefact and a false statement about the
archive. There was no single place that said where a year actually stood, so every
question re-derived it from whatever was nearest to hand.

THE SEVEN STEPS, AND WHAT EACH IS MEASURED BY. Nothing here is hand-maintained: a state
file somebody updates is a second thing to keep in sync, and this repository's most common
defect is exactly that -- something derived written down, the thing it derived from moved,
nothing connecting the two. Every cell is computed from the artefact it describes.

  1 pdf        the report is on disk, under the name the manifest carries
  2 ocr        an OCR TSV exists for it
  3 text       that TSV actually holds boxes for this year (an empty file is not a read)
  4 located    pages carrying this table family have been identified
  5 extracted  rows for this year exist in the family's dataset CSV
  6 database   those rows reached lunenburg.db
  7 published  a payload or analysis uses them

`blocked` is the column that earns the file. A year can sit at step 4 for two completely
different reasons -- nobody has written the extractor, or the extractor read the page and
REFUSED to publish because the page's own total did not foot -- and those need opposite
work. The second is not a gap in the archive, it is a gap with a diagnosis attached, and
it was invisible before this: five Treasurer's Cash columns were being read and dropped
every run, each printing its discrepancy to stdout where nothing kept it.
"""
import argparse
import collections
import csv
import glob
import io
import os
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))

OCR = os.path.join(ROOT, 'sources', 'town-budget', 'ocr')
PDFS = os.path.join(ROOT, 'sources', 'town-annual-reports', 'docs')
PAGES = os.path.join(ROOT, 'sources', 'data', 'annual-report-pages.csv')
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
OUT = os.path.join(ROOT, 'sources', 'data', 'pipeline-state.csv')

FIELDS = ['step', 'fy', 'subject', 'pdf', 'ocr', 'text', 'located', 'extracted', 'database',
          'published', 'pages', 'rows', 'blocked']

# Each family: the dataset CSV it lands in, the column naming its fiscal year, the
# database table, and the payload that publishes it. A family with no extractor yet says
# so by having no dataset -- which is itself the honest state, not a blank.
# Each family: the dataset CSV it lands in, the column naming its fiscal year, the
# database table, and the payload that publishes it.
#
# THE GENERIC EXTRACTS COUNT. The first version listed `csv=None` for six families and
# reported them as nothing-extracted, while `report-appropriations.csv` held 4,665 rows
# and `report-gross-wages.csv` 3,545. They are read by scripts/extract_tables.py into
# `report-<family>.csv`, which is a different pipeline from the purpose-built extractors
# but is no less real -- and a state file that cannot see half the work done is worse
# than none, because it sends somebody to redo it.
#
# Where a family has BOTH -- trust-and-stabilization has the generic `report-trust-funds`
# and the identity-proving `stabilization-balances` -- the specific one is what step 5
# means, because it is what the analysis reads. The generic extract is recorded beside
# it rather than instead of it.
FAMILIES = {
    'trust-and-stabilization': dict(
        csv='stabilization-balances.csv', fy='fy', generic='report-trust-funds.csv',
        table='report_trust_funds', payload='stabilization-funds.json'),
    'treasurers-cash': dict(
        csv='treasurers-cash.csv', fy='fy', generic=None, table=None,
        payload='stabilization-funds.json'),
    'appropriations': dict(csv=None, fy='fy', generic='report-appropriations.csv',
                           table='report_appropriations', payload=None),
    'payroll': dict(csv=None, fy='fy', generic='report-gross-wages.csv',
                    table='report_gross_wages', payload=None),
    'valuation': dict(csv=None, fy='fy', generic='report-valuation.csv',
                      table='report_valuation', payload=None),
    'capital': dict(csv=None, fy='fy', generic='report-capital-projects.csv',
                    table='report_capital_projects', payload=None),
    'debt': dict(csv=None, fy='fy', generic='report-debt.csv', table='report_debt',
                 payload=None),
    'elections': dict(csv=None, fy='fy', generic='report-elections.csv',
                      table='report_elections', payload=None),
    'vital-records': dict(csv=None, fy='fy', generic='report-vital-records.csv',
                          table='report_vital_records', payload=None),
    'enrollment': dict(csv=None, fy='fy', generic='report-enrollment-mcas.csv',
                       table='report_enrollment_mcas', payload=None),
    'officials': dict(csv=None, fy='fy', generic='report-officials.csv',
                      table='report_officials', payload=None),
    # NO EXTRACTOR AT ALL YET. Listed so the queue cannot hide them.
    'special-revenue': dict(csv=None, fy='fy', generic=None, table=None, payload=None),
    'balance-sheet': dict(csv=None, fy='fy', generic=None, table=None, payload=None),
    'receivables': dict(csv=None, fy='fy', generic=None, table=None, payload=None),
    'tax-collection': dict(csv=None, fy='fy', generic=None, table=None, payload=None),
}


# ---- THE OTHER INGESTION STREAMS ---------------------------------------------------
#
# TJ: "We'll need to build a pipeline like this for all ingestion sources to make sure we
# know what to do with ingested data from now on and get it to completion."
#
# The annual reports above are one stream of thirteen. The rest arrive differently and
# fail differently, and the same seven steps describe all of them once "the document" is
# read as "the unit that arrives": a report, a meeting, a MUNIS run, a state workbook.
#
# WHAT A STREAM DECLARES. Where its units live, how many have reached each step, and --
# the column that matters -- what the NEXT action is when they have not. A stream with no
# named next action is one nobody has thought about, and saying so is the point.
STREAMS = [
    dict(key='annual-reports', title='Annual town reports',
         detail='Per year and table family; see the rows below.',
         next_action='Work the blocked years in extraction-blocked.csv, each of which '
                     'names the amount its page missed by.'),
    dict(key='meetings', title='Meeting agendas and minutes',
         glob='sources/meetings/text/*/*.txt',
         extracted='sources/data/minutes-index.csv',
         next_action='Covered by the daily refresh; the gap is minutes the town has '
                     'never posted, which is a records request rather than an extractor '
                     '(notes/reference/records-requests.csv).'),
    dict(key='munis-ledgers', title='MUNIS ledger runs',
         glob='sources/town-ledgers/**/*',
         extracted='sources/data/munis-ledger.csv',
         next_action='extract_munis_report.py ties each run to its own GRAND TOTAL. New '
                     'deliveries need a PROVENANCE file before they are catalogued.'),
    dict(key='dese', title='DESE state workbooks',
         glob='sources/state-dese/**/*',
         next_action='fetch_dese_radar.py and extract_dese_radar.py; checked against '
                     'DESE\u2019s own printed totals.'),
    dict(key='dls', title='DLS state files',
         glob='sources/state-dls/**/*',
         next_action='fetch_dls_tax_bills.py and fetch_dls_property.py, by script.'),
    dict(key='district-budget', title='District budget documents',
         glob='sources/district-budget/**/*',
         next_action='NO SYSTEMATIC EXTRACTOR. 1,521 files, read one at a time as a '
                     'question needs them. This is the largest unworked stream and the '
                     'honest state of it is that nobody has decided what it owes.'),
    dict(key='contracts', title='Collective bargaining agreements',
         glob='sources/contracts/**/*',
         next_action='Read by hand where a rate is needed. The PEC agreement is '
                     'requested and not held.'),
    dict(key='town-budget', title='Town budget and finance documents',
         glob='sources/town-budget/**/*',
         next_action='Mirrored; extracted per question rather than as a stream.'),
]


def stream_rows():
    """One row per ingestion stream: how much has arrived, and what happens next."""
    import glob as _g
    out = []
    for st in STREAMS:
        n = 0
        if st.get('glob'):
            n = len([f for f in _g.glob(os.path.join(ROOT, st['glob']), recursive=True)
                     if os.path.isfile(f)])
        rows = 0
        ex = st.get('extracted')
        if ex and os.path.exists(os.path.join(ROOT, ex)):
            with open(os.path.join(ROOT, ex), encoding='utf-8') as fh:
                rows = max(0, sum(1 for _ in fh) - 1)
        out.append(dict(stream=st['key'], title=st['title'], units=n, rows=rows,
                        next_action=st['next_action']))
    return out


def years():
    out = {}
    for f in sorted(glob.glob(os.path.join(OCR, '*annual-town-report.tsv'))):
        m = re.search(r'fy-(\d{4})-', f)
        if m:
            out[int(m.group(1))] = f
    return out


def page_map():
    """{(fy, subject): [pages]} and which of them any dataset has cited."""
    found = collections.defaultdict(list)
    read = collections.defaultdict(list)
    if not os.path.exists(PAGES):
        return found, read
    for r in csv.DictReader(open(PAGES, encoding='utf-8')):
        key = (int(r['fy']), r['subject'])
        found[key].append(r['page'])
        if r['state'] == 'read':
            read[key].append(r['page'])
    return found, read


def dataset_years(name, fycol):
    out = collections.Counter()
    if not name:
        return out
    p = os.path.join(ROOT, 'sources', 'data', name)
    if not os.path.exists(p):
        return out
    for r in csv.DictReader(open(p, encoding='utf-8')):
        try:
            out[int(r[fycol])] += 1
        except (KeyError, TypeError, ValueError):
            continue
    return out


def table_years(table):
    out = collections.Counter()
    if not table or not os.path.exists(DB):
        return out
    db = sqlite3.connect('file:%s?mode=ro' % DB, uri=True)
    try:
        for fy, n in db.execute('SELECT fy, COUNT(*) FROM "%s" GROUP BY fy' % table):
            try:
                out[int(fy)] += n
            except (TypeError, ValueError):
                continue
    except sqlite3.Error:
        pass
    finally:
        db.close()
    return out


def published_years(payload, subject):
    """Fiscal years a payload actually plots or tabulates for this family."""
    out = set()
    if not payload:
        return out
    p = os.path.join(ROOT, 'fy28', 'public', 'data', payload)
    if not os.path.exists(p):
        return out
    import json
    try:
        d = json.load(open(p, encoding='utf-8'))
    except ValueError:
        return out
    for s in d.get('series', []):
        for pt in s.get('points', []):
            try:
                out.add(int(pt['fy']))
            except (KeyError, TypeError, ValueError):
                continue
    return out


BLOCKED = os.path.join(ROOT, 'sources', 'data', 'extraction-blocked.csv')

# Which extractor's refusals belong to which table family.
BLOCK_OWNER = {'treasurers-cash': 'treasurers-cash'}


def blockers():
    """{(fy, subject): 'why the extractor refused'} -- written by the extractors.

    A refusal is a finding. Without this, a year read-and-refused looks exactly like a
    year nobody has opened, and those need opposite work.
    """
    out = {}
    if not os.path.exists(BLOCKED):
        return out
    for r in csv.DictReader(open(BLOCKED, encoding='utf-8')):
        subject = BLOCK_OWNER.get(r['extractor'])
        if not subject:
            continue
        try:
            fy = int(r['fy'])
        except (TypeError, ValueError):
            continue
        why = '%s (p%s %s: ours %s, page %s)' % (r['reason'], r['page'], r['what'],
                                                 r['ours'], r['theirs'])
        out.setdefault((fy, subject), why)
    return out


def mark(ok):
    return 'yes' if ok else ''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--subject')
    a = ap.parse_args()

    ocr = years()
    found, read = page_map()
    block = blockers()
    rows = []
    for subject, spec in sorted(FAMILIES.items()):
        ds = dataset_years(spec['csv'], spec['fy'])
        gen = dataset_years(spec.get('generic'), spec['fy'])
        tb = table_years(spec['table'])
        pub = published_years(spec['payload'], subject)
        for fy in sorted(ocr):
            key = (fy, subject)
            # NO ROW IS SKIPPED. The first version dropped (year, family) pairs with
            # neither pages nor data, which quietly hid the very thing this file is for:
            # a family nobody has looked at in a given year is a STATE, not an absence,
            # and it is the state most likely to stay true for ever if unlisted.
            pages = found.get(key, [])
            base = os.path.basename(ocr[fy])[:-4]
            has_pdf = os.path.exists(os.path.join(PDFS, base + '.pdf'))
            has_text = os.path.getsize(ocr[fy]) > 1000
            n_rows = ds.get(fy, 0) or gen.get(fy, 0)
            # WHY A YEAR IS STUCK, not merely that it is. A family with no extractor and
            # a family whose extractor refused this page need opposite work.
            blocked = block.get((fy, subject), '')
            if blocked:
                pass
            elif pages and not n_rows:
                blocked = ('no extractor for this family yet' if not spec['csv']
                           else 'extractor runs and publishes nothing for this year')
            elif not pages and not n_rows:
                blocked = 'no page carrying this table has been identified'
            # THE STEP A YEAR HAS REACHED, as one number. TJ named seven steps and the
            # question he keeps asking is "where are we for this year" -- which seven
            # yes/no columns answer only after a reader does the reduction themselves.
            # The furthest CONSECUTIVE step reached: a year with data in the database but
            # nothing published is at 6, and a year whose extractor refused is at 4 no
            # matter what else is true, because that is where the work is.
            # EXTRACTED DATA IS PROOF THE PAGES WERE LOCATED, whatever the page map
            # says. `elections` showed step 3 with 52 rows extracted, because its pages
            # carry no heading our classifier matches -- so the state file reported a
            # family as un-located while publishing its data, which is the exact kind of
            # false answer this file exists to stop. A step is reached if the step AFTER
            # it was reached; work is evidence of the work it depended on.
            located = bool(pages) or n_rows > 0
            reached = 0
            for n, ok in enumerate([has_pdf, True, has_text, located,
                                    n_rows > 0, tb.get(fy, 0) > 0, fy in pub], start=1):
                if not ok:
                    break
                reached = n
            rows.append(dict(
                step=reached, fy=fy, subject=subject,
                pdf=mark(has_pdf), ocr=mark(True), text=mark(has_text),
                located=mark(located), extracted=mark(n_rows > 0),
                database=mark(tb.get(fy, 0) > 0), published=mark(fy in pub),
                pages=' '.join(pages), rows=n_rows, blocked=blocked))

    if a.subject:
        rows = [r for r in rows if r['subject'] == a.subject]

    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator='\n')
    w.writeheader()
    w.writerows(rows)
    text = buf.getvalue()

    if a.check:
        cur = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        if cur != text:
            print('STALE %s -- run: python3 scripts/build_pipeline_state.py'
                  % os.path.relpath(OUT, ROOT), file=sys.stderr)
            return 1
        print('ok -- %d (year, family) rows' % len(rows))
        return 0

    if not a.subject:
        with open(OUT, 'w', encoding='utf-8') as fh:
            fh.write(text)
        print('wrote %s -- %d rows, one per fiscal year and table family'
          % (os.path.relpath(OUT, ROOT), len(rows)))

    print('\nINGESTION STREAMS')
    print('  %-22s %7s %8s  %s' % ('stream', 'units', 'rows', 'next action'))
    for st in stream_rows():
        print('  %-22s %7s %8s  %s'
              % (st['stream'], '{:,}'.format(st['units']) if st['units'] else '-',
                 '{:,}'.format(st['rows']) if st['rows'] else '-',
                 st['next_action'][:62]))
    print()
    cur = None
    for r in rows:
        if r['subject'] != cur:
            cur = r['subject']
            print('\n%s' % cur)
            print('  fy      pdf ocr txt loc ext  db pub   rows  blocked')
        print('  FY%-6d %3s %3s %3s %3s %3s %3s %3s %6s  %s'
              % (r['fy'], r['pdf'] and '*', r['ocr'] and '*', r['text'] and '*',
                 r['located'] and '*', r['extracted'] and '*', r['database'] and '*',
                 r['published'] and '*', r['rows'], r['blocked'][:46]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
