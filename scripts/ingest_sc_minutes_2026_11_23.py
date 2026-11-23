#!/usr/bin/env python3
"""School Committee and Policy Sub-Committee minutes, as TJ downloaded them on 23 November 2026.

    python3.11 scripts/ingest_sc_minutes_2026_11_23.py ~/Downloads/drive-download-20261123T201924Z-1-001.zip
    python3.11 scripts/ingest_sc_minutes_2026_11_23.py ZIP --dry-run
    python3.11 scripts/ingest_sc_minutes_2026_11_23.py --check

HOW IT REACHED US. A Google Drive folder shared with TJ by the Superintendent's office and
downloaded by him as one archive on 23 November 2026 (the timestamp in the zip's own name,
`20261123T201924Z`). It answers, in part, his request of 8 September 2026 for School
Committee minutes: the Superintendent's reply of 19 November says *"Please find a portion of
additional minutes from 2024, 2025, and 2026 in Liz's latest email to you"*
(`correspondence/2026-11-19-records-requests-superintendent.txt`).
`sources/meetings/PROVENANCE-school-committee-2026-11-23.md` is the full record.

WHERE EACH MEMBER GOES, decided by comparing it with what is already held:

  * ALREADY HELD, byte for byte: eight members. Four 2024 Policy minutes from the 18 November
    packet, and the 15 July, 29 July, 26 August and 9 September 2026 minutes, which are the
    very files the town has posted on its Agenda Center. Nothing new is written.
  * SAME TEXT AS HELD, different bytes: two members. The 21 June 2024 Policy minutes differ
    from the held copy by one word, and the 12 July 2024 Policy minutes arrive as the Word
    file behind the PDF already held. Not re-filed: a second copy
    of a text already held, under a new key, would put two documents on one meeting. Their
    sha256 is recorded in the register below, so the bytes stay identifiable.
  * FILED as minutes, `rr2026-11-23`, with an EMPTY url, so never counted as posted (the
    convention of `PROVENANCE-school-committee-2026-10-27.md`): three School Committee
    meetings of 2025 and four Policy Sub-Committee meetings of 2025. The Policy minutes are
    filed under `meetings/school-committee/`, because that is the Agenda Center board that
    posted those meetings' agendas, so each joins its own meeting in the register.
  * FILED as correspondence: `Minutes Overview.xlsx`, the district's own list of which
    meetings' minutes are posted.

`sources/data/sc-minutes-2026-11-23-delivery.csv` records what became of every member, and
`--check` re-proves it against the archive.
"""
import argparse
import csv
import hashlib
import os
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import archive_storage as A  # noqa: E402
import ingest  # noqa: E402
import fetch_agendas  # noqa: E402
import redact  # noqa: E402
from fetch_town_docs import extract  # noqa: E402
from ingest_finance_committee import text_for, held_by_hash, write_csv  # noqa: E402

ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, 'sources')
ZIP_NAME = 'drive-download-20261123T201924Z-1-001.zip'
DELIVERY = 'rr2026-11-23'
REGISTER = os.path.join(SRC, 'data', 'sc-minutes-2026-11-23-delivery.csv')
CATALOGUE = os.path.join(SRC, 'correspondence', 'index.csv')

SC = {'board': 'School Committee', 'board_id': '24', 'title': ''}
POLICY = {'board': 'School Committee', 'board_id': '24',
          'title': 'School Committee Policy Sub-Committee'}

# Minutes, by the date each document PRINTS in its heading (each was read; all agree with
# the date in the district's filename).
MINUTES = {
    '03.05.25 Minutes (Autosaved).pdf': ('2025-03-05', SC),
    'Minutes 04.02.25.pdf': ('2025-04-02', SC),
    '6.18.25 Minutes (002).pdf': ('2025-06-18', SC),
    'Copy of MINUTES 7  Policy Meeting  Minutes 2-21-25 (1).pdf': ('2025-02-21', POLICY),
    'Copy of MINUTES 8  Policy Meeting  Minutes 3-21-25.pdf': ('2025-03-21', POLICY),
    'Policy Meeting  Minutes 10-24-25.pdf': ('2025-10-24', POLICY),
    'Policy Meeting  Minutes 10-31-25.pdf': ('2025-10-31', POLICY),
}

