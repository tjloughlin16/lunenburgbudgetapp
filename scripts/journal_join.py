#!/usr/bin/env python3
"""THE SCHOOL JOURNAL'S ENTRIES, JOINED ONCE: every journal entry with its other side.

    python3.11 scripts/journal_join.py           # write sources/data/munis-school-journal-entries.csv
    python3.11 scripts/journal_join.py --check   # rebuild in memory; fail if the file differs

    import journal_join as JJ
    E = JJ.entries()                              # one dict per entry, the CSV's columns

WHAT AN ENTRY IS. A general-journal entry -- source `GEN`, or its reversal `GRV` -- is every
line the school journal (`scripts/journal.py`, Report 1) holds under one journal number. It is
the only kind of posting in the journal that MOVES money between accounts rather than paying
somebody: an invoice (`API`) has a vendor and a check, a pay run (`PRJ`) a warrant, a journal
entry has neither. So "how much moves by journal entry" is a question about these rows.

WHY A JOIN IS NEEDED. Five reasons a journal entry's other side is not simply the other lines
under its number (notes/findings/JOURNAL-RECLASSES.md):
  1. SCOPE. Report 1 holds school accounts only. An entry whose other side is a Town account
     (a fuel charge, a health insurance reclass, the summer-pay accrual's liability) shows one
     side and nets to something other than zero. That is `net` here, and `one-sided`.
  2. CORRECTIONS UNDER A NEW NUMBER. A mistake is undone by a later entry, not edited, so a
     correction and what it corrects are two journal numbers. `pairs_with` joins them, and
     `chain` groups every entry so joined, so a correction is counted once, not twice.
  3. NO PAYEE on these lines, so the join is by ACCOUNT and AMOUNT, never by vendor.
  4. FREE-TEXT MONTH TAGS in `doc_no` (`feb`, `March`, `JE JUN`). `month_tag` reads them.
  5. ACCRUALS put several months into June. They are a kind of their own.

HOW TWO ENTRIES ARE PAIRED -- three bases, tried in order, and the CSV says which one held:
  reference   the entry's text names the other journal (`J# 2025/7/286`, `2023/9 GEN J #14`)
  reversal    the entry says it reverses or corrects (`REVERSAL_SIGNAL`), or is a `GRV`, and at
              least one of its lines cancels a line of an earlier journal -- same account, the
              opposite amount to the cent. The earlier journal with the most such lines is the
              one; a tie goes to the later of them (a duplicate is the SECOND posting). Any
              source may be the target: the December 2025 `Duplicate` reverses a pay run (PRJ).
  cancels     no word says so, but the entry cancels EVERY line of an earlier GEN/GRV entry.
              Stricter, because amounts repeat by coincidence: the summer-pay accruals share
              per-account salary figures with that December reversal, line for line.
A pair is a claim about the LEDGER (these lines undo those), never about why anybody posted it.

WHAT FAILS LOUDLY. An entry that says it reverses or corrects and pairs with nothing stops the
build unless `UNPAIRED` declares why, with the evidence. A declaration that no longer applies
(the entry now pairs) stops it too. Every GEN/GRV line must land in exactly one entry.

KIND -- one per entry, our classification, the first rule that holds (`KIND_RULES`):
  reversal        paired, and a GRV or worded as a reversal
  correction      paired by any other basis: it re-posts or moves what an earlier entry did
  payroll accrual year-end payroll booked to the year it was earned (`ACCRUAL`)
  town charge     a recurring charge between the Town and the schools: fuel, postage, sewer,
                  rent, the turf payment (`TOWN_CHARGE`), whatever its balance
  reclass         every line inside school accounts, netting to zero: a move between them
  one-sided       anything else that does not net to zero: the other side is not in Report 1
The words that sort entries are the Town's own, read off the descriptions; the sorting is ours.
"""
import csv
import io
import json
import os
import re
import sys
from collections import Counter, defaultdict
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import journal as J  # noqa: E402

OUT = os.path.join(J.DATA, 'munis-school-journal-entries.csv')
SOURCES = ('GEN', 'GRV')

REVERSAL_SIGNAL = re.compile(r'\bREVERS|\bREV\b|DUPLICATE|\bCRT\b|CORRECT', re.I)
REVERSAL_WORD = re.compile(r'\bREVERS|\bREV\b|DUPLICATE', re.I)
REFERENCE = [re.compile(r'J#\s*(\d{4})/(\d{1,2})/(\d{1,6})', re.I),
             re.compile(r'(\d{4})/(\d{1,2})\s+GEN\s+J\s*#\s*(\d{1,6})', re.I)]
