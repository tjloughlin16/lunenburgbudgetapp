"""Recompute every figure in the athletics analysis, and fail if one drifted.

Rule 9: figures in a finished document get re-checked by script, not re-read. Prose drifts
during editing and the version that ships is the one nobody checked.

Everything here is recomputed from primary sources -- the FY27 workbook, the fund's own
year-end reconciliation, the extracted line history, and the FY19 split document as
transcribed into model/athletics.py -- and then asserted to be present in the document.

    python3 scripts/verify_athletics.py
"""
import os, sys, csv, collections, json, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'model'))
DOC = os.path.join(ROOT, 'sources/analyses/athletics.md')
DATA = os.path.join(ROOT, 'sources/data')

LEDGER_DOC = os.path.join(ROOT, 'sources/analyses/athletics-ledger.md')

TEXT = open(DOC, encoding='utf-8').read()
PLAIN = TEXT.replace('**', '').replace('`', '')

# THE SECOND DOCUMENT WAS NEVER CHECKED BY ANYTHING.
#
# `athletics-ledger.md` states the comparison against the district's own workbook and the
# share it implies, and both moved when three FY2024 rows were withdrawn. This file read
# only `athletics.md`, so a figure could be recomputed, found wrong, corrected in one
# document and left standing in the other -- which is what happened. A verifier that names
# one document is a verifier with a blind spot the size of the second one.
LEDGER = open(LEDGER_DOC, encoding='utf-8').read()
LEDGER_PLAIN = LEDGER.replace('**', '').replace('`', '')

FAILS = []


def present(label, needle):
    # Prose uses the typographic minus and en dash; code emits the ASCII hyphen, and they
    # are the same number. Normalising both sides beats reporting drift that is only a
    # character -- the same fix verify_budget_vs_actual.py carries.
    def norm(t):
        return t.replace('\u2212', '-').replace('\u2013', '-')
    n = str(needle)
    ok = (n in TEXT or n in PLAIN or norm(n) in norm(TEXT) or norm(n) in norm(PLAIN))
    if not ok:
        FAILS.append(f'{label}: "{n}" not in the document')
    print(f"  {'OK  ' if ok else 'GONE'}  {label:<46} {n}")


def present_ledger(label, needle):
    """The same assertion, against athletics-ledger.md."""
    def norm(t):
        return t.replace('\u2212', '-').replace('\u2013', '-')
    n = str(needle)
    ok = (n in LEDGER or n in LEDGER_PLAIN
          or norm(n) in norm(LEDGER) or norm(n) in norm(LEDGER_PLAIN))
    if not ok:
        FAILS.append(f'{label}: "{n}" not in athletics-ledger.md')
    print(f"  {'OK  ' if ok else 'GONE'}  {label:<46} {n}")


def head(t):
    print(f'\n{t}')


# --- the FY19 split document, via the model ---------------------------------------
import athletics as A
S = A.SPLIT_REPORTING

head('The FY19 split document — transportation, both sides')
for r in S['transportation']:
    tot = r['general'] + r['revolving']
    share = r['revolving'] / tot * 100
    present(f"FY{r['fy']} appropriated", f"{r['general']:,}")
    present(f"FY{r['fy']} revolving", f"{r['revolving']:,}")
    present(f"FY{r['fy']} total", f"{tot:,}")
    present(f"FY{r['fy']} fund share", f'{share:.1f}%')

head('The FY19 split document — whole programme')
for r in S['programme']:
    present(f"FY{r['fy']} general appropriation", f"{r['general']:,}")
    present(f"FY{r['fy']} revolving 658", f"{r['revolving']:,}")
    present(f"FY{r['fy']} grand total", f"{r['stated']:,}")
    present(f"FY{r['fy']} revenues", f"{r['revenue']:,}")

# The document claims its source's grand totals are $1 off in FY14/FY15 and exact after.
off = {r['fy']: r['general'] + r['revolving'] - r['stated'] for r in S['programme']}
bad = {fy: d for fy, d in off.items() if abs(d) > 1}
if bad:
    FAILS.append(f'source grand totals off by more than $1: {bad}')
exact = sorted(fy for fy, d in off.items() if d == 0)
print(f"\n  {'OK  ' if len(exact) == 4 else 'FAIL'}  "
      f"grand totals exact in {len(exact)} of {len(off)} years        {exact}")
