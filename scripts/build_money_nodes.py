#!/usr/bin/env python3
"""Every node in the school money graph — inputs and outputs — as a flat list.

    python3 scripts/build_money_nodes.py
    python3 scripts/build_money_nodes.py --check

Writes `notes/reference/MONEY-NODES.md`.

WHY A LIST BEFORE A DIAGRAM

Because we kept forgetting nodes, and a diagram makes an omission look like a complete
picture. Three were missed in a single afternoon:

  - the athletics revolving fund, because the town calls it `CHAPTER 658 REVOLVING FUND`
    and a filter on the word "school" or "athletic" does not match it;
  - nine grant funds, because they spent money in FY26 while booking no revenue in FY26,
    so a filter on revenue returns none of them;
  - school retiree health, because it is appropriated to `dept 914`, not to the schools.

Every one of those is real money and none of them was in the first diagram. So this file
comes first: the simplest possible format, one row per node, so a person can read down it
and say *"you have missed X"*.

THE THREE COLUMNS THAT MATTER

`basis` says what kind of claim the figure is:

  traced      a named account or fund in the town's ledger holds this exact figure
  partial     real, but this is not the whole of it -- a nine-month ledger, or one side
              of a two-sided flow
  unknown     the quantity exists and cannot be sized from anything published

Nothing is left out for being unknown. A node with no number is the most important kind
of row in this file, because it is the one a diagram would silently drop.

WHAT IS AN INPUT, AND WHY WRRS IS NOT ONE

An INPUT is money available to be spent on schools. An OUTPUT is money spent on them.

The pension assessment is not revenue the schools receive -- it is the town spending on
school employees, from the general fund, outside the school budget. So it is an output.
The same is true of school retiree health. They raise what the schools COST without
raising what the schools GET, which is precisely why they keep getting mislaid.
"""

import argparse
import os
import sqlite3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
OUT = os.path.join(ROOT, 'notes', 'reference', 'MONEY-NODES.md')

FY, P_DEPT, P_ACCT = 2026, 9, 12

# Funds the schools run. Listed by NUMBER, not matched on name, because the name is
# exactly what fails: fund 1301 is the athletics revolving fund and is called
# `CHAPTER 658 REVOLVING FUND`. Anything in these ranges that appears in the ledger and is
# not named here shows up in the "unclassified" check at the end rather than vanishing.
SCHOOL_FUND_PREFIXES = ('13', '15', '22', '26', '27', '28', '29')

# EDGES: which source pays which use. `basis` is the whole point of this table.
#
#   traced      we can see it. A named account or a report holds the connection.
#   restricted  near-certain, and NOT OBSERVED. A revolving fund exists for one purpose,
#               so the money almost certainly goes there -- but no report we hold shows
#               what the fund actually paid for. This is a presumption, not evidence.
#   unknown     the connection exists and cannot be sized or shown from anything published.
#   impossible  there is no such connection to find. Not missing data.
EDGES = [
    ('Any general-fund revenue source', 'Department 300', 'impossible',
     'Money in fund 0100 is fungible and no record ties a source to a department. The '
     'town apportions by share when presenting a budget; that is a convention, not a '
     'flow. **No further data will fix this.**'),
    ('Department 300 appropriation', 'Its 258 accounts, by function', 'traced',
     '`glytdbud-expense-fy2026-p12-gf-all` holds every account.'),
    ('Fund 1301 (athletics)', 'Athletics spending', 'restricted',
     'The fund is athletics — established from its cash journal. But **no expense report '
     'exists for special revenue funds**, so what it actually paid for is not observed. '
     'The general-fund athletics line (function 3510) is a separate, traced thing.'),
    ('Fund 2200 (school lunch)', 'Food service', 'restricted', 'Same gap.'),
    ('Fund 2640 (circuit breaker)', 'Special education', 'restricted',
     'Same gap — and see the assumption below about whether this is the same money as the '
     'general-fund `SCHCOSTREI` line.'),
    ('Fund 1312 / 1305 / 1306 / 1302 / 1300', 'Their own programmes', 'restricted',
     'Same gap.'),
    ('Fund 1308 (school choice)', '—', 'unknown',
     'School choice money is not restricted the way a programme revolving fund is. Where '
     'it is spent is not established here at all.'),
    ('Grant funds 26xx–29xx', 'The purpose of each grant', 'restricted',
     'Restricted by the grant award rather than by a town vote, and equally unobserved.'),
    ('Pension assessment (dept 820)', 'School staff', 'unknown',
     'The assessment covers town and school employees together. No published document '
     'gives the split.'),
    ('Dept 914 `SCHRETHLTH`', 'School retirees', 'traced',
     'The account name states it and it sits beside the town-retiree equivalent.'),
    ('State teachers’ pension system', 'District teaching staff', 'unknown',
     'Not appropriated by Lunenburg, not in our archive, and not sized anywhere here.'),
]

