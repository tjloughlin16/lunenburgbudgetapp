#!/usr/bin/env python3
"""THE CHERRY SHEET: every line of state aid and every state assessment, per town and per
regional school district, from the Division of Local Services.

    python3 scripts/fetch_dls_cherry_sheet.py            # fetch every year, ingest, extract
    python3 scripts/fetch_dls_cherry_sheet.py --recent   # this FY, the two before, and newer: the refresh's
    python3 scripts/fetch_dls_cherry_sheet.py --check    # the extract still reproduces

WHY THIS EXISTS. TJ, on the argument this town keeps having about regionalising: *"transportation
is the big one. are regional schools saving or paying for transportation? The argument is,
transportation funding is a LOT for regional schools, earning a lot from the state."* He was
right that it matters and this project could not measure it: DESE's per-pupil categories carry
no transportation line at all, and Chapter 70 is the same formula whether a town is regional or
not. The money that DOES follow from being regional is a CHERRY SHEET line -- `Regional
Transportation`, paid under M.G.L. c.71 s.16C to regional districts and to nobody else.

FINDING THE REPORT TOOK A PERSON. Nine plausible `rdReport=` names were tried and refused, and
mass.gov answers 403 to a script. TJ found the address. Recorded here because the lesson
generalises: the DLS Gateway does not publish its own catalogue, so a report nobody has linked
is unreachable by guessing, and the honest move is to ask rather than to conclude the data does
not exist.

THE EXPORT IS A TWO-STEP, which is why the earlier DLS fetchers' pattern does not work here.
Posting the form returns a 302 to a one-time `/rdDownload/rdExport-<guid>/CherrySheet.xlsx`, and
that URL only answers inside the session that created it. So: open the report to get a cookie,
post the form with that cookie, follow the redirect with it.

WHAT IT HOLDS. Two populations -- MUNICIPALITIES and REGIONAL SCHOOLS -- each with RECEIPTS
(money from the state) and ASSESSMENTS (money owed to it), for every fiscal year the Gateway
offers. The regional receipts sheet is the one that answers the question above; it carries
Chapter 70, Regional Transportation, Charter Tuition Reimbursement and School Choice Receiving
Tuition side by side.

AND `Final Budget` IS THE ONE TO READ. The form also offers the Governor's, House, Senate and
Conference versions of each year -- proposals, not money. The final is what was appropriated.
A year with no final budget yet returns the header and no rows, and is skipped rather than
recorded as a year with no aid.
"""
import argparse
import csv
import datetime
import http.cookiejar
import io
import os
import re
import sys
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from fetch_dls_tax_bills import land_export, newest_export   # noqa: E402

REPORT = 'CherrySheets.CherrySheet_detail'
PAGE = 'https://dls-gw.dor.state.ma.us/reports/rdPage.aspx?rdReport=' + REPORT
EXPORT = (PAGE + '&rdReportFormat=NativeExcel&rdExportTableID=xtCherrySheet'
          '&rdExportFilename=CherrySheet&rdShowGridlines=True&rdExcelOutputFormat=Excel2007')
OUT_DIR = os.path.join(ROOT, 'sources', 'state-dls')
OUT_CSV = os.path.join(ROOT, 'sources', 'data', 'dls-cherry-sheet.csv')
# PROVENANCE ONE ROW PER WORKBOOK, NOT ONE PER FIGURE. The first version carried the source
# filename and its sha256 on every one of 235,254 rows -- 30 MB of a 46 MB file to say 72
# things. A row's workbook is fully determined by its year, population and direction, so the
# mapping lives here and the data file keeps the data.
SRC_CSV = os.path.join(ROOT, 'sources', 'data', 'dls-cherry-sheet-sources.csv')
INDEX = os.path.join(ROOT, 'sources', 'state-dls', 'index.csv')
UA = {'User-Agent': 'Mozilla/5.0 (lunenburgbudgetproject.org research)', 'Referer': PAGE}
BUDGET = 'Final Budget'
COLS = ['fy', 'population', 'flow', 'dor_code', 'name', 'line', 'amount']
SRC_COLS = ['fy', 'population', 'flow', 'source_file', 'sha256', 'rows']
POPULATIONS = ('Municipalities', 'Regional Schools')
FLOWS = ('Receipts', 'Assessments')
# Between requests. Each export already takes the Gateway about seven seconds to build
# (measured 28 October 2026), so this is courtesy rather than throttling.
PAUSE = 1.0


def opener():
    """One session. The download URL the form hands back is scoped to its cookie."""
    jar = http.cookiejar.CookieJar()
    o = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    o.addheaders = list(UA.items())
    o.open(PAGE, timeout=120).read()
    return o