if len(exact) != 4:
    FAILS.append(f'expected 4 exact years, found {len(exact)}')

# --- FY26 general fund athletics, from the workbook -------------------------------
head('FY26 whole programme')
import re
try:
    import openpyxl
    ws = openpyxl.load_workbook(
        os.path.join(ROOT, 'sources/budget-workbooks/fy27-proposals.xlsx'), data_only=True).active
    cur, gf = None, 0.0
    for row in range(6, ws.max_row + 1):
        a, b, v = ws.cell(row, 1).value, ws.cell(row, 2).value, ws.cell(row, 7).value
        if a and isinstance(a, str) and re.match(r'^\d{4}\s*-', a.strip()):
            cur = a.strip()
        if cur and cur.startswith('3510') and b and isinstance(v, (int, float)):
            gf += v
except ImportError:
    print('  SKIP  openpyxl not available'); gf = None

REV_FY26 = 146911.44          # school-funds-fy26.xlsx, Athletics Revolving, net expenditures
if gf is not None:
    present('FY26 general fund athletics', f'{gf:,.0f}')
    present('FY26 revolving expenditures', f'{REV_FY26:,.0f}')
    present('FY26 whole programme', f'{gf + REV_FY26:,.0f}')
    present('FY26 fund share', f'{REV_FY26 / (gf + REV_FY26) * 100:.1f}%')
    g19, r19 = 307931, 87902
    present('FY19 fund share', f'{r19 / (g19 + r19) * 100:.1f}%')

# --- the transportation line, budget against reported actual ----------------------
head('Athletic transportation — budget against reported actual')
# The stage a later budget document reports for a year that has closed. NOT `actual`:
# `line_history` has three stages -- proposed, settled, restated -- and the third is what
# `athletics.json` calls a restated actual. See notes/reference/SCHEMA.md.
ACTUAL_STAGE = 'restated'
rows = list(csv.DictReader(open(os.path.join(DATA, 'line-history.csv'))))
cell = collections.defaultdict(dict)
for r in rows:
    # variant='' only -- a scenario column is a different proposal for the same year,
    # not another reading of the same figure. See notes/reference/SCHEMA.md, budget_figure.
    if r['key'] == 'athletic transportation' and not r.get('variant'):
        cell[int(r['fy'])][r['stage']] = float(r['value'])
exact_years = []
for fy in sorted(cell):
    b = cell[fy].get('settled') or cell[fy].get('proposed')
    a_ = cell[fy].get(ACTUAL_STAGE)
    if b and a_ and b == a_:
        exact_years.append(fy)
usable = [fy for fy in sorted(cell)
          if (cell[fy].get('settled') or cell[fy].get('proposed')) and cell[fy].get(ACTUAL_STAGE)]
# WHAT WENT WRONG HERE, because it is rule 13 in one word. This block asked for stage
# `actual` and `line_history` has not carried that name for some time -- the stage a later
# budget document reports for a closed year is `restated`, which is what athletics.json's
# own `general_basis` calls a "restated actual". So the lookup matched nothing, `usable`
# came back empty, and the check printed "Four of zero usable years" rather than the "Four
# of nine" the document states. It FAILED loudly, which is the only reason it is fixable
# rather than silent -- but the shape is the one this project keeps hitting: a name typed
# into a script, the thing it named moved, and nothing connected the two.
if not usable:
    FAILS.append(f'no year carries both a budget and a {ACTUAL_STAGE!r} figure for '
                 'athletic transportation. That is an empty join, not a line nobody '
                 'reported -- check the stage vocabulary in line-history.csv.')
print(f'  {"OK  " if len(exact_years) == 4 else "FAIL"}  '
      f'years where actual equals budget exactly      {exact_years} of {len(usable)} usable')
if len(exact_years) != 4:
    FAILS.append(f'expected 4 exact years, found {len(exact_years)}: {exact_years}')
# Assert the counts the prose states, not merely that some sentence is present. The first
# draft said "four of eight" because FY25 was missed; the string check passed and the claim
# was still wrong.
WORDS = ['zero', 'one', 'two', 'three', 'four', 'five', 'six',
         'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve']