# ASSUMPTIONS currently load-bearing somewhere in this workstream. Each says plainly what
# would settle it. A row leaves this table only when a document arrives, never because it
# started to feel obvious.
ASSUMPTIONS = [
    ('A restricted fund’s spending goes to its own programme',
     'It is what the fund exists for, and a revolving fund is bound by the vote that '
     'created it.',
     'Every restricted edge above rests on this.',
     'An expense report for the special revenue funds.'),
    ('`SCHRESSTIP` is a school resource officer stipend',
     'Read from the abbreviation, in the police department.',
     'A $6,800 line. Immaterial, and still an inference.',
     'The account’s full name from MUNIS, which truncates at ten characters.'),
    ('The general-fund `SCHCOSTREI` line and fund 2640 are not the same money',
     'Nothing. They are similar magnitudes and we have not established either way.',
     '**If they are the same money, a total that counts both double-counts $318,424.**',
     'The town accountant, or a transfer record between the two.'),
    ('The district workbook total ties to the dept 300 appropriation',
     'They land 0.4% apart for FY2026.',
     'Used to argue the $26m is the town’s bill rather than a gross figure.',
     'Whether the 0.4% is netting or simply that `settled` holds 252 lines where '
     '`proposed` holds 321.'),
    ('The pension assessment includes school non-teaching staff',
     'Standard Massachusetts practice: teachers in the state system, other municipal '
     'employees in the county system. **Our archive does not say this.**',
     'The reason the pension is treated as a school cost at all.',
     'The WRRS annual actuarial valuation, which reports by member unit.'),
    ('MSBA reimbursement stopped because a bond reached term',
     'Nothing. It is a guess that fits.',
     'Explains $474,239 a year that arrived through FY2022 and is zero in FY2026.',
     'The town’s debt schedule, or the MSBA’s own payment record.'),
]

# CLASSIFICATION — reasoned per item, not matched on a substring.
#
# `how` records what the judgement rests on, because the judgement is the thing a reader
# should be able to disagree with:
#
#   stated      the town's own name says it outright
#   paired      the town's name pairs a code with a programme, so the code is defined by
#               the town rather than by us -- "FY26 #309 TITLE IV PART A" defines 309
#   neighbours  read from what it sits among in the same report. This is how `BUS CERTIF`
#               was caught: it sits with marriage licences, certified vitals, street lists,
#               genealogy and dog licences, so it is BUSINESS certificates, not buses
#   outside     it depends on knowing what a programme is, from outside this archive.
#               Flagged every time, because it is the weakest kind here
#   unresolved  ten characters is not enough and nothing else settles it
#
# Two of my own earlier errors are in here as `neighbours` rows. Both came from matching a
# substring instead of reading the column: BUS CERTIF and the TRANS* family.
FUND_CLASS = [
    ('0100', 'town',   'stated',    'The general fund.'),
    ('1300', 'school', 'stated',    'Lost books and technology — charged to students.'),
    ('1301', 'school', 'evidence',  'Its cash journal says CHAPTER 658 ATHLET and it '
                                    'refunds families by name.'),
    ('1302', 'school', 'outside',   'Adult education is run by the district in '
                                    'Massachusetts. Not stated here.'),
    ('1303', 'school', 'stated',    'Summer school.'),
    ('1305', 'school', 'stated',    'After school activities.'),
    ('1306', 'school', 'stated',    'Use of school facilities.'),
    ('1308', 'school', 'stated',    'School choice.'),
    ('1309', 'school', 'stated',    'Insurance recoveries, school.'),
    ('1310', 'unresolved', 'unresolved', '“Greenthumb” — a school garden programme or a '
                                    'town one. Nothing here says. No FY26 activity.'),
    ('1311', 'school', 'stated',    'School gifts.'),
    ('1312', 'school', 'stated',    'Extended day.'),
    ('1314', 'unresolved', 'unresolved', 'Vending machines — in a school or a town '
                                    'building. No FY26 activity.'),
    ('1315', 'unresolved', 'unresolved', '“Family Network” — plausibly the district’s '
                                    'family engagement work, plausibly the Council on '
                                    'Aging’s. No FY26 activity.'),
    ('1549', 'school', 'stated',    'Technology for school children.'),
    ('2200', 'school', 'stated',    'School lunch.'),
    ('2582', 'town',   'outside',   'EECBG is the federal Energy Efficiency and '
                                    'Conservation Block Grant, made to municipalities.'),
    ('2640', 'school', 'stated',    'Special education circuit breaker.'),
    ('2649', 'school', 'stated',    'Displaced students.'),
    ('2650', 'town',   'outside',   'Underground storage tanks — a public works and fire '
                                    'matter, not a school one.'),
    ('2681', 'school', 'stated',    'Comprehensive school health services.'),
    ('2667', 'unresolved', 'unresolved', 'Arts and cultural — the district or the Cultural '
                                    'Council. The #718 code is not paired with a '
                                    'programme name anywhere here.'),
    ('2709', 'unresolved', 'unresolved', '“Regional dissemination” #321, FY12. Dormant and '
                                    'undefined here.'),
    ('2903', 'unresolved', 'unresolved', 'A Blue Cross mini grant — school wellness or '
                                    'town employee wellness.'),
    ('2911', 'school', 'outside',   'Tech Prep is a federal vocational-education '
                                    'programme.'),
    ('2912', 'unresolved', 'unresolved', 'A Tufts University grant; “HEAT” is not expanded '
                                    'anywhere here.'),
    ('2914', 'school', 'outside',   'The Hach Scientific Foundation funds high-school '
                                    'chemistry teaching.'),
    ('2793', 'school', 'stated',    'School water improvement.'),
    ('2772', 'school', 'stated',    'School reopening.'),
    ('5000', 'town',   'stated',    'Sewer betterments.'),
    ('5100', 'town',   'stated',    'Water betterments.'),
    ('6000', 'town',   'stated',    'Sewer enterprise.'),
    ('6100', 'town',   'stated',    'Water enterprise.'),
    ('6200', 'town',   'stated',    'PEG access enterprise.'),
    ('7900', 'town',   'stated',    'Solid waste enterprise.'),
]

