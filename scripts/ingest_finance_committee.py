#!/usr/bin/env python3
"""The Finance Committee's files, received 4 October 2026, into the archive.

    python3 scripts/ingest_finance_committee.py ZIP            # stage, secure, catalogue
    python3 scripts/ingest_finance_committee.py ZIP --dry-run  # say what it would do
    python3 scripts/ingest_finance_committee.py --check        # catalogue and register hold

WHAT ARRIVED. One OneDrive download, `OneDrive_1_10-4-2026.zip`, 299 files: the Finance
Committee's own working folders, FY20 to FY27, sent by its chair in answer to TJ's public
records request. The committee's folder tree is the only record of which meeting a file
was presented at, so it is kept -- slugged, because a bucket key may only hold
`[A-Za-z0-9._/-]` -- and the exact path each file was delivered under is kept beside it in
`delivered_as`, which is the name somebody asks the town for when they want the file
again (rule 12).

EVERY MEMBER GETS A DISPOSITION, in `sources/data/finance-committee-delivery.csv`:

  filed          new to the archive; staged and secured through `ingest.py`
  already held   byte-identical to a document the archive already holds under another
                 key -- not stored twice; the register says where it is
  duplicate      a second copy of another member of this same zip
  withheld       about identifiable people, and no redacted copy could be anonymous. Raw
                 in the PRIVATE bucket only (`redact.py`), never in `sources/`.
  redacted       about identifiable people. Raw private; OUR redacted copy is public,
                 under a `.redacted` key, opening with the notice TJ set.
  held           the screen flagged it or could not read it, and nobody has decided yet.
                 Raw private; nothing public until `redactions.csv` says otherwise.

Every one of the last three went through `redact.gate()`, which `ingest.stage()` calls.

A member with no disposition is a failure, not a default: `--check` counts them.

THE CATALOGUE is `sources/budget-workbooks/index.csv`, in the shape
`build_search_index.py` discovers on its own (`label`, `local`, `text`), so the delivery
is searchable the day it lands. It covers this delivery only; the six workbooks that
were in the folder before it are described by hand in `build_source_index.py`.
"""
import argparse
import csv
import datetime
import hashlib
import json
import os
import re
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import archive_storage as A  # noqa: E402
import ingest  # noqa: E402
import redact  # noqa: E402
from fetch_town_docs import extract  # noqa: E402

ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, 'sources')
PREFIX = 'budget-workbooks/finance-committee/'
CATALOGUE = os.path.join(SRC, 'budget-workbooks', 'index.csv')
REGISTER = os.path.join(SRC, 'data', 'finance-committee-delivery.csv')
ZIP_NAME = 'OneDrive_1_10-4-2026.zip'


# THE DECISIONS FOR THIS DELIVERY, keyed by the path the committee delivered each file
# under. Every one of them is a file `pii_screen.py` flagged; the screen holds a flagged
# file until a decision exists, and these are seeded into `sources/data/redactions.csv`
# before anything is staged. Made under the policy TJ set on 4 October 2026 -- raw private,
# redacted public, withheld where rows cannot be made anonymous -- and recorded as made BY
# ME, for him to overrule, not as his.
DECIDED_BY = 'Claude, under the policy TJ approved 4 October 2026; for his review'
SALARY_COLUMNS = [r'emp\s*(no\.?|#|number|id)', r'last(\s*name)?', r'first(\s*name)?',
                  r'(employee\s*)?name', r'start\s*(dt|date)', r'eff(ective)?\s*(dt|date)',
                  r'hire\s*date', r'service\s*date']
SALARY = ('redact', {'columns': SALARY_COLUMNS},
          'per-person salary tables: the employee number, the name and the start and '
          'effective dates are removed. Position, grade and pay are kept, as the town\'s own '
          'budgets print them')
