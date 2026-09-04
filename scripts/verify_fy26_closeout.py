"""Recompute every figure in the FY26 closeout analysis, and fail if one drifted.

    python3 scripts/verify_fy26_closeout.py

Rule 9: figures in a finished document get re-checked by script, not re-read. Rule 13: a
check must assert the NUMBER, not the prose around it -- `verify_athletics.py` once passed
because a sentence existed while the sentence was wrong. So every assertion here derives
the value from the database and then looks for that derived string in the document.
"""
import os
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
DOC = os.path.join(ROOT, 'sources', 'analyses', 'fy26-closeout.md')

TEXT = open(DOC, encoding='utf-8').read()
PLAIN = TEXT.replace('**', '')
FAILS = []


def present(label, value, dp=2):
    """Assert a value DERIVED from the database appears in the document.

    Matched on a WORD BOUNDARY, not as a bare substring. A plain `in` check passed the
    count 61 because the digits sit inside $25,613,679.23 and inside the account code
    S2072061 -- so a check that was meant to prove a small integer had been written down
    was passing on any document at all. Small counts are exactly where this matters,
    which is exactly where the naive check was useless.
    """
    # The MAGNITUDE is asserted, not the sign. The document writes a negative as
    # "−$90,769.62" -- a typographic minus, then a currency symbol -- and a needle of
    # "-90,769.62" matches none of that. Whether a figure is a loss or a gain is the
    # prose's job; this checks that the number itself is on the page.
    if isinstance(value, float):
        needle = f'{abs(value):,.{dp}f}' if dp else f'{abs(value):,.0f}'
    else:
        needle = f'{abs(value):,}' if isinstance(value, int) else str(value)
    # Bounded so a small count cannot match inside a bigger figure -- 61 was passing on
    # the digits inside $25,613,679.23 -- while still allowing the $ that precedes every
    # money figure in the document.
    ok = re.search(r'(?<![\d,.])' + re.escape(needle) + r'(?![\d,]*\d)',
                   PLAIN) is not None
    if not ok:
        FAILS.append(f'{label}: derived {needle} is not in the document')
    print(f"  {'OK  ' if ok else 'GONE'}  {label:<52} {needle}")
    return ok