# Grant funds whose NAME pairs a numeric code with a federal or state programme. The town
# defines the code for us, so any other fund carrying the same code is the same programme
# — which is how the bare `#240` funds are read, and that step is marked `outside`.
GRANT_CODES = [
    ('#305', 'Title I', 'paired'),
    ('#140', 'Title II Part A', 'paired'),
    ('#309', 'Title IV Part A', 'paired'),
    ('#274', 'Special education programme improvement', 'paired'),
    ('#117', 'Student Opportunity Act, evidence-based', 'paired'),
    ('#237', 'Family and community engagement', 'paired'),
    ('#113 / #119', 'ESSER — federal pandemic relief for schools', 'paired'),
    ('#102', 'School reopening', 'paired'),
    ('#240', 'NOT paired anywhere in our data. Three funds carry a bare 240 and no name. '
             'Read as IDEA special education from outside knowledge — **flagged, because '
             'these are the two largest grant spends at $229,398 and $179,637**', 'outside'),
]

# Revenue accounts, reasoned. Only those that are plausibly school are listed; the point of
# the list is the ones that turned out NOT to be.
REV_CLASS = [
    ('CH 70 AID',  9229410, 'school', 'stated', 'Chapter 70 is the state education aid '
     'formula. Lands UNRESTRICTED in the general fund — a school-caused receipt, not '
     'school money.'),
    ('SCHCOSTREI',  318424, 'school', 'stated', 'School cost reimbursement — the circuit '
     'breaker. See the assumption about whether this duplicates fund 2640.'),
    ('SPED REIMB',   50000, 'school', 'stated', '**Missed in the first pass.** Special '
     'education reimbursement.'),
    ('CHARTER',      26136, 'school', 'outside', '**Missed in the first pass.** Charter '
     'school reimbursement — state aid to the town for resident pupils at charters.'),
    ('PS TUITION',   10000, 'school', 'stated', 'Pre-school tuition.'),
    ('MSBA REIMB',       0, 'school', 'stated', 'School building authority. $474,239 a '
     'year through FY2022, zero now.'),
    ('SCHOOL TRA',       0, 'school', 'stated', 'School transportation.'),
    ('STUDENTBUS',       0, 'school', 'stated', 'Student bus fees — and see the worked '
     'example. Charged, and zero here.'),
    ('ERATEREIMB',       0, 'school', 'outside', 'E-Rate is the federal telecoms discount '
     'for schools and libraries. Could be either.'),
    ('MIN TEACHE',       0, 'unresolved', 'unresolved', 'Ten characters. Nothing settles '
     'it.'),
    ('PROF DEV',         0, 'unresolved', 'unresolved', 'Professional development — for '
     'whose staff is not stated.'),
    ('SD ADM FEE',   35000, 'unresolved', 'unresolved', '“SD” is School Department or '
     'Sewer District, and both exist in this ledger.'),
    ('BUS CERTIF',    2000, 'town', 'neighbours', '**Not buses.** BUSINESS certificates. '
     'It sits among marriage licences, certified vitals, street lists, genealogy, dog '
     'licences and raffle permits — the Town Clerk’s fee schedule. *An error of mine, '
     'caught by reading the column instead of matching a substring.*'),
    ('TRANS ENT',   338397, 'town', 'neighbours', '**Not transportation.** A TRANSFER. It '
     'sits with `OP TRAN AG`, `OP TRAN CP`, `OP TRAN SR`, `OP TRAN TR` — the operating '
     'transfers. Same error, same cause.'),
    ('TRANSOFFSE',       0, 'town', 'neighbours', 'Transfer, as above.'),
    ('TRANSRECRE',       0, 'town', 'neighbours', 'Transfer, as above.'),
    ('BUS RENTAL',       0, 'unresolved', 'unresolved', 'Bus rental, or business rental. '
     'Zero in FY26 either way.'),
]

