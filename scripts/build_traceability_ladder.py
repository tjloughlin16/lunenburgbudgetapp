#!/usr/bin/env python3
"""How far the money can be followed — one rung per question, computed from the ledger.

    python3 scripts/build_traceability_ladder.py            # write it
    python3 scripts/build_traceability_ladder.py --check    # fail if it is stale

WHAT THIS IS. `/what-we-cannot-answer` lists gaps as prose. The central gap is not a list:
it is a DEPTH. Six questions about the same dollar, ordered from the coarsest to the
finest, and the archive answers the first three, half-answers the fourth, and answers the
last two for exactly one fund out of sixty-one. Drawn, that is a ladder whose top rungs
hold and whose bottom rungs do not — which is a different claim from "there are gaps",
because it says WHERE the following stops.

THE VOCABULARY IS NOT NEW. `notes/reference/data-model/join-map.html` already frames this
as levels of detail, each turning on a key, with tiers 1/2/3 and "the tier we do not
have". This file uses those words — level, key, tier — rather than inventing a second set
for the same idea, and the rungs are the same six levels in the same order.

WHY ATHLETICS IS ON THE DIAGRAM AND NOT IN A FOOTNOTE. `fund_1301_cash_journal` is the
only transaction-level data in this archive: 277 postings from a records request, with the
posting source, the document number and, on half of them, the clerk's own comment. It is
the CONTROL CASE. Without it, "we cannot see what the money bought" reads as a statement
about municipal accounting in general. With it, the same sentence is a statement about
which report was run: the town produced this for one fund, so the bottom rungs are missing
rather than impossible — and rung 6 is the one place where that is not true, because no
report reaches it.

RULE 2. Not one figure is typed into the page. Every count and every amount below is
computed here, from the database, and the page renders what this writes.

RULE 7. A rung states what the records contain and what they do not. The `why` on each
rung is quoted from `money_gaps` / `money_edges` — the town's own gap register — wherever
one exists, rather than rewritten here into a second wording of the same reason. The join
onto those tables is ASSERTED: a gap register row that has been renamed would otherwise
silently produce a rung with no reason on it, which reads exactly like a rung that has no
reason to give.

RULE 11. Every figure here is an APPROPRIATION or a POSTED LEDGER AMOUNT. None of it is a
cost, and the ladder is about what can be FOLLOWED, not about what anything bought.
"""
import argparse
import json
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources/data/lunenburg.db')
OUT = os.path.join(ROOT, 'fy28/public/data/traceability.json')

# The two ledger snapshots this archive holds for FY2026, and what each one is. Period 12
# is the general fund at account level; period 9 is the only one that carries revenue.
# Named here rather than inside a query so that a rung cannot quietly change which report
# it is describing.
FY = 2026
P_ACCOUNTS = 12
P_REVENUE = 9

# The school department, as the town's chart of accounts codes it.
SCHOOL_DEPTS = ('300', '301')


def one(db, sql, *args):
    r = db.execute(sql, args).fetchone()
    return dict(r) if r else None


def gap_reason(db, what):
    """The `why` the gap register already carries for this question.

    A rung whose reason is missing is worse than a rung with no reason, because the shape
    on the page is identical to a rung whose reason is 'we did not look'. So a miss stops
    the build.
    """
    r = db.execute('SELECT why FROM money_gaps WHERE what = ?', (what,)).fetchone()
    if r is None:
        sys.exit(f'money_gaps has no row `{what}` — a rung on the traceability ladder '
                 f'quotes its reason from that table. The register was renamed, not '
                 f'emptied; update this script rather than dropping the reason.')
    return r['why']


def wanted(db, what):
    """The document `money_gaps` says would close this, with the half after ' — closes: '
    dropped: the page prints the document, and what it closes is the rung itself."""
    why = gap_reason(db, what)
    return dict(document=what, detail=why.split(' — closes: ')[0],
                closes=(why.split(' — closes: ')[1] if ' — closes: ' in why else None))


def edge_reason(db, source):
    r = db.execute('SELECT basis, why FROM money_edges WHERE source = ?', (source,)).fetchone()
    if r is None:
        sys.exit(f'money_edges has no row for source `{source}`, which the bottom rung of '
                 f'the traceability ladder is built on.')
    return dict(r)


