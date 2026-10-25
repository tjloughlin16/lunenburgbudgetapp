#!/usr/bin/env python3
"""The SERF report: the Special Education Reserve Fund, as a hub and six topic pages.

    python3 scripts/build_serf_topics.py           # write fy28/public/data/topics/*.json
    python3 scripts/build_serf_topics.py --check   # fail if any output would change

WHY THIS EXISTS. TJ, 24 October 2026, three questions for the reserve the Select Board sets a
policy for on 27 October and Special Town Meeting funds on 17 November: how big the reserve
should be, what state and federal money to expect, and what level of budget to carry. And the
correction that shapes every page: *"the school committee just talks about the big additions
in the year as if they are always a problem. 'we brought in a kid and it cost us $100k'.
Thats a problem because we already budgeted for that, so it comes out of the budget, so its
hard to see what is 'unaccounted for' in the year."*

So the pages measure the RESIDUAL -- spending beyond the vote -- never the price of an
arrival. Three residuals, nested, because which one a reserve meets is a policy choice the
record has not yet made:

    line by line     each line's overrun, an underspend on another line not set against it
                     (special-education-costs.json's `surprise`, the series the overrun page uses)
    three together   in district + tuition + transportation, net
    whole school     the school general fund against its ORIGINAL vote

IT COMPUTES NOTHING IT CAN READ INSTEAD, and re-derives what it reads where a raw file exists:

  fy28/public/data/special-education-costs.json   build_sped_costs.py: voted vs spent per
                     line, FY2010-FY2026; the circuit breaker account; the placement snapshots.
                     Each year's need is recomputed here from its own ledger rows.
  fy28/public/data/topics/school-budget-against-actual.json
                     build_school_spending_topics.py: the whole school general fund, original
                     vote and spent, every year. Parsed from its table, and its own claims
                     (under its revised budget every year) re-asserted.
  sources/data/dese-circuit-breaker.csv           DESE's payments, read directly.
  sources/data/dese-entitlement-allocations.csv   DESE's IDEA allocations, read directly.
  sources/data/munis-school-journal.csv           every tuition payment, FY2023-FY2026.
  sources/correspondence/text/...pptx.txt         the Superintendent's deck, 22 October 2026:
                     STATED figures (rule 13a); each is asserted present in the deck text, and
                     the threshold asserted equal to DESE's own.

RULE 1. Budget against actual is the QUANTITY here, as on the overrun page: the reserve exists
to pay spending beyond a vote. Nothing projects a budget from an actual.

RULE 7. The pages state what the ledger shows. Why a line ran over (a new child, a price rise,
a longer route) is not in the ledger, and every page says so where it matters.
"""
import argparse
import collections
import csv
import json
import os
import re
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import conclusions as C  # noqa: E402
from conclusions import figure  # noqa: E402
import ladder as LD  # noqa: E402
import topic as TP  # noqa: E402
import topics as REG  # noqa: E402
import topic_blocks as TB  # noqa: E402
from brief import step  # noqa: E402

PUB = os.path.join(ROOT, 'fy28', 'public', 'data')
OUT_DIR = os.path.join(PUB, 'topics')
DATA = os.path.join(ROOT, 'sources', 'data')
MANIFEST = os.path.join(DATA, 'archive-manifest.csv')
HUB = 'special-education-reserve'
MINE = [t for t, (_, home, gen) in REG.TOPICS.items() if home == HUB]
LINES = ('ood', 'trans', 'indist')
LINE_NAME = {'ood': 'Out-of-district tuition', 'trans': 'Special education transportation',
             'indist': 'In-district special education'}
DECK = 'correspondence/2026-10-22-special-education-funding-superintendent-finance-committee.pptx'
DECK_TEXT = 'sources/correspondence/text/' + os.path.basename(DECK) + '.txt'
TOWN_REPORT = 'town-annual-reports/text/4130-fy-2025-annual-town-report.txt'
TUITION_OBJECTS = ('535019', '535022', '535023')     # journal.py's 'tuition' component
REG_KEY = 'state-dese/603cmr28-special-education-regulations.html'
REG_TEXT = 'sources/state-dese/text/603cmr28-special-education-regulations.txt'
LAW_KEY = 'state-law/2026-10-24/section5.html'
LAW_TEXT = 'sources/state-law/text/c71b-5.txt'
SERF_KEY = 'state-law/2026-10-24/section13e.html'
SERF_TEXT = 'sources/state-law/text/c40-13e.txt'
LAW_Q = ('moves to a different school district on or after July 1 of any fiscal year, such school '
         'committee of the former community of residence shall pay the approved budgeted costs')
LAW_APRIL_Q = ('if such move occurs between April 1 and June 30, such school committee of the former '
               'community of residence shall pay such costs for the balance of the fiscal year in '
               'which the move occurred as well as for the subsequent fiscal year')
LAW_INCR_Q = ('the school committee of such new community of residence shall be financially '
              'responsive for any increase')
# Machine captions carry no speaker, and our notes of the 7 October 2026 recording do not name
# one either; a guessed name would be a derived thing quoted as observed (rule 13).
CAPTION_WHO = 'Speaker not identified in the captions'
MONTHS = ('Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun')


def fail(msg):
    raise SystemExit('build_serf_topics: ' + msg)


def load(name):
    return json.load(open(os.path.join(PUB, name), encoding='utf-8'))


def norm(s):
    s = s.replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"')
    return ' '.join(s.split())


def text_of(rel):
    return open(os.path.join(ROOT, rel), encoding='utf-8', errors='ignore').read()


def minute(board_slug, board, fname, quote, who):
    """A quotation from the town's minutes, checked verbatim against our extracted copy. `who`
    is the speaker as the minutes name them, with their role -- TJ, 24 October 2026: a quote
    with no person and no year could be from 2009 or 2026."""
    rel = 'sources/meetings/text/%s/%s' % (board_slug, fname)
    if norm(quote) not in norm(text_of(rel)):
        fail('%r is not verbatim in %s' % (quote[:60], rel))
    date = fname[:10]
    return dict(quote=quote, board=board, date=date, who=who,
                href='/docs/meetings/text/%s/%s' % (board_slug, fname),
                label='%s minutes, %s' % (board, date))


def video(board_slug, board, fname, at, quote, who=None):
    """A quotation from the machine captions of a meeting recording, at its timestamp, checked
    verbatim against our copy of the captions every build. Captions name nobody, so `who` stays
    CAPTION_WHO unless the captions themselves say who is speaking (rule 13: never a guess)."""
    rel = 'sources/data/youtube-transcripts/%s/%s' % (board_slug, fname)
    t = json.load(open(os.path.join(ROOT, rel), encoding='utf-8'))
    if norm(quote) not in norm(' '.join(x['text'] for x in t['segments'])):
        fail('%r is not verbatim in %s' % (quote[:60], rel))
    h, m, sec = (int(x) for x in at.split(':'))
    secs = h * 3600 + m * 60 + sec
    if not any(abs(x['start'] - secs) < 60 and norm(quote).split()[0] in norm(x['text'])
               for x in t['segments']):
        fail('%r does not begin near %s in %s' % (quote[:40], at, rel))
    return dict(quote=quote, board=board, date=t['meeting_date'], who=who or CAPTION_WHO,
                href='%s&t=%ds' % (t['video_url'], secs), caption=True,
                label='%s, %s, video at %s (machine captions)' % (board, t['meeting_date'], at))


def money(s):
    t = s.replace('−', '-').strip()
    if not re.fullmatch(r'-?\$[\d,]+', t):
        fail('%r is not a whole-dollar figure' % s)
    return int(t.replace('$', '').replace(',', ''))


def sources():
    man = {r['key'] for r in csv.DictReader(open(MANIFEST, encoding='utf-8'))}
    out = []
    for key, pub, what in (
            ('town-ledgers/expenses/glytdbud-expense-fy2026-p13-gf-school.xlsx',
             'Town of Lunenburg — Town Accountant (MUNIS)', 'school general fund, FY2026 at the close'),
            ('budget-workbooks/finance-committee/fy26-budget/general-fund-budget-vs-actuals-history.xlsx',
             'Lunenburg Finance Committee', 'voted against spent, FY2010 to FY2022'),
            ('state-dese/dese-circuit-breaker.xlsx', 'Massachusetts DESE', 'circuit breaker payments'),
            (DECK, 'Lunenburg Public Schools',
             'special education funding, to the Finance Committee, 22 October 2026'),
            (TOWN_REPORT.replace('/text/', '/docs/').replace('.txt', '.pdf'),
             'Town of Lunenburg', 'FY2025 annual town report: the May 2025 Town Meeting votes'),
            ('state-dese/radar-sped-direct-expenditure-trends-fy2008-fy2025.xlsx', 'Massachusetts DESE',
             'special education direct expenditure trends, FY2008 to FY2025')):
        if key not in man:
            fail('%s is not in archive-manifest.csv' % key)
        out.append(dict(label='%s — %s (%s)' % (pub, os.path.basename(key), what), href='/docs/' + key))
    for key, what in ((SERF_KEY, 'G.L. c.40 §13E, the special education reserve fund'),):
        if key not in man:
            fail('%s is not in archive-manifest.csv' % key)
        out.append(dict(label='General Court of Massachusetts — %s' % what, href='/docs/' + key))
    for f, what in (('munis-school-journal.csv', 'every school journal line, FY2023–FY2026'),
                    ('dese-entitlement-allocations.csv', 'DESE entitlement grant allocations'),
                    ('placement-counts.csv', 'the town’s 1 March placement counts')):
        if not os.path.exists(os.path.join(ROOT, 'fy28', 'public', 'docs', 'data', f)):
            fail('/docs/data/%s is not published' % f)
        out.append(dict(label='Lunenburg Budget Project — %s (%s)' % (f, what), href='/docs/data/' + f))
    return out


# --------------------------------------------------------------------- the readings

def read_lines(SC):
    """{fy: {line: (voted, spent)}} and the need series, each year recomputed from the ledger."""
    led = {r['fy']: r for r in SC['ledger']}
    sur = {r['fy']: r for r in SC['surprise']}
    ys = list(range(SC['first_fy'], SC['last_fy'] + 1))
    if sorted(led) != ys or sorted(sur) != ys:
        fail('special-education-costs.json: the ledger or the need series misses a year')
    over = {}
    for y in ys:
        over[y] = {g: led[y][g]['spent'] - led[y][g]['original'] for g in LINES}
        if any(over[y][g] != sur[y][g] for g in LINES):
            fail('FY%d: a line\'s overrun no longer recomputes from the ledger' % y)
        if sum(max(0, v) for v in over[y].values()) != sur[y]['need']:
            fail('FY%d: the need is no longer the sum of the lines that ran over' % y)
    return ys, over


def read_school(ys):
    """The whole school general fund: {fy: (original vote, spent)}, from the published table."""
    P = load(os.path.join('topics', 'school-budget-against-actual.json'))
    want = ['Original budget', 'Revised budget', 'Spent or committed', 'Of revised']
    out = {}
    for v in P['table']['views']:
        if v['columns'] != want:
            fail('school-budget-against-actual: its columns moved: %s' % v['columns'])
        for r in v['rows']:
            y = int(r['label'][2:])
            o, rv, s = (money(c) for c in r['cells'][:3])
            if s > rv:
                fail('FY%d: the school spent more than its revised budget; that page says it '
                     'never did' % y)
            out[y] = (o, s)
    if sorted(out) != ys:
        fail('the whole-school years %s are not the special education years' % sorted(out))
    return out


def read_cb(ys):
    """DESE's circuit breaker payments to Lunenburg by year PAID, quarterly plus extra."""
    num = lambda x: float(x) if x not in (None, '') else 0.0
    out = {}
    for r in csv.DictReader(open(os.path.join(DATA, 'dese-circuit-breaker.csv'), encoding='utf-8')):
        if r['lea'] == '01620000':
            out[int(r['fy'])] = dict(
                paid=num(r['total_quarterly_payment']) + num(r['extra_relief_payment'])
                + num(r['additional_supplemental_payment']),
                quarterly=num(r['total_quarterly_payment']),
                eligible=num(r['total_eligible_expenses']), net=num(r['total_net_claim']),
                children=int(num(r['eligible_students_claimed'])),
                threshold=num(r['threshold_amount']))
    if not set(ys) <= set(out):
        fail('dese-circuit-breaker.csv does not hold every year FY%d to FY%d' % (ys[0], ys[-1]))
    return out


def read_idea():
    """DESE's IDEA allocations: 0240 school age plus 0262 preschool, every year the form lists."""
    al = collections.defaultdict(dict)
    for r in csv.DictReader(open(os.path.join(DATA, 'dese-entitlement-allocations.csv'),
                                 encoding='utf-8')):
        if r['district_code'] == '0162':
            al[int(r['fy'])][r['fund_code']] = float(r['amount'])
    ys = sorted(y for y in al if '0240' in al[y])
    if ys != list(range(ys[0], ys[-1] + 1)):
        fail('the IDEA allocations skip a year')
    return {y: al[y]['0240'] + al[y].get('0262', 0.0) for y in ys}


def read_tuition_payments():
    """{fy: [paid in each month, July first]} -- every fund, every tuition payment the journal
    posts as actual (accounts payable). A month is a MUNIS period: 1 is July."""
    out = collections.defaultdict(lambda: [0.0] * 12)
    for r in csv.DictReader(open(os.path.join(DATA, 'munis-school-journal.csv'), encoding='utf-8')):
        if r['object'] in TUITION_OBJECTS and r['source'] == 'API' and r['posts_to'] == 'actual':
            p = int(r['period'])
            if not 1 <= p <= 12:
                fail('a tuition payment posts to period %d' % p)
            out[int(r['fiscal_year'])][p - 1] += float(r['amount'])
    if not out:
        fail('the journal holds no tuition payments')
    return dict(out)


def read_accounts(SC, ys):
    """{fy: {account: (function, group, original, spent)}} for the three groups, read with
    build_sped_costs' own classifier and loaders' rules, and TIED to its ledger rows: each
    group's accounts must sum to the group, every year. Two uses: private against
    collaborative tuition (functions 9300, 9400), and the account-by-account draw rule.
    TJ, 24 October 2026: "is that an actual single line item, or a collection/sum of a bunch?"
    -- a bunch: out-of-district tuition is three accounts, in district about fifty."""
    import build_sped_costs as SCB
    acc = collections.defaultdict(lambda: [None, None, 0.0, 0.0])
    munis_years = set()
    for r in csv.DictReader(open(SCB.MUNIS, encoding='utf-8')):
        if r['period'] != '13' or r['type'] != 'E':
            continue
        g = SCB.group_of(r['account'], r['description'])
        if g not in LINES:
            continue
        fy = int(r['fiscal_year'])
        munis_years.add(fy)
        a = acc[(fy, r['account'])]
        a[0], a[1] = SCB.segs(r['account'])[3], g
        a[2] += SCB.num(r['original_approp'])
        a[3] += SCB.num(r['ytd_expended']) + SCB.num(r['encumbrances'])
    for r in csv.DictReader(open(SCB.GL, encoding='utf-8')):
        if r['sheet'] != 'general_fund' or r['department_code'] != '300':
            continue
        fy = int(r['fiscal_year'])
        if fy in munis_years or r['actual_is_partial'] == 'true':
            continue
        g = SCB.group_of(r['account'], r['org_desc'])
        if g not in LINES:
            continue
        a = acc[(fy, r['account'])]
        a[0], a[1] = SCB.segs(r['account'])[3], g
        a[2] += SCB.num(r['original'])
        a[3] += SCB.num(r['actual'])
    led = {r['fy']: r for r in SC['ledger']}
    out = {y: {} for y in ys}
    for (fy, account), (fn, g, o, sp) in acc.items():
        if fy in out:
            out[fy][account] = (fn, g, o, sp)
    for y in ys:
        for g in LINES:
            o = sum(v[2] for v in out[y].values() if v[1] == g)
            sp = sum(v[3] for v in out[y].values() if v[1] == g)
            if abs(round(o) - led[y][g]['original']) > 2 or abs(round(sp) - led[y][g]['spent']) > 2:
                fail('FY%d %s: the accounts do not sum to the ledger row (%s / %s against %s / %s)'
                     % (y, g, round(o), round(sp), led[y][g]['original'], led[y][g]['spent']))
    return out