DECISIONS = {
    'FY27 Budget/TM Warrant/Copy of Vacation Buyout_ - Copy.xlsx':
        ('withhold', {}, 'about 170 town employees by name with hire dates, hourly rates and '
         'leave buyouts. Without the names, job title and hire date still identify each '
         'person, so no redacted copy can be anonymous'),
    'FY26 Budget/Department Presentations/Lunenburg Public Schools/FY26 INSURANCE PROJECTIONS.xlsx':
        ('withhold', {}, 'one row per insured school employee, role and plan tier. A post '
         'held by one person identifies that person\'s family coverage'),
    'FY24 Budget/20230323 - PACC, Sewer, Fire, & Other Moneyed Articles/PACC/PACCDraft 1 (version 3).xlsx': SALARY,
    'FY25 Budget/Public Access Cable/FY25 Working SW 7.xlsx': SALARY,
    'FY27 Budget/Department Presentations/PACC/FY27 Budget Worksheets PACC FY26 FY27 Comparison.xlsx': SALARY,
    'FY27 Budget/Department Presentations/PACC/FY27 Budget Worksheets PACC FY26 FY27 Comparison - Contingency REV2.xlsx': SALARY,
    'FY26 Budget/Department Presentations/Lunenburg Public Schools/School Budget Files - Amanda Moore FOIA request to School Dept/PARA CONTRACT 24-25.pdf':
        ('publish', {}, 'the screen matched the contract\'s own Family and Medical Leave '
         'and sick-leave articles. Terms of employment, not anybody\'s leave'),
    'FY27 Budget/Trust Funds/Background information/Trust_Fund_Manual_Low_ Income.pdf':
        ('publish', {}, 'the screen matched `DOB` on a blank application form'),
}
# DOCUMENTS WHOSE OWN NAME IS PERSONAL. Keyed by sha256, never by filename, because the
# filename names a person and this file is public. Everything public about them -- the
# register, the catalogue, the bucket key -- is derived from the hash, and the delivered name
# is held only in the PRIVATE bucket (`rules/<sha256>.json`). TJ, 5 October 2026: *"lets make
# sure it doesnt end up in any publically accesible way. delete anything public. Anything
# redacted here shoudl be super redacted and point to a summary ... that we write."*
WITHHELD_BY_SHA = {
    '86208269645bfc0f61c1c5c2d21a48571dcae94180a5ef37f38ad9c055d742af': {
        'public_name': "withheld: an email answering the Finance Committee's FY27 questions, "
                       "26 February 2026",
        'summary': 'budget-workbooks/finance-committee/summaries/withheld-86208269.md',
        'reason': 'personal material about private individuals and a member of staff; '
                  'withheld whole, and described in a summary we wrote instead',
    },
}

# Reached the PUBLIC bucket on 4 October 2026, in the 32 pushed before the screen existed
# and before the run was stopped. The bucket cannot delete them. What can still be done is
# to say so, and to catalogue the redacted copy instead.
PUBLISHED_BEFORE_REVIEW = 'PUBLISHED BEFORE REVIEW, 4 October 2026: the raw is in the public bucket and cannot be deleted'

SOURCE_NOTE = ('Finance Committee files, sent by its chair in answer to a public records '
               'request, received 4 October 2026')

HEADER = ['label', 'upstream', 'local', 'text', 'bytes', 'sha256', 'read', 'delivered_as']
REG_HEADER = ['delivered_as', 'bytes', 'sha256', 'disposition', 'key', 'note']


def slug(part):
    s = part.lower().replace('&', ' and ').replace('‌', '').replace('½', '-half')
    s = re.sub(r'[^a-z0-9.]+', '-', s)
    s = re.sub(r'-{2,}', '-', s).strip('-.')
    return s or 'x'


def key_for(member):
    *dirs, name = member.split('/')
    stem, ext = os.path.splitext(name)
    return PREFIX + '/'.join([slug(d) for d in dirs] + [slug(stem) + ext.lower()])


def text_for(key):
    """Text sits in a `text/` folder beside the document, which `frozen()` treats as ours."""
    d, name = os.path.split(key)
    return os.path.join(d, 'text', name + '.txt')


def label_for(member):
    """What the file is and where the committee kept it -- short, because `build_views.py`
    names every browsable link after it. How the delivery reached us is said ONCE, in the
    PROVENANCE note and the register, not appended to 272 filenames."""
    *dirs, name = member.split('/')
    stem = os.path.splitext(name)[0].strip()
    where = ' › '.join(d.strip() for d in dirs[:2])
    return f'{stem} — Finance Committee{", " + where if where else ""}'


def members(zpath):
    with zipfile.ZipFile(zpath) as z:
        for i in z.infolist():
            if i.is_dir():
                continue
            yield i.filename, z.read(i)


def held_by_hash():
    out = {}
    for k, row in A.read_manifest().items():
        out.setdefault(row['sha256'], k)
    return out


def write_csv(path, header, rows):
    tmp = path + '.tmp'
    with open(tmp, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=header, lineterminator='\n', extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, path)


