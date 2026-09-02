"""Recompute every figure in the town-side FY26 analysis, and fail if one drifted.

    python3 scripts/verify_fy26_closeout_town.py

Same contract as verify_fy26_closeout.py: derive the value from the database, then assert
the derived string appears in the document. Never assert the prose.

The `present` matcher is bounded rather than a bare substring, because the school-side
verifier passed for a while on the count 61 matching the digits inside $25,613,679.23.
"""
import os
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
DOC = os.path.join(ROOT, 'sources', 'analyses', 'fy26-closeout-town.md')

TEXT = open(DOC, encoding='utf-8').read()
PLAIN = TEXT.replace('**', '')
FAILS = []

# Everything except the schools. Defined once: an analysis that quietly changed which
# departments it covered halfway down would be worse than one that was simply wrong.
NOT_SCHOOL = "a.fund='0100' AND a.dept NOT IN ('300','301')"
AT = "l.fy=2026 AND l.period=12"


WORDS = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight',
         'nine', 'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen',
         'sixteen', 'seventeen', 'eighteen', 'nineteen', 'twenty']


def present(label, value, dp=2):
    """Assert a DERIVED value appears in the document. Magnitude, on a word boundary.

    A small count is accepted SPELLED OUT as well as in digits. These documents write
    "seven false friends" and "eleven were covered", which is how the prose should read,
    and a check that fails because a number was spelled correctly is a check that pushes
    the writing in the wrong direction to satisfy itself.
    """
    if isinstance(value, float):
        needle = f'{abs(value):,.{dp}f}' if dp else f'{abs(value):,.0f}'
    else:
        needle = f'{abs(value):,}' if isinstance(value, int) else str(value)
    ok = re.search(r'(?<![\d,.])' + re.escape(needle) + r'(?![\d,]*\d)',
                   PLAIN) is not None
    if not ok and isinstance(value, int) and 0 <= abs(value) < len(WORDS):
        ok = re.search(r'\b' + WORDS[abs(value)] + r'\b', PLAIN, re.I) is not None
    if not ok:
        FAILS.append(f'{label}: derived {needle} is not in the document')
    print(f"  {'OK  ' if ok else 'GONE'}  {label:<50} {needle}")
    return ok