def read_late():
    """What the journal shows ORDERED after the school year was under way (after 30 September),
    FY2023-FY2026, every fund: {fy: {line: {added, spring, released}}}, plus the Van Pool spring
    orders, the last-day collaborative order, and the FY2025 moves into and out of the out-of-
    district tuition budget. Opening and raising an order count as added; closing or cutting
    one as released. A close and a re-issue to the same vendor on the same day net to nothing,
    so a re-booking is not counted as a new cost."""
    OBJ = {o: 'ood' for o in TUITION_OBJECTS}
    OBJ['535026'] = 'trans'
    ev = collections.defaultdict(float)
    van, coll, moves = {}, None, collections.defaultdict(lambda: {'day1': 0.0, 'atm': 0.0})
    for r in csv.DictReader(open(os.path.join(DATA, 'munis-school-journal.csv'), encoding='utf-8')):
        g = OBJ.get(r['object'])
        if not g:
            continue
        y, d, a = int(r['fiscal_year']), r['effective_date'], float(r['amount'])
        if r['source'] in ('POE', 'POM') and d > '%d-09-30' % (y - 1):
            ev[(y, g, d, r['vendor'])] += a
        if (g == 'ood' and r['source'] == 'POE' and d == '%d-06-30' % y
                and 'COLLABORATIVE TUITIONS' in r['description'] and (coll is None or a > coll[1])):
            coll = (y, a)
        if g == 'ood' and r['source'] == 'BUA' and r['fund'] == '0100':
            if d == '%d-07-01' % (y - 1):
                moves[y]['day1'] += a
            elif 'ATM' in r['description']:
                moves[y]['atm'] += a
    late = {}
    for (y, g, d, v), a in ev.items():
        e = late.setdefault(y, {}).setdefault(g, {'added': 0.0, 'spring': 0.0, 'released': 0.0})
        if a > 0.5:
            e['added'] += a
            if d[5:7] in ('03', '04', '05', '06'):
                e['spring'] += a
            if v == 'VAN POOL' and g == 'trans' and a > 10000:
                van[y] = van.get(y, 0.0) + a
        elif a < -0.5:
            e['released'] += a
    for y in late:
        for g in ('ood', 'trans'):
            late[y].setdefault(g, {'added': 0.0, 'spring': 0.0, 'released': 0.0})
    if sorted(late) != [2023, 2024, 2025, 2026] or coll is None:
        fail('the journal\'s late orders are not FY2023-FY2026, or the last-day order is gone')
    return late, sorted(van.items()), coll, dict(moves)


def meanings(conclusions, lines):
    """WHAT EACH CONCLUSION MEANS, attached in order (ladder.conclusion's `so`, built here so the
    sentences sit together where they can be read as one argument). TJ, 24 October 2026: "what
    does the fact mean or suggest? ... how does it impact decision making or citizens or boards".
    `lines`: one (text, figures) per conclusion, None to leave one bare. Same checks as so=."""
    if len(lines) != len(conclusions):
        fail('%d meanings for %d conclusions' % (len(lines), len(conclusions)))
    for c, ln in zip(conclusions, lines):
        if ln is None:
            continue
        ln = ln if isinstance(ln, tuple) else (ln,)
        text, figs, allow = ln[0], (ln[1] if len(ln) > 1 else None), (ln[2] if len(ln) > 2 else ())
        c['so'] = LD.conclusion(c['text'], c['rests_on'], {k: v for k, v in (c['figures'] or {}).items()},
                                c.get('literals', ()), so=text, so_figures=figs, so_allow=allow)['so']


def led_line(SC, fy, g):
    return next(r for r in SC['ledger'] if r['fy'] == fy)[g]


# --------------------------------------------------------------------- the pages