def plan(zpath):
    """What each member is BEFORE the gate: new, already held, or a copy within the zip."""
    held = held_by_hash()
    seen, reg, filed, used = {}, [], [], set()
    for member, blob in members(zpath):
        sha = hashlib.sha256(blob).hexdigest()
        private = WITHHELD_BY_SHA.get(sha)
        row = {'delivered_as': private['public_name'] if private else member,
               'bytes': len(blob), 'sha256': sha, '_member': member}
        if private:
            row.update(disposition='filed', note='',
                       key=PREFIX + 'withheld/' + sha + os.path.splitext(member)[1].lower())
            seen[sha] = row['key']
            filed.append((member, row['key']))
            reg.append(row)
            continue
        if sha in seen:
            row.update(disposition='duplicate', key=seen[sha],
                       note='same bytes as another member of this delivery')
        elif sha in held and not held[sha].startswith(PREFIX):
            row.update(disposition='already held', key=held[sha], note='')
        else:
            k = key_for(member)
            if k in used:
                # Two DIFFERENT files whose names differ only in what slugging removes --
                # two saves of one unclassified-budget deck, `(Insurances Workers Comp
                # FICA)` and `(Insurances, Workers Comp, FICA)`. The sha prefix keeps both,
                # the way the DLS exports are named; `delivered_as` keeps the real names.
                stem, ext = os.path.splitext(k)
                k = f'{stem}-{sha[:8]}{ext}'
            used.add(k)
            row.update(disposition='filed', key=k, note='')
            seen[sha] = k
            filed.append((member, k))
        reg.append(row)
    keys = [k for _, k in filed]
    dupes = {k for k in keys if keys.count(k) > 1}
    if dupes:
        sys.exit('two members slug to one key: %s' % sorted(dupes))
    return reg, filed


def seed_decisions(reg):
    """Write this delivery's decisions into the redaction register, before staging."""
    rows = {r['raw_sha256']: r for r in redact.load()}
    public = {o['key'] for o in A.list_objects(PREFIX)}
    for r in reg:
        priv = WITHHELD_BY_SHA.get(r['sha256'])
        if priv and r['disposition'] == 'filed':
            rows[r['sha256']] = {
                'raw_sha256': r['sha256'], 'delivered_as': priv['public_name'],
                'raw_key': r['key'], 'decision': 'withhold', 'reason': priv['reason'],
                'raw_private_key': 'raw/by-sha256/' + r['sha256'] + os.path.splitext(r['key'])[1],
                'decided_by': DECIDED_BY + '; withheld whole on his instruction, 5 October 2026',
                'decided_on': '2026-10-05', 'note': 'summary: ' + priv['summary']}
            continue
        if r['delivered_as'] not in DECISIONS or r['disposition'] != 'filed':
            continue
        decision, rule, reason = DECISIONS[r['delivered_as']]
        row = rows.get(r['sha256'], {})
        row.update({'raw_sha256': r['sha256'], 'delivered_as': r['delivered_as'],
                    'raw_key': r['key'], 'raw_private_key': redact.private_key_for(r['key']),
                    'decision': decision,
                    'rule': json.dumps({'private_rule': 'rules/' + r['sha256'] + '.json'}
                                       if rule.get('private_rule') is True else rule)
                            if rule else '',
                    'reason': reason, 'decided_by': DECIDED_BY,
                    'decided_on': row.get('decided_on') or datetime.date.today().isoformat(),
                    'note': PUBLISHED_BEFORE_REVIEW if r['key'] in public else ''})
        rows[r['sha256']] = row
    redact.save(list(rows.values()))


