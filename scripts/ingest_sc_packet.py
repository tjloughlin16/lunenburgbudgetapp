#!/usr/bin/env python3
"""The School Committee's packet for its meeting of 21 October 2026, as TJ downloaded it.

    python3.11 scripts/ingest_sc_packet.py ~/Downloads/'10-21-26 SC Meeting-20261118T195513Z-1-001.zip'
    python3.11 scripts/ingest_sc_packet.py ZIP --dry-run
    python3.11 scripts/ingest_sc_packet.py --check

HOW IT REACHED US. A Google Drive folder named `10-21-26 SC Meeting`, shared with TJ and
downloaded by him as one archive on 18 November 2026 (the timestamp in the zip's own name,
`20261118T195513Z`). Most members carry `Copy of` in front of their name, which is what Drive
writes when a file is copied into another folder; the name after it is the district's.
`sources/budget-workbooks/PROVENANCE-school-committee-2026-10-21.md` is the full record.

WHERE EACH MEMBER GOES, decided by what it is rather than by the folder it came in:

  * the 21 October agenda and the four sets of regular-session minutes are ALREADY HELD,
    byte for byte, from the town's Agenda Center. Nothing new is written for them.
  * six School Committee Policy Sub-Committee minutes (2024) are MINUTES, so they are filed
    under `meetings/school-committee/`, the Agenda Center board where the town posts that
    sub-committee's agendas, so each set joins its own meeting's row (refiled there from
    `school-advisory-councils-committees/` on 23 November 2026), with the delivery id
    `rr2026-11-18`, the convention of `PROVENANCE-school-committee-2026-10-27.md`: held and
    searchable, never counted as posted. Dated by the date each PRINTS, which for two of them
    is not the date the agenda lists.
  * twelve warrant batches are HELD PRIVATE (see BATCH_REASON).
  * everything else -- the capital request forms, the Superintendent's capital narrative, the
    vendor quotes, the line item transfer, the homecoming memo -- is filed under
    `budget-workbooks/school-committee-2026-10-21/`, the tree for documents sent to us.

`sources/data/sc-packet-2026-10-21-delivery.csv` records what became of every member, and
`--check` re-proves it against the archive.
"""
import argparse
import csv
import datetime
import hashlib
import os
import re
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import archive_storage as A  # noqa: E402
import ingest  # noqa: E402
import redact  # noqa: E402
import fetch_agendas  # noqa: E402
from fetch_town_docs import extract  # noqa: E402
from ingest_finance_committee import slug, text_for, held_by_hash, write_csv  # noqa: E402

ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, 'sources')
PREFIX = 'budget-workbooks/school-committee-2026-10-21/'
CATALOGUE = os.path.join(SRC, 'budget-workbooks', 'index.csv')
REGISTER = os.path.join(SRC, 'data', 'sc-packet-2026-10-21-delivery.csv')
ZIP_NAME = '10-21-26 SC Meeting-20261118T195513Z-1-001.zip'
DELIVERY = 'rr2026-11-18'
WHERE = 'School Committee packet, 21 October 2026'
DECIDED_BY = 'Claude, by eye, 20 November 2026; for TJ to overrule'

# THE POLICY SUB-COMMITTEE MINUTES, by the date each document PRINTS in its heading. The
# agenda's item 6b lists `6/21/24, 7/12/24, 9/6/24, 9/29/24, 10/2/24, 11/1/24`; the files
# print 20 September 2024 (not the 29th) and Friday 4 October 2024 (the file is named
# `10-2-24`). The document is the record of its own meeting, so it is filed by its own date.
POLICY = {
    'Copy of 7  Policy Meeting  6-21-24 Minutes.pdf': '2024-06-21',
    'Copy of MINUTES 1 Policy Meeting  7-12-24.pdf': '2024-07-12',
    'Copy of Minutes 3 Policy Meeting  9-6-24.pdf': '2024-09-06',
    'Copy of MINUTES 4 Policy Meeting  9-20-24 (1).pdf': '2024-09-20',
    'Copy of 5 Policy Meeting  Minutes 10-2-24.pdf': '2024-10-04',
    'Copy of MINUTES -6  Policy Meeting  11-1-24 (1).pdf': '2024-11-01',
}
POLICY_BOARD = {'board': 'School Committee', 'board_id': '24',
                'title': 'School Committee Policy Sub-Committee'}