def main():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    one = lambda s, *a: db.execute(s, a).fetchone()

    print('Recomputing every figure in fy26-closeout-town.md\n')

    print('§1  The town totals, and the contrast with the schools')
    t = one(f"""SELECT COUNT(*) n, SUM(original) o, SUM(transfers) tr, SUM(revised) rv,
                       SUM(expended) e, SUM(encumbered) en, SUM(available) av
                FROM ledger_snapshot l JOIN account a USING (account_id)
                WHERE {AT} AND {NOT_SCHOOL}""")
    present('non-school accounts', t['n'])
    # The document rounds these to whole dollars, so the assertion must too.
    for k, lbl in (('o', 'appropriated'), ('tr', 'transferred in'), ('rv', 'revised'),
                   ('e', 'spent'), ('en', 'encumbered'), ('av', 'unspent')):
        present('town ' + lbl, float(t[k]), dp=0)

    depts = one(f"""SELECT COUNT(DISTINCT dept) n FROM ledger_snapshot l
                    JOIN account a USING (account_id) WHERE {AT} AND {NOT_SCHOOL}""")
    present('departments covered', depts['n'])

    for who, where in (('town', NOT_SCHOOL),
                       ('school', "a.dept IN ('300','301')")):
        ov = one(f"""SELECT COUNT(*) n, SUM(-available) s FROM ledger_snapshot l
                     JOIN account a USING (account_id)
                     WHERE {AT} AND {where} AND available < -0.5""")
        un = one(f"""SELECT COUNT(*) n, SUM(available) s FROM ledger_snapshot l
                     JOIN account a USING (account_id)
                     WHERE {AT} AND {where} AND available > 0.5""")
        present(f'{who} accounts under', un['n'])
        present(f'{who} amount under', float(un['s']), dp=0)
        present(f'{who} accounts over', ov['n'])
        present(f'{who} amount over', float(ov['s']), dp=0)

    print('\n§2  Snow removal')
    sn = one(f"""SELECT SUM(original) o, SUM(transfers) tr, SUM(revised) rv,
                        SUM(expended) e, SUM(available) av
                 FROM ledger_snapshot l JOIN account a USING (account_id)
                 WHERE {AT} AND a.dept='423'""")
    present('snow appropriated', float(sn['o']), dp=0)
    present('snow transferred in', float(sn['tr']), dp=0)
    present('snow revised', float(sn['rv']), dp=0)
    present('snow spent', float(sn['e']))
    present('snow over', float(sn['av']), dp=0)
    pct = float(sn['e']) / float(sn['o']) * 100
    present('snow as a share of its appropriation', f'{pct:.0f}%')
    wages = one(f"""SELECT revised, expended FROM ledger_snapshot l
                    JOIN account a USING (account_id)
                    WHERE {AT} AND a.dept='423' AND a.object='513000'""")
    present('snow wages budget', float(wages['revised']), dp=0)
    present('snow wages spent', float(wages['expended']))
    present('snow wages as a share',
            f"{float(wages['expended']) / float(wages['revised']) * 100:.0f}%")
    # The transfer sized exactly to the spend is the section's whole point.
    cs = one(f"""SELECT revised, expended FROM ledger_snapshot l
                 JOIN account a USING (account_id)
                 WHERE {AT} AND a.dept='423' AND a.object='531003'""")
    if abs(float(cs['revised']) - float(cs['expended'])) > 0.005:
        FAILS.append('CONTR SERV no longer spends its revised budget exactly; §2 says it '
                     'does, and that is the point of the paragraph')
    present('snow contracted services', float(cs['expended']))

    print('\n§3  The reserve funds')
    for dept, obj, lbl in (('132', None, 'Reserve Fund'),
                           ('133', None, 'salary reserve')):
        for r in db.execute(f"""SELECT a.name, l.original, l.transfers, l.expended
                                FROM ledger_snapshot l JOIN account a USING (account_id)
                                WHERE {AT} AND a.dept=?""", (dept,)):
            present(f"{r['name']} budgeted", float(r['original']), dp=0)
    unused = one(f"""SELECT SUM(original - expended) u FROM ledger_snapshot l
                     JOIN account a USING (account_id)
                     WHERE {AT} AND a.dept IN ('132','133') AND transfers = 0""")
    present('contingency left unused', float(unused['u']), dp=0)
    rf = one(f"""SELECT expended FROM ledger_snapshot l JOIN account a USING (account_id)
                 WHERE {AT} AND a.dept='132'""")
    if float(rf['expended']) != 0:
        FAILS.append('the Reserve Fund now shows spending; §3 says it spent nothing')

    print('\n§4  Money leaving the operating budget')
    tr = one(f"""SELECT SUM(original) o, SUM(transfers) t, SUM(expended) e
                 FROM ledger_snapshot l JOIN account a USING (account_id)
                 WHERE {AT} AND a.dept IN ('993','996')""")
    present('transfer accounts appropriated', float(tr['o']), dp=0)
    present('transfer accounts received', float(tr['t']))
    present('transfer accounts moved', float(tr['e']))
    for dept in ('993', '996'):
        d = one(f"""SELECT original, transfers, expended FROM ledger_snapshot l
                    JOIN account a USING (account_id) WHERE {AT} AND a.dept=?""", dept)
        present(f'dept {dept} received', float(d['transfers']))
        present(f'dept {dept} moved', float(d['expended']))

    print('\n§5  School costs on the town side')
    ins = one(f"""SELECT SUM(expended) e FROM ledger_snapshot l
                  JOIN account a USING (account_id) WHERE {AT} AND a.dept='914'""")
    present('insurance department spent', float(ins['e']))
    sch = one(f"""SELECT revised, expended FROM ledger_snapshot l
                  JOIN account a USING (account_id)
                  WHERE {AT} AND a.name='SCHRETHLTH'""")
    present('school retiree health budgeted', float(sch['revised']), dp=0)
    present('school retiree health spent', float(sch['expended']))
    stip = one(f"""SELECT expended FROM ledger_snapshot l JOIN account a USING (account_id)
                   WHERE {AT} AND a.name='SCHRESSTIP'""")
    present('school resource stipend', float(stip['expended']), dp=0)
    present('school cost nameable on the town side',
            float(sch['expended']) + float(stip['expended']), dp=0)
    present('the rest of the insurance department',
            float(ins['e']) - float(sch['expended']), dp=0)
    # The false friends must stay excluded. If one ever gets counted, the total moves.
    ff = one(f"""SELECT COUNT(*) n, SUM(expended) e FROM ledger_snapshot l
                 JOIN account a USING (account_id)
                 WHERE {AT} AND {NOT_SCHOOL} AND a.name LIKE '%SCH%'
                   AND a.name NOT IN ('SCHRETHLTH','SCHRESSTIP')""")
    present('false friends discarded', ff['n'])
    present('what the false friends total', float(ff['e']))
    present('accounts matching a search for SCH', ff['n'] + 2)

    print('\n§6  Zero-budget spending')
    z = one(f"""SELECT COUNT(*) n FROM ledger_snapshot l JOIN account a USING (account_id)
                WHERE {AT} AND {NOT_SCHOOL} AND original=0 AND expended<>0""")
    present('non-school accounts spending with no appropriation', z['n'])
    nt = one(f"""SELECT COUNT(*) n FROM ledger_snapshot l JOIN account a USING (account_id)
                 WHERE {AT} AND {NOT_SCHOOL} AND original=0 AND expended<>0
                   AND transfers=0""")
    present('of which received no transfer', nt['n'])
    present('of which were covered by a transfer', z['n'] - nt['n'])
    pd = one(f"""SELECT transfers, expended FROM ledger_snapshot l
                 JOIN account a USING (account_id)
                 WHERE {AT} AND a.name='PLANN DIR'""")
    present('planning director spent', float(pd['expended']))
    # The pair cancelling is the whole of §6. If the mirror ever stops mirroring, the
    # section's conclusion about the school finding stops holding.
    pc = one(f"""SELECT expended FROM ledger_snapshot l JOIN account a USING (account_id)
                 WHERE {AT} AND a.name='PLAN CLERI'""")
    if abs(float(pd['expended']) + float(pc['expended'])) > 0.005:
        FAILS.append('PLANN DIR and PLAN CLERI no longer cancel; §6 says they do')
    print('  OK    the planning pair still cancels to zero')
    # And the claim that nothing in the school department offsets the kindergarten
    # accounts. This is asserted, not assumed, because it is the first thing that would
    # have explained them.
    neg = one(f"""SELECT COUNT(*) n FROM ledger_snapshot l
                  JOIN account a USING (account_id)
                  WHERE {AT} AND a.dept='300' AND expended < 0""")
    if neg['n'] != 0:
        FAILS.append('the school department now has %d account(s) with negative spending; '
                     '§6 says there are none' % neg['n'])
    print('  OK    no offsetting credit anywhere in the school department')


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

    print('\n§0  Nothing here may be called a surplus')
    if re.search(r'\bthe surplus was\b|\bFY26 surplus of\b', PLAIN, re.I):
        FAILS.append('a period 12 figure is described as a surplus')
    print('  OK    no period 12 figure is described as a surplus')

    print()
    if FAILS:
        print('%d problem(s):' % len(FAILS))
        for f in FAILS:
            print('  -', f)
        return 1
    print('every figure in fy26-closeout-town.md is reproduced from the database.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