def build():
    SC = load('special-education-costs.json')
    ys, over = read_lines(SC)
    sch = read_school(ys)
    cb = read_cb(ys)
    idea = read_idea()
    pay = read_tuition_payments()
    late, van_pool, coll_june, moves = read_late()
    fewest_months = min(sum(1 for v in pay[y] if v > 0) for y in pay)
    deck = norm(text_of(DECK_TEXT))
    src = sources()
    U = lambda v: figure(v, C.usd(v))
    F = lambda v: figure(v, C.fy(v), 'fiscal year')
    P = lambda v, dp=1: figure(v, C.pct(v, dp))
    N = lambda v, unit=None: figure(v, C.num(v), unit)
    f, con = LD.fact, TP.conclusion
    fy0, fy1, nyrs = ys[0], ys[-1], len(ys)
    X = [C.fy(y) for y in ys]
    out = {}

    # The three residuals. `need` is the series every reserve statistic on the site uses.
    need = {y: sum(max(0, v) for v in over[y].values()) for y in ys}
    net = {y: sum(over[y].values()) for y in ys}
    whole = {y: sch[y][1] - sch[y][0] for y in ys}
    two = lambda m: max(((ys[i], m[ys[i]] + m[ys[i + 1]]) for i in range(nyrs - 1)),
                        key=lambda t: t[1])
    pos = lambda m: {y: max(0, m[y]) for y in ys}

    # ------------------------------------------------ surprise costs: which lines run over, and when
    by_line = {g: sum(max(0, over[y][g]) for y in ys) for g in LINES}
    total_over = sum(by_line.values())
    if total_over != sum(need.values()):
        fail('the lines\' overruns do not add to the need')
    share = {g: 100.0 * by_line[g] / total_over for g in LINES}
    yrs_over = {g: sum(1 for y in ys if over[y][g] > 0) for g in LINES}
    worst = {g: max(ys, key=lambda y: over[y][g]) for g in LINES}
    for g in LINES:
        pl = SC['per_line'][g]
        if (yrs_over[g], worst[g], over[worst[g]][g]) != (pl['years_over'], pl['worst_fy'], pl['worst']):
            fail('%s: years over or worst year disagree with special-education-costs.json' % g)
    # PRIVATE AGAINST COLLABORATIVE (TJ, 24 October 2026: "is there a meaning we need to
    # define/understand about the difference in private and collab tuition lines... and which
    # one is the one that gets 'surprise' costs added?"). Read account by account, tied above.
    acct = read_accounts(SC, ys)
    fn_over = lambda y, fn: round(sum(v[3] - v[2] for v in acct[y].values() if v[0] == fn))
    fn_bud = lambda y, fn: round(sum(v[2] for v in acct[y].values() if v[0] == fn))
    priv = {y: fn_over(y, '9300') for y in ys}
    coll = {y: fn_over(y, '9400') for y in ys}
    for y in ys:
        if abs(priv[y] + coll[y] + fn_over(y, '9100') - over[y]['ood']) > 3:
            fail('FY%d: private, collaborative and public tuition do not sum to the line' % y)
    priv_over = sum(max(0, v) for v in priv.values())
    coll_over = sum(max(0, v) for v in coll.values())
    priv_n = sum(1 for v in priv.values() if v > 0)
    coll_n = sum(1 for v in coll.values() if v > 0)
    priv_net = sum(priv.values())
    if not (coll_over > priv_over and priv_net < 0 and priv[fy1] < 0 < coll[fy1]):
        fail('the surprise page says collaborative tuition carries the overruns and private runs under')
    acct_need = {y: round(sum(max(0, v[3] - v[2]) for v in acct[y].values())) for y in ys}
    rank = sorted(LINES, key=lambda g: -by_line[g])
    if rank[0] != 'ood' or not share['ood'] < 50:
        fail('the surprise page says out-of-district tuition is the largest share and under half')
    # WHY IT SURPRISES, from the journal (FY2023-FY2026): what was ORDERED after the school
    # year was under way. TJ, 24 October 2026: "waht about them changes and comes in late, and
    # try to use the ldger/journal to prove it".
    JY = sorted(late)
    add = {g: sum(late[y][g]['added'] for y in JY) for g in ('ood', 'trans')}
    spr = {g: sum(late[y][g]['spring'] for y in JY) for g in ('ood', 'trans')}
    rel_ood = sum(late[y]['ood']['released'] for y in JY)
    spring_pct = 100.0 * (spr['ood'] + spr['trans']) / (add['ood'] + add['trans'])
    if not spring_pct > 80:
        fail('the surprise page says most late orders came in spring')
    vp = van_pool
    if [e[0] for e in vp] != [2023, 2024, 2026]:
        fail('the Van Pool spring orders are no longer FY2023, FY2024 and FY2026: %s' % vp)
    surprise_chart = TP.series(
        'Spent above budget, each year, by line', X,
        [TP.track(LINE_NAME[g], [max(0, over[y][g]) for y in ys]) for g in LINES],
        '$', kind='bar', stacked=True,
        note='Each bar: how far spending went above the budget voted for that line. A line that '
             'stayed within its budget adds nothing.')
    split_chart = TP.series(
        'Private and collaborative tuition against budget', X, [
            TP.track('Private schools', [priv[y] for y in ys]),
            TP.track('Collaboratives', [coll[y] for y in ys])],
        '$', kind='bar',
        note='Above zero is over budget. Private: an approved private school, its rate set by the '
             'state. Collaborative: a programme run jointly by school districts.')
    late_chart = TP.series(
        'Ordered after the school year began', [C.fy(y) for y in JY], [
            TP.track('Out-of-district tuition, ordered', [late[y]['ood']['added'] for y in JY]),
            TP.track('Transportation, ordered', [late[y]['trans']['added'] for y in JY]),
            TP.track('Out-of-district tuition, released', [late[y]['ood']['released'] for y in JY])],
        '$', kind='bar',
        note='Purchase orders opened or raised after 30 September, every fund; released is orders '
             'closed or cut. Orders, not children.', note_allow=('30',))
    deck_q = ('New student needs, tuition increases and transportation changes can create costs '
              'after the budget is adopted.')
    if norm(deck_q) not in deck:
        fail('the deck no longer says %r' % deck_q[:40])
    # THE ARRANGED PARTS (scripts/topic_blocks.py). TJ, 25 October 2026, on the page that
    # first drew these outside the framework: "the most interesting page we've built in a
    # while... merged into surprise costs without losing the excellence." The answer to "which
    # moves are a surprise" is a RULE, not a quantity, so it is drawn as a decision matrix,
    # each cell naming what it rests on: c.71B §5 and 603 CMR 28 are read and asserted below
    # (LAW_Q, REG_Q); where the statute is silent, the cell says "Our reading".
    LAW5, REG10, REG03 = ('law', 'Statute: c.71B §5'), ('law', 'Regulation: 603 CMR 28.10'), \
        ('law', 'Regulation: 603 CMR 28.03')
    OURS, VOTED = ('reading', 'Our reading'), ('budget', 'The budget as voted')
    sc_define = TB.explain('“Out of district” is about the school, not the move', [
        '**Out-of-district tuition** is what Lunenburg pays when a **Lunenburg child** goes to '
        'school outside its own schools: a **private school** or a **collaborative**. A family '
        'moving in or out only changes **which town pays**.'])
    # HOW MANY, AND WHAT ONE COSTS -- on the matrix's headings, each with how solid it is.
    # TJ, 25 October 2026: "how many kids per year land in each category... and the cost, and
    # how solid we know of the costs. that way, the school committee can fill in the gaps when
    # people ask about it", and: "if we dont have the info say something like 'Unknown Kids,
    # gap in data'". What IS published: children on education plans moving in and out (DESE's
    # special education movement file, FY2019 on; a year that repeats the one before is
    # dropped), and children placed out of district on 1 March by type (the town report's
    # Special Services section, placement-counts.csv). Those are the grid's EDGES. Its boxes --
    # how many of the movers were in which setting -- are published nowhere, so they are said
    # once, in the note, and not nine times (TJ: "wait NONE of them have data"). Nor is a box
    # filled by subtracting one edge from another: the two counts come from different
    # publishers on different days (rule 7).
    svc = [x for x in SC['movement']['services'] if not x['repeats_prior_year']]
    sv0, sv1 = svc[0]['fy'], svc[-1]['fy']
    rng = lambda xs: '%s to %s a year' % (C.num(min(xs)), C.num(max(xs)))
    mv_in = rng([x['moved_in'] for x in svc])
    mv_out = rng([x['moved_out'] for x in svc])
    on_iep = '%s to %s' % (C.num(min(x['on_iep'] for x in svc)), C.num(max(x['on_iep'] for x in svc)))
    pc = [r for r in csv.DictReader(open(os.path.join(DATA, 'placement-counts.csv'), encoding='utf-8'))
          if r['collaborative_basis'] == 'parallel category' and r['parts_tie'] == 'yes'
          and int(r['fy']) >= 2022]
    if [int(r['fy']) for r in pc] != list(range(2022, int(pc[-1]['fy']) + 1)):
        fail('placement counts by type no longer run unbroken from FY2022')
    pc0, pc1 = int(pc[0]['fy']), int(pc[-1]['fy'])
    n_coll = rng([int(r['collaborative']) for r in pc])
    n_priv_l = [int(r['day']) + int(r['residential']) for r in pc]
    n_priv = ('%s a year' % C.num(n_priv_l[0])) if len(set(n_priv_l)) == 1 else rng(n_priv_l)
    nets = [x['net'] for x in SC['movement']['snapshots']]
    sn0, sn1 = SC['movement']['snapshots'][0]['fy'], SC['movement']['snapshots'][-1]['fy']
    bt = SC['request']['by_type']
    broken = min(bt, key=lambda x: x['per_collaborative'])
    if broken['fy'] != 2025 or broken['per_collaborative'] > 20000:
        fail('the year whose collaborative count and dollars do not line up is no longer FY2025')
    pcol = [x['per_collaborative'] for x in bt if x is not broken]
    pcol_y = [x['fy'] for x in bt if x is not broken]
    np_med_v = SC['request']['nonpublic_median']
    np_y = [x['fy'] for x in bt]
    FYR = lambda a, b: ({'y': F(a), 'z': F(b)},)
    # SPECIAL EDUCATION IN LUNENBURG'S OWN SCHOOLS, PER CHILD SERVED THERE. TJ, 25 October 2026:
    # "i swear we MUST have this data somewhere.... per pupil special education cost?!" DESE
    # publishes the dollars (Special Education Direct Expenditure Trends: in-district teaching and
    # other instructional spending, which include Circuit Breaker spending) and, separately, the
    # children served in district (Program Characteristics). The division is OURS, so the figure
    # is an estimate: what the programme spends per child it serves, not what one more child adds.
    dx = {int(r['fy']): float(r['teaching'] or 0) + float(r['other_instructional'] or 0)
          for r in csv.DictReader(open(os.path.join(DATA, 'dese-sped-expenditure.csv'), encoding='utf-8'))
          if r['lea'] == '01620000' and r['reconciles'] == 'yes' and r['teaching']}
    dn = {int(r['fy']): int(r['measure_cnt'])
          for r in csv.DictReader(open(os.path.join(DATA, 'dese-sped-program.csv'), encoding='utf-8'))
          if r['lea'] == '01620000' and r['indicator_category'].startswith('In District')
          and r['indicator'] == 'In-District' and r['measure_cnt']}
    ind_y = sorted(set(dx) & set(dn))
    if len(ind_y) < 4:
        fail('DESE in-district special education spending and children served overlap in fewer than four years')
    ind_pc = [dx[y] / dn[y] for y in ind_y]
    ind_med = statistics.median(ind_pc)
    meas = TB.measure
    sc_row_m = [
        [meas(('Children on education plans moving in, %s to %s' % (C.fy(sv0), C.fy(sv1)),) + FYR(sv0, sv1),
              mv_in, 'published')],
        [meas(('Children on education plans, %s to %s' % (C.fy(sv0), C.fy(sv1)),) + FYR(sv0, sv1),
              on_iep, 'published'),
         meas(('Children placed, net change October to March, %s to %s' % (C.fy(sn0), C.fy(sn1)),)
              + FYR(sn0, sn1), '%s to %s' % (C.num(min(nets)), '+' + C.num(max(nets))), 'published')],
        [meas(('Children on education plans moving out, %s to %s' % (C.fy(sv0), C.fy(sv1)),) + FYR(sv0, sv1),
              mv_out, 'published')]]
    sc_col_m = [
        [meas(('Special education spending per child served here, median %s to %s'
               % (C.fy(ind_y[0]), C.fy(ind_y[-1])),) + FYR(ind_y[0], ind_y[-1]),
              'about %s' % C.usd(ind_med), 'estimate'),
         meas(('Over budget, %s to %s' % (C.fy(fy0), C.fy(fy1)),) + FYR(fy0, fy1),
              '%s in %s years' % (C.usd(by_line['indist']), C.num(yrs_over['indist'])), 'published')],
        [meas(('Children placed, 1 March, %s to %s' % (C.fy(pc0), C.fy(pc1)),) + FYR(pc0, pc1) + (('1',),),
              n_coll, 'published'),
         meas(('Cost of one child a year, %s to %s' % (C.fy(pcol_y[0]), C.fy(pcol_y[-1])),)
              + FYR(pcol_y[0], pcol_y[-1]),
              '%s to %s' % (C.usd(min(pcol)), C.usd(max(pcol))), 'estimate'),
         meas(('Over budget, %s to %s' % (C.fy(fy0), C.fy(fy1)),) + FYR(fy0, fy1),
              '%s in %s years' % (C.usd(coll_over), C.num(coll_n)), 'published')],
        [meas(('Children placed, 1 March, %s to %s' % (C.fy(pc0), C.fy(pc1)),) + FYR(pc0, pc1) + (('1',),),
              n_priv, 'published'),
         meas(('Cost of one child a year, median %s to %s' % (C.fy(np_y[0]), C.fy(np_y[-1])),)
              + FYR(np_y[0], np_y[-1]), 'about %s' % C.usd(np_med_v), 'estimate'),
         meas(('Over budget, %s to %s' % (C.fy(fy0), C.fy(fy1)),) + FYR(fy0, fy1),
              '%s in %s years; %s under on balance' % (C.usd(priv_over), C.num(priv_n), C.usd(-priv_net)),
              'published')]]
    sc_gaps = [
        'How many children a year arrive already in a collaborative, or in a private school, and '
        'how many of those come from another state?',
        'How many Lunenburg children are placed out of district for the first time during a '
        'school year, and in which kind of setting?',
        'How many children leave Lunenburg while placed, and in which kind of setting?',
        'What does one child’s placement cost a year, by kind of setting, with transport?',
        'What does an arrival who needs new staff in Lunenburg’s own schools cost?']
    # WHICH BOX IS COSTLIEST, decided here from the figures on the headings, never typed:
    # per child, the setting with the higher estimate; in total, the line that ran furthest over.
    per_child = {'coll': max(pcol), 'priv': np_med_v, 'indist': ind_med}
    dearest = max(per_child, key=per_child.get)
    overrun = {'coll': coll_over, 'priv': priv_over, 'indist': by_line['indist']}
    most_over = max(overrun, key=overrun.get)
    if (dearest, most_over) != ('priv', 'coll'):
        fail('the matrix chips say private is costliest per child and collaborative overran most')
    CHIP_DEAR = ('Costliest per child', 'estimate')
    CHIP_OVER = ('Most overspending', 'published')
    sc_matrix = TB.matrix(
        'Which moves cause a surprise cost',
        ['Moves into Lunenburg', 'Already lives in Lunenburg', 'Moves out of Lunenburg'],
        ['Lunenburg’s own schools', 'A collaborative', 'A private school'],
        {(0, 0): TB.cell('S', 'Moves in, goes to Lunenburg’s schools',
                         'Lunenburg serves the child’s plan from the first day, so an aide or '
                         'therapist the budget did not carry is new cost.', REG03,
                         'In-district special education'),
         (0, 1): TB.cell('S', 'Moves in already in a collaborative',
                         'Lunenburg pays from the day the family arrives. The old-town rule '
                         'covers only private placements. Arriving in spring, after next year’s '
                         'budget is set, it misses that budget too.', OURS,
                         'Collaborative tuition and transport', chips=[CHIP_OVER]),
         (0, 2): TB.cell('N', 'Moves in already in a private school',
                         'The old town pays the rest of the year, and the next year too if the '
                         'move is April to June. **From another state: a surprise** (our reading).',
                         LAW5, 'Private tuition and transport, from next year'),
         (1, 0): TB.cell('N', 'Stays in Lunenburg’s schools',
                         'Already in the budget. A surprise only if the plan changes mid-year and '
                         'needs new staff.', VOTED, 'In-district special education'),
         (1, 1): TB.cell('S', 'Sent to a collaborative mid-year',
                         'The budget was built on the children already placed. Lunenburg pays '
                         'from the day the placement starts.', REG10,
                         'Collaborative tuition and transport', chips=[CHIP_OVER]),
         (1, 2): TB.cell('S', 'Sent to a private school mid-year',
                         'The same as a collaborative: Lunenburg pays from the start date, and '
                         'the budget did not carry it.', REG10, 'Private tuition and transport',
                         chips=[CHIP_DEAR]),
         (2, 0): TB.cell('N', 'Was in Lunenburg’s schools',
                         'The new town takes over. Nothing new to pay.', REG10,
                         'In-district special education'),
         (2, 1): TB.cell('U', 'Was in a collaborative',
                         'The new town pays from arrival, so part of Lunenburg’s budget goes '
                         'unspent.', OURS, 'Collaborative tuition, left unspent'),
         (2, 2): TB.cell('N', 'Was in a private school',
                         'Lunenburg keeps paying to June, and the next year too if the move is '
                         'April to June. It was already budgeted.', LAW5,
                         'Private tuition and transport')},
        [('S', 'Surprise', 'bad'), ('N', 'Not a surprise', 'neutral'),
         ('U', 'Underspend', 'good')],
        row_label='where the family is moving', col_label='where the child goes to school',
        row_measures=sc_row_m, col_measures=sc_col_m, gaps=sc_gaps,
        note=('**How many children fall in each box is not published.** The counts on the '
              'edges are: children moving in and out, and children placed in each setting. '
              'Nothing says how many of the movers were in which setting. '
              'Our reading, marked amber: c.71B §5 names only approved private day and '
              'residential placements, so a collaborative falls under the rule that the town '
              'where the child lives pays. Written guidance from the state education department '
              'would settle it.', None, ('71', '5')))
    # THE HIGHEST IMPACT, said once and findable. TJ, 25 October 2026: "did you write anywhere
    # what the highest impact is and why? i want to look for that". Impact here is MEASURED as
    # the overrun summed over the years a line ran over -- not cost times cases, which needs
    # the unpublished boxes. The two things beside it are a measurement (slack) and our reading
    # (no old-town year); that either CAUSED the overrun is untested, and the text says so.
    coll_net = sum(coll.values())
    if not (coll_over > priv_over > by_line['indist'] and coll_net > 0 > priv_net):
        fail('the callout says collaboratives ran furthest over, with no slack, and private under on balance')
    def impact(place, where_counts):
      return TB.explain('The biggest impact: collaborative placements', [
        ('**Measured:** of the three settings, collaborative tuition ran furthest over budget: '
         '%s across %s of %s years. Private schools ran %s over in their bad years; Lunenburg’s '
         'own schools, %s.' % (C.usd(coll_over), C.num(coll_n), C.num(nyrs), C.usd(priv_over),
                                C.usd(by_line['indist'])),
         {'a': U(coll_over), 'n': N(coll_n), 't': N(nyrs), 'b': U(priv_over), 'c': U(by_line['indist'])}),
        ('**Two things sit beside it.** The collaborative line has had almost no slack: %s over on '
         'balance across those years, where private ran %s under. And a child arriving already in '
         'a collaborative is Lunenburg’s from the first day, with no year paid by the old town '
         '(our reading of c.71B §5).' % (C.usd(coll_net), C.usd(-priv_net)),
         {'a': U(coll_net), 'b': U(-priv_net)}, ('71', '5')),
        '**Not shown:** whether either of those caused the overruns, or how many children did. '
        'That needs counts the district does not publish: %s.' % where_counts],
        tone='callout', place=place)
    # The same block on three pages (TJ: "that should go on the main SERF page, as well as other
    # pages too. thats a huge conclusion"): built once, so the three cannot drift apart.
    sc_impact = impact('top', 'the grid below names them')
    hub_impact = impact('lead', 'the Surprise costs page names them')
    mv_impact = impact('lead', 'the Surprise costs page names them')
    sc_panels = TB.panels('Inside out-of-district tuition: private and collaborative', [
        TB.panel('Private schools', [
            ('Years over budget', '%s of %s' % (C.num(priv_n), C.num(nyrs)), None),
            ('Added up over those years', C.usd(priv_over), None),
            (('On balance, %s to %s' % (C.fy(fy0), C.fy(fy1)), {'y': F(fy0), 'z': F(fy1)}),
             '%s under' % C.usd(-priv_net), 'good')],
            sub='An approved private day or residential school. The state sets its rate.'),
        TB.panel('Collaboratives', [
            ('Years over budget', '%s of %s' % (C.num(coll_n), C.num(nyrs)), None),
            ('Added up over those years', C.usd(coll_over), None),
            (('On balance, %s to %s' % (C.fy(fy0), C.fy(fy1)), {'y': F(fy0), 'z': F(fy1)}),
             '%s %s' % (C.usd(abs(sum(coll.values()))), 'over' if sum(coll.values()) > 0 else 'under'),
             'bad' if sum(coll.values()) > 0 else 'good')],
            sub='A programme run jointly by several school districts.')],
        place='also1',
        so=('Private has usually had room to spare, so an unplanned private placement mostly fits. '
            'Collaborative has had almost none, so one shows as overspending. The two share one '
            'total, so private room has often covered collaborative overruns.'))
    sc_checks = TB.checks('What causes a surprise cost', [
        'Private', 'Collab\u00adorative', 'Transport', 'In-district'], [
        TB.check_row('A Lunenburg child is placed out of district during the year',
                     'The budget was built on the children already placed. Lunenburg pays from '
                     'the day the placement starts, and a van usually comes with it.', {0, 1, 2}),
        TB.check_row('A child arrives already in a collaborative',
                     'The old-town rule covers only private placements, so Lunenburg pays from '
                     'arrival. Our reading.', {1, 2}),
        TB.check_row('A child arrives from another state',
                     'The old-town rule binds Massachusetts towns, so Lunenburg pays from '
                     'arrival, even for a private school. Our reading.', {0, 1, 2}),
        TB.check_row('A placement changes to a costlier one',
                     'A review changes the plan mid-year. For a child who arrived in a private '
                     'placement, the old town pays the old cost and Lunenburg “any increase”.',
                     {0, 1, 2}),
        TB.check_row('A tuition rate rises after the budget is set',
                     'The rate is set by the state or by the collaborative’s board, not by '
                     'Lunenburg.', {0, 1}),
        TB.check_row('A transport contract is topped up late in the year',
                     ('Routes are added or repriced after the budget: the van contract was '
                      'raised %s in %s.' % (C.usd(vp[1][1]), C.fy(vp[1][0])),
                      {'a': U(vp[1][1]), 'y': F(vp[1][0])}), {2}),
        TB.check_row('Staff or services are added in Lunenburg’s own schools',
                     'A child’s plan needs an aide or a therapist the budget did not carry. '
                     'This line is mostly staff pay.', {3}),
        TB.check_row('A bill only becomes known at year end',
                     'Invoices settle after the year’s spending is planned.', {0, 1, 2, 3}),
        TB.check_row('Not a surprise: a child arrives in a private school from a Massachusetts town',
                     'The old town pays the rest of the year, and the next year too if the move '
                     'is April to June. Lunenburg has time to budget it.', {0, 2},
                     contrast=True)],
        place='also2',
        note=('**What the books cannot tell us:** the ledger records invoices, not children. It '
              'shows which line ran over, not which of these causes was behind it in a year.'))
    MO = ['Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
    def strip(fill_from, code, before=None, nxt=None, after=None):
        st = [before if (before and i < fill_from) else (code if i >= fill_from else None)
              for i in range(12)]
        return st + [nxt, after]
    oc, ma = MO.index('Oct'), MO.index('May')
    sc_timeline = TB.timeline(
        'When a family moves: which town pays, month by month',
        MO + ['Next yr', 'Yr after'],
        [('A family moves into Lunenburg, with a child already placed out of district', [
            TB.track('In a private school, arrives in October', strip(oc, 'O', nxt='B', after='B'),
                     'The old town pays to June. Lunenburg budgets it from next year.', oc,
                     tags=['Private tuition', 'Transport'], verdict='N', basis=LAW5),
            TB.track('In a private school, arrives in May', strip(ma, 'O', nxt='O', after='B'),
                     'The old town pays to June and all of next year.', ma,
                     tags=['Private tuition', 'Transport'], verdict='N', basis=LAW5),
            TB.track('In a collaborative, arrives in October', strip(oc, 'S', nxt='B', after='B'),
                     'Lunenburg pays from the day the family arrives.', oc,
                     tags=['Collaborative tuition', 'Transport'], verdict='S', basis=OURS),
            TB.track('In a collaborative, arrives in May', strip(ma, 'S', nxt='S', after='B'),
                     'Arrives after next year’s budget is set, so it misses two budgets.', ma,
                     tags=['Collaborative tuition', 'Transport'], verdict='S', basis=OURS)]),
         ('A child who already lives in Lunenburg', [
            TB.track('Placed out of district for the first time, in January',
                     strip(MO.index('Jan'), 'S', nxt='B', after='B'),
                     'Lunenburg pays from the day the placement starts.', MO.index('Jan'),
                     tags=['Private or collaborative tuition', 'Transport'], verdict='S',
                     basis=REG10)]),
         ('A family moves out of Lunenburg, with a child placed out of district', [
            TB.track('In a private school, leaves in October', strip(0, 'B', nxt=None, after=None),
                     'Lunenburg keeps paying to June. It was budgeted, so nothing is saved.', oc,
                     cut=True, tags=['Private tuition', 'Transport'], verdict='N', basis=LAW5),
            TB.track('In a private school, leaves in May', strip(0, 'B', nxt='B', after=None),
                     'Lunenburg pays all of next year too, for a child who has left.', ma,
                     cut=True, tags=['Private tuition', 'Transport'], verdict='N', basis=LAW5),
            TB.track('In a collaborative, leaves in October', strip(oc, 'U', before='B'),
                     'The new town pays from arrival, so the rest of the budget goes unspent.',
                     oc, cut=True, tags=['Collaborative tuition'], verdict='U', basis=OURS)])],
        [('S', 'Surprise: Lunenburg pays, nothing budgeted', 'bad'),
         ('B', 'Budgeted: Lunenburg pays, known in time', 'neutral'),
         ('O', 'Another town pays', 'other'),
         ('U', 'Budgeted, not spent', 'good', 'outline')],
        verdicts=[('S', 'Surprise', 'bad'), ('N', 'Not a surprise', 'neutral'),
                  ('U', 'Underspend', 'good')],
        marker=(MO.index('Mar'), 'next year’s budget set, in spring (our assumption)'),
        event_label='the move', place='body',
        note='Each strip runs July to June, then the next two years. One placement, not any '
             'child’s bill.')
    out['surprise-costs'] = TP.page(
        'surprise-costs',
        'A surprise cost is spending above the budget as voted: %s over %s years.'
        % (C.usd(total_over), C.num(nyrs)),
        [f('s-ood', P(share['ood']), 'of overspending: out-of-district tuition', 'published'),
         f('s-trans', P(share['trans']), 'of overspending: transportation', 'published'),
         f('s-ind', P(share['indist']), 'of overspending: in-district services', 'published'),
         f('s-ood-n', N(yrs_over['ood'], 'years'), 'of %s out-of-district tuition ran over' % C.num(nyrs),
           'published', {'n': N(nyrs)}),
         f('s-trans-n', N(yrs_over['trans'], 'years'), 'of %s when transportation ran over'
           % C.num(nyrs), 'published', {'n': N(nyrs)}),
         f('s-coll', U(coll_over), 'collaborative tuition above budget, %s years' % C.num(coll_n),
           'published', {'n': N(coll_n)}),
         f('s-priv', U(priv_over), 'private tuition above budget, %s years' % C.num(priv_n),
           'published', {'n': N(priv_n)}),
         f('s-privnet', U(-priv_net), 'private tuition under budget, net, %s to %s'
           % (C.fy(fy0), C.fy(fy1)), 'published', {'y': F(fy0), 'z': F(fy1)}),
         f('s-late-o', U(add['ood']), 'out-of-district tuition ordered after September',
           'published'),
         f('s-late-t', U(add['trans']), 'transportation ordered after September', 'published'),
         f('s-spring', P(spring_pct, 0), 'of those late orders placed March to June', 'published'),
         f('s-why', None, 'why each order changed', 'gap',
           closes='the district’s year-end explanation of each line’s variance')],
        [con('Out-of-district tuition was %s of all overspending above budget; transportation, %s.'
             % (C.pct(share['ood']), C.pct(share['trans'])),
             ['s-ood', 's-trans', 's-ind', 's-ood-n', 's-trans-n'],
             {'a': P(share['ood']), 'b': P(share['trans'])}),
         con('Line by line, collaborative tuition ran %s over budget; private, %s, yet far under on balance.'
             % (C.usd(coll_over), C.usd(priv_over)), ['s-coll', 's-priv', 's-privnet'],
             {'a': U(coll_over), 'b': U(priv_over)},
             notes=[step('In %s private tuition came in %s under and collaborative %s over; '
                         'together they showed %s.' % (C.fy(fy1), C.usd(-priv[fy1]), C.usd(coll[fy1]),
                                                       C.usd(over[fy1]['ood'])), 'measured',
                         {'y': F(fy1), 'a': U(-priv[fy1]), 'b': U(coll[fy1]), 'c': U(over[fy1]['ood'])}),
                    step('Why private runs under is untested; one possibility is that the circuit '
                         'breaker account pays part of it.', 'hypothesis')]),
         con('Many arrive after the budget is set: %s of orders placed after September came March to June.'
             % C.pct(spring_pct, 0), ['s-late-o', 's-late-t', 's-spring'],
             {'a': P(spring_pct, 0)},
             notes=[step('Transportation: the van contract was raised %s in %s and %s in %s, and a '
                         'new %s order opened in %s.'
                         % (C.usd(vp[0][1]), C.fy(vp[0][0]), C.usd(vp[1][1]), C.fy(vp[1][0]),
                            C.usd(vp[2][1]), C.fy(vp[2][0])), 'measured',
                         {'a': U(vp[0][1]), 'y': F(vp[0][0]), 'b': U(vp[1][1]), 'z': F(vp[1][0]),
                          'c': U(vp[2][1]), 'w': F(vp[2][0])}),
                    step('Out-of-district tuition: %s of collaborative tuition was ordered on the '
                         'last day of %s.' % (C.usd(coll_june[1]), C.fy(coll_june[0])), 'measured',
                         {'a': U(coll_june[1]), 'y': F(coll_june[0])})])],
        chart=surprise_chart, also=[split_chart, late_chart],
        blocks=[sc_impact, sc_define, sc_matrix, sc_panels, sc_checks],
        finding_figures={'a': U(total_over), 'n': N(nyrs)},
        lead_quote=TP.lead_quote(deck_q, 'Dr. Jodi Fortuna, Superintendent of Schools',
                                 'Finance Committee', '2026-10-22', '/docs/' + DECK,
                                 'special education funding deck to the Finance Committee, slide 9, '
                                 '22 October 2026', DECK_TEXT),
        said=[minute('select-board', 'Select Board', '2025-10-07-minutes-7441.txt',
                     'The Select Board supported the article as a prudent tool to address '
                     'mid-year unanticipated placements without requiring a return to Town Meeting.',
                     'The Select Board, as minuted'),
              minute('school-committee', 'School Committee', '2024-02-28-minutes-6439.txt',
                     'Ms. Brzozoski regarding the 14% increase in tuition, when did we find out '
                     'about this?', 'Laura Brzozoski, School Committee member')],
        sources=src)

    # ------------------------------------------------ move-ins: who pays, from when
    tm = norm(text_of('sources/' + TOWN_REPORT))
    TM_Q = 'School Department (Unanticipated SPED Move-Ins) $50,000'
    m = re.search(re.escape(TM_Q) + r'.{0,200}?VOTED \(yes (\d+), no (\d+), abstain (\d+)\) to '
                  r'transfer from Free Cash the sum of \$50,000\.00 to Line 79', tm)
    if not m or 'Annual Town Meeting - May 3, 2025' not in tm[:tm.find(TM_Q)]:
        fail('the May 2025 Town Meeting vote for move-ins is no longer read from the FY2025 report')
    moved, tm_fy = 50000, 2025
    if moves[tm_fy]['atm'] != moved:
        fail('the journal does not post the Town Meeting\'s %s to out-of-district tuition' % moved)
    out_day1 = -moves[tm_fy]['day1']
    held = led_line(SC, tm_fy, 'ood')['original'] - out_day1 + moved
    spent25 = led_line(SC, tm_fy, 'ood')['spent']
    # THE LAW, read whole (CLAUDE.md 13c: look at the document, not a pattern). The regulation
    # says the new district SERVES a child without delay; the statute says who PAYS. TJ, 24
    # October 2026: "can you confirm this is actually true: April 1st is the deadline..."
    reg = norm(text_of(REG_TEXT))
    body = reg[reg.find('28.01: Authority, Scope and Purpose (1)'):]
    REG_Q = ('the last Individualized Education Program IEP written by the former school district '
             'and accepted by the parent shall be provided in a comparable setting without delay')
    if REG_Q not in body or 'April' in body:
        fail('603 CMR 28 no longer reads as the move-ins page says (served without delay; no '
             'April date)')
    law = norm(text_of(LAW_TEXT))
    for q in (LAW_Q, LAW_APRIL_Q, LAW_INCR_Q):
        if q not in law:
            fail('G.L. c.71B §5 no longer says %r' % q[:50])
    snaps = SC['movement']['snapshots']
    span_s = (min(s['fy'] for s in snaps), max(s['fy'] for s in snaps))
    for s in snaps:
        if s['march'] - s['october'] != s['net']:
            fail('FY%d: a placement snapshot\'s net is not March less October' % s['fy'])
    max_move = max(abs(s['net']) for s in snaps)
    SY = sorted(s['fy'] for s in snaps)
    sn = {s['fy']: s for s in snaps}
    # WORKED EXAMPLES of G.L. c.71B §5 (TJ, 24 October 2026: "give examples to make it HYPER
    # clear... if someone moves in in Nov... if someone moves in in June"). One placement at a
    # round $100,000 a year, as the district's own deck uses, split by the months left in the
    # school year: tuition is billed monthly (the journal), and an even split is OUR simplification.
    # THE COST OF ONE PLACEMENT: not a round number (TJ: "use the AVERAGE cost... not a random
    # 100k"). The statute covers PRIVATE day and residential placements, so the figure is
    # private-school tuition divided by the children in day and residential placements, each
    # year FY2022-FY2025 (build_sped_costs.py's by_type, OUR ESTIMATE), averaged. Then what the
    # state repays on it a year later, at the regular rate above the per-child threshold.
    per_np = [r['per_nonpublic'] for r in SC['request']['by_type']]
    np_years = [r['fy'] for r in SC['request']['by_type']]
    EX = round(statistics.mean(per_np))
    np_thr = cb[fy1]['threshold'] / cb[fy1]['children']
    np_back = round(0.75 * (EX - np_thr))
    np_net = EX - np_back
    left = lambda month: 12 - (MONTHS.index(month))          # months left from the 1st of `month`
    def ex_in(month):
        # a child already in a private placement moves IN on the 1st of `month`
        rest = round(EX * left(month) / 12)
        late = month in ('Apr', 'May', 'Jun')                  # 'between April 1 and June 30'
        return [C.usd(0), C.usd(0 if late else EX), C.usd(rest + (EX if late else 0))]
    def ex_out(month):
        rest = round(EX * left(month) / 12)
        late = month in ('Apr', 'May', 'Jun')
        return [C.usd(rest), C.usd(EX if late else 0), C.usd(0 if late else EX)]
    ex_rows = [
        dict(label='Moves into Lunenburg, 1 November', cells=ex_in('Nov')),
        dict(label='Moves into Lunenburg, 1 March', cells=ex_in('Mar')),
        dict(label='Moves into Lunenburg, 1 June', cells=ex_in('Jun')),
        dict(label='Leaves Lunenburg, 1 November', cells=ex_out('Nov')),
        dict(label='Leaves Lunenburg, 1 June', cells=ex_out('Jun')),
        dict(label='Already lives in Lunenburg, newly placed, 1 November',
             cells=[C.usd(round(EX * left('Nov') / 12)), C.usd(EX), C.usd(0)]),
    ]
    # THE CHART: the same two whole school years in every bar -- the year of the move and the
    # year after -- so every bar is the same height and the rule reads straight off it (TJ:
    # "why are those bars different heights?", then "why does lunenburg pay 33k on nov1?" -- a
    # twelve-month window from the move crossed 1 July and was right but unreadable). A child
    # who moves IN was the other town's before the move anyway; by c.71B §5 the other town
    # keeps the rest of that year, and the next year too if the move was from 1 April.
    def two_years(month, into):
        late = month in ('Apr', 'May', 'Jun')
        other = EX + (EX if late else 0) if into else (EX if not late else 0)
        return EX * 2 - other, other
    win = [(lab,) + two_years(m, into) for lab, m, into in (
        ('Moves into Lunenburg, 1 November', 'Nov', True),
        ('Moves into Lunenburg, 1 June', 'Jun', True),
        ('Leaves Lunenburg, 1 November', 'Nov', False), ('Leaves Lunenburg, 1 June', 'Jun', False))]
    if win != [(win[0][0], EX, EX), (win[1][0], 0, 2 * EX), (win[2][0], EX, EX),
               (win[3][0], 2 * EX, 0)]:
        fail('the two-year example no longer follows the statute')
    if ex_in('Nov')[0] != '$0' or ex_in('Jun')[1] != '$0' or ex_out('Jun')[1] != C.usd(EX):
        fail('the worked examples no longer follow the statute')
    ex_table = dict(caption='Who pays, worked examples: an average private placement',
                    views=[dict(key='examples', label='Examples',
                                columns=['Lunenburg pays, rest of the school year of the move',
                                         'Lunenburg pays, the whole school year after',
                                         'The other town pays, across both'],
                                kinds=['stated'] * 3, rows=ex_rows,
                                note=('An example, not any child’s bill: %s a year, the average private placement, %s to %s '
                                      '(private tuition divided by the children placed, our estimate), '
                                      'split by the months left in the school year. The law: the town the '
                                      'child came from pays the rest of that year; from 1 April to 30 June, '
                                      'the next year too. A child placed here who was not already placed is '
                                      'Lunenburg’s from the start. If the new team changes the placement, '
                                      'Lunenburg pays any increase. A year later the state repays about %s '
                                      'of a year’s %s, leaving about %s a year to Lunenburg (our arithmetic).'
                                      % (C.usd(EX), C.fy(np_years[0]), C.fy(np_years[-1]), C.usd(np_back), C.usd(EX), C.usd(np_net))))])
    APRIL_Q = ('April 1st is the deadline, if a student enters the district before this date our '
               'school incurs the cost, if it is after this date the sending school assumes the '
               'expense for the rest of the year and the following year')
    LAWREF = ('/docs/' + LAW_KEY, 'G.L. c.71B §5')
    out['arrivals-and-the-budget'] = TP.page(
        'arrivals-and-the-budget',
        'A child in a private placement who moves in is the former town’s cost that year; after 1 April, the next too.',
        [f('m-law', figure(5, 'c.71B §5'), 'the former town pays the rest of the year',
           'statute', allow=('71', '5')),
         f('m-apr', figure(1, '1 April'), 'moves from then: it pays the next year too', 'statute',
           allow=('1',)),
         f('m-reg', figure(28.03, '28.03(1)(c)'), 'the new town serves the child without delay',
           'statute', allow=('28.03(1)(c)',)),
         f('m-tm', U(moved), 'Town Meeting added for move-ins, %s' % C.fy(tm_fy), 'published',
           {'y': F(tm_fy)}),
         f('m-out', U(out_day1), 'moved out of the same line on 1 July 2024', 'published',
           allow=('1', '2024')),
         f('m-held', U(held), 'left in the line after both moves, %s' % C.fy(tm_fy), 'published',
           {'y': F(tm_fy)}),
         f('m-spent', U(spent25), 'spent on out-of-district tuition, %s' % C.fy(tm_fy), 'published',
           {'y': F(tm_fy)}),
         f('m-move', N(max_move, 'children'), 'most the placed count moved, October to March',
           'published'),
         f('m-in', None, 'children who moved to town already placed', 'gap',
           closes='the district’s placement log: each placement’s start and end date, and how it began')],
        # Two conclusions were the statute's two halves (TJ, 25 October 2026, the SERF walk:
        # three of four restated one law); the timeline above draws both, month by month.
        [con('By law, a child in a private placement who moves in is the former town’s cost that year.',
             ['m-law', 'm-reg', 'm-apr'],
             notes=[step('Lunenburg serves the child from arrival and pays only any increase in cost.',
                         'quote', cite=LAWREF),
                    step('From 1 April to 30 June, the former town pays the following year too.',
                         'quote', cite=LAWREF, allow=('1', '30')),
                    step('The minutes of 28 February 2024 record the first half the other way round: '
                         'before 1 April the cost stays with the former town for that year.',
                         'measured', allow=('28', '2024', '1')),
                    step('The law covers private day and residential placements only. A child '
                         'placed in a collaborative, or newly placed here, is not covered by it.',
                         'quote', cite=LAWREF)]),
         con('So a child moving in from a private placement is mostly a next-year cost, known in time.',
             ['m-law', 'm-apr', 'm-in'],
             notes=[step('Which of the FY2025 move-ins were already placed is not published.', 'gap',
                         closes='the district’s placement log: each placement’s start and end '
                                'date, and how it began', allow=('FY2025',))]),
         con('In %s, %s left out-of-district tuition on 1 July; Town Meeting put %s back in May.'
             % (C.fy(tm_fy), C.usd(out_day1), C.usd(moved)), ['m-out', 'm-tm', 'm-held', 'm-spent',
                                                              'm-move'],
             {'y': F(tm_fy), 'a': U(out_day1), 'b': U(moved)}, allow=('1',))],
        chart=TP.series('Example, who pays when a placed child moves', [w[0] for w in win], [
            TP.track('Lunenburg', [w[1] for w in win], 'stated', colour=1),
            TP.track('The other town', [w[2] for w in win], 'stated', colour=2)],
            '$', kind='bar', stacked=True,
            note='The same %s-a-year private placement in every bar, our average, over two school '
                 'years: the year of the move and the next. G.L. c.71B §5.' % C.usd(EX),
            note_figures={'a': U(EX)}, note_allow=('71', '5')),
        also=[TP.series('Children placed out of district, October and March',
                        [C.fy(y) for y in SY], [
                            TP.track('October (DESE)', [sn[y]['october'] for y in SY]),
                            TP.track('1 March (the town)', [sn[y]['march'] for y in SY])],
                        'children', kind='bar',
                        note='Two counts a school year, by two different bodies. The count moved by '
                             'at most %s children between them; neither says who arrived or left.'
                             % C.num(max_move), note_figures={'a': N(max_move)})],
        table=ex_table,
        lead_quote=TP.lead_quote(APRIL_Q, 'Julianna Hanscom, Director of Special Services',
                                 'School Committee', '2024-02-28',
                                 '/docs/meetings/text/school-committee/2024-02-28-minutes-6439.txt',
                                 'School Committee minutes, 28 February 2024',
                                 'sources/meetings/text/school-committee/2024-02-28-minutes-6439.txt'),
        said=[minute('finance-committee', 'Finance Committee', '2025-03-27-minutes-7011.txt',
                     'School special education move in transfer of $50,000 (may be reduced at '
                     'town meeting)', 'Jennifer Warren-Dyment, Town Manager, presenting her budget'),
              said_of(SC, 'radar', 'Dr. Jodi Fortuna, Superintendent of Schools')],
        finding_allow=('1',), blocks=[mv_impact, sc_timeline],
        sources=src + [dict(label='General Court of Massachusetts — G.L. c.71B §5 (Section5.html)',
                            href='/docs/' + LAW_KEY),
                       dict(label='Massachusetts DESE — 603 CMR 28.00, special education regulations',
                            href='/docs/' + REG_KEY)])

    # ------------------------------------------------ how tuition is paid
    PY = sorted(pay)
    months_paid = {y: sum(1 for v in pay[y] if v > 0) for y in PY}
    fewest = min(months_paid.values())
    first_month = {y: next(i for i, v in enumerate(pay[y]) if v > 0) for y in PY}
    july_none = all(pay[y][0] == 0 for y in PY)
    if not july_none:
        fail('a year paid tuition in July; the page says payments start after it')
    # The per-student threshold is the deck's (stated): DESE's file prints a district's TOTAL
    # threshold, every claimed child's added together, not the one a placement is measured by.
    mt = re.search(r'\$100,000 in an eligible FY26 out of district placement [\u2212-] \$([\d,]+) threshold',
                   deck)
    if not mt:
        fail('the deck no longer gives its worked example\'s threshold')
    thr = int(mt.group(1).replace(',', ''))
    for s in ('$%s threshold' % format(thr, ',d'), 'Example: $100,000', '$34,926.75', 'At 75%',
              'FY26: July 2025–June 2026', 'Quarterly in FY27'):
        if norm(s) not in deck:
            fail('the deck no longer states %r' % s)
    back = 0.75 * (100000 - thr)
    if abs(back - 34926.75) > 0.005:
        fail('the deck\'s example no longer follows from DESE\'s threshold')
    np_med = SC['request']['nonpublic_median']
    # WHAT THE STATE PAYS, from DESE's own file (TJ: "how much does the state pay, what percent
    # and how much?"). DESE lists a year by the year it PAID, for the costs of the year before.
    cy = fy1
    c = cb[cy]
    cshare = {y: 100.0 * cb[y]['quarterly'] / cb[y]['eligible'] for y in ys if cb[y]['eligible']}
    on_net = 100.0 * c['quarterly'] / c['net']
    per_child_thr = c['threshold'] / c['children']
    if not 70 <= on_net <= 76:
        fail('the state no longer repaid about three quarters of the claim above threshold')
    out['how-tuition-is-paid'] = TP.page(
        'how-tuition-is-paid',
        'In %s the state paid back %s of %s in placement costs, %s, a year after Lunenburg paid.'
        % (C.fy(cy), C.usd(c['quarterly']), C.usd(c['eligible']), C.pct(cshare[cy])),
        [f('t-months', N(fewest, 'months'), 'fewest months with a payment, in a year',
           'published'),
         f('t-elig', U(c['eligible']), 'placement costs the state counted, for %s' % C.fy(cy), 'published',
           {'y': F(cy)}),
         f('t-paid', U(c['quarterly']), 'repaid by the state, %s' % C.fy(cy), 'published', {'y': F(cy)}),
         f('t-share', P(cshare[cy]), 'the state’s share of placement costs, %s' % C.fy(cy), 'published',
           {'y': F(cy)}),
         f('t-share0', P(cshare[fy0]), 'the state’s share, %s' % C.fy(fy0), 'published',
           {'y': F(fy0)}),
         f('t-net', P(on_net), 'the formula’s rate, on cost above the first share', 'published'),
         f('t-thr', U(per_child_thr), 'threshold a child, %s (our division)' % C.fy(cy), 'estimate',
           {'y': F(cy)}),
         f('t-np', U(EX), 'average private placement, a year (ours)', 'estimate'),
         f('t-back', U(np_back), 'paid back on it, a year later (ours)', 'estimate'),
         f('t-left', U(np_net), 'left to Lunenburg, a year (ours)', 'estimate'),
         # The two kinds of placement, defined where the money is (TJ, 24 October 2026).
         f('t-privb', U(fn_bud(fy1, '9300')), 'private school, rate set by the state: %s budget'
           % C.fy(fy1), 'published', {'y': F(fy1)}),
         f('t-collb', U(fn_bud(fy1, '9400')), 'collaborative, run jointly by districts: %s budget'
           % C.fy(fy1), 'published', {'y': F(fy1)})],
        [con('The state paid back %s of placement costs in %s, up from %s in %s.'
             % (C.pct(cshare[cy]), C.fy(cy), C.pct(cshare[fy0]), C.fy(fy0)),
             ['t-share', 't-share0', 't-elig', 't-paid'],
             {'a': P(cshare[cy]), 'y': F(cy), 'b': P(cshare[fy0]), 'z': F(fy0)}),
         con('Why not more: the formula pays %s of each child’s cost only above the first %s.'
             % (C.pct(on_net), C.usd(per_child_thr)), ['t-net', 't-thr'],
             {'a': P(on_net), 'b': U(per_child_thr)},
             notes=[step('The first share per child is our division of the total threshold DESE '
                         'lists; the rate is the payment over the claim above it.', 'estimate')]),
         con('On an average private placement of %s, the state pays back %s; Lunenburg keeps %s.'
             % (C.usd(EX), C.usd(np_back), C.usd(np_net)), ['t-np', 't-back', 't-left', 't-privb', 't-collb'],
             {'a': U(EX), 'b': U(np_back), 'c': U(np_net)},
             notes=[step('Average of private tuition divided by the children placed, %s to %s: a '
                         'division of totals, not any child’s bill.' % (C.fy(np_years[0]),
                                                                        C.fy(np_years[-1])),
                         'estimate', {'y': F(np_years[0]), 'z': F(np_years[-1])})]),
         con('Lunenburg pays first, by invoice, in at least %s months of every year read.'
             % C.num(fewest), ['t-months'], {'a': N(fewest)})],
        # THE SIGNATURE (TJ, 25 October 2026, the SERF walk): the page's point -- a placement's
        # price is not what it costs the town -- drawn as the subtraction it is.
        chart=TP.parts('One average private placement’s tuition, a year, split',
                       [('Repaid by the state, a year later', np_back), ('Left to Lunenburg', np_net)],
                       '$', basis='estimate', highlight='Left to Lunenburg',
                        note='Private tuition over children placed, %s to %s. The state repays about '
                             'three quarters above a threshold. Our arithmetic, not a bill.'
                             % (C.fy(np_years[0]), C.fy(np_years[-1])),
                        note_figures={'y': F(np_years[0]), 'z': F(np_years[-1])}),
        also=[TP.series('Share of placement costs the state paid back', X, [
                  TP.track('The state’s share', [cshare.get(y) for y in ys])],
                  '%', note='Of every dollar of placement cost the state counts, how much it paid '
                            'back, by the year it paid; each payment covers the year before.'),
              TP.series('Out-of-district tuition paid, by month', list(MONTHS),
                        [TP.track(C.fy(y), pay[y]) for y in PY], '$', kind='bar',
                        note='Every out-of-district tuition payment the school journal posts, every '
                             'fund. The year’s bills arrive from August.')],
        finding_figures={'y': F(cy), 'a': U(c['quarterly']), 'b': U(c['eligible']),
                         'p': P(cshare[cy])},
        said=[said_of(SC, 'carryover', 'Dave Passios (minuted as Passion), Finance Committee; '
                                       'Julianna Hanscom, Director of Special Services')],
        sources=src)

    # ------------------------------------------------ special education grants
    cbys = [y for y in ys]                     # FY2010-FY2026, the overrun window
    cbv = [cb[y]['paid'] for y in cbys]
    cb_med, cb_mean = statistics.median(cbv), statistics.mean(cbv)
    cb_lo = min(cbys, key=lambda y: cb[y]['paid'])
    cb_hi = max(cbys, key=lambda y: cb[y]['paid'])
    recent = cbys[-5:]
    cb_med5 = statistics.median(cb[y]['paid'] for y in recent)
    iys = sorted(idea)
    i_med = statistics.median(idea.values())
    steps_ = [100.0 * (idea[y] / idea[y - 1] - 1) for y in iys[1:]]
    both = [y for y in iys if y in cb and y <= fy1]
    both_med = statistics.median(cb[y]['paid'] + idea[y] for y in both)
    FY27_CB = 818087
    if '$818,087' not in deck or 'FY27 initial' not in deck:
        fail('the deck no longer states the FY2027 initial circuit breaker listing')
    if not FY27_CB > max(cb[y]['paid'] for y in cbys):
        fail('the grants page says the FY2027 listing tops every year paid')
    gx = list(range(fy0, iys[-1] + 1))
    i_hi_step = max(abs(x) for x in steps_)
    if not (FY27_CB > cb_med5 > 0 and i_hi_step < 15):
        fail('the grants outlook says the FY2027 listing tops the recent median and IDEA moves '
             'little')
    g_next = TB.panels('What to expect next year', [
        TB.panel('Circuit breaker (state)', [
            (('Initial listing, %s' % C.fy(fy1 + 1), {'y': F(fy1 + 1)}), C.usd(FY27_CB), 'good'),
            (('Median, last %s years' % C.num(len(recent)), {'n': N(len(recent))}), C.usd(cb_med5), None),
            (('Lowest year, %s' % C.fy(cb_lo), {'y': F(cb_lo)}), C.usd(cb[cb_lo]['paid']), 'bad')],
            sub='Repays last year’s placement costs. Revised during the year.',
            so='A listing, not a payment: it moves with last year’s costs and DESE’s rate, so the '
               'range matters more than the number.'),
        TB.panel('IDEA (federal)', [
            (('Allocated, %s' % C.fy(iys[-1]), {'y': F(iys[-1])}), C.usd(idea[iys[-1]]), None),
            (('Median, %s to %s' % (C.fy(iys[0]), C.fy(iys[-1])), {'y': F(iys[0]), 'z': F(iys[-1])}),
             C.usd(i_med), None),
            ('Largest change in a year', C.pct(i_hi_step), None)],
            sub='An award spent over two years, set by formula.',
            so='The steady part: close to last year’s, every year, and too small a step to absorb '
               'a new placement.')],
        place='lead')
    out['special-education-grants'] = TP.page(
        'special-education-grants',
        'The circuit breaker paid a median %s a year, %s to %s; IDEA allocated %s for %s.'
        % (C.usd(cb_med), C.fy(fy0), C.fy(fy1), C.usd(idea[iys[-1]]), C.fy(iys[-1])),
        [f('g-med', U(cb_med), 'circuit breaker, median year, %s to %s' % (C.fy(fy0), C.fy(fy1)),
           'published', {'y': F(fy0), 'z': F(fy1)}),
         f('g-mean', U(cb_mean), 'circuit breaker, average year', 'published'),
         f('g-lo', U(cb[cb_lo]['paid']), 'circuit breaker, lowest, %s' % C.fy(cb_lo), 'published',
           {'y': F(cb_lo)}),
         f('g-hi', U(cb[cb_hi]['paid']), 'circuit breaker, highest, %s' % C.fy(cb_hi), 'published',
           {'y': F(cb_hi)}),
         f('g-med5', U(cb_med5), 'circuit breaker, median of the last %s years' % C.num(len(recent)),
           'published', {'n': N(len(recent))}),
         f('g-27', U(FY27_CB), 'circuit breaker, %s initial listing (district)' % C.fy(fy1 + 1),
           'published', {'y': F(fy1 + 1)}),
         f('g-idea', U(idea[iys[-1]]), 'IDEA allocated, %s' % C.fy(iys[-1]), 'published',
           {'y': F(iys[-1])}),
         f('g-imed', U(i_med), 'IDEA, median year, %s to %s' % (C.fy(iys[0]), C.fy(iys[-1])),
           'published', {'y': F(iys[0]), 'z': F(iys[-1])}),
         f('g-both', U(both_med), 'the two together, median year', 'published')],
        [con('The circuit breaker paid a median %s a year, from %s in %s to %s in %s.'
             % (C.usd(cb_med), C.usd(cb[cb_lo]['paid']), C.fy(cb_lo), C.usd(cb[cb_hi]['paid']),
                C.fy(cb_hi)), ['g-med', 'g-mean', 'g-lo', 'g-hi'],
             {'a': U(cb_med), 'b': U(cb[cb_lo]['paid']), 'y': F(cb_lo), 'c': U(cb[cb_hi]['paid']),
              'z': F(cb_hi)},
             notes=[step('Paid in the year after the costs it repays, so a bad year shows up in '
                         'the next one’s payment.', 'measured')]),
         con('IDEA moved steadily, %s to %s, never more than %s in a year.'
             % (C.usd(idea[iys[0]]), C.usd(idea[iys[-1]]), C.pct(max(abs(s) for s in steps_))),
             ['g-idea', 'g-imed'],
             {'a': U(idea[iys[0]]), 'b': U(idea[iys[-1]]), 'p': P(max(abs(s) for s in steps_))},
             notes=[step('An award spent over two years, not cash. %s and %s list the school-age '
                         'grant only.' % (C.fy(iys[0]), C.fy(iys[1])), 'measured',
                         {'y': F(iys[0]), 'z': F(iys[1])})]),
         con('The %s listing, %s, is above every year paid since %s.'
             % (C.fy(fy1 + 1), C.usd(FY27_CB), C.fy(fy0)), ['g-27', 'g-hi', 'g-med5'],
             {'y': F(fy1 + 1), 'a': U(FY27_CB), 'z': F(fy0)},
             notes=[step('An initial listing, from the district’s deck; DESE revises it during '
                         'the year.', 'gap',
                         closes='DESE’s final FY2027 circuit breaker listing, June 2027',
                         allow=('FY2027', '2027'))])],
        chart=TP.series('State and federal special education money', [C.fy(y) for y in gx], [
            TP.track('Circuit breaker, paid (state)', [cb[y]['paid'] if y in cb and y <= fy1
                                                       else None for y in gx]),
            TP.track('IDEA, allocated (federal)', [idea.get(y) for y in gx])],
            '$', note='IDEA is school age and preschool. Title I and the pandemic grants are not '
                      'special education and are left out.'),
        finding_figures={'a': U(cb_med), 'y': F(fy0), 'z': F(fy1), 'b': U(idea[iys[-1]]),
                         'w': F(iys[-1])},
        blocks=[g_next], sources=src)

    # ------------------------------------------------ after the circuit breaker: what is left
    # Folded into reserve options and the hub (TJ, 24 October 2026: "do you think 'After the
    # circuit breaker' is too much as a new page? ... wrap it into the other pages").
    # TJ, 24 October 2026: "the circuit breaker is an offset, so if we built into the serf fund
    # accounting for circuit breaker, we'd budget TOO much. so thats what this task is: how much
    # do we have to account for in the serf given the trends of circuit breaker and other
    # funding we already have." The need series is the GENERAL FUND's overrun, so it is already
    # after the account paid; this page shows that, and what the account's own trend means.
    cba = {r['fy']: r for r in SC['cb_account']['years']}
    cyrs = sorted(cba)
    for y in cyrs:
        r = cba[y]
        if abs(r['opening'] + r['received'] - r['spent'] - r['closing']) > 1:
            fail('FY%d: the circuit breaker account does not carry (opening + received - spent)' % y)
    for a_, b_ in zip(cyrs, cyrs[1:]):
        if abs(cba[a_]['closing'] - cba[b_]['opening']) > 1:
            fail('FY%d: the account does not open where FY%d closed' % (b_, a_))
    rec_t = round(sum(cba[y]['received'] for y in cyrs))
    spt_t = round(sum(cba[y]['spent'] for y in cyrs))
    drawn = {y: round(cba[y]['spent'] - cba[y]['received']) for y in cyrs}
    n_drawn = sum(1 for v in drawn.values() if v > 0)
    dmax_y = max(cyrs, key=lambda y: drawn[y])
    below = [y for y in cyrs if cba[y]['closing'] < 0]
    af = {r['fy']: r for r in SC['all_funds']}
    afy = sorted(af)
    if afy != ys[-len(afy):]:
        fail('the all-funds tuition years are not the last years of the ledger: %s' % afy)
    gf_af = sum(need[y] for y in afy)
    all_af = sum(max(0, af[y]['above_voted']) + max(0, over[y]['trans']) + max(0, over[y]['indist'])
                 for y in afy)
    for y in afy:
        if af[y]['gf_spent'] - af[y]['gf_original'] != over[y]['ood']:
            fail('FY%d: the all-funds row is not the ledger’s out-of-district line' % y)
    if not gf_af < all_af:
        fail('the page says counting the circuit breaker raises the overrun')
    cb_peak_y = max((y for y in cyrs if y < fy1), key=lambda y: cba[y]['closing'])

    # ------------------------------------------------ reserve size: three draw rules
    stats = {}
    for k, m in (('acct', acct_need), ('line', need), ('net', pos(net)), ('school', pos(whole))):
        w = max(ys, key=lambda y: m[y])
        t = two(m)
        stats[k] = dict(worst=m[w], wfy=w, two=t[1], tfy=t[0], years=sum(1 for y in ys if m[y] > 0))
    sl = stats['line']
    if (sl['worst'], sl['wfy']) != (SC['need']['worst']['gross'], SC['need']['worst']['fy']):
        fail('the line-by-line worst year is not the overrun page\'s')
    cap = SC['reserve']['cap']
    # The cap is the statute's, now held (G.L. c.40 §13E): 2% of net school spending.
    if 'shall not exceed 2 per cent of the annual net school spending' not in norm(text_of(SERF_TEXT)):
        fail('G.L. c.40 §13E no longer states the 2 per cent cap')
    if abs(cap - 0.02 * SC['reserve']['nss']['nss']) > 1:
        fail('the cap is not 2%% of the net school spending it names: %s' % cap)
    ours = sl['two']
    wb = SC['request']['worst_before']
    if not wb['before'] > cap:
        fail('the reserve page says the worst year without the circuit breaker passes the cap')
    mean_need = statistics.mean(need.values())
    sd_need = statistics.stdev(need.values())
    lvl2 = round(mean_need) + 2 * round(sd_need)       # the overrun page's own rounding
    sa = stats['acct']
    sa['median'] = round(statistics.median(acct_need.values()))
    if not (stats['school']['worst'] <= stats['net']['worst'] <= sl['worst'] <= lvl2 < ours < cap
            < sa['worst']):
        fail('the reserve levels are no longer in the order the page describes')
    out['reserve-size'] = TP.page(
        'reserve-size',
        'Which overruns count moves the worst year from %s to %s.'
        % (C.usd(stats['school']['worst']), C.usd(sa['worst'])),
        [f('r-aw', U(sa['worst']), 'account by account, worst year, %s' % C.fy(sa['wfy']), 'published',
           {'y': F(sa['wfy'])}),
         f('r-am', U(sa['median']), 'account by account, median year', 'published'),
         f('r-lw', U(sl['worst']), 'line by line, worst year, %s' % C.fy(sl['wfy']), 'published',
           {'y': F(sl['wfy'])}),
         f('r-l2', U(sl['two']), 'line by line, worst two years running', 'published'),
         f('r-2sd', U(lvl2), 'average plus two standard deviations', 'published'),
         f('r-nw', U(stats['net']['worst']), 'three lines net, worst year, %s' % C.fy(stats['net']['wfy']),
           'published', {'y': F(stats['net']['wfy'])}),
         f('r-nn', N(stats['net']['years'], 'years'), 'of %s with a net overrun' % C.num(nyrs),
           'published', {'n': N(nyrs)}),
         f('r-sw', U(stats['school']['worst']), 'whole school, worst year, %s'
           % C.fy(stats['school']['wfy']), 'published', {'y': F(stats['school']['wfy'])}),
         f('r-sn', N(stats['school']['years'], 'years'), 'of %s the whole school ran over'
           % C.num(nyrs), 'published', {'n': N(nyrs)}),
         f('r-cap', U(cap), 'the most it may hold: 2% of net school spending', 'statute',
           allow=('2%',)),
         f('r-ours', U(ours), 'a balance that met every year and every pair', 'estimate'),
         f('r-rule', None, 'which overrun the reserve is drawn against', 'gap',
           closes='the Special Education Reserve Fund policy, on the Select Board agenda for '
                  '27 October 2026', allow=('27', '2026'))],
        [con('Drawn account by account, as the budget book lists them: %s at worst, past the cap.'
             % C.usd(sa['worst']), ['r-aw', 'r-am', 'r-cap', 'r-rule'], {'a': U(sa['worst'])},
             notes=[step('An upper bound: money moves between accounts all year, by School '
                         'Committee transfer, so one account’s overrun is often met by another.',
                         'estimate')]),
         con('Drawn line by line, the worst year needed %s; the worst two running, %s.'
             % (C.usd(sl['worst']), C.usd(sl['two'])), ['r-lw', 'r-l2', 'r-2sd', 'r-ours'],
             {'a': U(sl['worst']), 'b': U(sl['two'])},
             notes=[step('Measured after the circuit breaker account paid. In %s, without it, '
                         'the need was %s.' % (C.fy(wb['fy']), C.usd(wb['before'])), 'estimate',
                         {'y': F(wb['fy']), 'a': U(wb['before'])})]),
         con('Drawn when the three lines ran over together: %s at worst, in %s of %s years.'
             % (C.usd(stats['net']['worst']), C.num(stats['net']['years']), C.num(nyrs)),
             ['r-nw', 'r-nn'],
             {'a': U(stats['net']['worst']), 'b': N(stats['net']['years']), 'n': N(nyrs)}),
         con('Drawn when the whole school ran over its vote: %s at worst, in %s years.'
             % (C.usd(stats['school']['worst']), C.num(stats['school']['years'])),
             ['r-sw', 'r-sn'], {'a': U(stats['school']['worst']), 'b': N(stats['school']['years'])})],
        chart=TP.ranking('Each draw rule, worst year and worst pair', [
            ('Account by account, one year', sa['worst']),
            ('Account by account, two running', sa['two']),
            ('Line by line, one year', sl['worst']),
            ('Line by line, two running', sl['two']),
            ('Three lines net, one year', stats['net']['worst']),
            ('Three lines net, two running', stats['net']['two']),
            ('Whole school, one year', stats['school']['worst']),
            ('Whole school, two running', stats['school']['two']),
            ('The cap in law', cap)], '$',
            note='Beyond the general fund vote, %s to %s. Two running: the worst pair of '
                 'consecutive years.' % (C.fy(fy0), C.fy(fy1)),
            note_figures={'y': F(fy0), 'z': F(fy1)}),
        finding_figures={'a': U(stats['school']['worst']), 'b': U(sa['worst'])},
        said=[caption(SC, 'motion'),
              minute('select-board', 'Select Board', '2025-10-07-minutes-7441.txt',
                     'The total balance cannot exceed 2% of annual net school spending.',
                     'Jennifer Warren-Dyment, Town Manager'),
              minute('select-board', 'Select Board', '2025-10-21-minutes-7466.txt',
                     'Member McLeod expressed lingering concern about potential budget impacts if '
                     'the reserve were to reduce urgency around special education line-item '
                     'funding.', 'Select Board member McLeod')],
        sources=src)

    # ------------------------------------------------ reserve options: six sizes, side by side
    # TJ, 24 October 2026: "we could propose ALL the options then. max of 12, median of 12,
    # median of 5, or the adjusted 12 year. We could show ALL on a single page and let someone
    # pick... show how to view that and compare it and validate which one makes sense".
    # ADJUSTED = each year's overrun as a share of the three lines' budget as first voted, times
    # FY2026's. It assumes an overrun grows with the budget it runs over -- ours, untested;
    # if overruns are fixed-size events the as-spent figures are the right ones.
    led = {r['fy']: r for r in SC['ledger']}
    bud = {y: sum(led[y][g]['original'] for g in LINES) for y in ys}
    b1 = bud[fy1]
    share_y = {y: need[y] / bud[y] for y in ys}
    bad_y = [y for y in ys if need[y] > 0]
    r5 = ys[-5:]
    bad5 = [y for y in r5 if need[y] > 0]
    half_up = lambda v: int(v + 0.5)
    o_med = half_up(statistics.median(need[y] for y in bad_y))
    o_adj = half_up(statistics.median(share_y[y] for y in bad_y) * b1)
    o_med5 = half_up(statistics.median(need[y] for y in bad5))
    o_max = sl['worst']
    o_pair = ours
    adj_wfy = max(ys, key=lambda y: share_y[y])
    o_adjmax = half_up(share_y[adj_wfy] * b1)
    adj_pfy = max(ys[:-1], key=lambda y: share_y[y] + share_y[ys[ys.index(y) + 1]])
    o_adjpair = half_up((share_y[adj_pfy] + share_y[ys[ys.index(adj_pfy) + 1]]) * b1)
    if not o_med < o_adj < o_med5 < o_max < o_pair < o_adjmax < cap < o_adjpair:
        fail('the reserve options are no longer in the order the page describes')
    if adj_wfy != sl['wfy']:
        fail('the options page says the worst year is the same year either way')
    covered = lambda X: sum(1 for y in bad_y if need[y] <= X)
    covered_adj = lambda X: sum(1 for y in bad_y if share_y[y] * b1 <= X)
    options = [
        ('Median bad year, all %s' % C.num(nyrs), o_med, 'the middle of the %s years that ran over'
         % C.num(len(bad_y))),
        ('Median bad year, at today’s budget', o_adj, 'the same, each year scaled to the %s budget (ours)'
         % C.fy(fy1)),
        ('Median bad year, last five', o_med5, 'the middle of %s: %s' % (C.num(len(bad5)),
                                                                          ', '.join(C.fy(y) for y in bad5))),
        ('Worst year', o_max, C.fy(sl['wfy'])),
        ('Worst two years running', o_pair, '%s and %s' % (C.fy(sl['tfy']), C.fy(sl['tfy'] + 1))),
        ('Worst year, at today’s budget', o_adjmax, '%s scaled to the %s budget (ours)'
         % (C.fy(adj_wfy), C.fy(fy1))),
    ]
    opt_rows = [dict(label=lab, cells=[C.usd(v), '%s of %s' % (C.num(covered(v)), C.num(len(bad_y))),
                                       '%s of %s' % (C.num(covered_adj(v)), C.num(len(bad_y))), how])
                for lab, v, how in options]
    opt_table = dict(caption='The six options, and the bad years each would have covered',
                     views=[dict(key='options', label='Options',
                                 columns=['Reserve', 'Bad years covered, as spent',
                                          'Bad years covered, at today’s budget', 'How it is measured'],
                                 kinds=['ledger'] * 4, rows=opt_rows,
                                 note=('Covered means the year’s overrun, beyond the three lines’ budget '
                                       'as first voted, fit inside the reserve, assuming the reserve '
                                       'was full at the start of the year. At today’s budget, each '
                                       'year’s overrun as a share of its own budget times %s, the '
                                       'three lines in %s: our arithmetic, which assumes overruns '
                                       'grow with the budget.' % (C.usd(b1), C.fy(fy1))))])
    # THE COMPARISON A READER IS MAKING (TJ, 25 October 2026, the SERF walk): each option against
    # each bad year, a mark where it would have covered it. Worst year first, so the grid is a
    # staircase: the bigger the year, the fewer options reach it. As spent, every column.
    cov_opts = [(lab, v) for lab, v, _ in options]
    cov_cols = [('%s: %s' % (('Median', 'Median, today', 'Median, last five', 'Worst',
                              'Worst two', 'Worst, today')[i], C.usd(v)), {'a': U(v)})
                for i, (_, v) in enumerate(cov_opts)]
    if len(cov_opts) != 6:
        fail('the coverage grid names six options')
    met = lambda y: sum(1 for _, v in cov_opts if need[y] <= v)
    cov_rows = [TB.check_row(('%s, %s over' % (C.fy(y), C.usd(need[y])), {'y': F(y), 'a': U(need[y])}),
                             ('Met by %s of %s' % (C.num(met(y)), C.num(len(cov_opts))),
                              {'a': N(met(y)), 'n': N(len(cov_opts))}),
                             {i for i, (_, v) in enumerate(cov_opts) if need[y] <= v})
                for y in sorted(bad_y, key=lambda y: -need[y])]
    if not all(need[y] <= o_pair for y in bad_y):
        fail('the coverage grid says the worst two years running met every bad year')
    n_all = sum(1 for _, v in cov_opts if covered(v) == len(bad_y))
    if n_all != 3 or [covered(v) == len(bad_y) for _, v in cov_opts] != sorted(
            covered(v) == len(bad_y) for _, v in cov_opts):
        fail('the grid says the largest options, and only those, meet every year')
    cov_grid = TB.checks('Which bad years each option would have met', cov_cols, cov_rows,
                         place='chart', first='Bad year', second='Options that met it', tone='good',
                         note='A mark: that year’s overrun, as spent, fit inside the reserve, '
                              'assuming it was full when the year began.',
                         so=('Every option meets the small years; they differ only on the biggest '
                             'few, and the %s largest meet every year on record.' % C.num(n_all),
                             {'a': N(n_all)}))
    out['reserve-options'] = TP.page(
        'reserve-options',
        'Six ways to size the reserve run from %s to %s; the law caps it at %s.'
        % (C.usd(o_med), C.usd(o_adjmax), C.usd(cap)),
        [f('o-med', U(o_med), 'median bad year, %s to %s' % (C.fy(fy0), C.fy(fy1)), 'published',
           {'y': F(fy0), 'z': F(fy1)}),
         f('o-adj', U(o_adj), 'median bad year, at today’s budget', 'estimate'),
         f('o-med5', U(o_med5), 'median bad year, last five years', 'published'),
         f('o-max', U(o_max), 'worst year, %s' % C.fy(sl['wfy']), 'published', {'y': F(sl['wfy'])}),
         f('o-pair', U(o_pair), 'worst two years running', 'published'),
         f('o-adjmax', U(o_adjmax), 'worst year, at today’s budget', 'estimate'),
         f('o-adjpair', U(o_adjpair), 'worst two running, at today’s budget', 'estimate'),
         f('o-cap', U(cap), 'the most it may hold: 2% of net school spending', 'statute',
           allow=('2%',)),
         f('o-b1', U(b1), 'the three lines’ budget, %s' % C.fy(fy1), 'published', {'y': F(fy1)}),
         f('o-share', P(100 * share_y[adj_wfy]), 'over budget in %s, the worst share' % C.fy(adj_wfy),
           'published', {'y': F(adj_wfy)})],
        [con('A median bad year ran %s over; scaled to today’s budget, %s; in the last five years, %s.'
             % (C.usd(o_med), C.usd(o_adj), C.usd(o_med5)), ['o-med', 'o-adj', 'o-med5', 'o-b1'],
             {'a': U(o_med), 'b': U(o_adj), 'c': U(o_med5)},
             notes=[step('Every size here is the general fund’s overrun: the cost left after the '
                         'circuit breaker account has paid its share.', 'measured'),
                    step('%s to %s that was %s; counting what the account paid, %s.'
                         % (C.fy(afy[0]), C.fy(afy[-1]), C.usd(gf_af), C.usd(all_af)), 'measured',
                         {'y': F(afy[0]), 'z': F(afy[-1]), 'a': U(gf_af), 'b': U(all_af)}),
                    step('The last five years hold %s bad years, so their median is the middle one, %s.'
                         % (C.num(len(bad5)), C.fy(bad5[1])), 'measured',
                         {'n': N(len(bad5)), 'y': F(bad5[1])})]),
         con('The worst year was %s as spent; %s ran %s over, which is %s at today’s budget.'
             % (C.usd(o_max), C.fy(adj_wfy), C.pct(100 * share_y[adj_wfy]), C.usd(o_adjmax)),
             ['o-max', 'o-adjmax', 'o-share'],
             {'a': U(o_max), 'y': F(adj_wfy), 'p': P(100 * share_y[adj_wfy]), 'b': U(o_adjmax)}),
         con('At today’s budget the worst two years running come to %s, past the %s cap.'
             % (C.usd(o_adjpair), C.usd(cap)), ['o-adjpair', 'o-pair', 'o-cap'],
             {'a': U(o_adjpair), 'b': U(cap)})],
        chart=TP.ranking('Six ways to size the reserve', [(lab, v) for lab, v, _ in options]
                         + [('The most the law allows', cap)], '$',
                         highlight=['Median bad year, at today’s budget', 'Worst year, at today’s budget',
                                    'The most the law allows'],
                         note='Overruns beyond the three special education lines’ budget, %s to %s. '
                              'At today’s budget is our arithmetic.' % (C.fy(fy0), C.fy(fy1)),
                         note_figures={'y': F(fy0), 'z': F(fy1)}),
        also=[TP.series('Each year’s overrun, as spent', X, [
                  TP.track('Overrun beyond budget', [need[y] for y in ys], mark='bar'),
                  TP.track('Median bad year', [o_med] * nyrs, mark='line'),
                  TP.track('Median, last five', [o_med5] * nyrs, mark='line'),
                  TP.track('Worst year', [o_max] * nyrs, mark='line')],
                  '$', note='A bar above a line is a year that size of reserve would not have covered.'),
              TP.series('Each year’s overrun at today’s budget', X, [
                  TP.track('Overrun, scaled to today', [half_up(share_y[y] * b1) for y in ys], 'estimate',
                           mark='bar'),
                  TP.track('Median, at today’s budget', [o_adj] * nyrs, 'estimate', mark='line'),
                  TP.track('Worst year, at today’s budget', [o_adjmax] * nyrs, 'estimate', mark='line')],
                  '$', reference=(cap, 'The most the law allows'),
                  note='Each year’s overrun as a share of its own budget, times %s. Older years grow '
                       'most, because the budget was smaller then.' % C.usd(b1),
                  note_figures={'a': U(b1)})],
        tables=[opt_table],
        finding_figures={'a': U(o_med), 'b': U(o_adjmax), 'c': U(cap)},
        blocks=[cov_grid], sources=src)

    # ------------------------------------------------ reserve or budget: a stock or a flow
    # TJ, 24 October 2026: "it seems like the budget option is bad but its not stated in a way
    # that makes it clear WHY". Three reasons, each measured: it raises more, the money sits
    # unused, and money in a budget line can be moved out of it on the first day of the year.
    L = lvl2                                  # the smallest level that met every single year
    if any(need[y] > L for y in ys):
        fail('the budget comparison assumes the level met every year')
    n_under = sum(1 for y in ys if net[y] < 0)
    net_total = sum(net.values())
    raised = L * nyrs
    paid_out = sum(need.values())
    lapsed = raised - paid_out
    as_reserve = L + paid_out
    extra = raised - as_reserve
    cushion = -net_total / nyrs
    cum = lambda vals: [sum(vals[:i + 1]) for i in range(len(vals))]
    SB_RULE = minute('select-board', 'Select Board', '2025-10-07-minutes-7441.txt',
                     'The fund requires a majority vote of both the School Committee and the Select '
                     'Board to expend.', 'Jennifer Warren-Dyment, Town Manager')
    out['reserve-or-budget'] = TP.page(
        'reserve-or-budget',
        'Budgeting the cushion every year raises %s more than a reserve covering the same years.'
        % C.usd(extra),
        [f('b-l', U(L), 'a level that met every year, %s to %s' % (C.fy(fy0), C.fy(fy1)),
           'published', {'y': F(fy0), 'z': F(fy1)}),
         f('b-raised', U(raised), 'raised if added to the budget every year', 'estimate'),
         f('b-res', U(as_reserve), 'raised if held once and refilled', 'estimate'),
         f('b-paid', U(paid_out), 'overspending either one would have paid', 'published'),
         f('b-lapsed', U(lapsed), 'budgeted and never needed', 'estimate'),
         f('b-moved', U(out_day1), 'moved out of out-of-district tuition, 1 July 2024', 'published',
           allow=('1', '2024')),
         f('b-under', N(n_under, 'years'), 'of %s the three lines spent under budget' % C.num(nyrs),
           'published', {'n': N(nyrs)}),
         f('b-cush', U(cushion), 'budget above spending, three lines, a year', 'published')],
        [con('Added to the budget every year, %s raises %s over %s years to pay %s of overspending.'
             % (C.usd(L), C.usd(raised), C.num(nyrs), C.usd(paid_out)),
             ['b-l', 'b-raised', 'b-paid', 'b-lapsed'],
             {'a': U(L), 'b': U(raised), 'n': N(nyrs), 'c': U(paid_out)},
             notes=[step('The other %s is raised and never needed; it reaches free cash a year or '
                         'two later, not the year it was raised.' % C.usd(lapsed), 'estimate',
                         {'a': U(lapsed)})]),
         con('Held once as a reserve, the same protection raises %s: %s up front, then refills.'
             % (C.usd(as_reserve), C.usd(L)), ['b-res', 'b-l', 'b-paid'],
             {'a': U(as_reserve), 'b': U(L)}),
         con('A cushion in the budget can be moved: on 1 July 2024, %s left out-of-district tuition.'
             % C.usd(out_day1), ['b-moved'], {'a': U(out_day1)}, allow=('1', '2024'),
             notes=[step('A reserve cannot be moved that way: spending it needs a majority of both '
                         'the School Committee and the Select Board.', 'quote',
                         cite=(SB_RULE['href'], SB_RULE['label']))]),
         con('The cushion is already there: the three lines spent under budget in %s of %s years.'
             % (C.num(n_under), C.num(nyrs)), ['b-under', 'b-cush'],
             {'a': N(n_under), 'n': N(nyrs)},
             notes=[step('So a reserve replaces the cushion in the budget rather than adding to it, '
                         'if the budget is set lower once the reserve exists (our reading).',
                         'estimate')])],
        chart=TP.series('Budgeted every year, or held once', X, [
            TP.track('Raised, if added to every budget', cum([L] * nyrs), 'estimate'),
            TP.track('Raised, if held once and refilled', [L + c for c in cum([need[y] for y in ys])],
                     'estimate'),
            TP.track('Overspending actually paid', cum([need[y] for y in ys]))],
            '$', note='Running totals from %s. Both ways pay the same overspending; the gap between '
                      'the top two lines is money raised and not needed.' % C.fy(fy0),
            note_figures={'y': F(fy0)}),
        also=[TP.series('Spent less budget, each year', X, [
            TP.track('Special education, three lines', [net[y] for y in ys]),
            TP.track('Whole school general fund', [whole[y] for y in ys])],
            '$', kind='bar',
            note='Below zero is a year that came in under its budget as first voted; spent includes '
                 'what was still owed at the close.')],
        finding_figures={'a': U(extra)},
        said=[SB_RULE,
              minute('select-board', 'Select Board', '2025-10-21-minutes-7466.txt',
                     'Member McLeod expressed lingering concern about potential budget impacts if '
                     'the reserve were to reduce urgency around special education line-item '
                     'funding.', 'Select Board member McLeod')],
        sources=src)

    # ------------------------------------------------ the hub
    # THE WALK A BOARD MEMBER TAKES (TJ, 24 October 2026: "walk the hub from a user's
    # perspective, a board member... they need to draw conclusions, so we need to... make the
    # bold statements of what the data is actually saying"). In the order they ask it:
    #   1. does special education run short?           a line does, most years; the three
    #                                                  together less often (TJ, 25 October 2026:
    #                                                  "the school committee will disagree with
    #                                                  'Special education rarely runs short'" --
    #                                                  and the ledger agrees with them)
    #   2. then what surprises us?                     late orders, in spring
    #   3. aren't move-ins the problem?                by law, a placed child is the old town's cost that year
    #   4. so what is the reserve for?                 the slack in the budget gets moved; the
    #                                                  circuit breaker account that absorbed it is shrinking
    #   5. how big?                                    six sizes, side by side; none singled out
    #                                                  (TJ, 25 October 2026: highlighting one
    #                                                  "suggest thats the option to pick" -- rule 8)
    #   6. why not just budget it?                     it raises far more for the same protection
    cba_y = {r['fy']: r['closing'] for r in SC['cb_account']['years']}
    cb_hi_y = max((y for y in cba_y if y < fy1), key=lambda y: cba_y[y])
    cb_close = cba_y[fy1]
    if not cb_close < cba_y[cb_hi_y]:
        fail('the hub says the circuit breaker account has fallen from its high')
    # VOTED, REPAID, OVER -- ONE BAR A YEAR (TJ, 25 October 2026: "a chart that shows the
    # amount allocated, then, how much is 'paid back' and the overrun, all in one chart"). The
    # honest stack is what these three lines COST, all funds: the general fund spent (inside its
    # vote, and above it, line by line) plus what the circuit breaker account spent. The
    # repayment is not a refund to the general fund: it lands in its own account and pays
    # tuition directly, so the overrun the ledger shows is already AFTER it (see "after the
    # circuit breaker" above). Line by line: voted = within + unspent, spent = within + over.
    mys = [y for y in ys if y in cba]
    if mys != list(range(mys[0], fy1 + 1)):
        fail('the circuit breaker account skips a year inside the ledger')
    led_h = {r['fy']: r for r in SC['ledger']}
    mrow = {}
    for y in mys:
        vo = sum(led_h[y][g]['original'] for g in LINES)
        wi = sum(min(led_h[y][g]['original'], led_h[y][g]['spent']) for g in LINES)
        ov = sum(max(0, led_h[y][g]['spent'] - led_h[y][g]['original']) for g in LINES)
        if ov != need[y] or wi + ov != sum(led_h[y][g]['spent'] for g in LINES):
            fail('FY%d: the money chart does not tie to the ledger and the need series' % y)
        st = round(cba[y]['spent'])
        mrow[y] = dict(fy=C.fy(y), voted=vo, within=wi, over=ov, state=st,
                       t_voted=C.usd(vo), t_over=C.usd(ov), t_state=C.usd(st),
                       t_spent=C.usd(wi + ov + st))
    st_more = sum(1 for y in mys if mrow[y]['state'] > mrow[y]['over'])
    st_sum = sum(mrow[y]['state'] for y in mys)
    ov_sum = sum(mrow[y]['over'] for y in mys)
    st_hi = max(mys, key=lambda y: mrow[y]['state'])
    if not (st_more == len(mys) and st_sum > 3 * ov_sum and mrow[fy1]['state'] < mrow[st_hi]['state']):
        fail('the money chart\'s meaning says the repayment outran overspending every year, by '
             'several times in total, and has fallen from its high')
    mfig = [v for y in mys for k, v in mrow[y].items() if k == 'fy' or k.startswith('t_')]
    h = {}
    n_line = len(bad_y)                       # years at least one line spent past its vote
    h['h-line'] = f('h-line', N(n_line, 'years'), 'of %s a line spent past its vote' % C.num(nyrs),
                    'published', {'n': N(nyrs)})
    h['h-under'] = f('h-under', N(n_under, 'years'), 'of %s the three lines spent under budget'
                     % C.num(nyrs), 'published', {'n': N(nyrs)})
    h['h-school'] = f('h-school', U(stats['school']['worst']), 'whole school over its budget, worst year',
                      'published')
    h['h-spring'] = f('h-spring', P(spring_pct, 0), 'of late orders placed March to June', 'published')
    h['h-law'] = f('h-law', figure(5, 'c.71B §5'), 'a private placement moving in: old town pays',
                   'statute', allow=('71', '5'))
    h['h-moved'] = f('h-moved', U(out_day1), 'moved out of the tuition budget, 1 July 2024', 'published',
                     allow=('1', '2024'))
    h['h-cba'] = f('h-cba', U(cb_close), 'circuit breaker account, close of %s' % C.fy(fy1), 'published',
                   {'y': F(fy1)})
    h['h-cba0'] = f('h-cba0', U(cba_y[cb_hi_y]), 'the same account, close of %s' % C.fy(cb_hi_y),
                    'published', {'y': F(cb_hi_y)})
    h['h-repaid'] = f('h-repaid', N(st_more, 'years'), 'of %s the state’s repayment paid more than ran over'
                      % C.num(len(mys)), 'published', {'n': N(len(mys))})
    # The sizes, side by side (TJ, 24 October 2026: "propose ALL the options... and let
    # someone pick"). The full set, with the years each covers, is reserve-options.
    h['h-med'] = f('h-med', U(o_med), 'median bad year, as spent', 'published')
    h['h-adj'] = f('h-adj', U(o_adj), 'median bad year, at today’s budget', 'estimate')
    h['h-med5'] = f('h-med5', U(o_med5), 'median bad year, last five', 'published')
    h['h-worst'] = f('h-worst', U(o_max), 'worst year, %s' % C.fy(sl['wfy']), 'published',
                     {'y': F(sl['wfy'])})
    h['h-ours'] = f('h-ours', U(o_pair), 'worst two years running', 'published')
    h['h-adjmax'] = f('h-adjmax', U(o_adjmax), 'worst year, at today’s budget', 'estimate')
    h['h-cap'] = f('h-cap', U(cap), 'the most the reserve may hold, by law', 'statute')
    h['h-policy'] = f('h-policy', None, 'what the reserve may be drawn for', 'gap',
                      closes='the Special Education Reserve Fund policy, Select Board, 27 October 2026',
                      allow=('27', '2026'))
    ladder = LD.ladder([
        LD.tier('Does it run short?', [h['h-line'], h['h-under'], h['h-school'], h['h-spring'], h['h-law']]),
        LD.tier('Where the slack goes', [h['h-moved'], h['h-repaid'], h['h-cba'], h['h-cba0']]),
        LD.tier('How big, and why a reserve', [h['h-med'], h['h-adj'], h['h-med5'], h['h-worst'],
                                               h['h-ours'], h['h-adjmax'], h['h-cap'],
                                               h['h-policy']]),
    ], [
        LD.conclusion('A line spent past its vote in %s of %s years; the three together came in under in %s.'
                      % (C.num(n_line), C.num(nyrs), C.num(n_under)), ['h-line', 'h-under', 'h-school'],
                      {'a': N(n_line), 'n': N(nyrs), 'b': N(n_under)}),
        LD.conclusion('When it does, the bill comes late: %s of orders placed after September came March to June.'
                      % C.pct(spring_pct, 0), ['h-spring'], {'a': P(spring_pct, 0)}),
        LD.conclusion('A child already in a private placement who moves in is, by law, the old town’s cost that year.',
                      ['h-law']),
        LD.conclusion('The slack in the budget does not wait for spring: %s left out-of-district tuition on 1 July.'
                      % C.usd(out_day1), ['h-moved'], {'a': U(out_day1)}, allow=('1',)),
        LD.conclusion('In %s of %s years the state’s repayment paid for more than ran over the budget.'
                      % (C.num(st_more), C.num(len(mys))), ['h-repaid', 'h-cba', 'h-cba0'],
                      {'a': N(st_more), 'n': N(len(mys))}),
        LD.conclusion('Six ways to size the reserve run from %s, a median bad year, to %s, the worst at today’s budget.'
                      % (C.usd(o_med), C.usd(o_adjmax)),
                      ['h-med', 'h-adj', 'h-med5', 'h-worst', 'h-ours', 'h-adjmax', 'h-cap',
                       'h-policy'],
                      {'a': U(o_med), 'b': U(o_adjmax)}),
    ])
    vp24 = dict(vp)[2024]
    terms = [
        TP.term('Surprise cost',
                # Measured as spending above each account's ORIGINAL budget in the town's ledger.
                'Spending above the budget set at the start of the year. The law’s words: '
                'unanticipated or unbudgeted costs.',
                'A child, a rate or a route nobody planned for, often ordered only in spring, '
                'after the budget is set.'),
        # The CORE is what moves the bill -- children placed, arriving, and the
        # price -- (TJ, 24 October 2026: "we lost the 'core' of the intention of those, like
        # children moving in or out"); private and collaborative ride along as the two lines.
        TP.term('Out-of-district tuition',
                # "Out of district" names where the child is SCHOOLED, not a move: TJ read the
                # old wording as "moves into Lunenburg", 25 Oct 2026.
                'Tuition for a Lunenburg child schooled outside Lunenburg’s schools: an approved '
                'private school, at a state-set rate, or a collaborative of districts.',
                # c.71B §5 covers PRIVATE day and residential placements only: a child moving in
                # from a collaborative is Lunenburg's from arrival; the new town also pays "any
                # increase" its own review makes. Rates: "when did we find out about this?" (SC,
                # 28 Feb 2024, on a 14% rise). Year end: $250,000 ordered on 30 June 2026.
                'A Lunenburg child newly placed, or arriving already in a collaborative; a '
                'costlier placement after review; a rate raised after the budget; a bill known '
                'at year end.'),
        TP.term('Special education transportation',
                # Payees read off the journal, FY2023-FY2026: the van contractor, then mileage
                # reimbursed to parents and staff. Which children ride is not in the ledger.
                'Transport a child’s plan requires: contracted van companies, and mileage paid '
                'to parents and staff.',
                'Contracts are topped up late in the year: the van contract was raised %s in '
                'spring %s.' % (C.usd(vp24), C.fy(2024)),
                {'a': U(vp24), 'y': F(2024)}),
        TP.term('In-district special education',
                'Dozens of budget lines, added up by us: staff, therapists and contracted '
                'services in Lunenburg’s own schools.',
                'The smallest share of overspending; it is mostly staff pay. It ran over in %s of '
                '%s years.'
                % (C.num(yrs_over['indist']), C.num(nyrs)),
                {'a': N(yrs_over['indist']), 'n': N(nyrs)}),
        TP.term('Circuit breaker',
                # The district's own words (2023-2024 presentation): "approximately 75 percent of
                # the costs above that threshold", "for the district's prior year's expenses",
                # "may be expended by the school committee... without further appropriation".
                'The state repaying about three quarters of each child’s cost above a threshold, '
                'a year later, into an account spent without a Town Meeting vote.',
                # Finance Committee minutes, 14 March 2024: the 14% rise "is probably absorbed
                # with a lot of the carry over for the circuit breaker monies".
                'The district said in March 2024 it probably absorbed a 14%% tuition rise. It '
                'closed %s at %s, down from %s.'
                % (C.fy(fy1), C.usd(cb_close), C.usd(cba_y[cb_hi_y])),
                {'y': F(fy1), 'a': U(cb_close), 'b': U(cba_y[cb_hi_y])}, allow=('14%', '2024')),
    ]
    # THE HUB, REARRANGED (TJ, 25 October 2026): "the main SERF page has the most important
    # information/data and conclusions right on it (including the reserve options, the biggest
    # impacts, etc). we may need to move some definitions into a deeper topic page 'to learn
    # more' like circuit breaker flow and definitions of surprises." So: the three answers the
    # report exists for, side by side; the biggest impact; the reserve options as the signature;
    # where overspending lands under it. The definitions moved to Surprise costs; the circuit
    # breaker's step-by-step lives on its own page.
    money_chart = TB.custom(
        # TJ, 25 October 2026: "how does the repayment work on this chart? it looks additive"
        # -- it IS additive, and nothing said so. `read` says it above the bars.
        'serf-money-stack', 'Each year’s bill: the vote, then what was spent on top of it',
        dict(rows=[mrow[y] for y in mys],
             read='Each bar adds up. Left: the budget Town Meeting voted, hatched where a line left '
                  'some unspent. Then what was spent on top of the vote: red from the town budget, '
                  'green from the state’s repayment of the year before.',
             legend=dict(within='Spent, inside what was voted', unspent='Voted, not spent',
                         over='Spent above a line’s vote', state='Paid from the state’s repayment'),
             note='The three special education lines, each year. The repayment is the circuit '
                  'breaker: it goes into its own account, which pays tuition without a Town Meeting '
                  'vote, so the overspending shown is what was left after it.'),
        place='chart', figures=mfig,
        alt='Bars by year: voted budget, spending above it, and spending from the circuit breaker account.',
        so=('Added up, %s to %s, the state’s repayment paid %s and overspending came to %s. The '
            'reserve covers the smaller of the two cushions; if the repayment falls, what is left '
            'to cover grows.' % (C.fy(mys[0]), C.fy(fy1), C.usd(st_sum), C.usd(ov_sum)),
            {'y': F(mys[0]), 'z': F(fy1), 'a': U(st_sum), 'b': U(ov_sum)}))
    if not (covered(o_med5) < len(bad_y) == covered(o_max) and o_max < cap and cb_med > o_med5):
        fail('the three answers say the recent median misses some bad years, the worst year '
             'meets them all inside the cap, and a median repayment exceeds a median bad year')
    FYR2 = lambda txt, a, b: (txt, {'y': F(a), 'z': F(b)})
    hub_answers = TB.panels('The three answers', [
        TB.panel('What reserve to keep', [
            ('Median bad year, last five', C.usd(o_med5), None),
            ((('Worst year on record, %s' % C.fy(sl['wfy'])), {'y': F(sl['wfy'])}), C.usd(o_max), None),
            ('The most the law allows', C.usd(cap), None)],
            sub='Six ways to size it are compared on Reserve options.',
            so=('Held at the recent median it would have met %s of %s bad years; at the worst year, '
                'all of them. The choice is how rare a year to insure against.'
                % (C.num(covered(o_med5)), C.num(len(bad_y))),
                {'a': N(covered(o_med5)), 'n': N(len(bad_y))})),
        TB.panel('What comes back', [
            (FYR2('Circuit breaker, median a year, %s to %s' % (C.fy(fy0), C.fy(fy1)), fy0, fy1),
             C.usd(cb_med), None),
            (('Share of placement costs repaid, %s' % C.fy(cy), {'y': F(cy)}), C.pct(cshare[cy]), None),
            (('IDEA allocated, %s' % C.fy(iys[-1]), {'y': F(iys[-1])}), C.usd(idea[iys[-1]]), None)],
            sub='The circuit breaker arrives a year after Lunenburg pays.',
            so='More comes back in a typical year than runs over, but a year late and in amounts '
               'that swing, so it cannot stand in for a reserve.'),
        TB.panel('What budget to carry', [
            (('Years the three lines spent under budget, of %s' % C.num(nyrs), {'n': N(nyrs)}),
             C.num(n_under), 'good'),
            (('Moved out of tuition, 1 July 2024', None, ('1', '2024')), C.usd(out_day1), None),
            ('Budgeting the cushion yearly costs more than a reserve by', C.usd(extra), 'bad')],
            sub='The slack is there, but it can be moved before the spring bill.',
            so='The budget is usually big enough. The risk is its slack being moved before a spring '
               'bill, and padding every year costs more than holding a reserve once.')],
        place='lead')
    # WHAT WAS SAID, BESIDE THAT YEAR'S LEDGER. TJ, 25 October 2026: "the school committee will
    # disagree ... can you find quotes that say the surprises from special education crush the
    # budget and put them on this page." Found by a search of every board's minutes and
    # captions (43 candidates); these eight vary by board, year and kind of surprise. Each
    # sits beside the town's ledger for the fiscal year it was said in -- the line-by-line
    # record, so a reader sees what a meeting saw and what the year closed at, and neither is
    # marked wrong. The October 2026 Finance Committee remark is left out: its captions render
    # out of district as "Audit district", and a quote is not built around a mis-hearing.
    # THE OPENING QUOTATION (TJ, 25 October 2026: "i expected at least one at the top of the
    # page"): the claim the hub's ledger is set against, in a School Committee meeting's words.
    OPEN = video('school-committee', 'School Committee', '2025-02-05-ad6QtSaJqVU.json', '2:33:32',
                 'it\'s dangerous to hedge our bets and go lean on our special edlines because those '
                 'are the lines that blow our budget out of the water when we have unanticipated '
                 'students moving in to lunenberg')
    SAID = [
        video('school-committee', 'School Committee', '2025-09-03-SI-irBe6ABs.json', '1:07:09',
              'somebody could move 350 ft across the town line and now we have a million dollar '
              'hole in our budget.'),
        video('select-board', 'Select Board', '2024-12-17-jrG1b_tADyo.json', '1:56:30',
              'those costs are enormous they are staggering and we have no way to Abate them no '
              'way to prepare for them no way to alter them'),
        video('school-committee', 'School Committee', '2023-10-04-RSuhiVz9L-A.json', '0:40:09',
              'if we get a sped private tuition that comes in unexpected it\'s going to affect our '
              'budget and here we are I mean it just happened'),
        video('finance-committee', 'Finance Committee', '2025-06-12-iRhUTui_HRY.json', '1:11:12',
              'the outofd district placement can just kill you'),
        video('school-committee', 'School Committee', '2025-06-18-AIhtA5pkPI0.json', '2:37:06',
              'We had so much unexpected special ed costs creep in this year.'),
        minute('school-committee', 'School Committee', '2024-01-24-minutes-6375.txt',
               'Our out of District placements have skyrocketed, our transportation has skyrocketed',
               'Mr. Beardmore, School Committee member, as minuted'),
        minute('select-board', 'Select Board', '2012-05-01-minutes-4804.txt',
               'the schools cannot cover their deficit due to higher than expected special education '
               'costs.', 'Not named in the minutes'),
    ]
    LONG = ('January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September',
            'October', 'November', 'December')
    s_fig, s_items, s_years = [], [], {}
    for q in SAID:
        yy, mm, dd = (int(x) for x in q['date'].split('-'))
        fy = yy + 1 if mm >= 7 else yy
        if fy not in mrow:
            fail('a quotation from %s falls in %s, a year the ledger does not hold' % (q['date'], C.fy(fy)))
        when = '%d %s %d' % (dd, LONG[mm - 1], yy)
        rows = [(LINE_NAME[g], '%s over' % C.usd(over[fy][g]), 'bad')
                for g in LINES if over[fy][g] > 0]
        s_years[fy] = bool(rows)
        if not rows:
            rows = [('Every line', 'within its vote', 'good')]
        rows.append(('The three together', '%s %s' % (C.usd(abs(net[fy])), 'over' if net[fy] > 0 else 'under'),
                     'bad' if net[fy] > 0 else None))
        rows.append(('Paid from the state’s repayment', mrow[fy]['t_state'], None))
        s_fig += [C.fy(fy), when, mrow[fy]['t_state']] + [r[1] for r in rows]
        s_items.append(dict(quote=q['quote'], who=q['who'], when=when, board=q['board'],
                            href=q['href'], label=q['label'], caption=bool(q.get('caption')),
                            fy=C.fy(fy), ledger=[dict(label=a, value=b, tone=c) for a, b, c in rows]))
        s_fig += [q['label'], q['quote']]
    s_top = max(s_years, key=lambda y: sum(1 for i in s_items if i['fy'] == C.fy(y)))
    if s_years[s_top]:
        fail('the quotations say the year quoted most closed with every line inside its vote')
    said_block = TB.custom(
        'serf-said-ledger', 'What was said, beside that year’s ledger',
        dict(items=s_items, ledger_head='The ledger, each line against its vote,'), place='body', figures=s_fig,
        allow=[q['href'] for q in SAID],          # addresses, not figures
        alt='Seven quotations from public meetings, each beside the special education lines’ '
            'results for that fiscal year.',
        so=('The quotations fall in %s fiscal years, and in %s a line spent past its vote. %s, quoted '
            'most, closed with every line inside it: much of the worry is about a year that could '
            'come, which is what a reserve is for.'
            % (C.num(len(s_years)), C.num(sum(s_years.values())), C.fy(s_top)),
            {'n': N(len(s_years)), 'a': N(sum(s_years.values())), 'y': F(s_top)}))
    out[HUB] = TP.hub(
        HUB,
        'A special education line spent past its vote in %s of %s years, the bill often in spring, '
        'after slack was moved. A median bad year of the last five ran %s over; the worst year '
        'on record, %s. Held once, a reserve costs less than a yearly cushion.'
        % (C.num(n_line), C.num(nyrs), C.usd(o_med5), C.usd(o_max)),
        ladder, chart=out['reserve-options']['chart'],
        answer_figures={'k': N(n_line), 'n': N(nyrs), 'm': U(o_med5), 'a': U(o_max)},
        lead_quote=TP.lead_quote(OPEN['quote'], OPEN['who'], OPEN['board'], OPEN['date'],
                                 OPEN['href'], OPEN['label'],
                                 'sources/data/youtube-transcripts/school-committee/2025-02-05-ad6QtSaJqVU.json',
                                 caption=True),
        blocks=[hub_impact, hub_answers, money_chart, said_block,
                TB.chart(surprise_chart, place='chart',
                         so=('Out-of-district tuition is the largest share, %s, but not most of it: '
                             'a reserve drawn only for tuition would miss the rest.' % C.pct(share['ood']),
                             {'a': P(share['ood'])}))])
    if not (max(share, key=share.get) == 'ood' and share['ood'] < 50):
        fail('the hub says tuition is the largest share of overspending and under half')
    # The definitions, one level down (see above): on the page about what surprises.
    out['surprise-costs']['blocks'].append(
        TB.terms('The terms, and why each one surprises', terms, place='end'))

    # ------------------------------------------------ what each conclusion means
    meanings(out[HUB]['ladder']['conclusions'], [
        'The surprises are real and frequent; what has absorbed them is slack in the other lines, and that slack can be moved.',
        'A spring bill finds the year’s money already committed; that timing, more than the size, is what a reserve covers.',
        'Such a move can be seen coming and budgeted the next year; the in-year risk is a child newly placed here.',
        'Padding the special education budget does not protect against spring bills if the padding can be moved in July.',
        'The vote has never been the whole bill, and the repayment’s account is thinner, so the next bad year lands closer to the budget.',

        ('The choice is how rare a year to insure against: the median bad year was covered in %s of %s, the worst in all.'
         % (C.num(covered(o_med)), C.num(len(bad_y))),
         {'a': N(covered(o_med)), 'n': N(len(bad_y))})])
    meanings(out['surprise-costs']['conclusions'], [
        ('A reserve meant only for out-of-district tuition would leave out %s of the risk; the law also covers transport.'
         % C.pct(100 - share['ood']), {'a': P(100 - share['ood'])}),
        'A placement added to the smaller collaborative line shows as an overrun even when private tuition has room to spare.',
        'Late orders are one way a cost escapes the budget; a child, a rate or a route nobody planned for is the other.'])
    meanings(out['arrivals-and-the-budget']['conclusions'], [
        'A child moving in from a private placement costs Lunenburg nothing that year; one from a collaborative does.',
        'The in-year placement risk is a child already living here who is newly placed, more than one moving in.',
        'The move-in money was voted into a line the district had already cut, on day one, by far more.'])
    meanings(out['how-tuition-is-paid']['conclusions'], [
        'The state now covers nearly half of placement costs, so a placement’s price overstates what it costs the town.',
        'A dear placement gets much more back than a cheap one, so the town’s own cost varies less than the prices do.',
        ('When a meeting cites a placement’s price, the town’s own cost is closer to %s a year, repaid in part a year late.'
         % C.usd(np_net), {'a': U(np_net)}),
        'Because Lunenburg pays first and is repaid a year later, some account carries a year of the cost in between.'])
    meanings(out['special-education-grants']['conclusions'], [
        'Circuit breaker income swings by hundreds of thousands from year to year, so it cannot be counted on as a fixed sum.',
        'IDEA is the steady part, and it barely grows, so it cannot absorb a new placement.',
        ('A larger repayment arrives in %s and refills the account; it also says the costs of %s were high.'
         % (C.fy(fy1 + 1), C.fy(fy1)), {'y': F(fy1 + 1), 'z': F(fy1)})])
    meanings(out['reserve-size']['conclusions'], [
        'If no budget line may cover another, the worst year alone passes the legal cap; the rule sets the size more than history does.',
        'If each line may draw on its own, a safe reserve is about the size of two bad years.',
        'If the lines cover each other first, the reserve is drawn about one year in three, and for less.',
        'If the whole school budget runs out first, a reserve this size would almost never be touched.',
        ])
    meanings(out['reserve-options']['conclusions'], [
        'The three medians differ mostly by how old years are counted; recent years and scaled years agree more closely.',
        'Whether old overruns count at today’s size nearly doubles the worst case; nothing in the data settles it.',
        'If overruns grow with the budget, no reserve the law allows covers a repeat of the worst stretch.'])
    meanings(out['reserve-or-budget']['conclusions'], [
        'Budgeting the cushion raises taxes for money that, in most years, is never needed for special education.',
        'A reserve asks taxpayers once, and afterwards only for what was actually used.',
        'Money in a budget line protects nothing if it can be moved out before the bill arrives.',
        'A reserve saves money only if the budget is set lower once it exists: that is the decision to watch.'])

    if sorted(k for k in out if k != HUB) != sorted(MINE):
        fail('the pages built are not the pages the registry gives this script: %s'
             % sorted(set(MINE) ^ set(out)))
    return out


def said_of(SC, key, who):
    """A quotation special-education-costs.json already verified against the minutes."""
    s = next((x for x in SC['said'] if x['key'] == key), None)
    if s is None or not s['cite'].startswith('/docs/'):
        fail('quotation %r is no longer in special-education-costs.json' % key)
    return dict(quote=s['quote'], board=s['board'], date=s['date'], href=s['cite'], who=who,
                label='%s minutes, %s' % (s['board'], s['date']))


def caption(SC, key, who=CAPTION_WHO):
    """A machine caption at its timestamp: a finding aid, never a record, and labelled so."""
    s = next((x for x in SC['request']['said'] if x['key'] == key), None)
    if s is None:
        fail('caption %r is no longer in special-education-costs.json' % key)
    return dict(quote=s['quote'], board=s['board'], date=s['date'], href=s['cite'], caption=True,
                who=who,
                label='%s, %s, video at %s (machine captions)' % (s['board'], s['date'], s['at']))


def outputs():
    return {os.path.join(OUT_DIR, '%s.json' % t):
            json.dumps(p, indent=1, ensure_ascii=False, sort_keys=True) + '\n'
            for t, p in build().items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    outs = outputs()
    if a.check:
        stale = [os.path.relpath(p, ROOT) for p, text in outs.items()
                 if not os.path.exists(p) or open(p, encoding='utf-8').read() != text]
        if stale:
            print('STALE %s' % ', '.join(stale), file=sys.stderr)
            return 1
        print('SERF topics: %d outputs current' % len(outs))
        return 0
    for p, text in outs.items():
        with open(p, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        print('wrote %s' % os.path.relpath(p, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