# WARRANT BATCHES ARE HELD, ALL TWELVE. Each is a MUNIS `INVOICE ENTRY PROOF LIST` followed
# by the scanned invoices it pays (307 pages, every one a picture). Batch 6210 is a single
# payment to `SPED TUITIONS-PRIVATE`, out-of-district special education tuition, and a
# tuition invoice is billed for a named child -- the exact harm notes/process/DATA-PRIVACY.md
# masks. The proof lists themselves are vendors and accounts and would be public; the invoices
# behind them have to be read page by page first. Raw in the private bucket until then.
BATCH_RE = re.compile(r'Batch#(\d+)\s+(\d+)-(\d+)-(\d+)\.pdf$')
BATCH_REASON = ('warrant batch: a MUNIS invoice entry proof list and the scanned invoices '
                'behind it, every page a picture. The set includes out-of-district special '
                'education tuition (batch 6210, SPED TUITIONS-PRIVATE), whose invoices name '
                'a child. Held until every page is read; the proof-list pages can then be '
                'published and any invoice naming a child or family withheld')

# Flagged by the screen only because a page is a picture; each was looked at.
SEEN = {
    'Copy of Line Item Transfer Multiple Budget ines 10-21-26.pdf':
        'one scanned page: the district budget transfer form dated 10/21/2026, '
        'account lines and staff signatures only. Nobody receiving a service',
    'Copy of Lunenburg School District-Turkey Hill Clocks and Bells.001702.v1.7 10132026.pdf':
        'a vendor quote; the one picture page (p6) is a floor plan of speaker coverage',
}

HEADER = ['label', 'upstream', 'local', 'text', 'bytes', 'sha256', 'read', 'delivered_as']
REG_HEADER = ['delivered_as', 'bytes', 'sha256', 'disposition', 'key', 'note']


def plain(name):
    """The district's own name for a member: Drive's `Copy of ` prefixes removed."""
    return re.sub(r'^(Copy of )+', '', name)


def key_for(name):
    if name in POLICY:
        return (f'meetings/school-committee/'
                f'{POLICY[name]}-minutes-{DELIVERY}.pdf')
    m = BATCH_RE.search(name)
    if m:
        n, mo, d, y = m.groups()
        return f'{PREFIX}warrants/batch-{n}-20{int(y):02d}-{int(mo):02d}-{int(d):02d}.pdf'
    stem, ext = os.path.splitext(plain(name))
    return PREFIX + slug(stem) + ext.lower()


def label_for(name):
    return f'{os.path.splitext(plain(name))[0].strip()} — {WHERE}'


def members(zpath):
    with zipfile.ZipFile(zpath) as z:
        for i in z.infolist():
            if not i.is_dir():
                yield os.path.basename(i.filename), z.read(i)


def plan(zpath):
    held = held_by_hash()
    seen, reg, filed = {}, [], []
    for name, blob in members(zpath):
        sha = hashlib.sha256(blob).hexdigest()
        row = {'delivered_as': name, 'bytes': len(blob), 'sha256': sha, 'note': ''}
        if sha in seen:
            row.update(disposition='duplicate', key=seen[sha],
                       note='same bytes as another member of this delivery')
        elif sha in held and held[sha] != key_for(name):
            row.update(disposition='already held', key=held[sha],
                       note='the same bytes the town posted on its Agenda Center')
        else:
            row.update(disposition='filed', key=key_for(name))
            seen[sha] = row['key']
            filed.append((name, row['key']))
        reg.append(row)
    keys = [k for _, k in filed]
    if len(keys) != len(set(keys)):
        sys.exit('two members map to one key')
    return reg, filed


def seed_decisions(reg):
    """This delivery's decisions, in the redaction register before anything is staged.
    Re-read immediately before writing: other sessions append to the same file."""
    rows = {r['raw_sha256']: r for r in redact.load()}
    today = datetime.date.today().isoformat()
    for r in reg:
        if r['disposition'] != 'filed':
            continue
        name = r['delivered_as']
        if BATCH_RE.search(name):
            decision, reason = 'pending', BATCH_REASON
        elif name in SEEN:
            decision, reason = 'publish', SEEN[name]
        else:
            continue
        old = rows.get(r['sha256'], {})
        old.update({'raw_sha256': r['sha256'], 'delivered_as': name, 'raw_key': r['key'],
                    'raw_private_key': redact.private_key_for(r['key']),
                    'decision': decision, 'reason': reason, 'decided_by': DECIDED_BY,
                    'decided_on': old.get('decided_on') or today})
        rows[r['sha256']] = old
    redact.save(list(rows.values()))


def index_minutes(reg):
    """One row per policy minutes in `sources/meetings/index.csv`, with an EMPTY url: a
    delivered set has no Agenda Center address, and that absence is what keeps it from being
    counted as posted (`meeting_records.status()`)."""
    rows = list(csv.DictReader(open(fetch_agendas.INDEX, newline='', encoding='utf-8')))
    have = {fetch_agendas.row_key(r) for r in rows}
    for r in reg:
        if r['delivered_as'] not in POLICY or r['disposition'] != 'filed':
            continue
        new = dict(POLICY_BOARD, date=POLICY[r['delivered_as']], kind='minutes',
                   file_id=DELIVERY, url='', path=r['key'][len('meetings/'):])
        if fetch_agendas.row_key(new) not in have:
            rows.append(new)
    fetch_agendas.write_index(rows)


