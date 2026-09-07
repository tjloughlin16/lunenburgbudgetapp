#!/usr/bin/env python3
"""The open decisions and open questions, pulled out for review on paper.

    python3 scripts/build_decisions_doc.py
    python3 scripts/build_decisions_doc.py --check

WHY THIS IS EXTRACTED RATHER THAN WRITTEN

There is already one list, in `notes/findings/DRILL-IN-PAGES.md`, sections 6 and 7. A
second copy typed for printing is a second thing to update and the first one to go stale
-- which is rule 2 applied to a document instead of a figure, and is exactly how three
figures in this project ended up stating amounts the model no longer produced.

So this reads those two sections out of the source document and adds the counts, derived.
If a decision is taken and struck from the notes, the printable copy loses it on the next
run rather than going on presenting it for review.

THE COUNTS ARE COMPUTED, not stated: how many decisions, how many questions, and how many
rows the gap registry actually holds. The last one is the check that matters, because
section 7 claims each question is registered and a count that disagrees means one is not.
"""
import argparse
import csv
import os
import re
import subprocess
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'notes', 'findings', 'DRILL-IN-PAGES.md')
GAPS = os.path.join(ROOT, 'sources', 'data', 'money-gaps.csv')
OUT = os.path.join(ROOT, 'notes', 'generated', 'OPEN-QUESTIONS-AND-DECISIONS.md')


def section(text, number):
    """The body of `## <number>. ...` up to the next `## ` heading."""
    m = re.search(r'^## %s\. (.+?)$(.*?)(?=^## |\Z)' % number, text, re.M | re.S)
    if not m:
        raise SystemExit('build_decisions_doc: no section %s in %s -- the notes were '
                         'restructured and this extractor still expects the old shape. '
                         'Refusing to write a document that would silently lose half its '
                         'content.' % (number, os.path.relpath(SRC, ROOT)))
    return m.group(1).strip(), m.group(2).strip()


def build():
    text = open(SRC, encoding='utf-8').read()
    d_title, decisions = section(text, 6)
    q_title, questions = section(text, 7)
    _, howto = section(text, 8)

    n_dec = len(re.findall(r'^\| D\d+ \|', decisions, re.M))
    n_q = len(re.findall(r'^\d+\. \*\*', questions, re.M))
    n_gaps = len(list(csv.DictReader(open(GAPS, encoding='utf-8'))))
    sides = sorted({r['side'] for r in csv.DictReader(open(GAPS, encoding='utf-8'))})

    if not n_dec or not n_q:
        raise SystemExit('build_decisions_doc: matched %d decisions and %d questions. A '
                         'list that matches nothing looks exactly like a list with '
                         'nothing on it. Refusing to write.' % (n_dec, n_q))

    o = [
        '# What is waiting on a decision, and what is waiting on a document',
        '',
        'The Lunenburg Budget Project — for review, %s' % date.today().strftime('%-d %B %Y'),
        '',
        '**%d decisions** and **%d open questions**. The gap registry behind the questions '
        'holds **%d rows** across %d kinds: %s.'
        % (n_dec, n_q, n_gaps, len(sides), ', '.join('`%s`' % s for s in sides)),
        '',
        'The two lists are kept apart because they behave differently, and section 3 below '
        'is the part worth reading first if you read nothing else.',
        '',
        '---',
        '',
        '## 1. %s' % d_title,
        '',
        decisions,
        '',
        '---',
        '',
        '## 2. %s' % q_title,
        '',
        questions,
        '',
        '---',
        '',
        '## 3. How to use the two lists',
        '',
        howto,
        '',
        '---',
        '',
        '*Extracted from `notes/findings/DRILL-IN-PAGES.md` sections 6-8 by '
        '`scripts/build_decisions_doc.py`. The counts above are computed at build time, '
        'and the gap count is read from `sources/data/money-gaps.csv` — so if a question '
        'here is not registered there, these two numbers stop agreeing.*',
        '',
    ]
    return '\n'.join(o)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    made = build()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    if a.check:
        have = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        if have != made:
            print('STALE — %s no longer reproduces from the notes' % os.path.relpath(OUT, ROOT))
            sys.exit(1)
        print('ok — %s reproduces' % os.path.relpath(OUT, ROOT))
    else:
        open(OUT, 'w', encoding='utf-8').write(made)
        print('wrote %s' % os.path.relpath(OUT, ROOT))