# Different bytes, same text as a document already held: compared word for word
# (pypdf / the docx XML), 23 November 2026.
SAME_TEXT = {
    '7  Policy Meeting  6-21-24 Minutes (1).pdf': (
        'meetings/school-advisory-councils-committees/2024-06-21-minutes-rr2026-11-18.pdf',
        'the held copy with one word fewer (a stray "In"); 223 words against 224'),
    'MINUTES 1 Policy Meeting  7-12-24.docx': (
        'meetings/school-advisory-councils-committees/2024-07-12-minutes-rr2026-11-18.pdf',
        'the Word file behind the held PDF; identical text but for an image-size field'),
}

# HELD BY THE SCREEN, and rightly. The 5 March 2025 budget hearing's public comment has two
# speakers, each named with a home address, describing a disability: one their own diagnosis,
# one a sibling's special education support. notes/process/DATA-PRIVACY.md's one test says
# mask that person. The raw waits in the private bucket for a redacted copy that masks the
# two speakers; no name is written here, because this file and the register are public.
HELD_NOTE = {
    '03.05.25 Minutes (Autosaved).pdf':
        'held private: public comment ties a disability to two named speakers; '
        'to be published as our redacted copy with those speakers masked',
}

OVERVIEW = 'Minutes Overview.xlsx'
OVERVIEW_KEY = 'correspondence/2026-11-23-school-committee-minutes-overview.xlsx'
OVERVIEW_LABEL = ("The district's own list of School Committee meetings and whether each "
                  "one's minutes are posted, 2024-2026 — in the Superintendent's office's "
                  "minutes delivery of 23 November 2026")

REG_HEADER = ['delivered_as', 'folder', 'bytes', 'sha256', 'disposition', 'key', 'note']
CAT_HEADER = ['label', 'upstream', 'local', 'text', 'bytes', 'sha256', 'read']


def key_for(name):
    if name in MINUTES:
        return f'meetings/school-committee/{MINUTES[name][0]}-minutes-{DELIVERY}.pdf'
    if name == OVERVIEW:
        return OVERVIEW_KEY
    return None


def members(zpath):
    with zipfile.ZipFile(zpath) as z:
        for i in z.infolist():
            if not i.is_dir():
                yield i.filename, z.read(i)


def plan(zpath):
    held = held_by_hash()
    reg, filed = [], []
    for path, blob in members(zpath):
        name = os.path.basename(path)
        sha = hashlib.sha256(blob).hexdigest()
        row = {'delivered_as': name, 'folder': os.path.dirname(path), 'bytes': len(blob),
               'sha256': sha, 'note': ''}
        if sha in held and held[sha] != key_for(name):
            row.update(disposition='already held', key=held[sha], note='the same bytes')
        elif name in SAME_TEXT:
            k, why = SAME_TEXT[name]
            row.update(disposition='same text as held', key=k, note=why)
        elif key_for(name):
            row.update(disposition='filed', key=key_for(name))
            filed.append((name, row['key']))
        else:
            sys.exit(f'no decision for {path}')
        reg.append(row)
    keys = [k for _, k in filed]
    if len(keys) != len(set(keys)):
        sys.exit('two members map to one key')
    return reg, filed