def run(zpath, dry):
    reg, filed = plan(zpath)
    if dry:
        n = {}
        for r in reg:
            n[r['disposition']] = n.get(r['disposition'], 0) + 1
        print(f'{len(reg)} members before the gate: '
              + ', '.join(f'{v} {k}' for k, v in sorted(n.items())))
        return
    seed_decisions(reg)

    # Anything staged before the gate existed and not yet in the bucket goes back through it.
    public = {o['key'] for o in A.list_objects(PREFIX)}
    for _, key in filed:
        if key not in public:
            ingest.unstage(key)

    # One pass over the zip, so the delivery is never held in memory whole.
    by_member = {r['_member']: r for r in reg}
    want = dict(filed)
    held = {}
    for member, blob in members(zpath):
        if member not in want:
            continue
        key = want[member]
        if key in public:
            # Already in the bucket: the gate cannot keep it out, but it still records the
            # raw privately and registers what the screen finds.
            # It is still pending in `ingest-pending.csv` from the first run, so `secure()`
            # below reads it back and files it.
            redact.gate(key, blob, '', by_member[member]['delivered_as'])
            continue
        ok, why = ingest.stage(key, blob, upstream='',
                               delivered_as=by_member[member]['delivered_as'])
        if not ok:
            if not why.startswith('HELD'):
                sys.exit(f'refused {member}: {why}')
            held[member] = why
    ingest.secure()

    # The dispositions, from the register -- never from what this run believed.
    decisions = redact.by_sha()
    for r in reg:
        if r['disposition'] != 'filed':
            continue
        d = decisions.get(r['sha256'])
        if not d or d['decision'] == 'publish':
            continue
        r['disposition'] = {'withhold': 'withheld', 'redact': 'redacted',
                            'pending': 'held'}[d['decision']]
        r['note'] = d.get('note', '')
        if r['sha256'] in WITHHELD_BY_SHA:
            r['key'] = WITHHELD_BY_SHA[r['sha256']]['summary']
        if d['decision'] == 'redact' and d.get('public_key'):
            r['key'] = d['public_key']

    # Text, beside each public document, and the catalogue.
    cat = []
    for r in reg:
        priv = WITHHELD_BY_SHA.get(r['sha256'])
        if priv:
            path = os.path.join(SRC, priv['summary'])
            cat.append({'label': priv['public_name'] + ' — a summary we wrote',
                        'upstream': '', 'local': os.path.relpath(path, ROOT),
                        'text': os.path.relpath(path, ROOT), 'bytes': os.path.getsize(path),
                        'sha256': A.hash_file(path)[0], 'read': 'written by us',
                        'delivered_as': priv['public_name']})
            continue
        if r['disposition'] not in ('filed', 'redacted'):
            continue
        path = A.local_path(r['key'])
        if not os.path.exists(path):
            sys.exit(f'{r["key"]} is not on disk; run `ingest.py --secure` and `redact.py --build`')
        txt = os.path.join(SRC, text_for(r['key']))
        os.makedirs(os.path.dirname(txt), exist_ok=True)
        how = ('had it' if os.path.exists(txt) and os.path.getsize(txt) > 0
               else extract(path, txt))
        label = label_for(r['delivered_as'])
        if r['disposition'] == 'redacted':
            label += ' (redacted by us)'
        cat.append({'label': label, 'upstream': '', 'local': os.path.relpath(path, ROOT),
                    'text': os.path.relpath(txt, ROOT) if os.path.exists(txt) else '',
                    'bytes': os.path.getsize(path), 'sha256': A.hash_file(path)[0],
                    'read': how, 'delivered_as': r['delivered_as']})
    write_csv(CATALOGUE, HEADER, cat)
    write_csv(REGISTER, REG_HEADER, reg)
    n = {}
    for r in reg:
        n[r['disposition']] = n.get(r['disposition'], 0) + 1
    print(f'{len(reg)} members: ' + ', '.join(f'{v} {k}' for k, v in sorted(n.items()))
          + f'; catalogued {len(cat)}')


def check():
    """Every member has a disposition, and each disposition is true of the archive."""
    problems = []
    reg = list(csv.DictReader(open(REGISTER)))
    cat = {r['local']: r for r in csv.DictReader(open(CATALOGUE))}
    manifest = A.read_manifest()
    decisions = redact.by_sha()
    for r in reg:
        d = r['disposition']
        if d not in ('filed', 'redacted', 'already held', 'duplicate', 'withheld', 'held'):
            problems.append(f'no disposition: {r["delivered_as"]}')
        elif d in ('filed', 'redacted'):
            if os.path.join('sources', r['key']) not in cat:
                problems.append(f'{d}, not catalogued: {r["key"]}')
            if r['key'] not in manifest:
                problems.append(f'{d}, not in the manifest: {r["key"]}')
            if d == 'filed' and manifest.get(r['key'], {}).get('sha256') != r['sha256']:
                problems.append(f'filed with different bytes: {r["key"]}')
        elif d == 'already held' and r['key'] not in manifest:
            problems.append(f'said to be held, and the manifest has no {r["key"]}')
        if d in ('withheld', 'redacted', 'held'):
            dec = decisions.get(r['sha256'])
            if not dec:
                problems.append(f'{d} with no row in redactions.csv: {r["delivered_as"]}')
            elif not dec.get('note', '').startswith('PUBLISHED BEFORE REVIEW') and \
                    os.path.exists(A.local_path(dec['raw_key'])):
                problems.append(f'{d}, and its raw copy is in sources/: {dec["raw_key"]}')
    for c in cat.values():
        if c['text'] and not os.path.exists(os.path.join(ROOT, c['text'])):
            problems.append(f'text named and absent: {c["text"]}')
    if problems:
        sys.exit('\n'.join(problems))
    n = {}
    for r in reg:
        n[r['disposition']] = n.get(r['disposition'], 0) + 1
    print(f'ok: {len(reg)} members (' + ', '.join(f'{v} {k}' for k, v in sorted(n.items()))
          + f'), {len(cat)} catalogued, {sum(1 for c in cat.values() if c["text"])} with text')


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