# A WORKED EXAMPLE, because the abstract version of this keeps being misunderstood.
# Transportation is the case TJ described and it turned out stranger than either of us
# expected. Held as data so the figures below are computed rather than typed.
WORKED = dict(
    title='Transportation — a fee that is charged, and cannot be followed anywhere',
    story=[
        'The district budgets transportation the way it budgets anything fee-funded: take '
        'the full cost, subtract what the fees are expected to bring in, and ask the town '
        'to appropriate the difference. **This is documented in the district’s own '
        'workbook**, in the comments column beside general education transportation: '
        '*"Does this reflect a reduction of $50K to accound for the money planned to come '
        'from the busing fees?"* — the people writing the budget, asking each other.',
        'So the appropriation is NET. The fees are supposed to pay the rest. To show that, '
        'you need three things: the fee schedule, the spending, and the fee revenue.',
        '**We have the first two and the third is missing.**',
    ],
    after=[
        'Bus fees are charged. The schedule is verified against the Superintendent’s May '
        '2025 email and the School Committee’s adoption of Bus Fee Policy 3601.01 on '
        '21 May 2025: $180 for a family with one student, $270 for two or more, $50 '
        'reduced, free for qualifying families. Grades 7–12 all charged; K–6 charged '
        'under two miles.',
        '**And the general-fund revenue account `STUDENTBUS` shows $0 budgeted and $0 '
        'received.** There is no transportation revolving fund in the town’s fund table '
        'either — the 13xx range holds athletics, lunch, extended day, adult education, '
        'facilities use, school choice, gifts, vending and greenthumb. No buses.',
        'So a fee that is charged by published policy has **no observable destination in '
        'any ledger we hold**. That is not the same as saying the money is unaccounted '
        'for — it is saying we cannot see it, which is a statement about our documents '
        'and not about the town’s books.',
        '**The meeting archive carries what the ledger does not.** Searching it for the '
        'contractor’s name — rule 15a, and TJ knew to look — produces the shape of the '
        'programme the accounts will not show:',
        '- *Transportation contract, School Committee 8 January 2025:* “Dr. Gilson '
        'supplied the bid with **Dee Bus**, it is a 3 year contract with tentative '
        'increases over the 3 years.” The vendor the $1.75M is paid to, and the term.\n'
        '- *Bus fee vote:* “a motion to vote on bus fees and send to policy subcommittee '
        'for setting rates… The rates would be **$180 for 1 child, $270 for 2 kids**.” '
        'Policy 3601.01 adopted 21 May 2025.\n'
        '- *Superintendent’s report, 4 June 2025:* “We have received **1,074 bus '
        'requests, and have 494 unpaid** at this time. We will send a list to Dee bus, so '
        'they can designate bus routes, **names will not be forwarded to Dee Bus unless '
        'or until the fee is paid**.”',
        '**That last quote is the closest thing to a measurement of this programme that '
        'exists anywhere.** It is a count of requests at one date, not of families and '
        'not of payments, so it does not yield a revenue figure — 1,074 requests could be '
        'far fewer families, and “unpaid at this time” in June says nothing about '
        'September. What it does establish is that the fee is administered, tracked, and '
        'enforced by withholding the route. This is real money moving through a programme '
        'whose receipts we cannot locate in any ledger.',
        'It also dates the fee. The policy was adopted **21 May 2025**, after the FY2026 '
        'budget was built — which is one ordinary explanation for `STUDENTBUS` being '
        'budgeted at zero, and explains nothing about it having received zero.',
        'Note what this does to the intuition. The natural guess is that the fees sit in '
        'a fund and pay bus bills directly, on top of the appropriation. That may be '
        'exactly right. It is also possible they land in the general fund and simply have '
        'not been booked yet. **Nothing we hold distinguishes those, and they imply very '
        'different things about who is paying for buses.**',
    ],
)

# The documents that would close the gaps, and what each one closes.
WANTED = [
    ('`glytdbud-expense` for the special revenue funds',
     'The identical report the town already runs for the general fund and for each of the '
     'four enterprise funds, pointed at funds 13xx/22xx/26xx–29xx instead.',
     'Turns **every restricted edge** above from presumption into traced fact — athletics, '
     'lunch, circuit breaker, extended day, and every grant.'),
    ('WRRS annual actuarial valuation, by member unit',
     'Published by the retirement system.',
     'Sizes the school share of the $2.39M pension assessment.'),
    ('The Town Manager’s revenue apportionment worksheet',
     'Seen once; we do not hold it.',
     'Documents the convention by which general-fund revenue is presented as split across '
     'departments. It cannot make the edge traceable — nothing can — but it makes the '
     'convention citable.'),
    ('DESE End of Year Financial Report',
     'Published by the state.',
     'Separates district spending by FUND, which is the one thing the town’s budget '
     'documents never show.'),
    ('Where bus fee receipts are booked',
     'A revenue account, a fund, or a statement that they are netted before booking.',
     'The fee schedule is published and verified; `STUDENTBUS` shows zero. **A charged '
     'fee with no observable destination** is the clearest single gap in this model.'),
    ('The period 13 ledger',
     'The year-end close.',
     'Reconciles FY2026 properly; period 12 is used for now.'),
]


import re


def function_names(c):
    """DESE function codes as the DISTRICT's own budget book names them."""
    out = {}
    for (label,) in c.execute("SELECT DISTINCT label FROM budget_line"):
        mm = re.match(r'^(\d{4})\s*[-–]\s*(.+)$', (label or '').strip())
        if mm and mm.group(1) not in out:
            out[mm.group(1)] = mm.group(2).strip()
    return out


def db():
    if not os.path.exists(DB):
        raise SystemExit(f'{DB} missing. Run: python3 scripts/build_db.py')
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def m(v):
    return f'{v:,.0f}' if v else '—'