def index_minutes(reg):
    """One row per filed set in `sources/meetings/index.csv`, with an EMPTY url: a delivered
    set has no Agenda Center address, and that absence keeps it from being counted posted."""
    rows = list(csv.DictReader(open(fetch_agendas.INDEX, newline='', encoding='utf-8')))
    have = {fetch_agendas.row_key(r) for r in rows}
    for r in reg:
        if r['delivered_as'] not in MINUTES or r['disposition'] != 'filed':
            continue
        date, board = MINUTES[r['delivered_as']]
        new = dict(board, date=date, kind='minutes', file_id=DELIVERY, url='',
                   path=r['key'][len('meetings/'):])
        if fetch_agendas.row_key(new) not in have:
            rows.append(new)
    fetch_agendas.write_index(rows)


def catalogue_overview():
    path = A.local_path(OVERVIEW_KEY)
    if not os.path.exists(path):
        sys.exit(f'{OVERVIEW_KEY} is not on disk; run `ingest.py --secure`')
    txt = os.path.join(SRC, text_for(OVERVIEW_KEY))
    os.makedirs(os.path.dirname(txt), exist_ok=True)
    how = 'had it' if os.path.exists(txt) and os.path.getsize(txt) > 0 else extract(path, txt)
    row = {'label': OVERVIEW_LABEL, 'upstream': '', 'local': os.path.relpath(path, ROOT),
           'text': os.path.relpath(txt, ROOT) if os.path.exists(txt) else '',
           'bytes': os.path.getsize(path), 'sha256': A.hash_file(path)[0], 'read': how}
    # Shared catalogue: re-read immediately before writing, replace only this row.
    rows = [r for r in csv.DictReader(open(CATALOGUE, newline='', encoding='utf-8'))
            if r['local'] != row['local']]
    write_csv(CATALOGUE, CAT_HEADER, rows + [row])


def counts(reg):
    n = {}
    for r in reg:
        n[r['disposition']] = n.get(r['disposition'], 0) + 1
    return ', '.join(f'{v} {k}' for k, v in sorted(n.items()))


def run(zpath, dry):
    reg, filed = plan(zpath)
    if dry:
        print(f'{len(reg)} members: {counts(reg)}')
        for r in reg:
            print(f"  {r['disposition']:18} {r['key']}")
        return
    want = dict(filed)
    for path, blob in members(zpath):
        name = os.path.basename(path)
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
            r['note'] = HELD_NOTE.get(r['delivered_as'], d.get('reason', ''))
    index_minutes(reg)
    catalogue_overview()
    write_csv(REGISTER, REG_HEADER, reg)
    print(f'{len(reg)} members: {counts(reg)}')


def check():
    problems = []
    reg = list(csv.DictReader(open(REGISTER)))
    manifest = A.read_manifest()
    index = {r['path'] for r in csv.DictReader(open(fetch_agendas.INDEX, encoding='utf-8'))}
    cat = {r['local'] for r in csv.DictReader(open(CATALOGUE, encoding='utf-8'))}
    for r in reg:
        d, k = r['disposition'], r['key']
        if d in ('held', 'withheld', 'redacted'):
            if r['sha256'] not in redact.by_sha():
                problems.append(f'{d} with no row in redactions.csv: {r["delivered_as"]}')
            if k in manifest:
                problems.append(f'{d}, and the public manifest lists its raw key: {k}')
            continue
        if d not in ('filed', 'already held', 'same text as held'):
            problems.append(f'no disposition: {r["delivered_as"]}')
        if d in ('filed', 'already held') and manifest.get(k, {}).get('sha256') != r['sha256']:
            problems.append(f'{d}, and the manifest does not hold these bytes at {k}')
        if d == 'same text as held' and k not in manifest:
            problems.append(f'same text as {k}, which the manifest does not hold')
        if d == 'filed' and k.startswith('meetings/') and k[len('meetings/'):] not in index:
            problems.append(f'minutes filed with no meetings/index.csv row: {k}')
        if d == 'filed' and k == OVERVIEW_KEY and os.path.join('sources', k) not in cat:
            problems.append(f'filed, not catalogued: {k}')
    if problems:
        sys.exit('\n'.join(problems))
    print(f'ok: {len(reg)} members ({counts(reg)})')


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