present('exact-match count', f'Four of {WORDS[len(usable)]} usable years')
ex21 = [fy for fy in exact_years if fy != 2021]
present('excluding FY21', f'three of {WORDS[len(usable) - 1]}')
if len(ex21) != 3:
    FAILS.append(f'expected 3 exact years excluding FY21, found {len(ex21)}')

# --- the FY25 deficit question ----------------------------------------------------
head('The fund across FY25/FY26 -- what is actually known')
OPEN26, REV, EXP, CLOSE26 = 110247.89, 188944.46, 146911.44, 152280.91
present('FY26 opening = FY25 closing', f'{OPEN26:,.2f}')
present('FY26 closing', f'{CLOSE26:,.2f}')
present('FY26 surplus', f'{REV - EXP:,.0f}')
if abs((OPEN26 + REV - EXP) - CLOSE26) > 0.01:
    FAILS.append('the fund roll-forward does not reconcile')
print(f'  OK    roll-forward reconciles                    '
      f'{OPEN26:,.2f} + {REV:,.2f} - {EXP:,.2f} = {OPEN26 + REV - EXP:,.2f}')
present('FY26 approved March 2025', f'{102550:,}')
present('FY26 final', f'{127550:,}')
present('the later increase', f'{127550 - 102550:,}')

# --- is $127,550 defensible ------------------------------------------------------
head('$127,550 against every documented base')
LINE = 127550
for label, v, fy in [('FY17 all-in', 73986, 2017), ('FY14 all-in', 47085, 2014),
                     ('FY25 reported actual', 87822, 2025), ('FY24 reported actual', 40000, 2024)]:
    yrs = 2026 - fy
    present(f'{label} ratio', f'{LINE / v:.2f}')
    present(f'{label} implied rate', f'{(( LINE / v) ** (1 / yrs) - 1) * 100:.2f}%')
present('FY26 committed at Q3', f'{47847 + 13169:,}')
present('FY26 Q3 ratio', f'{LINE / (47847 + 13169):.2f}')

# --- the memo's definition --------------------------------------------------------
head("The Finance Committee memo's arithmetic")
present('ledger expended', f'{34219013.80:,.2f}')
present('ledger encumbrances', f'{2626115.87:,.2f}')
present('their sum', f'{34219013.80 + 2626115.87:,.2f}')

# --- the swap ---------------------------------------------------------------------
head('The swap')
present('FY19 officials', f'{40117:,}')
present('FY19 uniforms', f'{8000:,}')
present('officials + uniforms', f'{40117 + 8000:,}')
present('ArbiterSports', f'{59400:,}')
present('Prime Time Sports', f'{25421:,}')

# --- section 6: the unproven workbook ---------------------------------------------
head('Section 6 -- the citizen workbook, recorded as unproven')
# The 25/26 column is the prior year escalated 6.5%. Asserted so a future edit cannot
# quietly promote a modelled column to a measurement.
for y2425, y2526 in ((43446.06, 46270.05), (29377.50, 31287.03), (18242.50, 19428.24)):
    if abs(y2425 * 1.065 - y2526) > 0.05:
        FAILS.append(f'{y2425} x 1.065 != {y2526}; the 25/26 escalation claim is wrong')
print('  OK    25/26 is 24/25 escalated 6.5% (three seasons checked)')
for label, gf_, tot in (('FY24', 40000.0, 117555.00), ('FY25', 87822.0, 91066.06)):
    present(f'{label} workbook total', f'{tot:,.0f}')
    present(f'{label} implied fund share', f'{(tot - gf_) / tot * 100:.1f}%')
# The fund's margin, both eras
head('Section 6 -- the fund never had slack')
for fy, cost, rev in ((2014, 107257, 110474), (2017, 131551, 109351), (2018, 60001, 108000)):
    present(f'FY{fy} margin', f'{rev - cost:+,}')
for fy, cost, rev in ((2024, 129125, 128252.50), (2025, 53940, 117069.00)):
    present(f'FY{fy} margin', f'{rev - cost:+,.0f}')

