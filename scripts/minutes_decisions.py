"""What the boards actually voted on, matched to each discrepancy — quotes verified.

Imported by `build_discrepancy_review.py`. Not a standalone report.

WHY THIS FILE IS DATA AND NOT PROSE

Every entry carries the exact words from the minutes, the file they are in, and the
board and date that said them. `verify()` re-reads each file and fails if the quote is
not in it, so a sentence cannot drift from its source during editing. That is rule 13
applied to quotations: the minutes are the source, our rendering of them is not.

WHAT "MATCHED" MEANS, AND WHAT IT DOES NOT

A match here means a vote naming the same accounts and the same amount as the ledger
movement. It does NOT mean the vote caused the ledger entry, and where a vote names an
amount that only partly accounts for the movement the entry says so. Anything where the
minutes are silent is recorded as silent rather than left out -- an absent vote is the
finding in several of these, and omitting it would hide it.

HOW THE MINUTES RECORD TRANSFERS AT ALL

`Review & Approve Line Item Transfers, Warrants & Donations` is a standing School
Committee agenda item, so every transfer goes to a vote. What the MINUTES contain varies:
some meetings itemise every transfer with amounts and both account names, and some record
only that transfers were approved. 24 June 2026 is the clearest case of the second kind --
"Mr. McNamara explains the four line item transfers for this meeting" -- and those four
are not named anywhere in the archive.
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXT = os.path.join(ROOT, 'sources', 'minutes', 'text')

BASE = 'https://www.lunenburgma.gov/AgendaCenter/ViewFile/Minutes/'

# key -> (board, date, file under sources/minutes/text, url suffix, quote, verdict, note)
# `verdict` is one of: approved, approved-partial, requested, silent, contradicts
DECISIONS = {
    'athletic_basis': (
        'School Committee', '2025-10-01',
        'school-committee/2025-10-01-minutes-7432.txt', '_10012025-7432',
        'We have one transfer it is to move $20,000 from athletic insurance to \n'
        'athletic dues and fees, they were classified in the wrong object and org number',
        'approved',
        'Voted unanimously. The district states the reason itself: the original coding '
        'was wrong. This is the $20,000 that makes the two documents differ.'),
    'phys_ed': (
        'School Committee', '2025-09-17',
        'school-committee/2025-09-17-minutes-7408.txt', '_09172025-7408',
        '$550 from the Elementary School art \nsupply to the Elementary Phys Ed line',
        'approved',
        'Matches the $550 moved into PHYS ED SU exactly.'),
    'curriculum': (
        'School Committee', '2025-09-17',
        'school-committee/2025-09-17-minutes-7408.txt', '_09172025-7408',
        'FY 26 we will be moving $4,222.59 out of the curriculum adoption line \n'
        'and putting it into the Primary School workbook line',
        'approved',
        'Both sides visible in the ledger: CURR ADOPT −$4,222.59, WORKBOOKS +$4,222.59.'),
    'sped_materials': (
        'School Committee', '2026-03-04',
        'school-committee/2026-03-04-minutes-7687.txt', '_03042026-7687',
        'A transfer of $462.07 will be transferring from \n'
        'the supply line items, math, art, periodicals, library, guidance, repair office '
        'machines and general \nsupplies to the Primary School special educations '
        'instructional material amount for testing \nsupplies.',
        'approved',
        'Names REPAIR OFFICE MACHINES as a source, which is the account whose coding the '
        'two documents disagree about.'),
    'kindergarten': (
        'Finance Committee', '2026-01-12',
        'finance-committee/2026-01-12-minutes-7597.txt', '_01122026-7597',
        'kindergarten classrooms were operating with 25 students and no aides',
        'contradicts',
        'Said by the School Committee Chair at a Tri-Board meeting in January 2026, in the '
        'same year the ledger charges $93,691 to KINDAIDREG and $5,373 to KINDPARREG. '
        'Both statements can be true only if those accounts paid for something other than '
        'aides in kindergarten classrooms. Nothing in the archive settles which.'),
    'kindergarten_fy27': (
        'Finance Committee', '2026-02-26',
        'finance-committee/2026-02-26-minutes-7673.txt', '_02262026-7673',
        '1 Kindergarten Paraprofessional: $22,205',
        'requested',
        'Not a transfer and not a vote: an FY27 staffing INCREASE request, i.e. a '
        'position to be ADDED rather than one already running.'),
    'soa': (
        'School Committee', '2026-03-04',
        'school-committee/2026-03-04-minutes-7687.txt', '_03042026-7687',
        'A transfer of $54,548.50 to transfer funds to represent the new allocations \n'
        'for the SOA account, these funds will be going from instructional staff salaries',
        'approved-partial',
        'The destinations are not in the minutes: they are "the list provided to the '
        'committee (and available online)". That list is not in this archive and is worth '
        'asking for.'),
    'november': (
        'School Committee', '2025-11-05',
        'school-committee/2025-11-05-minutes-7496.txt', '_11052025-7496',
        'We want to transfer $13,500 from admin tech contracts to school committee dues, '
        'to cover superintendent search invoice. Transfer $2000 from school science '
        'supply line item at Primary School to the reading supply line item at the '
        'Primary school to cover cost.',
        'approved',
        'Both are in the ledger to the dollar: CONT SERV −$13,500, SCI SUPP −$2,000, '
        'READ SUPPL +$2,000. Neither touches anything in this document — recorded here '
        'because these minutes were unreadable when this list was first compiled.'),
    'june_four': (
        'School Committee', '2026-06-24',
        'school-committee/2026-06-24-minutes-7869.txt', '_06242026-7869',
        'Mr. McNamara explains the four line item transfers for this meeting',
        'approved-partial',
        'Approved unanimously at the last meeting of FY26. The four are named nowhere in '
        'the archive, so any of the unexplained movements above could be among them.'),
}

SILENT = """No vote in the archive names this account. The School Committee votes on line
item transfers at almost every meeting, and several meetings record only that transfers
were approved without saying which."""


def verify():
    """Re-read every quoted file and fail if the quote is not in it."""
    bad = []
    for key, (board, date, path, _u, quote, _v, _n) in DECISIONS.items():
        full = os.path.join(TEXT, path)
        if not os.path.exists(full):
            bad.append('%s: %s does not exist' % (key, path))
            continue
        text = open(full, encoding='utf-8', errors='replace').read()
        # The minutes are extracted from PDFs and wrap mid-sentence, so compare on
        # collapsed whitespace rather than reproducing the line breaks exactly.
        flat = ' '.join(text.split())
        if ' '.join(quote.split()) not in flat:
            bad.append('%s: quote not found in %s' % (key, path))
    return bad


def url(key):
    return BASE + DECISIONS[key][3]


if __name__ == '__main__':
    import sys
    bad = verify()
    for b in bad:
        print('FAIL', b)
    print('%d of %d quotes verified against their source file'
          % (len(DECISIONS) - len(bad), len(DECISIONS)))
    sys.exit(1 if bad else 0)