def build():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row

    # ---------------------------------------------------------------- rung 1, budgeted
    lines = one(db, "SELECT COUNT(*) n FROM lps_budget_lines WHERE kind = 'line'")['n']
    if not lines:
        sys.exit('lps_budget_lines holds no lines — the district workbook join is empty, '
                 'which is not the same as a district that budgets nothing.')
    appropriated = one(db, """
        SELECT COUNT(*) accounts, SUM(original <> 0) with_appropriation,
               SUM(original) total
        FROM   ledger_snapshot WHERE fy = ? AND period = ?""", FY, P_ACCOUNTS)
    school = one(db, f"""
        SELECT COUNT(*) accounts, SUM(l.original) original, SUM(l.revised) revised,
               SUM(l.expended) expended, SUM(l.transfers <> 0) moved,
               SUM(ABS(l.transfers)) gross_moved
        FROM   ledger_snapshot l JOIN account a USING (account_id)
        WHERE  l.fy = ? AND l.period = ?
               AND a.dept IN ({','.join('?' * len(SCHOOL_DEPTS))})""",
              FY, P_ACCOUNTS, *SCHOOL_DEPTS)
    if not school['accounts']:
        sys.exit('no school-department accounts matched in the FY26 ledger. A join that '
                 'matches nothing looks exactly like a town that does not book the '
                 'schools.')

    # ---------------------------------------------------------------- rung 2, revenue
    revenue = one(db, """
        SELECT COUNT(*) accounts, COUNT(DISTINCT fund) funds, SUM(received) received
        FROM   v_revenue WHERE fy = ? AND period = ?""", FY, P_REVENUE)
    ch70 = one(db, """
        SELECT name, received FROM v_revenue
        WHERE fy = ? AND period = ? AND object = '450600'""", FY, P_REVENUE)
    if ch70 is None:
        sys.exit('the Chapter 70 revenue account (object 450600) is not in the FY26 '
                 'revenue ledger. The bottom rung rests on it.')
    gf_revenue = one(db, """
        SELECT SUM(received) received FROM v_revenue
        WHERE fy = ? AND period = ? AND fund = '0100'""", FY, P_REVENUE)
    years = one(db, 'SELECT MIN(fy) lo, MAX(fy) hi, COUNT(*) n FROM revenue_history')

    # ---------------------------------------------------------------- rung 3, spending
    spent = one(db, """
        SELECT COUNT(*) accounts, SUM(l.expended) expended,
               COUNT(DISTINCT a.dept) depts, COUNT(DISTINCT a.function) functions
        FROM   ledger_snapshot l JOIN account a USING (account_id)
        WHERE  l.fy = ? AND l.period = ?""", FY, P_ACCOUNTS)

    # ---------------------------------------------------------------- rung 4, transfers
    moved = one(db, """
        SELECT COUNT(*) accounts, SUM(transfers <> 0) moved, SUM(ABS(transfers)) gross
        FROM   ledger_snapshot WHERE fy = ? AND period = ?""", FY, P_ACCOUNTS)

    # ------------------------------------------------- rungs 5 and 6, and the control
    j = one(db, """
        SELECT COUNT(*) postings, COUNT(DISTINCT src) kinds,
               MIN(fy) lo, MAX(fy) hi,
               SUM(comments <> '') commented,
               SUM(vendor <> '') named,
               SUM(check_no <> '') numbered
        FROM   fund_1301_cash_journal""")
    if not j['postings']:
        sys.exit('fund_1301_cash_journal is empty. It is the control case for the whole '
                 'diagram; without it the ladder claims the bottom rungs are impossible '
                 'rather than unpublished.')
    kinds = [dict(src=r['src'], meaning=r['src_meaning'], postings=r['n']) for r in db.execute(
        """SELECT src, src_meaning, COUNT(*) n FROM fund_1301_cash_journal
           GROUP BY src, src_meaning ORDER BY n DESC""")]
    school_funds = one(db, """
        SELECT COUNT(DISTINCT fund) funds FROM school_special_revenue_fy26_q3""")['funds']
    impossible = edge_reason(db, 'Any general-fund revenue source')

    # ------------------------------------------------------------------- the six rungs
    # `state` is one of four, and they are the join map's four marks under its own names:
    # `answerable` = both sides supply the key and the join was run (its blue tick).
    # `partly`     = held for part of the question, and it says which part (its half circle).
    # `no`         = no report we hold answers it, and a document could (its red cross).
    # `never`      = no key exists on either side, and no document will ever make one
    #                (its grey cross). The difference between the last two is the whole
    #                point of the diagram and must never be collapsed into one colour.
    rungs = [
        dict(
            n=1, state='answerable', tier=1,
            question='What was budgeted, town and school',
            key='department · 300, 301',
            holds='The district prints a budget workbook; the town prints the same '
                  'department in its year-to-date ledger. Both sides supply the key, and '
                  'the join was run.',
            limit='A department total says nothing about which category, which school or '
                  'which fund paid.',
            figures=[
                dict(kind='count', value=lines,
                     label='budget lines in the district workbook'),
                dict(kind='count', value=appropriated['with_appropriation'],
                     label=f'town accounts carrying an FY{FY % 100} appropriation'),
                dict(kind='usd', value=school['original'],
                     label='appropriated to the school department, as the ledger opened'),
            ]),
        dict(
            n=2, state='answerable', tier=3,
            question='Where the revenue came from',
            key='revenue account · object 4xxxxx',
            holds='The town runs a revenue report by account. Every source it books is '
                  'named, budgeted and received on the same line.',
            limit='It says what arrived. It never says what any of it went on to pay '
                  'for — that is rung 6.',
            figures=[
                dict(kind='count', value=revenue['accounts'],
                     label=f'revenue accounts in the FY{FY % 100} ledger, across '
                           f"{revenue['funds']} funds"),
                dict(kind='usd', value=revenue['received'],
                     label='received, through the period this report covers'),
                dict(kind='usd', value=ch70['received'],
                     label='of it Chapter 70 school aid'),
            ]),
        dict(
            n=3, state='answerable', tier=3,
            question='What was spent, department by department and account by account',
            key='account number · 0100-S2055101-511001',
            holds='The year-to-date report run with totals off prints every account: what '
                  'was appropriated, what was spent, what is left.',
            limit='An account is a bucket, not a purchase. Two schools share a code and '
                  'the printed names truncate at ten characters.',
            figures=[
                dict(kind='count', value=spent['accounts'],
                     label=f"general-fund accounts, across {spent['depts']} departments"),
                dict(kind='count', value=school['accounts'],
                     label='of them in the school department'),
                dict(kind='usd', value=school['expended'],
                     label='spent against the school department accounts'),
            ]),
        dict(
            n=4, state='partly', tier=3,
            question='What money moved between accounts during the year',
            key='no key — the ledger prints a net, not a pair',
            holds='The ledger carries a transfers column, so the SIZE of the movement '
                  'into or out of an account is visible.',
            limit='Only the net. Nothing names the account the money came from, and no '
                  'budget document shows a transfer at all — they are approved during '
                  'the year, after the document was printed.',
            why=gap_reason(db, 'What the capital transfers bought'),
            why_of='What the capital transfers bought',
            figures=[
                dict(kind='count', value=moved['moved'],
                     label=f"of {moved['accounts']} accounts show a mid-year adjustment"),
                dict(kind='usd', value=moved['gross'],
                     label='moved in or out, added up without netting'),
                dict(kind='usd', value=school['gross_moved'],
                     label=f"of it across the school department's "
                           f"{school['moved']} adjusted accounts"),
            ]),
        dict(
            n=5, state='no', tier=None,
            question='What the money was spent ON — a vendor, a service, a person',
            key='check, warrant, journal',
            holds='Nothing, for the general fund. This is the tier we do not have.',
            limit='Held for exactly one fund, because exactly one was asked for and '
                  'produced. The report that would produce the rest is the one the town '
                  'already runs for the general fund.',
            why=gap_reason(db, 'What any special revenue fund bought'),
            why_of='What any special revenue fund bought',
            wanted=wanted(db, '`glytdbud-expense` for the special revenue funds'),
            control=dict(
                fund='1301', name='athletics revolving fund',
                postings=j['postings'], first_fy=j['lo'], last_fy=j['hi'],
                funds_like_it=school_funds,
                numbered=j['numbered'], named=j['named'], commented=j['commented'],
                kinds=kinds),
            figures=[
                dict(kind='count', value=j['postings'],
                     label='postings held, for the athletics fund alone'),
                dict(kind='ratio', value=1, of=school_funds,
                     label='school funds with any transaction detail'),
                dict(kind='count', value=spent['accounts'], zeroed=True,
                     label='general-fund accounts with none'),
            ]),
        dict(
            n=6, state='never', tier=None,
            question='Which revenue paid which expense',
            key='no key exists',
            holds='Both sides are complete and neither carries anything that ties them '
                  'together.',
            limit='This is the one rung a document cannot close. Money in the general '
                  'fund is fungible; the town apportions revenue across departments by '
                  'share when it presents a budget, and a share is a convention rather '
                  'than a flow.',
            why=impossible['why'],
            why_of='Any general-fund revenue source → Department 300',
            basis=impossible['basis'],
            wanted=wanted(db, 'The Town Manager’s revenue apportionment worksheet'),
            figures=[
                dict(kind='usd', value=ch70['received'],
                     label='of Chapter 70 lands in the general fund'),
                dict(kind='usd', value=gf_revenue['received'],
                     label='where it is indistinguishable from every other dollar in it'),
            ]),
    ]

    STATES = {'answerable': 'the archive answers it',
              'partly': 'answered in part, and it says which part',
              'no': 'no report we hold answers it — one exists and we do not have it',
              'never': 'no key exists on either side; no document can make one'}
    tally = [dict(state=s, label=STATES[s],
                  rungs=[r['n'] for r in rungs if r['state'] == s]) for s in STATES]

    return dict(
        generated_by='scripts/build_traceability_ladder.py',
        source='sources/data/lunenburg.db — ledger_snapshot, account, v_revenue, '
               'lps_budget_lines, fund_1301_cash_journal, '
               'school_special_revenue_fy26_q3, money_gaps, money_edges',
        vocabulary='notes/reference/data-model/join-map.html — levels of detail, the key '
                   'each turns on, and the tier we do not have',
        as_of=dict(fy=FY, accounts_period=P_ACCOUNTS, revenue_period=P_REVENUE,
                   revenue_history_from=years['lo'], revenue_history_to=years['hi']),
        headline=dict(
            answerable=len([r for r in rungs if r['state'] == 'answerable']),
            partly=len([r for r in rungs if r['state'] == 'partly']),
            unanswerable=len([r for r in rungs if r['state'] == 'no']),
            never=len([r for r in rungs if r['state'] == 'never']),
            rungs=len(rungs),
            control_fund='1301', control_postings=j['postings'],
            control_of_funds=school_funds),
        states=tally,
        rungs=rungs,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true',
                    help='fail if the published file is not what this would write')
    a = ap.parse_args()
    payload = json.dumps(build(), indent=1, sort_keys=True, ensure_ascii=False) + '\n'
    if a.check:
        have = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        if have != payload:
            print(f'STALE — {os.path.relpath(OUT, ROOT)} is not what the database now '
                  f'produces. Run scripts/build_traceability_ladder.py.')
            return 1
        print(f'ok — {os.path.relpath(OUT, ROOT)} reproduces from the database')
        return 0
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'w', encoding='utf-8').write(payload)
    d = json.loads(payload)
    h = d['headline']
    print(f"wrote {os.path.relpath(OUT, ROOT)} — {h['rungs']} rungs: "
          f"{h['answerable']} answerable, {h['partly']} in part, "
          f"{h['unanswerable']} unpublished, {h['never']} never; control case is "
          f"fund {h['control_fund']}, "
          f"{h['control_postings']} postings, 1 of {h['control_of_funds']} funds")
    return 0


if __name__ == '__main__':
    sys.exit(main())