# --- the general fund series, recomputed from athletics_history ---------------------
#
# THIS BLOCK EXISTS BECAUSE THE VERIFIER PASSED WHILE THE TABLE WAS WRONG.
#
# Commit 07aa298 withdrew three FY2024 rows -- Freshman & MS Coaches, Unified Sports Coach
# and Replacement of Uniforms -- when it fixed a workbook whose column mapping had let
# unlabelled cells through. The analysis table predated that and went on printing 314,319
# for a year the data now totals 285,281, a difference of exactly the three withdrawn rows.
#
# Nothing failed, because nothing checked the table: this file asserted the FY19 split
# document, the workbook totals and the fund margins, and never the series the document
# leads with. A figure sitting beside figures that ARE checked inherits their credibility
# and none of their maintenance -- which is why it survived every read-through, and why the
# fix is a check rather than more care.
head('The general fund series, recomputed from athletics_history')
import sqlite3
_db = sqlite3.connect(os.path.join(DATA, 'lunenburg.db'))
_gen = {fy: amt for fy, amt in _db.execute(
    "SELECT fy, SUM(amount) FROM athletics_history WHERE side='general' GROUP BY fy")}
for _fy in sorted(_gen):
    present(f'FY{_fy} general fund total', f'{round(_gen[_fy]):,}')

# The comparison against the district's own workbook, and the share it implies. Both
# numbers moved when the three rows came out and only one of them was in this file.
head('Section 5 -- appropriation against the workbook, FY2024')
_WORKBOOK_FY24 = 351642.89          # the workbook's own total, checked below
_UNMATCHED = 160980.00              # AD, trainer, insurance -- lines the workbook omits
_comparable = round(_gen[2024] - _UNMATCHED, 2)
present_ledger('FY2024 comparable general fund', f'{_comparable:,.2f}')
present_ledger('FY2024 workbook cost', f'{_WORKBOOK_FY24:,.2f}')
present_ledger('FY2024 share the appropriation covered', f'{_comparable / _WORKBOOK_FY24 * 100:.0f}%')
present_ledger('FY2024 outside the general fund', f'{_WORKBOOK_FY24 - _comparable:,.2f}')
if abs(_comparable + _UNMATCHED - _gen[2024]) > 0.005:
    FAILS.append('the comparable and unmatched halves no longer sum to the FY2024 total')

# --- document basis counts --------------------------------------------------------
head('Source-type counts, from document-basis.csv')
basis = collections.Counter(r['source_type']
                            for r in csv.DictReader(open(os.path.join(DATA, 'document-basis.csv'))))
for k in ('ledger', 'restatement', 'forward', 'narrative'):
    present(f'{k} documents', f'| {basis[k]} |')

# --- THE PER-SPORT DISAGREEMENT, WHICH IS NOW THE CENTREPIECE OF /what-sports-cost ----
#
# WHY THIS SECTION EXISTS. `model/athletics_sources.py` computes the three published
# per-sport costs and the spread between them, ships them in model.json, and until now
# NOTHING re-derived any of it. It is the most quoted material this project holds -- a
# reader uses it to decide which team to give up -- and it was the least checked.
#
# AND HOW IT IS CHECKED MATTERS MORE THAN THAT IT IS. This file's own history is the
# warning: it once asserted that a SENTENCE existed and passed while the sentence was
# wrong. So nothing below looks for a string in prose. Each check recomputes a value from
# the CSV or from the constants and compares it to the value that SHIPPED, which is what a
# reader gets.
head('The three per-sport cost columns, recomputed against what ships in model.json')

_MODEL = json.load(open(os.path.join(ROOT, 'fy28/src/data/model.json')))['athletics']['costSources']


def same(label, got, want, tol=0.005):
    ok = abs(float(got) - float(want)) <= tol
    if not ok:
        FAILS.append(f'{label}: recomputed {got!r}, model.json ships {want!r}')
    print(f"  {'OK  ' if ok else 'FAIL'}  {label:<46} {got}")


def same_text(label, got, want):
    ok = str(got) == str(want)
    if not ok:
        FAILS.append(f'{label}: recomputed {got!r}, model.json ships {want!r}')
    print(f"  {'OK  ' if ok else 'FAIL'}  {label:<46} {got}")


# 1. THE DERIVED COLUMN, READ BACK OUT OF THE EXTRACT BY A DIFFERENT ROUTE.
#    athletics_sources.py maps workbook rows onto the roster through a crosswalk. This
#    sums the workbook's own `Total Expenses` column for the comparison year with no
#    crosswalk at all, and asserts the mapped column plus the rows the module says it held
#    out come back to it. A crosswalk that silently stopped matching would publish a small
#    column and look exactly like a district that spends less.
_FY = _MODEL['fy']
_wb_rows = [r for r in csv.DictReader(open(os.path.join(DATA, 'athletics-by-sport.csv')))
            if r['metric'] == 'Total Expenses' and r['is_numeric'] == '1'
            and int(r['fy']) == _FY]