ACCRUAL = re.compile(r'SUMMER PAY|SUMM PAY|SUMMARY PAY|SUMMER PAYROLL|ACCRU|PORTION OF \d+ ?P'
                     r'|POERTION OF \d+P|ESCROW|SCHOOL OFFICE PYRL', re.I)
TOWN_CHARGE = re.compile(r'FUEL|POSTAGE|SEWER|\bRENT\b|TURF|LEASE OF|CHERRYROAD|SCHOOL METER', re.I)

# Entries that say they correct something and have no other side in Report 1 -- declared, each
# with the evidence, so a new one cannot slip through as "unmatched" without somebody reading it.
UNPAIRED = {
    '2026/12/000235': 'health insurance into the school GF, other side not in school accounts '
                      '(Report 1 p652); "crt wrt 57 26" names a warrant, not a journal',
    '2026/12/000237': '"move to correct acct": posted to unemployment, itself moved on to health '
                      'insurance by 2026/12/001640, which pairs with it',
    '2026/12/000239': 'health insurance into the school GF, other side not in school accounts; '
                      '"crt wrt 45 26" names a warrant, not a journal',
}

MONTHS = {m: i for i, m in enumerate(
    ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'], 1)}

COLUMNS = ['fiscal_year', 'entry', 'journal', 'source', 'period', 'effective_date', 'lines', 'debits',
           'credits', 'net', 'moved', 'accounts', 'funds', 'fund_groups', 'object_families',
           'kind', 'pairs_with', 'pair_basis', 'pair_cover', 'matched_lines', 'paired_by',
           'chain', 'chain_net', 'month_tag', 'posted_month', 'description', 'descriptions',
           'unpaired_reason',
           'first_page']

# Object families: the first two digits of the object code. The digits are the Town's chart;
# the names are ours, read off the account descriptions each family holds.
OBJECT_FAMILY = {'51': 'salaries', '52': 'utilities and repairs', '53': 'purchased services',
                 '54': 'supplies', '55': 'instructional materials', '57': 'benefits and other',
                 '58': 'equipment and capital'}


def object_family(obj):
    if obj[:1] == '4':
        return 'revenue'
    try:
        return OBJECT_FAMILY[obj[:2]]
    except KeyError:
        raise SystemExit('journal_join.py: object %s has no family in OBJECT_FAMILY' % obj)


def journal_id(y, m, n):
    return '%s/%02d/%06d' % (y, int(m), int(n))


def month_tag(doc_no):
    m = re.search(r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b', doc_no, re.I)
    return MONTHS[m.group(1).lower()] if m else None


def money(d):
    return '%.2f' % d


def _cancel_count(mine, theirs):
    """How many of `mine` cancel a line of `theirs` (same account, opposite amount), each line
    used once. Returns (count, matched lines of mine)."""
    pool = Counter((r['account'], r['amt']) for r in theirs)
    hit = []
    for r in mine:
        k = (r['account'], -r['amt'])
        if r['amt'] != 0 and pool[k] > 0:
            pool[k] -= 1
            hit.append(r)
    return len(hit), hit


def split(v):
    """A journal number is a BATCH: 14 of 150 hold unrelated postings (a sewer charge, a fee
    move and a grant-salary move under 2023/09/000014). So an entry is one DESCRIPTION group
    of a journal; two groups that cancel each other exactly (`DOG SHOW FR HIGH SCH` and
    `DOG SHOW TO MIDDLE SCH`) are one entry. Order is the order the lines were printed."""
    groups = defaultdict(list)
    for r in v:
        groups[r['description']].append(r)
    gs = sorted(groups.values(), key=lambda g: (int(g[0]['page']), int(g[0]['line'])))
    out, used = [], set()
    for i, g in enumerate(gs):
        if i in used:
            continue
        net = sum(r['amt'] for r in g)
        if net != 0:
            for k in range(i + 1, len(gs)):
                if k not in used and sum(r['amt'] for r in gs[k]) == -net:
                    g = g + gs[k]
                    used.add(k)
                    break
        out.append(g)
    return out


def build():
    L = J.lines()
    A = J.accounts()
    by_j = defaultdict(list)
    for r in L:
        by_j[(r['fy'], r['journal'])].append(r)
    jkeys = sorted(k for k, v in by_j.items() if v[0]['source'] in SOURCES)
    for k in jkeys:
        if {r['source'] for r in by_j[k]} - set(SOURCES):
            raise SystemExit('journal_join.py: %s mixes a journal entry with %s'
                             % (k[1], {r['source'] for r in by_j[k]}))
    # UNITS: every entry (GEN/GRV, split) and every other journal whole, as pairing targets.
    unit = {}                              # (fy, entry id) -> lines
    ent_keys = []
    for k, v in by_j.items():
        if k in jkeys:
            parts = split(v)
            for i, g in enumerate(parts, 1):
                eid = k[1] if len(parts) == 1 else '%s-%d' % (k[1], i)
                unit[(k[0], eid)] = g
                ent_keys.append((k[0], eid))
        else:
            unit[k] = v
    ent_keys.sort()
    n_lines = sum(1 for r in L if r['source'] in SOURCES)
    if sum(len(unit[k]) for k in ent_keys) != n_lines or len(
            {id(r) for k in ent_keys for r in unit[k]}) != n_lines:
        raise SystemExit('journal_join.py: entries do not hold each of the %d GEN/GRV lines '
                         'exactly once' % n_lines)
    jof = lambda u: u[1][:14]               # noqa: E731  the journal number of a unit
    touch = defaultdict(set)
    for u, v in unit.items():
        for r in v:
            touch[(u[0], r['account'])].add(u)

    rows = {}
    pairs = []
    for k in ent_keys:
        fy, e = k
        j = jof(k)
        v = unit[k]
        text = ' '.join(sorted({r['description'] + ' ' + r['comment'] for r in v}))
        net = sum(r['amt'] for r in v)
        debits = sum(r['amt'] for r in v if r['amt'] > 0)
        credits = -sum(r['amt'] for r in v if r['amt'] < 0)
        desc = Counter(r['description'] for r in v).most_common(1)[0][0]
        tag = Counter(month_tag(r['doc_no']) for r in v).most_common(1)[0][0]
        row = {'fiscal_year': fy, 'entry': e, 'journal': j, 'source': v[0]['source'],
               'period': v[0]['period'], 'effective_date': v[0]['effective_date'],
               'lines': len(v), 'debits': money(debits), 'credits': money(credits),
               'net': money(net), 'moved': money(min(debits, credits)),
               'accounts': len({r['account'] for r in v}),
               'funds': ';'.join(sorted({r['fund'] for r in v})),
               'fund_groups': ';'.join(sorted({J.fund_group(A[r['account']]) for r in v})),
               'object_families': ';'.join(sorted({object_family(r['object']) for r in v})),
               'kind': '', 'pairs_with': '', 'pair_basis': '', 'pair_cover': '',
               'matched_lines': '', 'paired_by': '', 'chain': '', 'chain_net': '',
               'month_tag': tag or '', 'posted_month': int(v[0]['effective_date'][5:7]),
               'description': desc,
               'descriptions': json.dumps(sorted({r['description'] for r in v}), ensure_ascii=False),
               'unpaired_reason': '',
               'first_page': min(int(r['page']) for r in v)}
        rows[k] = row
        cands = set()
        for r in v:
            cands |= {t for t in touch[(fy, r['account'])] if jof(t) < j}
        target, basis, hit = None, '', []
        # 1. reference: the named journal; within it, the unit this entry cancels most
        for rx in REFERENCE:
            for m in rx.finditer(text):
                ref = journal_id(*m.groups())
                inside = sorted(u for u in unit if u[0] == fy and jof(u) == ref)
                if inside:
                    best = max(inside, key=lambda u: (_cancel_count(v, unit[u])[0], u))
                    target, basis, hit = best, 'reference', _cancel_count(v, unit[best])[1]
                    break
            if target:
                break
        signal = bool(REVERSAL_SIGNAL.search(text)) or v[0]['source'] == 'GRV'
        # 2. reversal: worded, the earlier unit of any source it cancels most (tie: the later)
        if not target and signal:
            best = (0, None, [])
            for t in sorted(cands):
                n, h = _cancel_count(v, unit[t])
                if n and n >= best[0]:
                    best = (n, t, h)
            if best[1]:
                target, basis, hit = best[1], 'reversal', best[2]
        # 3. cancels every line of an earlier GEN/GRV entry
        if not target:
            for t in sorted(cands, reverse=True):
                if unit[t][0]['source'] not in SOURCES:
                    continue
                n, h = _cancel_count(unit[t], v)
                if n == len(unit[t]):
                    target, basis, hit = t, 'cancels', _cancel_count(v, unit[t])[1]
                    break
        if target:
            tl = unit[target]
            row['pairs_with'] = target[1]
            row['pair_basis'] = basis
            row['matched_lines'] = len(hit)
            row['pair_cover'] = 'full' if _cancel_count(tl, v)[0] == len(tl) else 'partial'
            pairs.append((k, target))
            if e in UNPAIRED:
                raise SystemExit('journal_join.py: %s is declared UNPAIRED but now pairs with %s '
                                 '(%s); remove the declaration' % (e, target[1], basis))
        elif signal:
            if e not in UNPAIRED:
                raise SystemExit('journal_join.py: %s says it reverses or corrects (%r) and '
                                 'cancels no earlier line. Find its other side, or declare it in '
                                 'UNPAIRED with the evidence.' % (e, desc))
            row['unpaired_reason'] = UNPAIRED[e]
    stale = set(UNPAIRED) - {k[1] for k in ent_keys}
    if stale:
        raise SystemExit('journal_join.py: UNPAIRED names entries not in the run: %s' % sorted(stale))

    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for a, b in pairs:
        parent[find(a)] = find(b)
    members = defaultdict(set)
    for k in ent_keys:
        members[find(k)].add(k)
    for a, b in pairs:
        members[find(a)].add(b)
    for ms in members.values():
        cid = min(m[1] for m in ms)
        cnet = sum(r['amt'] for m in ms for r in unit[m])
        for m in ms:
            if m in rows:
                rows[m]['chain'] = cid
                rows[m]['chain_net'] = money(cnet)
    for a, b in pairs:
        if b in rows:
            rows[b]['paired_by'] = ';'.join(filter(None, [rows[b]['paired_by'], a[1]]))

    for k in ent_keys:
        rows[k]['kind'] = kind_of(rows[k], unit[k])
    return [rows[k] for k in ent_keys]


def kind_of(row, v):
    text = ' '.join({r['description'] for r in v})
    for name, test in KIND_RULES:
        if test(row, text):
            return name
    raise SystemExit('journal_join.py: %s matches no kind' % row['journal'])


KIND_RULES = [
    ('reversal', lambda e, t: bool(e['pairs_with']) and (e['source'] == 'GRV'
                                                         or bool(REVERSAL_WORD.search(t)))),
    ('correction', lambda e, t: bool(e['pairs_with'])),
    ('payroll accrual', lambda e, t: bool(ACCRUAL.search(t))),
    ('town charge', lambda e, t: bool(TOWN_CHARGE.search(t))),
    ('reclass', lambda e, t: Decimal(e['net']) == 0),
    ('one-sided', lambda e, t: True),
]
KINDS = tuple(k for k, _ in KIND_RULES)


def render(rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLUMNS, lineterminator='\n')
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


def entries():
    """The joined entries, read from the CSV (types: amounts Decimal, fy/lines int)."""
    out = []
    for r in csv.DictReader(open(OUT, encoding='utf-8', newline='')):
        r['fy'] = int(r['fiscal_year'])
        for f in ('debits', 'credits', 'net', 'moved'):
            r[f] = Decimal(r[f])
        r['chain_net'] = Decimal(r['chain_net']) if r['chain_net'] else None
        r['lines'] = int(r['lines'])
        out.append(r)
    return out


def main():
    rows = build()
    text = render(rows)
    n = sum(r['lines'] for r in rows)
    kinds = Counter(r['kind'] for r in rows)
    pairs = sum(1 for r in rows if r['pairs_with'])
    summary = ('%d entries, %d lines assigned (every GEN/GRV line), %d paired, %d declared '
               'unpaired; kinds: %s' % (len(rows), n, pairs, len(UNPAIRED),
                                       ', '.join('%s %d' % (k, kinds[k]) for k in KINDS)))
    if '--check' in sys.argv:
        old = open(OUT, encoding='utf-8', newline='').read() if os.path.exists(OUT) else ''
        if old != text:
            print('journal_join.py: %s is STALE; run without --check' % os.path.relpath(OUT, J.ROOT))
            sys.exit(1)
        print('journal_join.py: reproduces. ' + summary)
        return
    tmp = OUT + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='') as f:
        f.write(text)
    os.replace(tmp, OUT)
    print('journal_join.py: wrote %s. %s' % (os.path.relpath(OUT, J.ROOT), summary))


if __name__ == '__main__':
    main()