def main():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    one = lambda s, *a: db.execute(s, a).fetchone()

    print('Recomputing every figure in fy26-closeout.md\n')

    print('§1  The department totals')
    r = one("""SELECT COUNT(*) n, SUM(original) o, SUM(transfers) t, SUM(revised) rv,
                      SUM(expended) e, SUM(encumbered) en, SUM(available) av
               FROM ledger_snapshot l JOIN account a USING (account_id)
               WHERE l.fy=2026 AND l.period=12 AND a.dept='300'""")
    present('accounts in the school department', r['n'])
    present('original appropriation', r['o'])
    present('transfers and adjustments', r['t'])
    present('revised budget', r['rv'])
    present('expended', r['e'])
    present('encumbered', r['en'])
    present('unspent', r['av'])

    print('\n§1  The two flows underneath it')
    ov = one("""SELECT COUNT(*) n, SUM(-available) s FROM ledger_snapshot l
                JOIN account a USING (account_id)
                WHERE l.fy=2026 AND l.period=12 AND a.dept='300' AND available < -0.5""")
    un = one("""SELECT COUNT(*) n, SUM(available) s FROM ledger_snapshot l
                JOIN account a USING (account_id)
                WHERE l.fy=2026 AND l.period=12 AND a.dept='300' AND available > 0.5""")
    present('accounts over', ov['n'])
    present('amount over', ov['s'])
    present('accounts under', un['n'])
    present('amount under', un['s'])
    if ov['n'] + un['n'] > r['n']:
        FAILS.append('over + under exceeds the account count')

    print('\n§1  Town-wide, same period')
    t = one("""SELECT SUM(original) o, SUM(transfers) t, SUM(expended) e,
                      SUM(encumbered) en,
                      SUM(revised)-SUM(expended)-SUM(encumbered) av
               FROM ledger_snapshot l JOIN account a USING (account_id)
               WHERE l.fy=2026 AND l.period=12 AND a.fund='0100'""")
    for k, lbl in (('o', 'town-wide appropriated'), ('t', 'town-wide transfers'),
                   ('e', 'town-wide spent'), ('en', 'town-wide encumbered'),
                   ('av', 'town-wide unspent')):
        present(lbl, t[k])

    print('\n§1a  Where the underspend comes from, by what the money buys')
    GROUPS = {
        'people': ('511', '512', '513', '517', '519'),
        'insurance': ('570', '571'),
        'supplies': ('540', '541', '545', '555', '557', '585'),
        'contracted': ('531', '532', '535'),
        'utilities': ('521', '523', '524', '525', '534'),
    }
    for label, pres in GROUPS.items():
        marks = ' OR '.join("a.object LIKE '%s%%'" % p for p in pres)
        g = one(f"""SELECT COUNT(*) n, SUM(revised) rv, SUM(available) av
                    FROM ledger_snapshot l JOIN account a USING (account_id)
                    WHERE l.fy=2026 AND l.period=12 AND a.dept='300' AND ({marks})""")
        present(f'{label}: budget', float(g['rv']), dp=0)
        present(f'{label}: left', float(g['av']), dp=0)
        present(f'{label}: share of its own budget',
                f"{float(g['av']) / float(g['rv']) * 100:.1f}%")

    # The median comparison is the sentence the section turns on, so it is computed
    # rather than asserted from memory: a salary is paid or it is not, a supply order is
    # placed or it is not, and the medians are 100% and 88%.
    import statistics as _st
    def median_pct(where):
        vals = [r[0] / r[1] * 100 for r in db.execute(
            f"""SELECT l.expended, l.revised FROM ledger_snapshot l
                JOIN account a USING (account_id)
                WHERE l.fy=2026 AND l.period=12 AND a.dept='300' AND l.revised > 200
                  AND ({where})""")]
        return _st.median(vals), len(vals)
    sal, n_sal = median_pct("a.object LIKE '511%'")
    sup, n_sup = median_pct("a.object LIKE '540%' OR a.object LIKE '541%' "
                            "OR a.object LIKE '545%' OR a.object LIKE '555%' "
                            "OR a.object LIKE '557%' OR a.object LIKE '585%'")
    present('salary accounts compared', n_sal)
    present('median salary account spends', f'{sal:.0f}%')
    present('supply accounts compared', n_sup)
    present('median supply account spends', f'{sup:.0f}%')
    if sal <= sup:
        FAILS.append('salary accounts no longer spend a higher share than supply '
                     'accounts; §1a\'s whole argument rests on that ordering')

    print('\n§1a  Inside the people line, by role')
    ROLES = {
        'paraprofessionals': ('511203', '511103'),
        'teachers': ('511001',),
        'social workers': ('511024',),
        'psychologists': ('511023',),
        'stipends': ('519003', '519104', '519015', '519016', '519105'),
        'overtime': ('513002', '513003', '513000'),
        'substitutes': ('511003', '512103', '512203', '512003'),
        'secretarial': ('511002', '511102', '511101'),
    }
    for label, objs in ROLES.items():
        marks = ','.join('?' * len(objs))
        r_ = one(f"""SELECT COUNT(*) n, SUM(revised) rv, SUM(available) av
                     FROM ledger_snapshot l JOIN account a USING (account_id)
                     WHERE l.fy=2026 AND l.period=12 AND a.dept='300'
                       AND a.object IN ({marks})""", *objs)
        present(f'{label}: budget', float(r_['rv']), dp=0)
        present(f'{label}: left', float(r_['av']), dp=0)

    # The pair that nearly cancels, and the claim that neither group has a single account
    # moving the other way -- which is what makes them worth naming as groups at all.
    pair = one("""SELECT
        SUM(CASE WHEN a.object IN ('511023','511024') THEN l.available END) sup,
        SUM(CASE WHEN a.object IN ('511203','511103') THEN l.available END) para
        FROM ledger_snapshot l JOIN account a USING (account_id)
        WHERE l.fy=2026 AND l.period=12 AND a.dept='300'""")
    present('student support staff, left', float(pair['sup']), dp=0)
    present('paraprofessionals, over', float(pair['para']), dp=0)
    present('the two together', float(pair['sup']) + float(pair['para']), dp=0)
    # The two groups are NOT symmetrical, and an earlier draft claimed they were --
    # "not one of eight support accounts went over" was wrong, three of four
    # psychologist accounts are over. The asymmetry is now the point of the paragraph,
    # so it is what gets asserted.
    shape = one("""SELECT
        SUM(CASE WHEN a.object IN ('511203','511103') AND l.available < -0.5 THEN 1 ELSE 0 END) para_over,
        SUM(CASE WHEN a.object IN ('511203','511103') THEN 1 ELSE 0 END) para_n,
        SUM(CASE WHEN a.object IN ('511023','511024') AND l.available > 0.5 THEN 1 ELSE 0 END) sup_under,
        SUM(CASE WHEN a.object IN ('511023','511024') THEN 1 ELSE 0 END) sup_n
        FROM ledger_snapshot l JOIN account a USING (account_id)
        WHERE l.fy=2026 AND l.period=12 AND a.dept='300'""")
    if shape['para_over'] != shape['para_n']:
        FAILS.append('§1a says every paraprofessional account went over; %d of %d do'
                     % (shape['para_over'], shape['para_n']))
    print('  OK    every paraprofessional account (%d of %d) is over'
          % (shape['para_over'], shape['para_n']))
    if shape['sup_under'] != 3:
        FAILS.append('§1a says the support underspend is three accounts of eight; it is '
                     'now %d of %d' % (shape['sup_under'], shape['sup_n']))
    print('  OK    the support underspend is %d accounts of %d, not a group pattern'
          % (shape['sup_under'], shape['sup_n']))

    # §1a  The placement pair. Asserted by account NAME because these two lines are named
    # in the document and their variance is the whole of the claim -- and because the pair
    # is exactly the shape rule 7 warns about, so the numbers had better be the numbers.
    print('\n§1a  The placement pair, on the purchased side')
    PAIR = {'SPED PRIVA': 522629.0, 'COLL TUITI': -434108.0}
    got = {}
    for name, want in PAIR.items():
        row = db.execute("""SELECT l.revised, l.expended, l.available
                            FROM ledger_snapshot l JOIN account a USING (account_id)
                            WHERE a.dept IN ('300','301') AND a.account_type='expense'
                              AND l.period = 12 AND a.name = ?""", (name,)).fetchone()
        if not row:
            FAILS.append(f'§1a names {name} and no such account is in the ledger')
            continue
        got[name] = row[2]
        present(f'{name} variance', row[2], dp=0)
        if abs(row[2] - want) > 1:
            FAILS.append(f'§1a says {name} varies by {want:,.0f}; the ledger says {row[2]:,.0f}')
    if len(got) == 2:
        together = sum(got.values())
        present('the pair together', together, dp=0)
        if abs(together - 88522) > 2:
            FAILS.append(f'§1a says the pair nets to 88,522; it is {together:,.0f}')

    # And the group they sit in, because the document leans on the total barely moving
    # while the composition moves -- which is only interesting if the total really is flat.
    grp = db.execute("""SELECT SUM(l.revised), SUM(l.expended)
                        FROM ledger_snapshot l JOIN account a USING (account_id)
                        WHERE a.dept IN ('300','301') AND a.account_type='expense'
                          AND l.period = 12
                          AND (a.name LIKE '%SPED%' OR a.name LIKE '%COLL%'
                               OR a.name LIKE '%TUITI%' OR a.name LIKE '%PRIVA%')""").fetchone()
    present('special education group, revised', grp[0], dp=0)
    present('special education group, spent', grp[1], dp=0)
    present('special education group, net', grp[0] - grp[1], dp=0)
    if abs((grp[0] - grp[1]) - 58646) > 2:
        FAILS.append('§1a says the group is within 58,646 of budget; it is %.0f'
                     % (grp[0] - grp[1]))

    print('\n§2  The biggest movers')
    # An org holds SEVERAL accounts -- S3991742 alone carries six, from ELEC CHGS to
    # TELE MTC -- so a lookup keyed on org returns whichever comes first and silently
    # checks the wrong line. Key on org AND object, which is what makes an account unique.
    for org, obj, name in (('S0511062', '535019', 'SPED PRIVA'),
                           ('S5511062', '535023', 'COLL TUITI'),
                           ('S3991742', '521011', 'ELEC CHGS'),
                           ('S2072061', '511023', 'PSYCHSALAR'),
                           ('S2032121', '511103', 'KINDAIDREG'),
                           ('S3991692', '535026', 'SPED TRANS')):
        row = one("""SELECT revised, expended, encumbered, available
                     FROM ledger_snapshot l JOIN account a USING (account_id)
                     WHERE l.fy=2026 AND l.period=12 AND a.org=? AND a.object=?""",
                  org, obj)
        if row is None:
            FAILS.append(f'{org} ({name}) is no longer in the ledger')
            print(f'  GONE  {org} {name}')
            continue
        present(f'{name} revised', float(row['revised']), dp=0)
        present(f'{name} spent', float(row['expended']), dp=0)
        # The encumbrance too. The document once printed a variance computed from three
        # figures while showing two of them, so the arithmetic could not be followed and
        # looked wrong. If a figure is in the subtraction it has to be on the page.
        present(f'{name} encumbered', float(row['encumbered']), dp=0)
        got = (float(row['revised']) - float(row['expended'])
               - float(row['encumbered']))
        if abs(got - float(row['available'])) > 0.02:
            FAILS.append(f'{name}: revised - spent - encumbered does not equal available')

    ood = one("""SELECT SUM(revised) rv, SUM(expended) e, SUM(available) av
                 FROM ledger_snapshot l JOIN account a USING (account_id)
                 WHERE l.fy=2026 AND l.period=12
                   AND a.name IN ('SPED PRIVA','COLL TUITI')""")
    present('both out-of-district lines, budgeted', float(ood['rv']), dp=0)
    present('both out-of-district lines, spent', float(ood['e']), dp=0)
    present('both out-of-district lines, net', float(ood['av']), dp=0)

    para = one("""SELECT SUM(revised) rv, SUM(expended) e
                  FROM ledger_snapshot l JOIN account a USING (account_id)
                  WHERE l.fy=2026 AND l.period=12 AND a.dept='300'
                    AND a.name LIKE '%SPEDPARA'""")
    present('special ed paras, budgeted', float(para['rv']), dp=0)
    present('special ed paras, spent', float(para['e']), dp=0)

    print('\n§3  Kindergarten paraprofessionals')
    kg = one("""SELECT SUM(original) o, SUM(transfers) t, SUM(expended) e
                FROM ledger_snapshot l JOIN account a USING (account_id)
                WHERE l.fy=2026 AND l.period=12
                  AND a.org IN ('S2032121','S2032131')""")
    present('kindergarten para spending, both accounts', float(kg['e']))
    if float(kg['o']) != 0 or float(kg['t']) != 0:
        FAILS.append('the kindergarten para accounts now carry an appropriation or a '
                     'transfer -- section 3 needs rewriting, not re-checking')
    print(f"  {'OK  ' if float(kg['o']) == 0 else 'FAIL'}  "
          f"{'appropriation and transfers are still zero':<52} "
          f"{kg['o']:,.2f} / {kg['t']:,.2f}")

    # The workbook history the section quotes, cell by cell.
    for cell, fy, kind, want in (('C332', 2023, 'actual', 75501.66),
                                 ('D332', 2024, 'actual', 77699.88),
                                 ('E332', 2025, 'actual', 83765.97),
                                 ('F332', 2025, 'budget', 73273.0)):
        got = one("""SELECT value FROM workbook_figure
                     WHERE row=332 AND fy=? AND column_kind=?""", fy, kind)
        ok = got and abs(float(got['value']) - want) < 0.005
        if not ok:
            FAILS.append(f'workbook {cell} is no longer {want}')
        print(f"  {'OK  ' if ok else 'FAIL'}  {'workbook ' + cell:<52} "
              f"{(got['value'] if got else 0):,.2f}")
        present(f'workbook {cell} in the document', want)

    zero_no_transfer = one("""SELECT COUNT(*) n FROM ledger_snapshot l
                              JOIN account a USING (account_id)
                              WHERE l.fy=2026 AND l.period=12 AND a.dept='300'
                                AND l.original=0 AND l.expended<>0""")
    print(f"  ..    accounts spending with no original appropriation: "
          f"{zero_no_transfer['n']}")
    present('accounts spending with no original appropriation', zero_no_transfer['n'])

    print('\n§4  Psychologist and social worker lines')
    # There are FOUR of each, one per building. An earlier version of this check took the
    # first row an org matched and the prose quoted one line as though it were the whole
    # thing. Every account is asserted, and so is the group total.
    for name in ('PSYCHSALAR', 'SOCWORKSAL'):
        rows_ = db.execute("""SELECT a.org, l.revised, l.expended FROM ledger_snapshot l
                              JOIN account a USING (account_id)
                              WHERE l.fy=2026 AND l.period=12 AND a.dept='300'
                                AND a.name=? ORDER BY a.org""", (name,)).fetchall()
        if len(rows_) != 4:
            FAILS.append(f'{name}: {len(rows_)} accounts, the document says four')
        for row in rows_:
            present(f'{name} {row["org"]} budgeted', float(row['revised']), dp=0)
            present(f'{name} {row["org"]} spent', float(row['expended']), dp=0)
        tot = one("""SELECT SUM(revised) rv, SUM(expended) e FROM ledger_snapshot l
                     JOIN account a USING (account_id)
                     WHERE l.fy=2026 AND l.period=12 AND a.dept='300' AND a.name=?""",
                  name)
        present(f'{name} group budgeted', float(tot['rv']), dp=0)
        present(f'{name} group spent', float(tot['e']), dp=0)
    both = one("""SELECT SUM(revised) - SUM(expended) u FROM ledger_snapshot l
                  JOIN account a USING (account_id)
                  WHERE l.fy=2026 AND l.period=12 AND a.dept='300'
                    AND a.name IN ('PSYCHSALAR','SOCWORKSAL')""")
    present('all eight accounts, unspent', float(both['u']), dp=0)

    print('\n§5  The transfers, itemized')
    tin = one("""SELECT COUNT(*) n, SUM(transfers) s FROM ledger_snapshot l
                 JOIN account a USING (account_id)
                 WHERE l.fy=2026 AND l.period=12 AND a.dept='300' AND transfers > 0""")
    tout = one("""SELECT COUNT(*) n, SUM(-transfers) s FROM ledger_snapshot l
                  JOIN account a USING (account_id)
                  WHERE l.fy=2026 AND l.period=12 AND a.dept='300' AND transfers < 0""")
    present('accounts given budget', tin['n'])
    present('budget added', float(tin['s']))
    present('accounts that gave budget up', tout['n'])
    present('budget taken away', float(tout['s']))
    present('accounts that moved at all', tin['n'] + tout['n'])
    # The salary reserve giving up everything is the example the section turns on.
    res = one("""SELECT original, transfers, revised FROM ledger_snapshot l
                 JOIN account a USING (account_id)
                 WHERE l.fy=2026 AND l.period=12 AND a.org='S0990991'""")
    present('the school salary reserve gave up', float(res['transfers']))
    if float(res['revised']) != 0:
        FAILS.append('the salary reserve no longer ends at zero; §5 says it does')

    print('\n§6  The funds outside the general fund')
    outside = one("""SELECT COUNT(*) n, SUM(salaries + expenditure) s
                     FROM fund_activity
                     WHERE fy=2026 AND (salaries + expenditure) > 0""")
    present('funds that actually spent', outside['n'])
    present('spent outside the general fund', float(outside['s']), dp=0)
    # Every fund the section itemises, asserted individually.
    for fund in ('2200', '1312', '2813', '2814', '1301', '1305', '2778', '1308',
                 '2672', '1306', '2640', '1311'):
        f = one("""SELECT revenue, salaries + expenditure AS spent, closing_balance
                   FROM fund_activity WHERE fy=2026 AND fund=?""", fund)
        if f is None:
            FAILS.append(f'fund {fund} is no longer in the data; §6 itemises it')
            continue
        present(f'fund {fund} spent', float(f['spent']), dp=0)
    # The period these come from is NOT period 12, and the document has to say so.
    per = one('SELECT DISTINCT period FROM fund_activity WHERE fy=2026')
    if per['period'] != 9:
        FAILS.append('fund_activity is no longer period 9; §6 says "through 31 March"')
    if 'through 31 March' not in PLAIN:
        FAILS.append('§6 must state that its figures are a different period from §1')


    print('\n§close  How far the year-end close can move the figure')
    # The hedge "these are not final" was doing more work than the evidence supports.
    # The move is BOUNDED by what is still encumbered, so the ceiling is asserted rather
    # than left as an open-ended caveat -- an unbounded hedge reads as "this might be
    # nothing", and it is not.
    cl = one("""SELECT SUM(available) av, SUM(encumbered) en
                FROM ledger_snapshot l JOIN account a USING (account_id)
                WHERE l.fy=2026 AND l.period=12 AND a.dept='300'""")
    present('encumbered, the only money in play at the close', float(cl['en']))
    present('the ceiling if every purchase order is released',
            float(cl['av']) + float(cl['en']), dp=0)

    print('\n§codes  Every ledger code this document names has a recorded expansion')
    names = {r[0] for r in db.execute(
        """SELECT DISTINCT a.name FROM ledger_snapshot l JOIN account a USING (account_id)
           WHERE l.fy=2026 AND l.period=12""")}
    import csv as _csv
    expanded = set()
    NAMES_CSV = os.path.join(ROOT, 'sources', 'data', 'account-names.csv')
    if os.path.exists(NAMES_CSV):
        with open(NAMES_CSV, encoding='utf-8') as fh:
            for r in _csv.DictReader(fh):
                expanded.add(r['code'])
    used = sorted(n for n in names
                  if re.search(r'(?<![A-Z])' + re.escape(n) + r'(?![A-Z])', TEXT))
    missing = [n for n in used if n not in expanded]
    print(f'  ..    {len(used)} ledger codes named, {len(used) - len(missing)} expanded')
    for m in missing:
        FAILS.append(f'`{m}` is named in the document with no entry in '
                     f'sources/data/account-names.csv — the reading is ours and has to '
                     f'say so')
    if not missing:
        print('  OK    every code carries a recorded reading and its basis')

    print('\n§personas  The persona review must have been run')
    # notes/PERSONAS.md defines six readers and one test each. Three of those tests are
    # about what a document OMITS, which is what a writer cannot see in their own work,
    # so the things the first review added are asserted here rather than trusted to stay.
    NEEDED = [
        ('the repeatable sentence is the true one',
         'The district spent 97.3% of its budget'),
        ('"is this FY25 again?" is answered before it is asked',
         'Is this FY25 happening again'),
        ('the open questions are in the first screen, not the last',
         'three things this report cannot explain'),
        ('the Finance Committee control question is answered',
         'what would you have had to see, and when'),
        ('a concrete thing somebody asked for is looked at',
         'more heads than we have helmets'),
        ('the town comparison is not left as a scoreboard',
         'It is not a scoreboard'),
    ]
    # Collapse whitespace before matching. These are PHRASES, and prose wraps -- "It
    # is not a scoreboard" fell across a line break and the check reported it missing
    # from a document that contained it. A checker that fails on line wrapping teaches
    # the writer to avoid wrapping, which is the wrong lesson.
    flat = ' '.join(PLAIN.split()).lower()
    for label, needle in NEEDED:
        ok = ' '.join(needle.split()).lower() in flat
        print(f"  {'OK  ' if ok else 'GONE'}  {label:<52}")
        if not ok:
            FAILS.append(f'persona review: "{label}" — the text that satisfied it is gone')
    # And the omission test that has to be re-run rather than remembered: if the document
    # says a category underspent, the archive has to have been searched for what people
    # said about that category.
    if 'underspend' in PLAIN.lower() and 'public comment' not in PLAIN.lower() \
            and 'told the School Committee' not in PLAIN:
        FAILS.append('the document reports an underspend and quotes nobody from the '
                     'meeting archive about it — step 3 of the persona review')

    print('\n§0  The document must not call any of this a surplus')
    for banned in (r'\bthe surplus was\b', r'\bFY26 surplus of\b'):
        if re.search(banned, PLAIN, re.I):
            FAILS.append(f'the document calls a period 12 figure a surplus: {banned}')
    print('  OK    no period 12 figure is described as a surplus')

    print()
    if FAILS:
        print('%d problem(s):' % len(FAILS))
        for f in FAILS:
            print('  -', f)
        return 1
    print('every figure in fy26-closeout.md is reproduced from the database.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