if not _wb_rows:
    FAILS.append(f'athletics-by-sport.csv carries no FY{_FY} Total Expenses rows at all')
_wb_column = round(sum(float(r['value']) for r in _wb_rows), 2)
_excluded_names = {(e['level'], e['sport']) for e in _MODEL['excluded']}
_excluded_sum = round(sum(float(r['value']) for r in _wb_rows
                         if (r['level'], r['sport']) in _excluded_names), 2)
same(f'FY{_FY} workbook Total Expenses column', _wb_column,
     round(_MODEL['totals']['workbook'] + _excluded_sum, 2))

# 2. EVERY COLUMN TOTAL IS THE SUM OF ITS OWN CELLS. The export states this identity and
#    a total that has drifted from its rows is the one error a reader cannot see.
for _col in sorted(_MODEL['totals']):
    same(f'{_col} total = sum of its per-sport cells',
         round(sum(s['columns'][_col] for s in _MODEL['sports'] if _col in s['columns']), 2),
         _MODEL['totals'][_col])

# 3. THE TWO TRANSCRIBED COLUMNS AGAINST THE CONSTANTS THEY WERE TRANSCRIBED INTO.
#    Rule 2 permits them to stay typed because no machine-readable extract of either
#    document exists. It does not permit them to go unchecked against the one place they
#    are written down.
_by_name = {s['name']: s for s in A.SPORTS}
for _s in _MODEL['sports']:
    _src = _by_name.get(_s['name'])
    if _src is None:
        FAILS.append(f"model.json ships a sport model/athletics.py does not: {_s['name']}")
        continue
    if abs(_s['columns']['costsBySport'] - _src['cost']) > 0.005:
        FAILS.append(f"{_s['name']}: costsBySport {_s['columns']['costsBySport']} is not "
                     f"the constant {_src['cost']}")
    if abs(_s['columns']['deck'] - _src['deckCost']) > 0.005:
        FAILS.append(f"{_s['name']}: deck {_s['columns']['deck']} is not the constant "
                     f"{_src['deckCost']}")
print(f"  {'OK  ' if not FAILS else '....'}  "
      f"{len(_MODEL['sports'])} sports against model/athletics.py's constants")

# 4. THE SPREAD, THE WIDEST TEAM AND THE COUNT THAT AGREE, all recomputed. These three are
#    the figures the page sets large, and rule 13a turns on them: publish the spread,
#    never a reconciliation.
_lo, _hi = min(_MODEL['totals'].values()), max(_MODEL['totals'].values())
same('total spread', round(_hi - _lo, 2), _MODEL['totalSpread'])
same('total spread, per cent', round((_hi - _lo) / _lo * 100, 1), _MODEL['totalSpreadPct'])
_widest = max(_MODEL['sports'], key=lambda s: s['spreadPct'] or 0)
same_text('widest team', _widest['name'], _MODEL['widest'])
same('widest team, per cent', _widest['spreadPct'], _MODEL['widestPct'], tol=0.05)
same('teams whose three figures agree',
     sum(1 for s in _MODEL['sports'] if s['spread'] < 0.005), _MODEL['agreeing'])
for _s in _MODEL['sports']:
    _vals = list(_s['columns'].values())
    if abs(_s['spread'] - (max(_vals) - min(_vals))) > 0.005:
        FAILS.append(f"{_s['name']}: the published spread is not high minus low")

# --- THE PAGE'S OWN PAYLOAD -------------------------------------------------------
#
# /what-sports-cost renders `fy28/public/data/athletics.json`. Its generator's --check
# proves the file still reproduces from the database; it cannot prove that the three-way
# figures the page sets large are arithmetically what they claim, because the generator
# computed them and would compute them the same way again.
head('The page payload — the three pots, recomputed')
_PAGE = json.load(open(os.path.join(ROOT, 'fy28/public/data/athletics.json')))
_t = _PAGE['three_way']
same('two pots = fund payments + appropriation',
     round(_t['fund_paid'] + _t['general'], 2), _t['two_pots'])