def inputs(c):
    rows = []
    appr = c.execute(f"""SELECT l.original FROM ledger_snapshot l
                         WHERE l.fy={FY} AND l.period={P_DEPT}
                           AND l.account_id='0100-300'""").fetchone()[0]
    rows.append(dict(node='General fund appropriation, dept 300', v=appr, basis='traced',
                     where='`ledger_snapshot` 0100-300, as voted',
                     note='What Town Meeting voted. Funded from the pot, which no source '
                          'can be traced through.'))
    nonrec = c.execute(f"""SELECT l.original FROM ledger_snapshot l
                           WHERE l.fy={FY} AND l.period={P_DEPT}
                             AND l.account_id='0100-301'""").fetchone()
    if nonrec:
        rows.append(dict(node='General fund appropriation, dept 301 non-recurring',
                         v=nonrec[0], basis='traced', where='`ledger_snapshot` 0100-301',
                         note='A separate Town Meeting article.'))

    for r in c.execute(f"""SELECT fund, name, revenue FROM v_fund_year
                           WHERE fy={FY} AND period={P_DEPT} AND revenue > 0
                           ORDER BY revenue DESC"""):
        if not any(r['fund'].startswith(p) for p in SCHOOL_FUND_PREFIXES):
            continue
        note = ''
        if r['fund'] == '1301':
            note = ('**This is the athletics revolving fund.** Its journal comments read '
                    '`CHAPTER 658 ATHLET` and it refunds families by name. A filter on '
                    'the word "athletic" misses it entirely.')
        rows.append(dict(node=f'Fund {r["fund"]} — {r["name"].title()}', v=r['revenue'],
                         basis='partial', where='`v_fund_year`, nine months, ACTUAL',
                         note=note or 'Never enters the general fund. Actual, not budget.'))

    grants = c.execute(f"""SELECT COUNT(*) n, SUM(spent) v FROM v_fund_year
                           WHERE fy={FY} AND period={P_DEPT} AND spent > 0
                             AND (revenue IS NULL OR revenue = 0)""").fetchone()
    rows.append(dict(node=f'Grant funds spending with no FY26 revenue booked '
                          f'({grants["n"]} funds)', v=grants['v'], basis='partial',
                     where='`v_fund_year`, spent side only',
                     note='Federal and state grants — Title I/II/IV, IDEA (#240), Student '
                          'Opportunity Act. The money was received in an earlier year, so '
                          'a filter on revenue returns none of these. **The spending is '
                          'real school spending and none of it is in the $26m.**'))
    rows.append(dict(node='Teachers’ pensions, paid by the state', v=None, basis='unknown',
                     where='not appropriated by Lunenburg; not in our archive',
                     note='Massachusetts pays teacher pensions through the state system. '
                          'Real compensation for district staff that the town never votes '
                          'on, never appropriates, and cannot see.'))
    return rows


def outputs(c):
    rows = []
    # The district's budget book names 45 function codes; the ledger uses more than that.
    # For a code the book does not name, the ACCOUNTS INSIDE IT are shown instead — the
    # town's own words for the same money. Naming 2305 "Classroom Teachers" from the DESE
    # chart of accounts would be exactly the derived-quoted-as-observed failure this file
    # is built to avoid, and `HS TEACHER, MS TEACHER, ES TEACHER` tells a reader as much.
    names = function_names(c)
    for r in c.execute(f"""SELECT a.function f, SUM(l.original) v, COUNT(*) n
                           FROM ledger_snapshot l JOIN account a USING (account_id)
                           WHERE l.fy={FY} AND l.period={P_ACCT} AND a.dept='300'
                             AND a.function IS NOT NULL
                           GROUP BY a.function ORDER BY v DESC LIMIT 8"""):
        inside = [x[0] for x in c.execute(f"""
            SELECT a.name FROM ledger_snapshot l JOIN account a USING (account_id)
            WHERE l.fy={FY} AND l.period={P_ACCT} AND a.dept='300' AND a.function=?
            ORDER BY l.original DESC LIMIT 3""", (r['f'],))]
        label = names.get(r['f'])
        node = (f'{r["f"]} — {label}' if label else f'{r["f"]} — ' +
                ', '.join(x.strip() for x in inside if x))
        rows.append(dict(node=node, v=r['v'], basis='traced',
                         where=f'{r["n"]} account' + ('s' if r['n'] != 1 else ''),
                         note='' if label else
                              'The district’s budget book does not name this code, so the '
                              'largest accounts in it are shown instead of a name taken '
                              'from general knowledge.'))
    rest = c.execute(f"""SELECT SUM(l.original) v FROM ledger_snapshot l
                         JOIN account a USING (account_id)
                         WHERE l.fy={FY} AND l.period={P_ACCT} AND a.dept='300'""").fetchone()['v']
    top = sum(r['v'] for r in rows)
    rows.append(dict(node='All other functions inside dept 300', v=rest - top,
                     basis='traced', where='the remainder of the 258 accounts', note=''))

    for aid, label, note in [
        ('0100-19142-570018', 'School retiree health insurance — dept 914',
         'Spending on former school employees, appropriated outside the schools.'),
        ('0100-13102-532000', 'Monty Tech assessment — dept 310',
         'A different district. Town education spending, not Lunenburg Public Schools.'),
        ('0100-12101-519021', 'School resource stipend — dept 210',
         'Name is an abbreviation; the expansion is inferred.'),
    ]:
        r = c.execute(f"""SELECT l.original v FROM ledger_snapshot l
                          WHERE l.fy={FY} AND l.period={P_ACCT}
                            AND l.account_id=?""", (aid,)).fetchone()
        if r:
            rows.append(dict(node=label, v=r['v'], basis='traced',
                             where=f'`{aid}`', note=note))

    pens = c.execute(f"""SELECT l.original v FROM ledger_snapshot l
                         WHERE l.fy={FY} AND l.period={P_ACCT}
                           AND l.account_id='0100-18202-560001'""").fetchone()
    rows.append(dict(node='Pension (WRRS) attributable to school staff',
                     v=None, basis='unknown',
                     where=f'inside `0100-18202-560001`, total {m(pens["v"])}',
                     note='The assessment covers town and school employees together and '
                          'no published document gives the split. Teachers are not in it '
                          '— they are in the state system. WRRS publishes an annual '
                          'actuarial valuation by member unit; that is the document.'))

    spend = c.execute(f"""SELECT SUM(spent) v FROM v_fund_year
                          WHERE fy={FY} AND period={P_DEPT} AND spent > 0
                            AND (fund LIKE '13%' OR fund LIKE '22%' OR fund LIKE '26%'
                                 OR fund LIKE '27%' OR fund LIKE '28%')""").fetchone()
    rows.append(dict(node='Spending from the schools’ own funds and grants', v=spend['v'],
                     basis='partial', where='`v_fund_year`, nine months, ACTUAL',
                     note='Includes the grant funds above. Actual — never add to a budget.'))
    return rows


