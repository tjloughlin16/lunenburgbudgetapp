"""Does everything in `sources/` sit where the layout says it should, under the name it
should have?

    python3 scripts/check_archive_layout.py

WHY THIS EXISTS

`sources/` was reorganised on 4 September 2026 so that one question decides where a
document goes: how did it reach us. That only holds if the next ingest follows it, and
twenty-three MUNIS report runs are expected. A layout that lives only in a plan document
is a layout that lasts until the next person is in a hurry.

So the rules are here, executable, and this fails when they are broken. It is deliberately
narrow: it checks WHERE a file sits and WHAT it is called, and nothing about its contents
-- `extract_munis_report.py --check` and `build_source_index.py` already own those.

THREE THINGS IT CATCHES

1.  **A new top-level folder.** Adding one is a decision about how the archive is
    organised, and it should be made on purpose rather than by dropping a directory in.
2.  **A MUNIS report in the wrong subfolder**, or in none.
3.  **A filename that does not carry its fiscal year and period.** Twenty-three reports
    are arriving with near-identical titles; two of them started this whole exercise by
    being indistinguishable except by the folder they happened to land in.

WHAT IT DOES NOT DO

It does not check the mirrors' filenames. Those keep the publisher's own name, because
rule 12 says that is how a resident asks the town for a document when the link dies.
"""
import argparse
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'sources')

# The whole archive, one line per folder, and why each is separate. A folder not on this
# list is not a mistake to be auto-corrected -- it is a question for a person.
TOP = {
    'town-budget':        'lunenburgma.gov, mirrored — budgets, plans, financial statements',
    'town-supplementary': 'lunenburgma.gov, mirrored — everything else the town publishes',
    'district-budget':    'lunenburgschools.net budget page, mirrored',
    'meetings':           'agendas and minutes, by board',
    'dese':               'state district and school profiles',
    'dls':                'state free cash certifications',
    'peers':              'other districts, assembled by us from several publishers',
    'contracts':          'union contracts, from the district HR page and DESE',
    'munis-ledgers':      'MUNIS reports — sent to us, never published',
    'budget-workbooks':   'budget workbooks, sent to us',
    'correspondence':     'emails and replies',
    'analyses':           'written here',
    'data':               'computed here',
}
TOP_FILES = {'MANIFEST.md', 'supplemental.csv', '.DS_Store'}

# What each MUNIS subfolder holds, and the name a file in it must carry. Period is part
# of the name because p09, p12 and p13 are three different answers to the same question
# and the folder cannot tell them apart.
LEDGER = {
    'expenses':        (re.compile(r'^glytdbud-expense-fy\d{4}-p\d{2}-[a-z0-9-]+$'),
                        'glytdbud-expense-fy2026-p13-gf-school'),
    'revenue':         (re.compile(r'^glytdbud-revenue-fy\d{4}-p\d{2}-[a-z0-9-]+$'),
                        'glytdbud-revenue-fy2025-p13-gf-all'),
    'account-details': (re.compile(r'^(account-details-fy\d{4}-[a-z0-9-]+'
                                   r'|athletics-by-sport-fy\d{4}-fy\d{4}'
                                   r'|athletic-fee-counts-fy\d{4})$'),
                        'account-details-fy2025-gf-school'),
    'transfers':       (re.compile(r'^transfers-fy\d{4}(-[a-z0-9-]+)?$'),
                        'transfers-fy2025'),
    'purchase-orders': (re.compile(r'^po-closed-fy\d{4}(-[a-z0-9-]+)?$'),
                        'po-closed-fy2025'),
    'fund-balances':   (re.compile(r'^[a-z-]+-fy\d{4}-p\d{2}$'),
                        'special-revenue-fy2026-p09'),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--quiet', action='store_true')
    args = ap.parse_args()
    problems = []

    # 1. the top level
    for name in sorted(os.listdir(SRC)):
        path = os.path.join(SRC, name)
        if os.path.isdir(path):
            if name not in TOP:
                problems.append(
                    'sources/%s/ is not one of the archive\'s folders.\n'
                    '      Every document belongs to one of these, chosen by HOW IT '
                    'REACHED US:\n%s\n'
                    '      If it genuinely belongs to none, that is a decision about the '
                    'archive\n      and belongs in plans/ARCHIVE-REORG.md, not in a new '
                    'directory.'
                    % (name, '\n'.join('        %-20s %s' % (k, v)
                                       for k, v in sorted(TOP.items()))))
        elif name not in TOP_FILES:
            problems.append('sources/%s is a loose file at the top level. Documents live '
                            'in a folder.' % name)

    # 2. and 3. the MUNIS reports
    base = os.path.join(SRC, 'munis-ledgers')
    if os.path.isdir(base):
        for entry in sorted(os.listdir(base)):
            p = os.path.join(base, entry)
            if os.path.isfile(p):
                problems.append(
                    'sources/munis-ledgers/%s sits loose. Every MUNIS report goes in the '
                    'subfolder for what it IS: %s.'
                    % (entry, ', '.join(sorted(LEDGER))))
                continue
            if entry not in LEDGER:
                problems.append(
                    'sources/munis-ledgers/%s/ is not a report type. The types are %s.'
                    % (entry, ', '.join(sorted(LEDGER))))
                continue
            pattern, example = LEDGER[entry]
            for fn in sorted(os.listdir(p)):
                if fn.startswith('.') or fn.startswith('PROVENANCE'):
                    continue
                stem = os.path.splitext(fn)[0]
                if not pattern.match(stem):
                    problems.append(
                        'sources/munis-ledgers/%s/%s does not carry its fiscal year and '
                        'period.\n      Expected something like %s%s\n'
                        '      Two reports printed the same title and differed only by '
                        'period; the\n      filename is the only place that distinction '
                        'survives.'
                        % (entry, fn, example, os.path.splitext(fn)[1]))

            # A delivery with no address is the thing rule 12 exists to prevent.
            if not any(f.startswith('PROVENANCE') for f in os.listdir(p)) \
                    and any(not f.startswith('.') for f in os.listdir(p)):
                problems.append(
                    'sources/munis-ledgers/%s/ has documents and no PROVENANCE file.\n'
                    '      Nothing here came off a website, so the request or the email '
                    'IS the address.' % entry)

    if problems:
        print('%d layout problem(s):\n' % len(problems))
        for i, p in enumerate(problems, 1):
            print('  %d. %s\n' % (i, p))
        print('The layout and the reasoning are in plans/ARCHIVE-REORG.md.')
        return 1
    if not args.quiet:
        n = sum(len(os.listdir(os.path.join(SRC, 'munis-ledgers', d)))
                for d in LEDGER
                if os.path.isdir(os.path.join(SRC, 'munis-ledgers', d)))
        print('sources/ layout is correct — %d folders, %d MUNIS files, all named and '
              'placed.' % (len(TOP), n))
    return 0


if __name__ == '__main__':
    sys.exit(main())