def run(zpath, dry):
    reg, filed = plan(zpath)
    n = {}
    for r in reg:
        n[r['disposition']] = n.get(r['disposition'], 0) + 1
    if dry:
        print(f'{len(reg)} members before the gate: '
              + ', '.join(f'{v} {k}' for k, v in sorted(n.items())))
        for r in reg:
            print(f"  {r['disposition']:13} {r['key']}")
        return
    seed_decisions(reg)
    want = dict(filed)
    for name, blob in members(zpath):
        if name not in want:
            continue
        ok, why = ingest.stage(want[name], blob, upstream='', delivered_as=name)
        if not ok and not why.startswith('HELD'):
            sys.exit(f'refused {name}: {why}')
    ingest.secure()

    decisions = redact.by_sha()
    for r in reg:
        d = decisions.get(r['sha256'])
        if r['disposition'] == 'filed' and d and d['decision'] != 'publish':
            r['disposition'] = {'withhold': 'withheld', 'redact': 'redacted',
                                'pending': 'held'}[d['decision']]
            r['note'] = d.get('reason', '')
    index_minutes(reg)

    cat = []
    for r in reg:
        if r['disposition'] != 'filed' or not r['key'].startswith(PREFIX):
            continue
        path = A.local_path(r['key'])
        if not os.path.exists(path):
            sys.exit(f'{r["key"]} is not on disk; run `ingest.py --secure`')
        txt = os.path.join(SRC, text_for(r['key']))
        os.makedirs(os.path.dirname(txt), exist_ok=True)
        how = ('had it' if os.path.exists(txt) and os.path.getsize(txt) > 0
               else extract(path, txt))
        cat.append({'label': label_for(r['delivered_as']), 'upstream': '',
                    'local': os.path.relpath(path, ROOT),
                    'text': os.path.relpath(txt, ROOT) if os.path.exists(txt) else '',
                    'bytes': os.path.getsize(path), 'sha256': A.hash_file(path)[0],
                    'read': how, 'delivered_as': r['delivered_as']})
    # The catalogue is shared with two other deliveries: rewrite only this one's rows.
    others = [r for r in csv.DictReader(open(CATALOGUE, newline=''))
              if not r['local'].startswith(os.path.join('sources', PREFIX))]
    write_csv(CATALOGUE, HEADER, others + cat)
    write_csv(REGISTER, REG_HEADER, reg)
    n = {}
    for r in reg:
        n[r['disposition']] = n.get(r['disposition'], 0) + 1
    print(f'{len(reg)} members: ' + ', '.join(f'{v} {k}' for k, v in sorted(n.items()))
          + f'; catalogued {len(cat)}')


def check():
    problems = []
    reg = list(csv.DictReader(open(REGISTER)))
    cat = {r['local']: r for r in csv.DictReader(open(CATALOGUE))}
    manifest = A.read_manifest()
    decisions = redact.by_sha()
    index = {r['path'] for r in csv.DictReader(open(fetch_agendas.INDEX, encoding='utf-8'))}
    for r in reg:
        d, k = r['disposition'], r['key']
        if d not in ('filed', 'already held', 'duplicate', 'held', 'withheld'):
            problems.append(f'no disposition: {r["delivered_as"]}')
        if d in ('filed', 'already held'):
            if manifest.get(k, {}).get('sha256') != r['sha256']:
                problems.append(f'{d}, and the manifest does not hold these bytes at {k}')
        if d == 'filed' and k.startswith(PREFIX) and os.path.join('sources', k) not in cat:
            problems.append(f'filed, not catalogued: {k}')
        if d == 'filed' and k.startswith('meetings/') and k[len('meetings/'):] not in index:
            problems.append(f'minutes filed with no meetings/index.csv row: {k}')
        if d in ('held', 'withheld'):
            if r['sha256'] not in decisions:
                problems.append(f'{d} with no row in redactions.csv: {r["delivered_as"]}')
            if os.path.exists(A.local_path(k)):
                problems.append(f'{d}, and its raw copy is in sources/: {k}')
            if k in manifest:
                problems.append(f'{d}, and the public manifest lists it: {k}')
    if problems:
        sys.exit('\n'.join(problems))
    n = {}
    for r in reg:
        n[r['disposition']] = n.get(r['disposition'], 0) + 1
    print(f'ok: {len(reg)} members (' + ', '.join(f'{v} {k}' for k, v in sorted(n.items()))
          + ')')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('zip', nargs='?')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    if a.check:
        check()
    elif not a.zip:
        sys.exit('give the path to ' + ZIP_NAME)
    else:
        run(a.zip, a.dry_run)