def render(c):
    ins, outs = inputs(c), outputs(c)
    L = []
    a = L.append
    a('# The school money graph — every node, inputs and outputs\n')
    a('**Generated by `scripts/build_money_nodes.py`. Do not edit.**\n')
    a('A flat list, on purpose. A diagram makes an omission look like a complete picture, '
      'and we kept losing nodes — the athletics fund because the town calls it '
      '`CHAPTER 658`, nine grant funds because they spend without booking revenue, school '
      'retiree health because it is appropriated to another department. Read down it and '
      'say what is missing.\n')
    a('`basis` — **traced**: a named account or fund holds this exact figure. '
      '**partial**: real, but not the whole of it (nine months, or one side of a '
      'two-sided flow). **unknown**: it exists and cannot be sized from anything '
      'published. *A row with no number is the most important kind here, because it is '
      'the one a diagram would silently drop.*\n')
    a('All figures FY2026. Appropriations are as voted; fund figures are actual through '
      'period 9 (31 March). **The two are on different bases and must never be added.**\n')

    a('\n## INPUTS — money available to be spent on the schools\n')
    a('| node | $ | basis | where |')
    a('|---|---:|---|---|')
    for r in ins:
        a(f'| {r["node"]} | {m(r["v"])} | {r["basis"]} | {r["where"]} |')
    a('')
    for r in ins:
        if r['note']:
            a(f'- **{r["node"]}** — {r["note"]}')

    a('\n## OUTPUTS — money spent on the schools\n')
    a('| node | $ | basis | where |')
    a('|---|---:|---|---|')
    for r in outs:
        a(f'| {r["node"]} | {m(r["v"])} | {r["basis"]} | {r["where"]} |')
    a('')
    for r in outs:
        if r['note']:
            a(f'- **{r["node"]}** — {r["note"]}')

    a(f'\n## Worked example — {WORKED["title"]}\n')
    for para in WORKED['story']:
        a(para + '\n')
    tr = c.execute(f"""SELECT a.account_id, a.name, l.original, l.expended
                       FROM ledger_snapshot l JOIN account a USING (account_id)
                       WHERE l.fy={FY} AND l.period={P_ACCT} AND a.dept='300'
                         AND (a.function='3300' OR a.name LIKE 'BUS %')
                       ORDER BY l.original DESC""").fetchall()
    a('| transportation account | voted | spent |')
    a('|---|---:|---:|')
    for r in tr:
        a(f'| `{r["account_id"]}` {r["name"].strip()} | {m(r["original"])} | '
          f'{m(r["expended"])} |')
    a(f'| **total** | **{m(sum(r["original"] for r in tr))}** | '
      f'**{m(sum(r["expended"] for r in tr))}** |')
    a('')
    for para in WORKED['after']:
        a(para + '\n')

    a('\n## What is SITTING in the funds — and the three patterns in it\n')
    a('“Spent” alone hides more than it shows. A fund that receives $325,970 and spends '
      '$4,005 is not a small programme; it is a reserve accumulating. Every fund below '
      'carries what moved **and what is left**, at 31 March.\n')
    rows = c.execute(f"""SELECT fund, name, revenue, spent, closing_balance
        FROM v_fund_year WHERE fy={FY} AND period={P_DEPT} AND (revenue>0 OR spent>0)
          AND (fund LIKE '13%' OR fund LIKE '15%' OR fund LIKE '22%' OR fund LIKE '26%'
               OR fund LIKE '27%' OR fund LIKE '28%' OR fund LIKE '29%')
        ORDER BY closing_balance DESC""").fetchall()
    a('| fund | | in | spent | held 31 Mar | net |')
    a('|---|---|---:|---:|---:|---:|')
    for r in rows:
        net = (r['revenue'] or 0) - (r['spent'] or 0)
        a(f'| `{r["fund"]}` | {r["name"].title()} | {m(r["revenue"])} | {m(r["spent"])} '
          f'| {m(r["closing_balance"])} | {net:+,.0f} |')
    tot = sum(r['closing_balance'] or 0 for r in rows)
    a(f'\n**{m(tot)} is sitting in the schools’ own funds at 31 March.**\n')
    a('**Pattern 1 — accumulating.** The circuit breaker took in $325,970, spent **$4,005**, '
      'and holds **$615,301** — nearly double the year’s receipts, so money has accumulated '
      'across years. *The reimbursement is arriving and largely not being spent out of this '
      'fund.* Why is not established: end-of-year timing, a carry-forward policy, or the '
      'costs being borne by the appropriation while the reserve builds all fit identically, '
      'and this project does not pick between explanations that fit equally.\n')
    a('**Pattern 2 — drawing down.** School lunch spends **$167,355 more than it receives** '
      'and holds $287,771. Extended day is the same shape at −$40,406. A fee-funded '
      'programme spending its balance is solvent this year and has a smaller cushion next '
      'year, and neither the appropriation nor the “spent” figure shows it.\n')
    a('**Pattern 3 — negative balances.** Several grant funds are **below zero** — FY26 #240 '
      'at −$179,637, FY25 117 SOA at −$91,220, FY25 #240 at −$88,503. Spending ahead of '
      'reimbursement is the ordinary explanation for a reimbursement-basis grant, and it is '
      'an *inference*: what is established is that the money went out and the receipt has '
      'not been booked.\n')
    a('*One caution on the circuit breaker.* Fund 2640 shows $325,970 received while the '
      'general-fund line `SCHCOSTREI` shows $318,424 budgeted and **nothing received**. Two '
      'circuit breaker figures about $7,500 apart, in two places. Whether they are the same '
      'money is **not established**, and if they are, a total counting both double-counts '
      'about $318,000.\n')

    a('\n## How money leaves a fund — three routes, and how to tell which was used\n')
    a('“Held” only means something once you know what the ways OUT are. There are three, '
      'and they are distinguishable:\n')
    a('| route | where it shows | for the circuit breaker, FY26 |')
    a('|---|---|---|')
    cb = c.execute(f"""SELECT * FROM fund_activity WHERE fund='2640' AND fy={FY}""").fetchone()
    sr = c.execute(f"""SELECT budgeted, received FROM v_revenue WHERE fy={FY}
                       AND name='OP TRAN SR'""").fetchone()
    a(f'| **Direct expenditure** | the fund’s own `expenditure` and `salaries` columns | '
      f'`expenditure` {m(cb["expenditure"])}, `salaries` {m(cb["salaries"])}, '
      f'`encumbered` {m(cb["encumbered"])} |')
    a(f'| **Transfer into the general fund** | the general-fund revenue account '
      f'`OP TRAN SR` — operating transfer from special revenue | **{m(sr["received"])} for '
      f'the WHOLE TOWN, every special revenue fund combined.** A tenth of what this one '
      f'fund holds, so it cannot have moved any material amount this way |')
    a('| **Offsetting the appropriation** | the district’s published budget offsets | '
      'The district publishes offsets for Extended Day, Facilities and Athletic and '
      '**none for the circuit breaker**. If it is used that way, no published number says '
      'so |')
    opening = ((cb['closing_balance'] or 0) - (cb['revenue'] or 0)
               + (cb['salaries'] or 0) + (cb['expenditure'] or 0))
    a(f'\n**So for FY2026 so far, it essentially has not come out.** The fund identity '
      f'recovers an opening balance the town’s report does not print:\n')
    a('```')
    a(f'opening balance   {opening:>10,.0f}   derived, not printed')
    a(f'+ revenue         {cb["revenue"]:>10,.0f}')
    a(f'- expenditure     {cb["expenditure"]:>10,.0f}')
    a(f'= closing balance {cb["closing_balance"]:>10,.0f}   ties exactly')
    a('```')
    a('\nIt began the year holding money, took in more than it spent by a factor of '
      'eighty, and is sitting on the result. **The diagram showing “spent $4,005 · held '
      '$615,301” is therefore correct**, and the “spent” figure on its own would have been '
      'close to a lie.\n')
    a('*Two things this does NOT establish.* Whether it is normal: we hold one period of '
      'one year, and a fund that spends at year end looks exactly like this on 31 March — '
      'the period 13 report would settle it. And whether `SCHCOSTREI` is the same money: '
      'the general fund shows $318,424 budgeted and **nothing received** against this '
      'fund’s $325,970 received. Two circuit breaker figures of similar size, one received '
      'and one not.\n')

    a('\n## EDGES — which source pays which use, and whether we can show it\n')
    a('The important column is `basis`. **`restricted` means we cannot show it** — the '
      'connection is near-certain because the fund exists for one purpose, but no report '
      'we hold says what the fund actually paid for. It is a presumption, and it is '
      'listed as one.\n')
    a('| source | use | basis | why |')
    a('|---|---|---|---|')
    for src, use, basis, why in EDGES:
        a(f'| {src} | {use} | **{basis}** | {why} |')
    a('\n**The traceability runs backwards from what anyone expects.** The general fund '
      'is $26.2M with an *unknown source* and a *fully traced use* — 258 named accounts. '
      'The restricted funds are $1.7M with a *fully known source* and an *untraced use*. '
      'Neither has both ends, and the big one is missing the end people ask about.\n')

    a('\n## ASSUMPTIONS in use, and what would settle each\n')
    a('Everything here is currently load-bearing somewhere. A row leaves this table when '
      'a document arrives — never because it started to feel obvious.\n')
    for what, ev, where, settle in ASSUMPTIONS:
        a(f'\n**{what}**\n')
        a(f'- *Evidence:* {ev}')
        a(f'- *What rests on it:* {where}')
        a(f'- *Settled by:* {settle}')
    a('')

    a('\n## The documents that would close the gaps\n')
    a('| document | what it is | what it closes |')
    a('|---|---|---|')
    for doc, what, closes in WANTED:
        a(f'| {doc} | {what} | {closes} |')

    a('\n## CLASSIFICATION — reasoned per item, not matched on a substring\n')
    a('`how` says what the judgement rests on, because that is the part worth arguing '
      'with. **`outside`** means it depends on knowing what a programme is from beyond '
      'this archive — the weakest kind here, and flagged every time.\n')

    a('### Funds\n')
    a('| fund | name | class | how | why |')
    a('|---|---|---|---|---|')
    named = {f for f, *_ in FUND_CLASS}
    fn = {r[0]: r[1] for r in c.execute('SELECT fund, name FROM fund')}
    for f, cls, how, why in FUND_CLASS:
        a(f'| `{f}` | {fn.get(f, "")} | **{cls}** | {how} | {why} |')
    rest = [f for f in sorted(fn) if f not in named]
    a(f'\nThe remaining **{len(rest)}** funds are dated federal and state grant shells '
      f'whose names pair a code with a programme. They are classified by that code:\n')
    a('| code | programme | how |')
    a('|---|---|---|')
    for code, prog, how in GRANT_CODES:
        a(f'| `{code}` | {prog} | {how} |')

    a('\n### Revenue accounts\n')
    a('Only the plausibly-school ones are listed. **The point of the list is the ones that '
      'turned out not to be.**\n')
    a('| account | FY26 | class | how | why |')
    a('|---|---:|---|---|---|')
    for name, v, cls, how, why in REV_CLASS:
        a(f'| `{name}` | {m(v)} | **{cls}** | {how} | {why} |')
    a('\n**Ten characters is why two of these were wrong.** `BUS` truncates both BUS and '
      'BUSINESS; `TRANS` truncates both TRANSPORTATION and TRANSFER. Neither can be read '
      'from the name — only from what the account sits among. This is `LEDGER-STRUCTURE.md` '
      'rule one, restated by breaking it.\n')

    a('\n## What is deliberately NOT a node\n')
    a('- **Chapter 70, and every other general-fund revenue line.** They are inputs to the '
      'TOWN, not to the schools. They land in fund 0100 and lose their identity; the '
      'appropriation is the only edge out of it that anyone can follow. Listing Chapter 70 '
      'as a school input would assert a connection no record supports.\n')
    a('- **The pension assessment and school retiree health as INPUTS.** They are money the '
      'town spends on school employees, not money the schools receive. They raise what the '
      'schools COST without raising what the schools GET, which is why they keep being '
      'mislaid on the wrong side.\n')

    a('\n## Known holes in this list\n')
    a('- Fund figures are **nine months**; the year is twelve. Nothing here is a year.\n')
    a('- Grant funds show spending with **no revenue booked in FY26**, so the input side of '
      'those grants is not sized here at all — only what went out.\n')
    a('- The athletics figure from the town ledger and the figure in the district’s own '
      'athletics documents **do not agree**, and they are on different bases and periods. '
      'Neither is wrong; they answer different questions.\n')
    a('- Anything the town holds under a name that does not say school, and that is not in '
      'a fund range listed in the script, is invisible to this file. `CHAPTER 658` is the '
      'proof that this happens.\n')
    return '\n'.join(L) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    c = db()
    fresh = render(c)
    rel = os.path.relpath(OUT, ROOT)
    if args.check:
        if not os.path.exists(OUT):
            raise SystemExit(f'{rel} does not exist. Run without --check.')
        if open(OUT, encoding='utf-8').read() != fresh:
            raise SystemExit(f'STALE: {rel} no longer reproduces.\n'
                             f'  Run: python3 scripts/build_money_nodes.py')
        print(f'ok: {rel} still reproduces')
        return
    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write(fresh)
    print(f'wrote {rel} ({len(fresh):,} bytes)')


if __name__ == '__main__':
    main()
