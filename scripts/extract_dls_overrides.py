#!/usr/bin/env python3
"""EVERY PROPOSITION 2½ REFERENDUM THE STATE RECORDS, all 351 towns, FY1990 onward.

    python3 scripts/extract_dls_overrides.py          # extract to sources/data/dls-override-votes.csv
    python3 scripts/extract_dls_overrides.py --check   # the extract still reproduces from the workbook

WHERE IT COMES FROM, and what we do not have. The workbook is the Division of Local
Services' `Override and Underride Votes` report, exported from the DLS Gateway and supplied
to this project by TJ on 25 September 2026. **The direct export address is not recorded**,
because we did not make the request: the report is not linked from the Gateway's front page
and nine plausible `rdReport=` names were tried and refused. So rule 12 is met the way rule
12 says to meet it when there is no link -- by saying what produced it and keeping the
PUBLISHER'S OWN FILENAME, `OverrideUnderrideVotes.xlsx`, which is the name a resident asks
DLS for. It is not called `public`.

WHAT IT HOLDS, one row per question on a ballot: the town, the fiscal year the vote was for,
the date it was held, whether it won, the yes and no tallies, whether it was an override or
an underride, the department, the description as printed, and the amount.

    4,743 questions, 305 of the 351 municipalities, FY1990-FY2029.

THE RECONCILIATION. The workbook states an identity about itself: `Win / Loss` is `WIN`
exactly when the yes votes exceed the no votes. It holds in all 4,743 rows, and this refuses
to write if it ever stops -- which is what makes the tallies safe to quote beside the result.

WHAT IT IS NOT. An override is a permanent increase in the levy LIMIT, so a won override
raises what the town may levy for ever after; a debt or capital exclusion sits outside the
limit for the life of the borrowing and is NOT in this report. A row is a question put, not a
dollar raised: the amount is what the question asked for, and a town that won an override may
levy less than its limit allows. Rule 11's caution applies whole -- none of this is a cost.
"""
import argparse
import csv
import hashlib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'sources', 'state-dls', 'OverrideUnderrideVotes.xlsx')
OUT = os.path.join(ROOT, 'sources', 'data', 'dls-override-votes.csv')
INDEX = os.path.join(ROOT, 'sources', 'state-dls', 'index.csv')

HEAD = ['DOR Code', 'Municipality', 'Fiscal Year', 'Vote Date', 'Win / Loss', 'Yes Votes',
        'No Votes', 'Vote Type', 'Department', 'Description', 'Amount']
COLS = ['dor_code', 'municipality', 'fy', 'vote_date', 'result', 'yes_votes', 'no_votes',
        'vote_type', 'department', 'description', 'amount', 'source_file', 'sha256']


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def num(v):
    """A vote tally. Printed with thousands separators, never fractional."""
    if v in (None, ''):
        return ''
    return int(str(v).replace(',', '').strip())


def money(v):
    """An amount asked for. SOME CARRY CENTS -- $641,448.76 is a real row -- so this may
    not go through `num`, which is the mistake this comment exists to stop repeating."""
    if v in (None, ''):
        return ''
    f = float(str(v).replace(',', '').replace('$', '').strip())
    return int(f) if f == int(f) else round(f, 2)


def extract():
    import openpyxl
    wb = openpyxl.load_workbook(SRC, read_only=True)
    rows = list(wb.worksheets[0].iter_rows(values_only=True))
    head = [str(c or '').strip() for c in rows[0]]
    if head != HEAD:
        raise SystemExit('the workbook’s columns moved: %s' % head)
    digest = sha256(SRC)
    base = os.path.basename(SRC)
    out, disagree = [], 0
    for r in rows[1:]:
        if not r or not r[1]:
            continue
        date = r[3]
        out.append(dict(
            dor_code=str(r[0] or '').strip(), municipality=str(r[1]).strip(), fy=int(r[2]),
            vote_date=(date.date().isoformat() if hasattr(date, 'date') else str(date or '')[:10]),
            result=str(r[4] or '').strip(), yes_votes=num(r[5]), no_votes=num(r[6]),
            vote_type=str(r[7] or '').strip(), department=str(r[8] or '').strip(),
            description=str(r[9] or '').strip(), amount=money(r[10]),
            source_file=base, sha256=digest))
        y, n = out[-1]['yes_votes'], out[-1]['no_votes']
        if y != '' and n != '' and (out[-1]['result'] == 'WIN') != (y > n):
            disagree += 1
    # THE WORKBOOK'S OWN IDENTITY. It holds in all 4,743 rows as received; a row where the
    # result contradicts the tally means one of the three was misread, and none of them may
    # then be quoted. Refuse rather than publish a tally beside a result it does not support.
    if disagree:
        raise SystemExit('%d row(s) where Win / Loss disagrees with the yes and no votes' % disagree)
    return out


def write_index():
    rows = [r for r in csv.DictReader(open(INDEX, encoding='utf-8'))
            if r['local'] != 'state-dls/OverrideUnderrideVotes.xlsx'] if os.path.exists(INDEX) else []
    rows.append(dict(
        local='state-dls/OverrideUnderrideVotes.xlsx', url='',
        title='Override and Underride Votes, all municipalities, FY1990–FY2029',
        note=('Division of Local Services Gateway report, exported by the publisher’s own '
              'name; obtained from TJ 25 September 2026. NO export address recorded — the '
              'report is not linked from the Gateway front page. Ask DLS for '
              '"Override and Underride Votes".')))
    with open(INDEX, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=['local', 'url', 'title', 'note'])
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    rows = extract()
    if a.check:
        have = list(csv.DictReader(open(OUT, encoding='utf-8'))) if os.path.exists(OUT) else []
        same = [{k: str(v) for k, v in r.items()} for r in rows] == have
        print('ok — %s reproduces from %s' % (os.path.relpath(OUT, ROOT), os.path.basename(SRC))
              if same else 'STALE %s — run extract_dls_overrides.py' % os.path.relpath(OUT, ROOT))
        return 0 if same else 1
    with open(OUT, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    write_index()
    wins = sum(1 for r in rows if r['result'] == 'WIN')
    print('%s: %d questions, %d municipalities, FY%d–FY%d; %d won, %d lost'
          % (os.path.relpath(OUT, ROOT), len(rows), len({r['municipality'] for r in rows}),
             min(r['fy'] for r in rows), max(r['fy'] for r in rows), wins, len(rows) - wins))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