def years(o):
    html = o.open(PAGE, timeout=120).read().decode('utf-8', 'replace')
    m = re.search(r'<SELECT[^>]*NAME="islYear".*?</SELECT>', html, re.S | re.I)
    if not m:
        raise SystemExit('the cherry sheet form has no year list -- the report has moved')
    ys = sorted(set(re.findall(r'VALUE="(\d{4})"', m.group(0))))
    if len(ys) < 10:
        raise SystemExit('the form offered %d years; expected the full run' % len(ys))
    return ys


def fetch_one(o, fy, population, flow):
    fields = [('islYear', fy), ('islCherryType', population), ('islRecChrg', flow),
              ('islBudgetType', BUDGET), ('rdreport', REPORT.lower()), ('lgxver', '')]
    req = urllib.request.Request(EXPORT, data=urllib.parse.urlencode(fields).encode(),
                                 headers=UA)
    data = o.open(req, timeout=180).read()
    if not data.startswith(b'PK'):
        return None
    return data


def read_sheet(blob, fy, population, flow):
    """One export, long -- a row per place per LINE, because the columns differ by year.

    The sheet is a crosstab: a row per municipality or district and a column per aid or
    assessment programme, and WHICH programmes exist changes between years as the Legislature
    adds and retires them. Storing it wide would need a schema migration every time that
    happened and would silently drop a new programme. Long survives it."""
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(blob), read_only=True, data_only=True)
    ws = wb.worksheets[0]
    rows_ = list(ws.iter_rows(values_only=True))
    if len(rows_) < 3:
        return []
    head = [str(c).strip() if c is not None else '' for c in rows_[0]]
    if not head or 'DOR Code' not in head[0]:
        raise SystemExit('%s FY%s: the first column is %r, not DOR Code'
                         % (population, fy, head[0]))
    out = []
    for r in rows_[1:]:
        if not r or r[0] is None or not str(r[1] or '').strip():
            continue
        for i, col in enumerate(head[2:], start=2):
            if not col:
                continue
            v = r[i] if i < len(r) else None
            if v in (None, ''):
                continue
            try:
                amount = float(v)
            except (TypeError, ValueError):
                continue
            out.append(dict(fy=int(fy), population=population, flow=flow,
                            dor_code=str(r[0]).strip(), name=str(r[1]).strip(),
                            line=col, amount=amount))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--recent', action='store_true',
                    help='only the current fiscal year, the two before it and any newer: the scheduled run')
    a = ap.parse_args()
    if a.check:
        if not os.path.exists(OUT_CSV):
            print('STALE %s does not exist' % os.path.relpath(OUT_CSV, ROOT))
            return 1
        have = list(csv.DictReader(open(OUT_CSV, encoding='utf-8')))
        src = list(csv.DictReader(open(SRC_CSV, encoding='utf-8')))
        files = {r['source_file'] for r in src}
        # EVERY ROW MUST TRACE TO A WORKBOOK. With provenance in a sidecar, a row whose
        # year-population-direction is not in it has no source at all, which is worse than a
        # missing file and would be invisible without this.
        keys = {(r['fy'], r['population'], r['flow']) for r in src}
        orphan = {(r['fy'], r['population'], r['flow']) for r in have} - keys
        if orphan:
            print('STALE \u2014 %d group(s) of rows have no workbook recorded: %s'
                  % (len(orphan), sorted(orphan)[:3]))
            return 1
        missing = [f for f in files if not os.path.exists(os.path.join(OUT_DIR, f))]
        if missing:
            print('STALE — %d source workbook(s) missing: %s'
                  % (len(missing), ', '.join(sorted(missing)[:3])))
            return 1
        print('ok — %s: %s rows from %d workbook(s), all present'
              % (os.path.relpath(OUT_CSV, ROOT), '{:,}'.format(len(have)), len(files)))
        return 0

    import hashlib
    import time

    o = opener()
    ys = years(o)
    # WHICH YEARS TO ASK FOR, FROM TODAY'S DATE. `--recent` is the refresh's command: a final
    # cherry sheet for a year long closed does not move, and asking for all of them is 72
    # requests at seven seconds each -- most of the ten minutes a scheduled job is allowed --
    # to confirm that FY2010 is still FY2010. The window is the fiscal year we are in, the two
    # before it (a final can still be corrected after its year closes) and anything newer the
    # form offers. A bare run still asks for every year, as it always has.
    if a.recent:
        today = datetime.date.today()
        fy_now = today.year + (1 if today.month >= 7 else 0)
        ask = [y for y in ys if int(y) >= fy_now - 2]
    else:
        ask = ys
    held = {(r['fy'], r['population'], r['flow']): r
            for r in (csv.DictReader(open(SRC_CSV, encoding='utf-8')) if os.path.exists(SRC_CSV) else [])}
    groups = {}
    if os.path.exists(OUT_CSV):
        for r in csv.DictReader(open(OUT_CSV, encoding='utf-8')):
            groups.setdefault((r['fy'], r['population'], r['flow']), []).append(r)
    sources = dict(held)
    changed, refused, empty = [], [], []
    for fy in ask:
        for population in POPULATIONS:
            for flow in FLOWS:
                g = (fy, population, flow)
                time.sleep(PAUSE)
                blob = fetch_one(o, fy, population, flow)
                rows_ = read_sheet(blob, fy, population, flow) if blob is not None else []
                # NOTHING BACK IS ONLY "NOT YET PUBLISHED" FOR A YEAR WE HAVE NEVER HELD. For
                # a group the extract already carries, an error page or an empty sheet means
                # this run could not see it, and the old code dropped its rows from the CSV
                # without a word. Now it is refused, and the run exits non-zero so the refresh
                # retries tomorrow instead of recording a look that did not happen.
                if not rows_:
                    if g in held:
                        refused.append('%s %s %s (%s)' % (fy, population, flow,
                                       'not a workbook' if blob is None else 'no rows'))
                    else:
                        empty.append('%s %s %s' % g)
                    continue
                stem = 'CherrySheet-%s-%s-%s' % (fy, population.replace(' ', ''), flow)
                current = (os.path.join(OUT_DIR, held[g]['source_file']) if g in held
                           else newest_export(OUT_DIR, stem, '.xlsx'))
                # An empty sheet is never landed (above), and an unchanged one is not landed
                # twice: the Gateway re-zips every export with the request's time, so it is
                # the CONTENT that is compared -- land_export in fetch_dls_tax_bills.py.
                key, moved = land_export(stem, '.xlsx', blob, EXPORT, current=current)
                if moved:
                    changed.append(key)
                name = os.path.basename(key)
                with open(os.path.join(OUT_DIR, name), 'rb') as fh:
                    digest = hashlib.sha256(fh.read()).hexdigest()
                groups[g] = rows_
                sources[g] = dict(fy=int(fy), population=population, flow=flow,
                                  source_file=name, sha256=digest, rows=len(rows_))
    if refused:
        raise SystemExit('the cherry sheet form did not answer for %d group(s) the extract '
                         'already holds; nothing rewritten: %s' % (len(refused), '; '.join(refused[:6])))
    if not groups:
        raise SystemExit('nothing came back from the cherry sheet form')
    if not changed and os.path.exists(OUT_CSV):
        print('unchanged: %d workbook(s) asked for, FY%s-FY%s; every one says what its held copy '
              'says. Nothing landed, nothing rewritten.'
              % (len(ask) * len(POPULATIONS) * len(FLOWS) - len(empty), ask[0], ask[-1]))
        if empty:
            print('  no %s published for: %s' % (BUDGET, ', '.join(empty[:6])))
        return 0
    order = sorted(groups, key=lambda g: (int(g[0]), POPULATIONS.index(g[1]), FLOWS.index(g[2])))
    all_rows = [r for g in order for r in groups[g]]
    got = len(order)
    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        w.writerows(all_rows)
    with open(SRC_CSV, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=SRC_COLS)
        w.writeheader()
        w.writerows(sources[g] for g in order)
    ys = sorted({g[0] for g in order}, key=int)

    rows_idx = [r for r in csv.DictReader(open(INDEX, encoding='utf-8'))
                if not r['local'].startswith('state-dls/CherrySheet-')] \
        if os.path.exists(INDEX) else []
    rows_idx.append(dict(
        local='state-dls/CherrySheet-*.xlsx', url=EXPORT,
        title='Cherry Sheet detail by programme, municipalities and regional school '
              'districts, FY%s–FY%s' % (ys[0], ys[-1]),
        note='DLS Gateway export, one workbook per year, population and direction; %s only. '
             'The form POST returns a 302 to a session-scoped download. Report address found '
             'by TJ; it is not linked from the Gateway front page.' % BUDGET))
    with open(INDEX, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=['local', 'url', 'title', 'note'])
        w.writeheader()
        w.writerows(rows_idx)

    print('%s: %s rows from %d workbooks, FY%s–FY%s'
          % (os.path.relpath(OUT_CSV, ROOT), '{:,}'.format(len(all_rows)), got,
             ys[0], ys[-1]))
    print('  %d line item(s); %d place(s)'
          % (len({r['line'] for r in all_rows}), len({r['name'] for r in all_rows})))
    if empty:
        print('  no %s published for: %s%s'
              % (BUDGET, ', '.join(empty[:6]), ' ...' if len(empty) > 6 else ''))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