same('over the workbook = two pots - workbook',
     round(_t['fund_paid'] + _t['general'] - _t['workbook'], 2), _t['over_workbook'])
_src_amounts = sorted(round(s['amount'], 2) for s in _t['sources'])
if _src_amounts != sorted(round(x, 2) for x in
                          (_t['workbook'], _t['fund_paid'], _t['general'])):
    FAILS.append('the three rows the page prints are not the three figures it computes')
print(f"  OK    the three printed rows are the three computed figures")

# THE TWO SEARCH COUNTS THE PAGE STATES IN PROSE, counted again over the same corpus.
# The page says `programmatic cost` appears in one document and `pay to play` in none, and
# both sentences are load-bearing: the first is the closest the record comes to saying what
# a column counts, and the second is the claim that this town does not use that phrase.
# Counted with a LEADING word boundary only -- residents write plurals.
head('The two search counts the page states, recounted')
_bodies = []
for _dirpath, _dirnames, _files in os.walk(os.path.join(ROOT, 'sources/meetings/text')):
    for _f in _files:
        if _f.endswith('.txt'):
            _bodies.append(os.path.join(_dirpath, _f))
if not _bodies:
    FAILS.append('sources/meetings/text holds no documents — a recount of nothing is not '
                 'a recount')
for _term in ('programmatic cost', 'pay to play'):
    _n = sum(1 for _b in _bodies
             if re.search(r'\b%s' % re.escape(_term),
                          open(_b, encoding='utf-8', errors='replace').read(), re.I))
    _shipped = next(s['documents'] for s in _PAGE['searched'] if s['term'] == _term)
    same(f'documents saying “{_term}”', _n, _shipped, tol=0)

# EVERY QUOTE THE PAGE PRINTS, STILL IN THE FILE IT NAMES. The generator asserts this on
# the way out; this asserts it against the published payload, which is what a reader gets.
head('Every quote in the payload, against the minutes file it cites')
for _key in ('by_sport_said', 'helmets_sequel'):
    _blk = _PAGE[_key]
    # The published address is /docs/minutes/...; on disk it is sources/meetings/text/...
    # Two names for one thing, and the mapping is written here rather than assumed.
    _path = os.path.join(ROOT, _blk['url'].replace('/docs/minutes/', 'sources/meetings/', 1))
    if not os.path.exists(_path):
        FAILS.append(f'{_key}: {_path} is not on disk')
        continue
    _flat = ' '.join(open(_path, encoding='utf-8', errors='replace').read().split())
    for _q in _blk['quotes']:
        _ok = ' '.join(_q['text'].split()) in _flat
        if not _ok:
            FAILS.append(f'{_key}: “{_q["text"][:50]}…” is no longer in {_blk["url"]}')
        print(f"  {'OK  ' if _ok else 'GONE'}  {_key:<20} line {_q['line']:<6} "
              f"{_q['text'][:44]}…")


# THE PERSONA REVIEW WAS RUN, AND THIS IS THE ONE ASSERTION HERE THAT IS ABOUT PROSE.
# It is deliberate and it is narrow. Everything else in this file recomputes a value and
# compares it, because a check on a sentence passes while the sentence is wrong -- this
# file's own history. But whether notes/process/PERSONAS.md records a review for this page
# is not a figure at all; it is a process artefact, and the only mechanical way to notice
# that a page was substantially rewritten without being re-read as its six readers.
head('The persona review — notes/process/PERSONAS.md')
_personas = open(os.path.join(ROOT, 'notes/process/PERSONAS.md'), encoding='utf-8').read()
_ok = '`/what-sports-cost`' in _personas
if not _ok:
    FAILS.append('notes/process/PERSONAS.md records no review for /what-sports-cost. '
                 'Rule 15a: a verifier checks the figures and cannot check that anybody’s '
                 'question was answered.')
print(f"  {'OK  ' if _ok else 'FAIL'}  a review is recorded for /what-sports-cost")

print()
if FAILS:
    print(f'FAILED — {len(FAILS)} figure(s) in the analysis do not match the data:')
    for f in FAILS:
        print(f'  {f}')
    sys.exit(1)
print('PASSED — every figure in the analysis matches what the data produces.')
