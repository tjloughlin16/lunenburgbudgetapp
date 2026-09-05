"""Write `sources/analyses/show-your-work.md` — every calculation, for the people who vote.

WHO IT IS FOR
-------------
Finance Committee, Town Manager, Select Board and School Committee members. People who
read budgets for a living or for love, and who do not write software. That audience
decides the voice of every line in the output:

  * No filenames, no scripts and no code in the body. All of that is Appendix A, where
    somebody who wants to rerun the arithmetic can find it and nobody else has to step
    over it.
  * Formulas are fine and are used where they are the clearest way to say a thing. They
    are written as arithmetic -- "share of the budget x (growth rate - levy cap)" -- and
    never as code, with no variable names, subscripts or function calls in them.
  * Where a calculation is really a column of figures that adds up, it is set out the way
    a budget worksheet sets one out, because that is how this audience reads.
  * Municipal vocabulary is assumed and technical vocabulary is not. "Levy limit", "new
    growth", "free cash" and "circuit breaker" go unexplained. Anything from our side of
    the fence gets explained or does not appear.
  * Every figure carries where it came from, and the labels are the point of the whole
    document: published / contract / statute / measured / ours.

WHY IT IS GENERATED
-------------------
A document made almost entirely of numbers is the worst possible place to type one. Three
figures were found in this project stating amounts the model no longer produced, one off
by $313,000, all of them in prose beside figures that were computed. So every number
below is read out of the live model at build time. Change a rate and re-run, and the
prose moves with it.

The prose is not automatically safe, and that is worth stating because it has already
gone wrong here once: a sentence that *interprets* a figure ("this is out by a factor of
four") is just as perishable as the figure, and interpretation cannot be generated. After
any change to the model, read the output, not only the diff.

    python3 scripts/build_show_your_work.py            # write it
    python3 scripts/build_show_your_work.py --check    # fail if the committed copy is stale

`scripts/audit_provenance.py` runs the check, so a stale copy fails the build rather than
being discovered by a reader.
"""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'model'))
os.chdir(ROOT)

import finance                                                    # noqa: E402
import sped                                                       # noqa: E402
import freecash                                                   # noqa: E402
import athletics                                                  # noqa: E402
import health                                                      # noqa: E402
import taxbase                                                    # noqa: E402
import levers                                                     # noqa: E402
import cascade                                                    # noqa: E402

OUT = os.path.join(ROOT, 'sources', 'analyses', 'show-your-work.md')


# ------------------------------------------------------------------ formatting
def usd(n, cents=False):
    if n is None:
        return '—'
    s = f'{abs(n):,.2f}' if cents else f'{abs(round(n)):,}'
    return ('-$' if n < 0 else '$') + s


def signed(n, cents=False):
    return ('+' if n >= 0 else '−') + usd(abs(n), cents)


def pct(x, dp=2):
    return '—' if x is None else f'{x * 100:.{dp}f}%'


def num(n, dp=0):
    return f'{n:,.{dp}f}'


def table(headers, rows, align=None):
    align = align or 'l' * len(headers)
    sep = {'l': ':--', 'r': '--:', 'c': ':-:'}
    out = ['| ' + ' | '.join(headers) + ' |',
           '|' + '|'.join(sep[a] for a in align) + '|']
    for r in rows:
        out.append('| ' + ' | '.join(str(c) for c in r) + ' |')
    return '\n'.join(out)


def ledger(rows, width=52):
    """A worked column of figures, the way a budget worksheet sets one out."""
    out = []
    for r in rows:
        if r is None:
            out.append(' ' * width + '  ' + '-' * 15)
            continue
        label, amount = r
        out.append(f'{label:<{width}}{amount:>17}')
    return '```\n' + '\n'.join(out) + '\n```'


def formula(*lines):
    """Arithmetic stated as arithmetic. Never a variable name, never a function call."""
    return '> ' + '\n> '.join(lines)


S = []
def w(*lines):
    S.extend(lines)


# ------------------------------------------------------------------ shared state
A = finance.DEFAULT_ASSUMPTIONS
F = finance.FY27
BASE = finance.expense_base()
BASE_WITH_ADDBACKS = dict(BASE)
BASE_WITH_ADDBACKS['salaries'] += F['stm_addbacks']
BASE_TOTAL = sum(BASE_WITH_ADDBACKS.values())
PROJ = finance.project(6)
LEVY_CAP = A['levy_growth']
WEDGE = (F['levy_limit'] + F['excluded_debt'] + F['state_aid']
         + F['local_receipts'] - F['omnibus'])

BUCKET_LABEL = {
    'salaries': 'Salaries, other than special education',
    'sped': 'Special education, in district',
    'health': 'Health insurance and unemployment',
    'other': 'Everything else',
    'transport': 'Transportation, other than special education',
    'sped_tuition': 'Out-of-district tuition',
    'utilities': 'Utilities',
}
BUCKET_BASIS = {
    'salaries': ('contract', 'The teachers’ agreement — scale increases plus steps'),
    'sped': ('ours', 'A blend of two contracts and two measured trends. Section 4'),
    'health': ('published', 'The district’s own stated assumption for FY27'),
    'other': ('published', 'The district’s own stated assumption for FY27'),
    'transport': ('ours', 'The district assumed 10% for FY27. This is softer, and ours'),
    'sped_tuition': ('ours', 'Held flat. Section 5 sets out why that is a finding rather '
                             'than a gap'),
    'utilities': ('published', 'The district’s own stated assumption for FY27'),
}
KIND_MARK = {'published': '`published`', 'contract': '`contract`',
             'statute': '`statute`', 'ours': '`ours`', 'measured': '`measured`'}


def weight(k):
    return BASE_WITH_ADDBACKS[k] / BASE_TOTAL


def pull(k):
    return weight(k) * (A[k] - LEVY_CAP)


BLENDED = sum(weight(k) * A[k] for k in BASE_WITH_ADDBACKS)


def _bump(key, delta, years=1):
    b = finance.project(years, A)[years - 1]['deficit']
    h = finance.project(years, {**A, key: A[key] + delta})[years - 1]['deficit']
    return h - b


def new_growth_per_dollar():
    d0 = finance.project(1, {**A, 'new_growth': 0})[0]['deficit']
    d1 = finance.project(1, {**A, 'new_growth': 1_000_000})[0]['deficit']
    return (d0 - d1) / 1_000_000


SHARE = new_growth_per_dollar()


# =====================================================================  OPENING
def opening():
    w('# Show your work',
      '',
      'Every figure this project publishes, and how it was arrived at.',
      '',
      'It is written for the people who have to decide something with it — Finance',
      'Committee, Town Manager, Select Board, School Committee. It assumes you read',
      'budgets and does not assume you write software. Nothing in the body of it requires',
      'a computer to follow; the files and commands are in Appendix A, for anyone who',
      'wants to rerun the arithmetic themselves.',
      '',
      '**The most useful thing here is not a number. It is the labels.** Every figure is',
      'marked with where it came from, because you cannot judge an argument without',
      'knowing which parts of it are somebody else’s work and which are ours:',
      '',
      table(['label', 'means'],
            [['`published`', 'A figure stated in a document by the town, the district or '
                             'the state. We transcribed it.'],
             ['`contract`', 'A rate set by a signed collective bargaining agreement.'],
             ['`statute`', 'Fixed by law.'],
             ['`measured`', 'We calculated it from somebody else’s figures. The '
                            'arithmetic is ours; the underlying numbers are not.'],
             ['`ours`', 'An estimate, a classification or an assumption we made. These '
                        'are the ones to argue with, and Section 12 lists every one of '
                        'them in order of how much it matters.']]),
      '',
      '**If you have limited time, read Section 12.** It is every assumption in the model,',
      'sorted by how much the answer moves if the assumption is wrong, with a plain',
      'statement of what backs each one — including the two that are backed by nothing.',
      '',
      'Every section is laid out the same way: the question being asked, what goes into',
      'it, the arithmetic worked through, and then what we assumed and what would settle',
      'it. That last heading appears in every section without exception.',
      '')

    w('## Two distinctions that everything here depends on',
      '',
      '**A budget is not an actual.** A budget is what somebody voted or proposed. An',
      'actual is what got spent. On some lines in this town the two differ by 59%.',
      ' A growth rate measured from an actual in one year to a budget in the next is',
      'partly real growth and partly the step between two different kinds of number, and',
      'it produces an answer that looks authoritative and is wrong — that mistake once put',
      'our special education growth rate a point and a half too high.',
      '',
      '**Every projection here uses budget figures only.** Actual spending answers other',
      'questions and is used for them. The two are never combined inside one calculation,',
      'and that is enforced automatically rather than by good intentions.',
      '',
      '**A one-time saving is not a change in direction.** A cut lowers the cost curve',
      'once and leaves its slope alone. Only a change in a *growth rate* changes the',
      'slope. Two figures growing at different rates move apart forever, no matter how',
      'much you subtract from one of them once — which is the arithmetic behind why a town',
      'can cut every year and face a larger gap every year. It is not mismanagement and it',
      'is not anybody being alarmist.',
      '',
      'Most of what follows is one or the other. Free cash, cuts and overrides change the',
      'level. Sections 3 to 5 are about the rates.',
      '',
      '**And a budget line is a net figure, in dollars.** The district budgets what the',
      'town must raise after grants, fees and reimbursements have paid their share. A line',
      'can rise because the thing got dearer, because a grant that was covering part of it',
      'ended, or because a fee stopped being collected — and all three look identical on',
      'the page. Nothing in this document measures what a service costs, how many people',
      'it employs, or how many children it serves. It measures **appropriations**, which',
      'is what Town Meeting votes on.',
      '')


# ===========================================================  1. THE PROJECTION
def s_projection():
    w('---',
      '',
      '## 1. How the gap is projected',
      '',
      '### The question',
      '',
      'If the district keeps doing exactly what it does now, and the town raises revenue',
      'the way the town says it raises revenue, how far apart are those two figures in',
      'each of the next several years?',
      '',
      'That is not a forecast of what will happen, because what will happen includes',
      'decisions nobody has taken yet. It is the arithmetic of taking no decision at all.',
      '')

    w('### What goes in, on the revenue side',
      '',
      'All of it from the Town Manager’s FY27 budget release of 17 April 2026 and the',
      'enacted state budget.',
      '',
      table(['figure', 'FY27', 'label'],
            [['Levy limit', usd(F['levy_limit'], cents=True), KIND_MARK['published']],
             ['Debt excluded from the limit', usd(F['excluded_debt'], cents=True),
              KIND_MARK['published']],
             ['State aid', usd(F['state_aid']), KIND_MARK['published']],
             ['Local receipts', usd(F['local_receipts']), KIND_MARK['published']],
             ['Omnibus budget as appropriated', usd(F['omnibus'], cents=True),
              KIND_MARK['published']],
             ['School appropriation', usd(F['lps_appropriation']), KIND_MARK['published']],
             ['September Town Meeting article', usd(F['stm_appropriation']),
              KIND_MARK['published']],
             ['Programs that article restores', usd(F['stm_addbacks']),
              KIND_MARK['published']]],
            'lrl'),
      '',
      '### How next year’s revenue is worked out',
      '',
      'Three figures grow, one is held flat, and one is subtracted.',
      '',
      formula(f'Next year’s levy limit = this year’s levy limit × '
              f'{1 + LEVY_CAP} + new growth'),
      '',
      ledger([
        ('Levy limit, FY27', usd(F['levy_limit'])),
        (f'  plus Proposition 2½ growth of {pct(LEVY_CAP, 1)}',
         signed(F['levy_limit'] * LEVY_CAP)),
        ('  plus new growth', signed(A['new_growth'])),
        None,
        ('Levy limit, FY28', usd(F['levy_limit'] * (1 + LEVY_CAP) + A['new_growth'])),
        ('Debt excluded from the limit (held flat)', usd(F['excluded_debt'])),
        (f'State aid, grown {pct(A["state_aid_growth"], 1)}',
         usd(F['state_aid'] * (1 + A['state_aid_growth']))),
        (f'Local receipts, grown {pct(A["local_receipts_growth"], 1)}',
         usd(F['local_receipts'] * (1 + A['local_receipts_growth']))),
        ('Less revenue not appropriated in the omnibus', signed(-WEDGE)),
        None,
        ('Town revenue available to appropriate, FY28',
         usd(F['levy_limit'] * (1 + LEVY_CAP) + A['new_growth'] + F['excluded_debt']
             + F['state_aid'] * (1 + A['state_aid_growth'])
             + F['local_receipts'] * (1 + A['local_receipts_growth']) - WEDGE)),
        ('The same figure for FY27', usd(F['omnibus'])),
        ('Growth', pct(PROJ[0]['growth_rate'])),
      ]),
      '',
      f'**That subtraction is worth a word.** {usd(WEDGE)} of FY27 revenue does not appear',
      'in the omnibus budget — assessments, the overlay, state charges and the rest. We do',
      'not model it changing, so it is worked out once from the FY27 figures and taken off',
      'every year. That is an assumption. If those charges grow faster than revenue does,',
      'this projection is too generous.',
      '',
      '**And then the schools get their share.**',
      '',
      formula('Next year’s school appropriation',
              '  = this year’s appropriation × (1 + the growth rate above)'),
      '',
      '**This is the single most consequential choice in the model, and it is ours.** It',
      'assumes the schools hold the share of the town budget they hold today —',
      f'{pct(F["lps_appropriation"] / F["omnibus"], 1)} of the omnibus — and neither gain',
      'nor lose ground against every other department. Nothing published commits the town',
      'to that, in either direction. A year in which the schools’ share moves by a single',
      'point swamps most of the growth rates in this document.',
      '')

    rows = []
    for k in sorted(BASE_WITH_ADDBACKS, key=lambda x: -BASE_WITH_ADDBACKS[x]):
        kind, _ = BUCKET_BASIS[k]
        rows.append([BUCKET_LABEL[k], usd(BASE_WITH_ADDBACKS[k]),
                     pct(weight(k), 1), pct(A[k]), KIND_MARK[kind]])
    rows.append(['**Total**', f'**{usd(BASE_TOTAL)}**', '**100.0%**',
                 f'**{pct(BLENDED)}** blended', ''])
    w('### What goes in, on the cost side',
      '',
      'The adopted FY27 school budget, line by line, sorted into seven groups. Each group',
      'grows at its own rate, because they behave nothing alike.',
      '',
      formula('Cost of the same services next year',
              '  = the sum of each group × (1 + that group’s growth rate)'),
      '',
      f'The line items come to {usd(sum(BASE.values()))}, against a published',
      f'appropriation of {usd(F["lps_appropriation"])} — a difference of',
      f'{usd(abs(sum(BASE.values()) - F["lps_appropriation"]))}, which is rounding in the',
      'district’s own workbook and is not corrected here.',
      '',
      f'The {usd(F["stm_addbacks"])} of programs restored at the September Special Town',
      'Meeting is added to salaries, because that money is one-time and carrying those',
      'programs into FY28 is itself a cost the district has to absorb.',
      '',
      table(['group', 'FY27', 'share of the budget', 'grows at', 'that rate is'],
            rows, 'lrrrl'),
      '',
      '**Two things in that table are worth stopping on.**',
      '',
      '*The cost side and the revenue side do not get the same addback.* Costs carry the',
      f'whole {usd(F["stm_addbacks"])} restoration plan. Revenue carries only the',
      f'{usd(F["stm_appropriation"])} Town Meeting article, because the balance —',
      f'{usd(F["stm_addbacks"] - F["stm_appropriation"])} — came from health insurance',
      'savings inside FY27 that do not recur. So the projection begins FY28 already',
      'carrying that amount as gap. That is deliberate, and it is a judgement; anyone who',
      'thinks those savings do recur should take it off.',
      '',
      f'*Unemployment compensation sits in the health insurance group.* It is',
      f'{usd(BASE_WITH_ADDBACKS["health"] - levers.HEALTH_TOTAL)} of the',
      f'{usd(BASE_WITH_ADDBACKS["health"])}, it shares an account code with health',
      f'insurance, and so it grows at {pct(A["health"], 1)} along with it. Unemployment',
      'does not behave like a health premium. It is too small to change any conclusion,',
      'and it is written down here because somebody adding up the lines should not find a',
      'figure they cannot account for.',
      '')

    levy = F['levy_limit'] * (1 + LEVY_CAP) + A['new_growth']
    aid = F['state_aid'] * (1 + A['state_aid_growth'])
    receipts = F['local_receipts'] * (1 + A['local_receipts_growth'])
    town_avail = levy + F['excluded_debt'] + aid + receipts - WEDGE
    growth = town_avail / F['omnibus'] - 1
    approp = (F['lps_appropriation'] + F['stm_appropriation']) * (1 + growth)
    ls = sum(v * (1 + A[k]) for k, v in BASE_WITH_ADDBACKS.items())
    gap = ls - approp
    p0 = PROJ[0]
    assert round(ls) == p0['level_service'], (round(ls), p0['level_service'])
    assert round(approp) == p0['appropriation'], (round(approp), p0['appropriation'])
    assert round(gap) == p0['deficit'], (round(gap), p0['deficit'])

    w('### The gap, worked through for FY28',
      '',
      ledger([
        ('School appropriation, FY27', usd(F['lps_appropriation'])),
        ('  plus the September Town Meeting article', signed(F['stm_appropriation'])),
        (f'  grown at the town’s revenue growth of {pct(growth)}',
         signed(approp - F['lps_appropriation'] - F['stm_appropriation'])),
        None,
        ('Money available to the schools, FY28', usd(approp)),
        None,
        ('Cost of the same services, on the FY27 basis', usd(BASE_TOTAL)),
        (f'  each group grown at its own rate (blended {pct(BLENDED)})',
         signed(ls - BASE_TOTAL)),
        None,
        ('Cost of the same services, FY28', usd(ls)),
        ('Money available to the schools, FY28', usd(approp)),
        None,
        ('GAP', usd(gap)),
      ]),
      '',
      'Those figures are recomputed from the steps above and checked against the model',
      'before this document will save. If they ever disagreed, it would stop rather than',
      'publish a walkthrough that does not reproduce the answer it is explaining.',
      '')

    fresh = _fresh_gaps()
    running, cum = [], 0
    for r in PROJ:
        cum += r['deficit']
        running.append(cum)

    w('### The projection',
      '',
      '**Read the gap column carefully, because it is the figure most often',
      'misunderstood.** Each row is *that year on its own* — what that single year’s',
      'shortfall would be if nothing had been done in any earlier year. The rows are not',
      'added together, and each one is not "the extra hole that year" either.',
      '',
      table(['year', 'cost of the same services', 'money available',
             'shortfall that year, if nothing is done first',
             'of which is new that year', 'town revenue growth'],
            [[f'FY{r["fy"]}', usd(r['level_service']), usd(r['available']),
              usd(r['deficit']), usd(fresh[i][1]), pct(r['growth_rate'])]
             for i, r in enumerate(PROJ)],
            'lrrrrr'),
      '',
      '**Three different questions, three different answers, and they get confused for',
      'each other constantly:**',
      '',
      table(['the question', f'answer for FY{PROJ[1]["fy"]}'],
            [[f'What is the shortfall in FY{PROJ[1]["fy"]}, if the town does nothing in '
              f'FY{PROJ[0]["fy"]}?', f'**{usd(PROJ[1]["deficit"])}** — the gap column'],
             [f'How much of that is new in FY{PROJ[1]["fy"]}, over and above the '
              f'FY{PROJ[0]["fy"]} hole carried forward?',
              f'**{usd(fresh[1][1])}** — the second column'],
             [f'What do the shortfalls come to across FY{PROJ[0]["fy"]}–'
              f'FY{PROJ[-1]["fy"]} added together?',
              f'**{usd(running[-1])}**']],
            'll'),
      '',
      f'So FY{PROJ[1]["fy"]}’s {usd(PROJ[1]["deficit"])} is **not**',
      f'{usd(PROJ[0]["deficit"])} plus something. It is what FY{PROJ[1]["fy"]} looks like',
      f'on its own if FY{PROJ[0]["fy"]} was left alone — the earlier shortfall is still',
      'there, and a year of growth has been added on top of it.',
      '',
      '**And the same word means something different in Section 10.** There, every year’s',
      'gap is what is left *after* the previous years have been cut, which is a much',
      f'smaller number: FY{PROJ[1]["fy"]} is {usd(PROJ[1]["deficit"])} here and',
      f'{usd(_cascade_gap(PROJ[1]["fy"]))} there — '
      f'{pct(1 - _cascade_gap(PROJ[1]["fy"]) / PROJ[1]["deficit"], 0)} lower. Both are',
      'correct. They answer different questions, and the distance between them is the',
      'value of acting early rather than late.',
      '',
      '**The gap widens because two figures grow at different rates.** Costs at',
      f'{pct(BLENDED)}, town revenue at about {pct(PROJ[0]["growth_rate"])} and drifting',
      f'down toward the statutory {pct(LEVY_CAP, 1)} as a fixed {usd(A["new_growth"])} of',
      'new growth becomes a smaller share of a larger base. Nothing about the size of any',
      'one budget line changes that. It is four numbers, and it is the whole argument.',
      '',
      '### What we assumed, and what would settle it',
      '',
      '- **The schools hold their present share of the town budget.** Nothing publishes a',
      '  commitment to that. It is the assumption most capable of making everything else',
      '  here beside the point.',
      f'- **New growth stays at {usd(A["new_growth"])} a year.** That is the town’s own',
      '  estimate. The Assessors’ own series runs from',
      f'  {usd(taxbase.NEW_GROWTH_HISTORY[0]["amount"])} in',
      f'  FY{taxbase.NEW_GROWTH_HISTORY[0]["fy"]} down to',
      f'  {usd(taxbase.NEW_GROWTH_HISTORY[-1]["amount"])} in',
      f'  FY{taxbase.NEW_GROWTH_HISTORY[-1]["fy"]}. Section 11.',
      '- **Excluded debt, and the revenue outside the omnibus, are held flat.** Both will',
      '  move. Neither is modelled.',
      '- **There is no FY28 budget.** Everything after FY27 is projection. When the',
      '  district publishes an FY28 request, that is the real number, and this is what it',
      '  should be compared against.',
      '')


# =========================================================  2. WHAT DRIVES IT
def s_drivers():
    rows = []
    for k in sorted(BASE_WITH_ADDBACKS, key=lambda x: -pull(x)):
        kind, _ = BUCKET_BASIS[k]
        rows.append([BUCKET_LABEL[k], pct(weight(k), 1), pct(A[k]),
                     pct(A[k] - LEVY_CAP), f'**{pull(k) * 100:.2f}**', KIND_MARK[kind]])
    total_pull = sum(pull(k) for k in BASE_WITH_ADDBACKS)
    biggest = max(BASE_WITH_ADDBACKS, key=lambda k: BASE_WITH_ADDBACKS[k])
    top = max(BASE_WITH_ADDBACKS, key=pull)

    w('---',
      '',
      '## 2. Which budget lines actually drive the gap',
      '',
      '### The question',
      '',
      'The instinct in every budget meeting is to go after the biggest line. That is the',
      'wrong ranking, and following it is how a town spends three meetings on athletics',
      'and none on special education.',
      '',
      '### How it is worked out',
      '',
      'A line adds to the gap in proportion to its share of the budget **multiplied by**',
      'how far its growth exceeds the levy cap.',
      '',
      formula(f'Contribution = share of the budget × (growth rate − {pct(LEVY_CAP, 1)})'),
      '',
      'Neither figure means anything on its own. A very large line growing at 2½% adds',
      'nothing. A small line growing at 9% adds a good deal.',
      '',
      'The result is in percentage points of budget growth above the cap, and the column',
      'adds up to the amount by which the whole budget outruns Proposition 2½.',
      '',
      table(['line', 'share', 'grows at', 'above the cap by', 'contribution',
             'that rate is'], rows, 'lrrrrl'),
      '',
      f'**Total: {total_pull * 100:.2f} points.** That is the number that has to reach',
      f'zero. Blended cost growth is {pct(BLENDED)}, the levy cap is {pct(LEVY_CAP, 1)},',
      f'and the difference between them is those {total_pull * 100:.2f} points.',
      '',
      '### The same fact, two ways',
      '',
      f'**{BUCKET_LABEL[biggest]}** is the largest line in the budget at',
      f'{usd(BASE_WITH_ADDBACKS[biggest])} — {pct(weight(biggest), 1)} of all spending.',
      f'It grows at {pct(A[biggest])}, which is {pct(A[biggest] - LEVY_CAP)} above the',
      f'cap, so it contributes {pull(biggest) * 100:.2f} points.',
      '',
      f'**{BUCKET_LABEL[top]}** is {pct(weight(top), 1)} of spending — a line',
      f'{weight(biggest) / weight(top):.1f} times smaller — and contributes',
      f'**{pull(top) * 100:.2f} points**, more, because it grows',
      f'{pct(A[top] - LEVY_CAP)} above the cap instead of {pct(A[biggest] - LEVY_CAP)}.',
      '',
      '**A line held flat pulls the average down.** Out-of-district tuition is',
      f'{pct(weight("sped_tuition"), 1)} of spending at {pct(A["sped_tuition"], 1)}, so it',
      f'contributes {pull("sped_tuition") * 100:.2f} points — a negative number, which is',
      'what "below the cap" looks like in this column.',
      '',
      'Rank by contribution. Never by size, and never by rate alone.',
      '',
      '### What we assumed, and what would settle it',
      '',
      '- Every rate in that table gets its own section below. Three of the seven are ours.',
      '- The shares are FY27 shares, held constant. In reality a faster-growing line',
      '  becomes a bigger share of the budget each year, so this table slightly understates',
      '  the top line over a long horizon. The projection itself grows each group',
      '  separately and does not have that problem — only this ranking does.',
      '')


# ===================================================  3. WHERE THE RATES COME FROM
def s_rate_sources():
    rows = []
    for k in sorted(BASE_WITH_ADDBACKS, key=lambda x: -BASE_WITH_ADDBACKS[x]):
        kind, why = BUCKET_BASIS[k]
        rows.append([BUCKET_LABEL[k], pct(A[k]), KIND_MARK[kind], why])
    w('---',
      '',
      '## 3. Where each growth rate comes from',
      '',
      '### The question',
      '',
      'You cannot judge this projection without knowing which of its growth rates are the',
      'district’s own, which are set by a signed contract or by statute, and which we',
      'chose. Here is the whole list in one place.',
      '',
      table(['group', 'grows at', 'label', 'basis'], rows, 'lrll'),
      '',
      '**Four of the seven are the district’s own stated assumptions or a signed',
      'contract.** We did not invent them and we have not adjusted them. The three marked',
      '`ours` are the ones to argue with, and two of them get a full section each: special',
      'education in Section 4, out-of-district tuition in Section 5.',
      '',
      f'**The third is transportation.** The district assumed 10% for FY27. We use',
      f'{pct(A["transport"], 1)}, which is *softer* than the district’s own figure — so',
      'the gap published here is smaller than the district’s own assumptions would',
      'produce. It is ours, and unlike the other two it does not rest on any test of the',
      'line’s own history. It is the least defended figure in the table, and it is named',
      'as such in Section 12.',
      '',
      '### Checking the rates against history',
      '',
      'Every assumption is compared against what that line actually did, **budget to',
      'budget** — never budget to actual, which would measure the step between two',
      'different kinds of number as well as the growth.',
      '',
      'Six lines have come back flagged. Three of those turned out to be one-time step',
      'changes rather than trends, which is why the year-by-year has to be read before a',
      'compound growth rate is believed. A three-year rate measured off a small base is',
      'not a trend, and a line that goes to zero and reappears under a new name produces a',
      'spectacular-looking rate that means nothing at all.',
      '')


# =========================================  4. SPECIAL EDUCATION, IN DISTRICT
def s_sped():
    cl = sped.classified()
    w('---',
      '',
      '## 4. Special education, in district',
      '',
      'The longest section, because this is the growth rate this project built rather than',
      'transcribed, and it moves the answer more than any other single choice in the',
      'model.',
      '',
      '### The question',
      '',
      'What should in-district special education be grown at, given that no contract',
      'governs it, the state has no account code for it, and three budget years cannot',
      'tell a one-time increase from a trend?',
      '')

    w('### Why it is separated out at all',
      '',
      'The state’s account codes cannot separate special education from everything else.',
      'One code covers paraprofessionals of both kinds; another covers transportation of',
      'both. Grouping by code alone put roughly $5.7 million of special education staffing',
      'in with general salaries, where it took the teachers’ contract rate.',
      '',
      'That hid no money — the total was always right — but it averaged together two lines',
      'that behave nothing alike. Teaching salaries move when a contract is bargained.',
      'This line moves when a child arrives who needs a paraprofessional.',
      '')

    w('### The classification, which is ours',
      '',
      '**This is the figure on the page most open to challenge, and it should be.** There',
      'is no published quantity called "special education", so this total is a rule we',
      'wrote:',
      '',
      '1. **Eight account groups are special education outright**, and every line inside',
      f'   them counts — {cl["byGroup"]} lines.',
      '2. **Inside groups that carry both kinds of cost**, a line counts when the',
      f'   district’s own label for it says special education — {cl["byName"]} lines. One',
      '   of those, special education transportation, is most of the money.',
      '',
      f'That is {len(cl["counted"])} lines totalling {usd(cl["total"])} in the adopted FY27',
      'budget. Every one of them is published as a list, so the total can be added up by',
      'hand.',
      '',
      '**What sits just outside, and why:**',
      '',
      table(['excluded', 'lines', 'FY27', 'why'],
            [[e['group'], e['lines'], usd(e['amount']), e['why']] for e in cl['excluded']],
            'lrrl'),
      '',
      '**English Language Learner lines are the correction most worth knowing about.** The',
      'district files some of that work inside groups that are otherwise special',
      'education, so a rule that took those groups at their word counted it — and ours',
      'did, until this was found. It is a different entitlement, serving different',
      'children, under a different part of the law.',
      '')

    dec = sped.decomposition()
    rows = []
    for d in dec:
        r1 = d['fy26'] / d['fy25'] - 1 if d['fy25'] else None
        r2 = d['fy27'] / d['fy26'] - 1 if d['fy26'] else None
        rows.append([d['label'], usd(d['fy25']), usd(d['fy26']), usd(d['fy27']),
                     pct(r1, 1), pct(r2, 1)])
    whole = [sum(d[c] for d in dec) for c in ('fy25', 'fy26', 'fy27')]
    rows.append(['**Whole line**', f'**{usd(whole[0])}**', f'**{usd(whole[1])}**',
                 f'**{usd(whole[2])}**', f'**{pct(whole[1] / whole[0] - 1, 1)}**',
                 f'**{pct(whole[2] / whole[1] - 1, 1)}**'])
    w('### The obvious answer, and why we did not use it',
      '',
      f'The obvious number is {pct(sped.WHOLE_LINE_RATE)} — what the whole line did across',
      'three budgets. It was our published choice for a day. Break the line into its parts',
      'and the whole increase is one component moving once:',
      '',
      table(['part', 'FY25 budget', 'FY26 final', 'FY27 level service',
             'FY26 change', 'FY27 change'], rows, 'lrrrrr'),
      '',
      f'The paraprofessional increase is {pct(sped.PARA_SHARE_OF_RISE, 0)} of the whole',
      'FY27 rise — every other part of special education fell that year. Take it out and',
      f'the rest of the line grew {pct(sped.EX_PARAS_RATE)} a year, below the levy cap.',
      '',
      f'So {pct(sped.WHOLE_LINE_RATE)} is not a growth rate. It is one hiring decision,',
      'averaged over two years and then compounded forever. **Those paraprofessionals were',
      'hired. Their cost is already inside the',
      f'{usd(sped.total(sped.FY27BAL, sped.is_sped))} this projection starts from.**',
      f'Growing that base at {pct(sped.WHOLE_LINE_RATE)} assumes the district hires',
      f'{pct(sped.PARA_FY27_RATE, 0)} more paraprofessionals again next year, and again',
      'the year after.',
      '')

    def trow(label, t):
        return [label, t['n'], f"FY{t['firstFy']}–FY{t['lastFy']}",
                usd(t['first']), usd(t['last']), f"{t['r2']:.2f}",
                f"{t['up']} up / {t['down']} down", pct(t['cagr']),
                f"{pct(t['cagrLow'])} to {pct(t['cagrHigh'])}"]

    w('### The test that decides every rate below',
      '',
      'Three budget years cannot tell a one-time increase from a trend. Our mirror of the',
      'district’s budget page reaches back to FY17, so each line below is measured over',
      'nine or ten budgets instead of two — **budget figures only, and always at the same',
      'stage of the budget process**, because a year has several budget figures at',
      'different stages and they are far apart. A series that takes whichever number each',
      'document happens to lead with is a walk across stages, not a trend.',
      '',
      'Each line gets the same two tests. The growth rate itself is the ordinary compound',
      'one:',
      '',
      formula('Growth rate = (last year ÷ first year) raised to the power of '
              '(1 ÷ number of years), minus 1'),
      '',
      '**Does the line follow a trend at all?** The "fit" column runs from 0 to 1 and',
      'measures how closely the years fall on a straight line. A figure near 1 means they',
      'do. **A figure near 0 means there is no trend to measure, and stating a growth rate',
      'anyway is a choice dressed up as a measurement.**',
      '',
      '**How much does the answer depend on where you start counting?** The last column is',
      'that same compound growth rate to FY27, worked from every possible starting year. A',
      'narrow band means the answer is robust. A band running from very negative to very',
      'positive means the "growth rate" is an artefact of the year you happened to pick.',
      '',
      table(['line', 'budgets', 'span', 'first', 'last', 'fit', 'direction',
             'growth rate', 'growth rate by starting year'],
            [trow('Paraprofessionals', sped.PARA_TREND),
             trow('Professional staff', sped.TEACHER_TREND),
             trow('Transportation', sped.TRANSPORT_TREND),
             trow('Out-of-district tuition', sped.tuition_trend())],
            'lrlrrrlrl'),
      '',
      'Read the last row against the first. Same test, same arithmetic, opposite verdicts:',
      f'paraprofessionals fit a trend at {sped.PARA_TREND["r2"]:.2f} and are grown at what',
      f'they have actually done. Tuition fits at {sped.tuition_trend()["r2"]:.2f} and is',
      'held flat. That comparison **is** the argument, which is why both are published.',
      '')

    units, blend = sped.contract_blend()
    w('### The rate we do use',
      '',
      'There is no special education bargaining unit. Professional staff are on the',
      'teachers’ agreement and paraprofessionals on their own; the buses are a vendor',
      'contract, and substitutes and supplies are not bargained at all. So the rate is a',
      'weighted average of contracts signed for other reasons.',
      '',
      formula('Rate = the sum, across the parts, of',
              '  (that part’s share of the line × that part’s own growth rate)'),
      '',
      '**Each part grows at its contract where a contract governs it and the line has',
      'behaved accordingly, and at what it has measurably done where no contract reaches',
      'it.** Which of those applies is decided by the test above, not by preference.',
      '',
      table(['part', 'FY27 amount', 'share of the line', 'grows at', 'basis'],
            [[u['label'], usd(u['amount']), pct(u['share'], 1), pct(u['rate']),
              u['basis']] for u in units]
            + [['**Blended rate**', '', '', f'**{pct(blend)}**', '']],
            'lrrrl'),
      '',
      '**Two published contract rates are deliberately not used, and it cuts both ways.**',
      f'The teachers’ agreement gives {pct(sped.LEA_RATE, 1)} and this line has run *below*',
      'it — which means headcount here has been drifting down, and using the contract rate',
      'would have overstated this component. The paraprofessionals’ agreement gives',
      f'{pct(sped.AFSCME_RATE, 1)}, and ten budgets show the line growing',
      f'{pct(sped.PARA_TREND["cagr"])} a year, because no pay settlement governs how many',
      'people are employed. Pricing them at their contract assumes the district stops',
      'adding them.',
      '')

    w('### The range, published beside the rate',
      '',
      'Five defensible answers to the same question. The one we use is neither the highest',
      'nor the lowest, and anyone who prefers a different one can see what it costs.',
      '',
      table(['rate', 'reading', 'what it is'],
            [[f'**{pct(r["rate"])}**' + ('  ← used' if r.get('used') else ''),
              r['label'], r['what']] for r in sped.RANGE],
            'lll'),
      '',
      '### What we assumed, and what would settle it',
      '',
      '- **We assume the FY27 hiring was a one-time step and not the first year of a',
      '  climb.** If more paraprofessionals are hired every year — because more children',
      '  arrive needing one, or because the ones here need more — this rate is too low and',
      '  the projection understates the gap.',
      '- **A budget line is dollars, not people.** Nothing here shows headcount. The',
      '  budget shows none. Two sources do and neither settles it: DESE publishes',
      '  paraprofessional FTE per district and year with no school or classification, and',
      '  the town prints per-school staff rosters by name in every annual report,',
      '  FY2011-FY2025, with no FTE (/data/staff-roster-entries.csv). So "the line grew"',
      '  still cannot be turned into',
      '  "the district employs more paraprofessionals" without inventing the step between.',
      '- **This is the one that carries the most weight.** This rate rests on a',
      '  paraprofessional line, and a line that rises because a grant ended looks exactly',
      '  like a line that rises because the district grew. **What would settle it is the',
      '  state’s End of Year Financial Report**, which separates spending by fund. We do',
      '  not hold it, and it is the single most valuable document this project is missing.',
      '- **The classification is ours.** Anyone who draws the boundary differently gets a',
      '  different total and a different blended rate.',
      '')


# ==================================================  5. OUT-OF-DISTRICT TUITION
def s_tuition():
    t = sped.tuition_trend()
    hist = sped.tuition_history()
    risk = sped.tuition_risk()
    w('---',
      '',
      '## 5. Out-of-district tuition, and why we grow it at zero',
      '',
      '### The question',
      '',
      'What should a line be grown at when eleven years of it show no direction at all?',
      '',
      '### What the eleven years show',
      '',
      'The same test as Section 4, on the district’s own budget documents back to FY17,',
      'always at the same budget stage. Three of those years reproduce the FY27 workbook',
      'exactly, which is what makes the other eight worth trusting.',
      '',
      table(['measurement', 'value'],
            [['Budgets', t['n']],
             ['Span', f"FY{t['firstFy']} to FY{t['lastFy']}"],
             ['Lowest', f"{usd(t['low'])} (FY{t['lowFy']})"],
             ['Highest', f"{usd(t['high'])} (FY{t['highFy']})"],
             ['Highest over lowest', f"{t['ratio']:.2f} times"],
             ['Years up / years down', f"{t['up']} / {t['down']}"],
             ['Fit to a straight line', f"{t['r2']:.2f}"],
             ['Growth rate, first year to last', pct(t['cagr'])],
             ['Growth rate, depending where you start',
              f"{pct(t['cagrLow'])} to {pct(t['cagrHigh'])}"]],
            'lr'),
      '',
      f'**A figure that swings from {pct(t["cagrLow"])} to {pct(t["cagrHigh"])} depending',
      'on the year you start counting is not a measurement of anything.** Publishing the',
      f'first-to-last rate of {pct(t["cagr"])}, because FY{t["firstFy"]} happens to be the',
      'earliest year our archive reaches, would be an arbitrary choice wearing a',
      'measurement’s clothes.',
      '',
      f'So the rate is **{pct(sped.TUITION_RATE, 1)}**, and that is a finding rather than a',
      'gap in the work. It says: nobody can say which way this line moves next.',
      '',
      table(['FY', 'private placements', 'collaboratives', 'total', 'stage'],
            [[f"FY{h['fy']}", usd(h['private']), usd(h['collaborative']),
              usd(h['total']), h['stage']] for h in hist],
            'lrrrl'),
      '',
      '### The risk is priced, not hidden',
      '',
      'A slider here would invite a reader to pick whichever number suits their argument,',
      'and the honest answer is that nobody knows which is right. So instead the range is',
      'priced: each row below re-runs the whole projection with tuition set to that amount.',
      '',
      table(['scenario', 'tuition', 'FY28 gap', 'against the budgeted figure'],
            [[r['label'], usd(r['tuition']), usd(r['gap']),
              ('—' if not r['delta'] else '+' + usd(r['delta']))] for r in risk],
            'lrrr'),
      '',
      f'The full width of that range is {usd(risk[-1]["gap"] - risk[0]["gap"])} of FY28',
      'gap. It is the widest single-assumption range anywhere in this model.',
      '',
      '### What we assumed, and what would settle it',
      '',
      '- **Holding a line flat is itself a bet**, not a neutral act. We chose it because',
      '  every alternative rate turned out to be an artefact of a start year, and the risk',
      '  is carried in the table above instead of buried inside a growth rate.',
      f'- **Dollars are not children.** A {pct(sped.level_service_year()["tuition_rate"], 0)}',
      '  move in this line could be fewer placements, or a more honest estimate after',
      '  years of over-budgeting, or the same children at different rates. A budget cannot',
      '  tell those apart. **What would settle it is a count of out-of-district placements',
      '  by year**, which nobody publishes.',
      '')


# =====================================================  6. HEALTH INSURANCE
def s_health():
    total = sum(health.plan_cost(p, health.DEFAULT_ENROLMENT.get(p['id'], 0))['total']
                for p in health.PLANS)
    hl = next(l for l in levers.LEVERS if l['id'] == 'health_design')
    w('---',
      '',
      '## 6. Health insurance',
      '',
      '### The question',
      '',
      f'Health insurance is {pct(weight("health"), 1)} of the school budget and grows at',
      f'{pct(A["health"], 1)}, so it contributes {pull("health") * 100:.2f} points — the',
      'largest single contribution to the gap relative to its size. What can actually be',
      'done about it, and what does each option cost an employee?',
      '',
      '### What goes in',
      '',
      'Premiums from the Town’s open enrolment notice of 21 April 2026. Rates rose',
      f'{pct(health.RATE_INCREASE_FY27)} for FY27. The Town pays',
      f'{pct(health.TOWN_SHARE, 0)} of the premium and the employee',
      f'{pct(1 - health.TOWN_SHARE, 0)}.',
      '',
      table(['plan', 'network', 'deductible', 'family, monthly', 'individual, monthly',
             'employee pays, family', 'employee pays, individual'],
            [[p['name'], p['network'], p['deductible'], usd(p['family'], cents=True),
              usd(p['individual'], cents=True),
              usd(health.annual(p['family']) * (1 - health.TOWN_SHARE)),
              usd(health.annual(p['individual']) * (1 - health.TOWN_SHARE))]
             for p in health.PLANS],
            'lllrrrr'),
      '',
      '**One correction was made to the source, and it should be on the record.** In the',
      'rate letter, one plan has its individual and family labels transposed — the figure',
      'labelled "individual" is plainly the family rate, matching every other plan’s',
      'ratio. We corrected it. Silently fixing a source is how a reader ends up unable to',
      'reproduce a figure from the document it cites, so it is said out loud instead.',
      '')

    w('### The part that is ours, and it is substantial',
      '',
      '**How many employees are on which plan, at which tier, is not published.** The',
      'counts below are placeholders, and the tool on the site lets you change them.',
      '',
      'They are not arbitrary. They are set so that the Town’s',
      f'{pct(health.TOWN_SHARE, 0)} share reconciles to the health insurance line in the',
      f'school budget. At {sum(health.DEFAULT_ENROLMENT.values())} enrollees split',
      f'{pct(health.DEFAULT_FAMILY_SHARE, 0)} family and',
      f'{pct(1 - health.DEFAULT_FAMILY_SHARE, 0)} individual, total premium comes to',
      f'{usd(total)}, of which the Town’s share is {usd(total * health.TOWN_SHARE)} —',
      f'against a budgeted {usd(health.SCHOOL_HEALTH_BUDGET)}. That is a difference of',
      f'{usd(abs(total * health.TOWN_SHARE - health.SCHOOL_HEALTH_BUDGET))}, or',
      f'{pct(abs(total * health.TOWN_SHARE - health.SCHOOL_HEALTH_BUDGET) / health.SCHOOL_HEALTH_BUDGET)}.',
      '',
      '**But that only pins down the total, not the mix.** Which plans people are actually',
      'on is entirely our guess, and every per-plan figure below moves with it. They should',
      'be replaced with real counts before anybody relies on them.',
      '')

    rows = []
    for s in (0.72, 0.70, 0.65):
        r = health.split_change(s)
        bce = r['perPlan'][0]
        rows.append([f'{pct(s, 0)} town / {pct(1 - s, 0)} employee', usd(r['districtSaves']),
                     usd(bce['familyNow']), usd(bce['familyNew']),
                     '+' + usd(bce['familyDelta'])])
    w('### Shifting the contribution split',
      '',
      formula('District saves = total premium × (the change in the town’s share)'),
      '',
      '**It saves the district precisely what it costs employees.** There is no efficiency',
      'in this option — it is a transfer, and the site says so wherever it appears.',
      '',
      table(['split', 'district saves', 'employee on the broadest plan pays now',
             'would pay', 'change'], rows, 'lrrrr'),
      '')

    mig = health.migration_saving('bce', 'bs', 40)
    w('### Moving employees to a cheaper plan',
      '',
      formula('Saving = (the dearer annual premium − the cheaper one) × how many move,',
              '  worked separately for family and individual coverage'),
      '',
      'Moving 40 employees from the broadest plan to the narrower one saves',
      f'{usd(mig["total"])} of premium in total — {usd(mig["town"])} to the Town and',
      f'{usd(mig["employee"])} to the employees, who are also the ones accepting the',
      'narrower network.',
      '',
      '### The statutory giveback, which is easy to miss',
      '',
      'Plan design changes go through the Public Employee Committee under Chapter 32B,',
      f'sections 21 to 23, and **{pct(1 - hl["mitigation"], 0)} of first-year savings must',
      'go back to employees as mitigation.** The saving in year one is therefore',
      f'{pct(hl["mitigation"], 0)} of the headline figure:',
      '',
      ledger([
        ('Premium moved by shifting one percentage point', usd(hl['basis'] * 0.01)),
        (f'  less the {pct(1 - hl["mitigation"], 0)} statutory giveback',
         signed(-hl['basis'] * 0.01 * (1 - hl['mitigation']))),
        None,
        ('District keeps, in year one', usd(hl['basis'] * 0.01 * hl['mitigation'])),
      ]),
      '',
      'Our own health panel applied that and our savings tool did not, so for a while the',
      f'two answered {pct(1 / hl["mitigation"] - 1, 0)} apart for the same change. Both',
      'apply it now.',
      '',
      '### What we assumed, and what would settle it',
      '',
      *[f'- {c}' for c in health.CONSTRAINTS[1:]],
      f'- **The {pct(A["health"], 1)} growth rate is the district’s own stated assumption**,',
      f'  not a measurement we made. Premiums themselves rose only',
      f'  {pct(health.RATE_INCREASE_FY27)} for FY27 — well under it — because the rate',
      '  covers the whole line, including how many people enrol and at which tier, not the',
      '  premium alone.',
      '- **What would settle the per-plan figures is enrolment by plan and tier.** One',
      '  table that nobody publishes.',
      '')


# ============================================================  7. FREE CASH
def s_freecash():
    fc = freecash
    w('---',
      '',
      '## 7. Free cash',
      '',
      '### A note on why this section exists at all',
      '',
      'Everything else in this projection is built from budget figures. Free cash is the',
      'opposite kind of number — it is what is left over once the year is done, which makes',
      'it an actual.',
      '',
      'We said at the top that the two must never be combined inside one calculation. Here',
      'is how this does not break that rule: free cash is applied as a **one-time',
      'subtraction after every growth rate has already run**. It touches no budget group,',
      'no growth rate, and it never carries into the next year’s base. The difference',
      'between "a growth rate measured across that boundary" and "a labelled one-time',
      'amount taken off at the end" is the whole of why this is allowed. It is checked',
      'automatically at nine different draw levels, and the build fails if enabling free',
      'cash moves anything it should not.',
      '')

    w('### What goes in',
      '',
      table(['figure', 'value', 'label', 'source'],
            [['Certified free cash, 1 July 2025', usd(fc.CERTIFIED),
              KIND_MARK['published'], 'State Division of Local Services free cash proof'],
             ['Identified before deductions', usd(fc.IDENTIFIED),
              KIND_MARK['published'], 'The same proof'],
             ['Unspent appropriations, 2025', usd(fc.UNSPENT_2025),
              KIND_MARK['published'], 'The same proof, one component of it'],
             ['Unspent appropriations, 2021–24 average', usd(fc.UNSPENT_AVG_2021_24),
              KIND_MARK['measured'], 'Averaged from the four prior years of the proof'],
             ['Operating budget', usd(fc.BUDGET_BASE), KIND_MARK['published'],
              'FY26 original appropriation'],
             ['Recommended range', f'{pct(fc.BAND_LOW, 0)}–{pct(fc.BAND_HIGH, 0)}',
              KIND_MARK['published'], 'The Town’s own FY27 budget release, quoting DLS']],
            'lrll'),
      '',
      '**Three different figures are all called "the operating budget", and none of them',
      f'is the same number.** {usd(fc.BUDGET_BASE)} as originally appropriated,',
      f'{usd(fc.BUDGET_REVISED)} as revised at the third quarter, and',
      f'{usd(fc.TOWN_IMPLIED_BASE)} implied by the Town’s own published figure of',
      f'{pct(0.0665)}, which we cannot reproduce. No conclusion turns on the difference —',
      'every version lands inside the recommended range — but a ratio quoted to two decimal',
      'places should not rest on a soft denominator without saying so.',
      '',
      '**The recommended range comes from one document, and it carries weight.** It appears',
      'once in everything we hold: the Town’s own budget release, quoting the state. We',
      'hold no state publication saying it. That matters, because at a lower threshold the',
      'same balance is *above* the range rather than comfortably inside it. So the caveat',
      'travels with the figure everywhere it is used.',
      '',
      '**A dating trap, confirmed rather than assumed.** The state dates free cash to the',
      '1 July on which it is certified. The Town dates the same money to the fiscal year it',
      'can be spent in. **They are one year apart.** Lunenburg’s three largest certified',
      'balances are 2021, 2022 and 2025; add one to each and you get exactly the three',
      'years the Town names as its good ones.',
      '')

    w('### How much there is, as a share',
      '',
      formula('Share = certified free cash ÷ operating budget'),
      '',
      ledger([
        ('Certified free cash', usd(fc.CERTIFIED)),
        ('Operating budget', usd(fc.BUDGET_BASE)),
        None,
        ('Free cash as a share of the budget', pct(fc.share())),
      ]),
      '',
      f'Inside the {pct(fc.BAND_LOW, 0)}–{pct(fc.BAND_HIGH, 0)} range, near the top of it.',
      '')

    w('### What a normal year produces — the most important figure here',
      '',
      '**The question:** is this balance a policy, or an event?',
      '',
      'Hold everything in the 2025 certification constant except the one component that',
      'moved, and carry the ratio between certified and identified across unchanged.',
      '',
      ledger([
        ('Identified free cash, 2025', usd(fc.IDENTIFIED)),
        ('  less unspent appropriations in 2025', signed(-fc.UNSPENT_2025)),
        ('  plus unspent appropriations at their 2021–24 average',
         signed(fc.UNSPENT_AVG_2021_24)),
        None,
        ('Identified, in a normal year',
         usd(fc.IDENTIFIED - (fc.UNSPENT_2025 - fc.UNSPENT_AVG_2021_24))),
        (f'  × the certified-to-identified ratio of {fc.CERTIFIED_RATIO}', ''),
        None,
        ('Certified free cash, in a normal year', usd(fc.NORMAL_CERTIFIED)),
        ('As a share of the operating budget', pct(fc.NORMAL_SHARE)),
      ]),
      '',
      f'**A normal year produces {usd(fc.NORMAL_CERTIFIED)} — {pct(fc.NORMAL_SHARE)},',
      'below the bottom of the recommended range.** This year’s record exists because 2025',
      f'unspent appropriations were {fc.UNSPENT_2025 / fc.UNSPENT_AVG_2021_24:.2f} times',
      'the town’s own four-year average — the largest jump of the nine towns in the state’s',
      'proof:',
      '',
      table(['town', '2025 unspent, against its own 2021–24 average',
             'share of its free cash that is unspent appropriations'],
            [[t, f'{m:.2f} times', pct(_comp().get(t), 1)]
             for t, m in fc.PEER_MULTIPLES], 'lrr'),
      '',
      '**Two different measures, and they disagree in a way worth understanding.** The',
      'middle column asks how unusual 2025 was *for that town*, and on it Lunenburg is the',
      'clear outlier. The right-hand column asks what the balance is *made of*, and on that',
      f'Lunenburg is the highest of the nine at {pct(_comp()["Lunenburg"], 1)} — but inside',
      f'a cluster, with {_comp_near()} not far behind. A balance built out of money',
      'appropriated and not spent is a different thing from one built out of revenue',
      'beating forecast, and it implies a different remedy.',
      '',
      '**What this table deliberately does not show, and cannot.** The obvious question is',
      'how each town’s free cash sits against the same 5–7% range, and that needs each',
      'town’s operating budget. **The state’s proof carries no denominator** — no',
      'population, budget, revenue or levy for any of the nine, Lunenburg included. So',
      f'Littleton’s {usd(_ident("Littleton"))} against Shirley’s {usd(_ident("Shirley"))}',
      'says nothing about which is closer to its own target, and a percentage-of-budget',
      'column here would be invented rather than measured. Composition is shown instead,',
      'because a share compares across towns of different size and an absolute dollar',
      'figure does not.',
      '',
      '**What would settle it:** each town’s operating budget for the same years, from the',
      'state’s municipal finance databank. It is obtainable, and we have not obtained it.',
      '',
      '**The state certifies less than it identifies, and we do not hold the reason.** So',
      'that gap is carried across as an observed ratio rather than explained. It is an',
      'input to the figure above, and it is measured rather than understood.',
      '')

    w('### What drawing the balance down would release',
      '',
      formula('Released once = certified free cash − (operating budget × share kept back)'),
      '',
      table(['draw the balance down to', 'which is', 'releases, once'],
            [[pct(t, 0), lab, usd(max(fc.spendable(t), 0))]
             for t, lab in fc.POLICY_STOPS], 'llr'),
      '',
      f'**{usd(fc.spendable(fc.BAND_LOW))} is the headline figure** — what could be',
      'redirected while the retained balance stays inside the range the Town itself quotes.',
      '')

    w('### One-off against policy, and the two must never be blurred',
      '',
      'Two completely different quantities, and running them together is the most common',
      'error in this argument:',
      '',
      '- **Drawing the balance down to a lower target releases the accumulated balance',
      '  ONCE.**',
      '- **Holding it there releases the annual flow EVERY year — and that annual figure',
      '  does not depend on the target at all.** A lower target does not generate more',
      '  money. It releases the accumulated balance sooner, and after that you are living',
      '  on the flow either way.',
      '',
      f'The flow is what a normal year produces: **{usd(fc.SUSTAINABLE_DRAW)}**.',
      '',
      '**And here is the difficulty, which is the honest answer to "just be less',
      'conservative".** The flow is produced *by* the underspending. Two thirds of the 2025',
      'balance is money appropriated and not spent. Budget more tightly and you shrink the',
      'gap — and you shrink the free cash you were going to fill it with. You cannot count',
      'both.',
      '')

    ladder = fc.policy_ladder(
        lambda years, free_cash: finance.project(years, A, free_cash=free_cash))
    w('Six years of gap under each policy:',
      '',
      table(['keep in reserve', 'which is', 'released once', 'plus, every year',
             'gap remaining, one-off only', 'gap remaining, with the policy'],
            [[pct(r['target'], 0), r['label'], usd(r['oneTime']), usd(r['annual']),
              usd(r['gapLeftOneTimeOnly']), usd(r['gapLeftWithPolicy'])]
             for r in ladder], 'llrrrr'),
      '')

    oc = fc.override_contrast(
        lambda years, free_cash: finance.project(years, A, free_cash=free_cash),
        LEVY_CAP, fc.spendable(fc.BAND_LOW))
    w('### Free cash against an override — a one-off against a permanent change',
      '',
      'The clearest single comparison in this project. The same dollars, once, against the',
      'same dollars permanently.',
      '',
      formula('Free cash lands in one year and is gone.',
              f'An override raises the levy limit permanently, so its value in a later '
              f'year',
              f'  = the amount × {1 + LEVY_CAP} raised to the power of the years since.'),
      '',
      f'At {usd(oc["amount"])}:',
      '',
      table(['FY', 'gap', 'free cash applied', 'gap after free cash',
             'override worth', 'gap after override'],
            [[f'FY{r["fy"]}', usd(r['deficit']), usd(r['freeCashApplied']),
              usd(r['afterFreeCash']), usd(r['overrideValue']),
              usd(r['afterOverride'])] for r in oc['years']],
            'lrrrrr'),
      '',
      table(['six-year total gap', 'amount'],
            [['Doing nothing', usd(oc['cumulativeNone'])],
             ['With the free cash draw', usd(oc['cumulativeFreeCash'])],
             ['With an override of the same size', usd(oc['cumulativeOverride'])]],
            'lr'),
      '',
      '**Note what this shows, and what it must not be made to say.** An override of this',
      f'size does not close the gap either. It grows at {pct(LEVY_CAP, 1)} while the gap',
      'grows faster, so it loses ground every year. Only a change in the cost growth rates',
      'changes the direction.',
      '')

    cap = fc.capital_consequence()
    w('### What redirecting free cash would cost the capital programme',
      '',
      '**Free cash is the capital programme’s money.** Saying an amount is "available',
      'within the guideline" without saying that is half the story.',
      '',
      table(['figure', 'value', 'source'],
            [['FY27 funded capital programme', usd(cap['programmeTotal']),
              'The FY27 capital plan'],
             ['Planned from free cash, FY27', usd(cap['plannedFromFreeCash']),
              'Annual Town Meeting warrant, Article 13'],
             ['Planned from taxation', usd(cap['plannedFromTaxation']),
              'The capital plan, funding page'],
             ['Planned from the Vehicle Use Stabilization Fund',
              usd(cap['restrictedTotal']), 'The same funding page'],
             ['Average free cash into capital, ten years',
              usd(cap['averageFromFreeCash']), 'The plan’s own Average row'],
             ['Ranked, costed, and already unfunded',
              f"{usd(cap['queueValue'])} across {cap['queueCount']} projects",
              'The same plan, below the funding line']],
            'lrl'),
      '',
      f'**A third of the programme was never school money.** {usd(cap["restrictedTotal"])}',
      'is the Vehicle Use Special Purpose Stabilization Fund, adopted at the 2017 Annual',
      'Town Meeting for vehicles and equipment and requiring a two-thirds vote. Cancelling',
      'what it pays for frees nothing for the schools. **So a draw can strand',
      f'{usd(cap["convertibleTotal"])}, not the whole programme.** An earlier version of',
      'this model took projects off the bottom of the full funded list and stranded a front',
      'end loader with free cash that had never been paying for it.',
      '',
      '**How that assignment is known**, since no project-by-project funding table is',
      'published: the plan footnotes exactly two projects as funded from that stabilization',
      f'fund, and they come to exactly the {usd(cap["restrictedTotal"])} its own funding',
      'page shows against it. That is a reconciliation, not a guess, and the model refuses',
      'to run if it ever stops tying.',
      '',
      table(['restricted project', 'rank', 'cost'],
            [[f"{i['dept']} — {i['project']}", i['rank'], usd(i['cost'])]
             for i in cap['restrictedItems']], 'lrr'),
      '')

    w('#### The dollars are exact. Which projects stop is a range.',
      '',
      'Two different quantities, and they are kept apart.',
      '',
      '**Dollars** need no assumption. Redirect an amount and the programme is funded by',
      'that much less. There is a queue of ranked, costed, unfunded work worth',
      f'{usd(cap["queueValue"])}, so no dollar removed creates slack anywhere.',
      '',
      '**Which projects stop** is a claim about how the Capital Planning Committee would',
      'behave, and it is reported as a range between two behaviours:',
      '',
      '- **Holding the ranking rigid** — take projects off the bottom of the published list',
      '  until the money is found. Because projects are indivisible, this overshoots.',
      '- **Re-sequencing** — drop whatever combination comes closest to the money removed.',
      '',
      table(['redirect', 'dollars out', 'holding the ranking', 're-sequencing',
             'projects stopped'],
            [[usd(d['redirect']), usd(d['lost']), usd(d['strictLost']),
              usd(d['resequencedLost']), len(d['projects'])]
             for d in cap['atDraw'] if d['redirect'] > 0],
            'rrrrr'),
      '',
      '**The difference between those two columns is not a cost.** It is the price of',
      'assuming projects are indivisible and the order cannot change. One rank in the',
      'middle of the list is a large roof with only a little below it, so any draw that',
      'reaches it removes the whole roof whether it needed to or not.',
      '',
      '**Nothing here establishes which of the two actually happens.** We hold no instance',
      'of the committee re-ranking after a funding cut. The published ranking is evidence',
      'of preference, not of procedure.',
      '')

    hist = cap['history']
    w('#### The draw against what capital normally receives',
      '',
      f'The {usd(cap["redirectCeiling"])} ceiling exceeds the *whole year’s* free cash',
      f'contribution to capital in {cap["yearsRedirectExceedsFreeCash"]} of the',
      f'{cap["yearsCovered"]} years the plan’s own table covers:',
      '',
      table(['FY', 'whole capital programme', 'of which free cash'],
            [[f"FY{h['fy']}", usd(h['total']), usd(h['freeCash'])] for h in hist],
            'lrr'),
      '',
      'That is the capital-side twin of the normal-year finding. The draw is affordable in',
      'this year and in few others.',
      '',
      '### What we assumed, and what would settle it',
      '',
      '- **The recommended range is one sentence written by one party to the argument.**',
      '  What would settle it is the state’s own published guidance.',
      '- **The normal-year figure holds every other component constant.** It is a',
      '  counterfactual on one line, not a forecast.',
      '- **The certified-to-identified ratio is carried across unexplained.**',
      '- **Which departments turned the money back is not published** — there is a',
      '  town-wide total and no breakdown. That is the difference between a structural',
      '  pattern and a run of one-offs, and we cannot tell which this is.',
      '- **Free cash is one-time by construction**, and the state’s own guidance is that it',
      '  should not fund ongoing operations. Everything above is a deferral of the gap, not',
      '  a closing of it.',
      '')


# ============================================================  8. ATHLETIC FEES
def s_athletics():
    at = athletics
    cur = at.CURRENT_ATHLETIC_FEES
    w('---',
      '',
      '## 8. Athletic fees',
      '',
      'The most heavily corrected calculation in this project, and the section where a',
      'reader will find the most explicit statements of what we got wrong.',
      '',
      '### The question',
      '',
      'What do athletic user fees raise now, and what fee would make the programme pay for',
      'itself?',
      '',
      '### What goes in',
      '',
      table(['figure', 'value', 'label', 'source'],
            [['2026-27 fee schedule',
              ' / '.join(f'{usd(v)} {k}' for k, v in cur['tiers'])
              + f", family cap {usd(cur['familyCap'])}",
              KIND_MARK['published'], 'Superintendent’s email to families, August 2026'],
             ['2025-26 schedule',
              f"{usd(at.FY26_ATHLETIC_FEES['hsFullPay'])} high school, "
              f"{usd(at.FY26_ATHLETIC_FEES['msFullPay'])} middle school, "
              f"{at.FY26_ATHLETIC_FEES['siblingDiscountPct']}% sibling discount",
              KIND_MARK['published'],
              'School Committee vote, 26 February 2025, by roll call'],
             ['High school participations', num(at.HS_PARTICIPATIONS),
              KIND_MARK['published'], 'District planning roster'],
             ['Middle school participations', num(at.MS_PARTICIPATIONS),
              KIND_MARK['published'], 'The same roster'],
             ['Fee revenue actually collected, FY26',
              usd(at.MEASURED_FY26_FEE_REVENUE, cents=True), KIND_MARK['measured'],
              'The athletics revolving fund’s own year-end reconciliation'],
             ['Mix of first, second and third children',
              ' / '.join(f'{pct(v, 1)}' for _, v in at.SIBLING_MIX),
              KIND_MARK['measured'],
              'Counted from the district’s own by-sport workbook. See below'],
             ['Fee waivers', pct(at.WAIVER_ASSUMPTION, 0), KIND_MARK['ours'],
              'Free-lunch families are waived. Still our estimate'],
             ['Drop-off as the fee rises',
              f'{at.FEE_DROPOFF_PER_100:.0f}% of participation per $100',
              KIND_MARK['ours'], 'Our assumption. No local figure has ever been measured']],
            'lrll'),
      '',
      '**Only high school participations can be charged** —',
      f'{num(at.CHARGEABLE_PARTICIPATIONS)}, not the full {num(at.PARTICIPATIONS)}. You',
      'cannot charge a fee for a team that does not exist, and the middle school and',
      'freshman coaching line is zero in both the level-service and the adopted budget, so',
      'those teams do not run in FY27.',
      '')

    w('### What the average participation actually pays',
      '',
      'A published schedule is a set of tiers. What matters for revenue is the average',
      'across them.',
      '',
      formula('Average fee = the sum, across the tiers, of',
              '  (that tier’s fee × the share of participations paying it)'),
      '',
      ledger(
        [(f'{usd(v)} for a {k}, at {pct(w_, 1)} of participations',
          usd(v * w_, cents=True))
         for (k, v), (_, w_) in zip(cur['tiers'], at.SIBLING_MIX)]
        + [None, ('Average fee per participation', usd(at.EFFECTIVE_ATHLETIC_FEE))]),
      '',
      'The family cap does not bite. Three children at the current tiers comes to',
      f'{usd(sum(v for _, v in cur["tiers"]))}, under the {usd(cur["familyCap"])} cap, so',
      'only a fourth participating child would reach it.',
      '')

    w('### What the fund actually collected, and the correction it forced',
      '',
      'This is the important part, and it is a correction to our own arithmetic.',
      '',
      ledger([
        ('What our model produces for FY26', usd(at.MODELLED_FY26_FEE_REVENUE)),
        ('What the fund reports collecting, gross',
         usd(at.MEASURED_FY26_FEE_REVENUE_GROSS, cents=True)),
        ('  net of refunds', usd(at.MEASURED_FY26_FEE_REVENUE, cents=True)),
        None,
        ('The model produces less than the fund collected, by',
         usd(at.MEASURED_FY26_FEE_REVENUE - at.MODELLED_FY26_FEE_REVENUE, cents=True)),
        ('  as a share of what the fund collected',
         pct(1 - at.MODELLED_FY26_FEE_REVENUE / at.MEASURED_FY26_FEE_REVENUE)),
        ('  as a share of what the model produces',
         pct(at.MEASURED_FY26_FEE_REVENUE / at.MODELLED_FY26_FEE_REVENUE - 1)),
      ]),
      '',
      '**What the receipts imply each participation paid**, against the rate the School',
      'Committee voted for that year:',
      '',
      table(['', 'gross receipts', 'participations', 'implied per participation',
             'the rate that was voted'],
            [['High school', usd(at.MEASURED_FY26_HS_GROSS, cents=True),
              num(at.FY26_HS_PARTICIPATIONS),
              usd(at.MEASURED_FY26_HS_PER_PARTICIPATION, cents=True),
              usd(at.FY26_ATHLETIC_FEES['hsFullPay'])],
             ['Middle school', usd(at.MEASURED_FY26_MS_GROSS, cents=True),
              num(at.FY26_MS_PARTICIPATIONS),
              usd(at.MEASURED_FY26_MS_PER_PARTICIPATION, cents=True),
              usd(at.FY26_ATHLETIC_FEES['msFullPay'])]],
            'lrrrr'),
      '',
      '**Both sit under the voted rate, and that matters, because this project used to say',
      'they did not.** When we priced FY26 on the previous year’s schedule — a right number',
      'from the wrong year — the implied rates came out *above* the undiscounted fee, which',
      'is arithmetically impossible, and we treated that as proof that a count somewhere',
      'was wrong. Correcting the fee to what was actually voted removed the impossibility.',
      'Nothing about the fund’s figures changed. Ours did.',
      '',
      '**What remains is an ordinary disagreement, and it is not settled.** Our assumed',
      'waiver rate discounts the published schedule by a little more than the receipts',
      'imply. Fewer waivers, participations undercounted, or sport surcharges outside any',
      'schedule we hold — ice hockey and skiing normally carry them — all fit the same',
      'figures.',
      '',
      '**So the model is anchored to the measurement rather than corrected to it**, and the',
      'adjustment is named rather than buried. Anchoring on what was actually collected is',
      'right, because it is the only observed figure. Carrying that adjustment forward to a',
      'fee this town has never charged is an assumption, and it is labelled as one',
      'everywhere it is used.',
      '',
      '**The two explanations imply different answers, so both are carried:**',
      '',
      table(['reading', 'what it assumes', 'how revenue behaves as the fee rises'],
            [['Cautious', 'There are surcharges outside the published schedule',
              'A surcharge does not rise when the base fee rises, so the difference stays '
              'a fixed amount'],
             ['Generous', 'The chargeable base is larger than we think',
              'The difference grows in proportion with the fee']],
            'lll'),
      '',
      'Both reproduce FY26 exactly, by construction. They separate as the fee rises, and',
      'the cautious one is what the site leads with.',
      '')

    w('### The sibling mix was invented, and is now counted',
      '',
      'The clearest example in this project of an assumption being **retired** rather than',
      'defended, so the whole path is set out.',
      '',
      '**What it was.** '
      + ' / '.join(f'{pct(v, 0)} {k}' for k, v in at.PRIOR_SIBLING_MIX)
      + ' — declared openly as ours, and supported by nothing. Searching every',
      'document in the meeting archive finds the word "sibling" in two of them, and the',
      'only athletics one is the School Committee vote of 26 February 2025, which sets the',
      f'**discount rate** at {pct(at.FY26_ATHLETIC_FEES["siblingDiscountPct"] / 100, 0)}',
      'and says nothing about how many participations receive it. Those are different',
      'quantities — how much comes off, against how many people get it — and the closeness',
      'of the two figures is the likeliest explanation for where the estimate came from.',
      'That is a hypothesis, and nothing here tests it.',
      '',
      '**What it is now.** The district’s own by-sport workbook, obtained by records',
      'request, records the fee category of every participation, and those categories add',
      'up to its own total — so it is this quantity exactly, not a substitute for it.',
      '',
      table(['category', 'participations', 'share'],
            [[lab, num(v), pct(v / at.MEASURED_CATEGORY_TOTAL, 2)]
             for lab, v in at.MEASURED_FEE_CATEGORIES]
            + [['**Total**', f'**{num(at.MEASURED_CATEGORY_TOTAL)}**', '']],
            'lrr'),
      '',
      f'**Coverage, stated rather than implied.** {at.MEASURED_SPORT_YEARS} sport-years and',
      f'{num(at.MEASURED_CATEGORY_TOTAL)} participations — meaning every sport, in every',
      'year, whose fee categories add up to the total the workbook itself prints for that',
      'sport. Rows that do not add up are left out, because where they disagree there is no',
      'way to tell which figure is wrong. Three reasons they disagree, and only the first',
      'would be ours to fix:',
      '',
      '- **The workbook mixes units.** One sheet’s total row multiplies the counts by the',
      '  fee and prints dollars, while the rows above it are counts of children. A few',
      '  individual entries carry dollars in a column that otherwise holds counts.',
      '- **Some of its totals are off by one** against the rows above them.',
      '- **The 2025-26 fee-category columns are empty throughout**, which is why a separate',
      '  one-page count sheet had to exist at all.',
      '',
      'Every one of those mismatches is published rather than hidden or quietly repaired,',
      'because those totals are wrong in the source document, and that is a fact about the',
      'document rather than a defect in our reading of it.',
      '',
      '**Two sources, two different years, one answer.** The workbook covers FY2024 and',
      'FY2025. The one-page count sheet covers FY2026, the year the workbook leaves blank.',
      'They are consecutive readings rather than a check on each other:',
      '',
      table(['source', 'year', 'took a sibling discount', 'received a full waiver'],
            [['By-sport workbook', 'FY2024–FY2025',
              pct(at.MEASURED_SIBLING_SHARE, 1), pct(at.MEASURED_WAIVER_SHARE, 1)],
             ['One-page count sheet', 'FY2026',
              pct(at.FY26_COUNTED_SIBLING_SHARE, 1), pct(at.FY26_COUNTED_WAIVER_SHARE, 1)],
             ['What we used to assume', '—',
              pct(sum(w for r, w in at.PRIOR_SIBLING_MIX if r != '1st child'), 0),
              pct(at.WAIVER_ASSUMPTION, 0)]],
            'llrr'),
      '',
      '**The waiver estimate survived. The sibling one did not.** One invented figure turned',
      'out close, and the other was out by roughly a factor of four.',
      '',
      '**Why correcting it moved the published figures less than you would expect.** The fee',
      'model is anchored to what the fund actually collected, so raising what the model',
      'produces lowered the adjustment by nearly as much, and the two offset. Revenue at',
      'today’s fee barely moved; the average fee moved several percent. **That is exactly',
      'why an input wrong by a factor of four survived as long as it did — nothing in the',
      'output looked wrong.** The figure that did improve is the unexplained difference,',
      'which is the thing the adjustment represents.',
      '',
      '**What it still does not establish.** Two years, neither of them the year the current',
      'fee schedule applies to. If the new schedule and the larger family cap change how',
      'many families enrol a second child, this mix moves and nothing here would show it.',
      '')

    w('### What happens as the fee rises',
      '',
      'Raising a fee raises more per family and prices some families out, so revenue rises,',
      'peaks, and then falls.',
      '',
      formula('Revenue = fee × chargeable participations × (1 − the waiver rate) × '
              'the share who stay',
              f'where the share who stay = 1 − (the increase ÷ $100) × '
              f'{at.FEE_DROPOFF_PER_100:.0f}%'),
      '',
      table(['fee per season', 'revenue, cautious reading', 'revenue, generous reading'],
            [[usd(f), usd(at.fee_revenue(f, mode='flat')),
              usd(at.fee_revenue(f, mode='scaled'))]
             for f in (at.EFFECTIVE_ATHLETIC_FEE, 500, 700, 900, 1100, 1300)],
            'rrr'),
      '',
      f'**Revenue peaks at about {usd(at.PEAK_FEE)} a season and roughly',
      f'{usd(at.PEAK_REVENUE)}.** Anything above that is unreachable at any price, which is',
      'the most useful single thing this curve says.',
      '')

    tgt = at.PROGRAM_TOTAL_TRAVEL
    rng = at.self_funding_range(tgt)
    w('### What self-funding would take',
      '',
      f'The adopted budget funds {usd(at.PROGRAM_TOTAL_ADOPTED)} of athletics **and no',
      f'athletic transportation at all.** Put the {usd(at.ATHLETIC_TRANSPORTATION)} of',
      'buses back — a team that cannot reach an away game is not a team — and the cost of',
      f'fielding these teams is {usd(tgt)}.',
      '',
      table(['target', 'covered at today’s fee', 'fee that would cover it'],
            [['The adopted budget, no buses',
              f"{pct(at.fee_revenue(at.EFFECTIVE_ATHLETIC_FEE) / at.PROGRAM_TOTAL_ADOPTED)}",
              f"{usd(at.self_funding_range(at.PROGRAM_TOTAL_ADOPTED)['low'])}–"
              f"{usd(at.self_funding_range(at.PROGRAM_TOTAL_ADOPTED)['high'])}"],
             ['With athletic transportation restored',
              f"{pct(at.fee_revenue(at.EFFECTIVE_ATHLETIC_FEE) / tgt)}",
              f"{usd(rng['low'])}–{usd(rng['high'])}"]],
            'lrr'),
      '',
      '**Two figures rather than one**, because the data cannot say which reading of the',
      'collection difference is right, and a single number on a page asking families to pay',
      'it would be a false precision.',
      '',
      '### What we assumed, and what would settle it',
      '',
      '- **The waiver rate is still ours.** Free-lunch families have the fee waived; the',
      '  district does not publish how many.',
      '- **The drop-off as fees rise is ours.** No local figure has ever been measured. It',
      '  is a shape, not a finding.',
      '- **The adjustment carries a measured FY26 difference forward to fees this town has',
      '  never charged.** That is the largest assumption in this section.',
      '- **The sibling mix is no longer ours**, but it is measured over two years that are',
      '  not the year the current schedule applies to.',
      '- **A budget line is not what athletics costs.** The district published athletics',
      '  against the revolving fund once, for FY19. In FY26 the general fund and the fund',
      f'  together came to {usd(at.ALL_IN_FY26, cents=True)}, of which the fee-funded fund',
      f'  paid {pct(at.FUND_SHARE_FY26)}. The fee figures here are modelled against the',
      '  general fund programme because that is what the district publishes — which makes',
      '  them a floor rather than the cost.',
      '- **What would settle it: participation counts by fee category for the current year,',
      '  and the revolving fund’s own ledger by object code.**',
      '')


# ==============================================================  9. THE LEVERS
def s_levers():
    w('---',
      '',
      '## 9. The other savings and revenue options',
      '',
      'Each control on the site is one of four shapes, and the shape decides the',
      'arithmetic.',
      '',
      table(['shape', 'how it is worked out', 'used by'],
            [['A fee', 'The curve in Section 8, with its own drop-off rate',
              'Athletics, buses, activities'],
             ['A contribution split', 'The premium moved, less the statutory giveback',
              'Health insurance'],
             ['A percentage of a line', 'That share of the line, capped', 'Technology'],
             ['A list of named positions', 'The sum of the ones actually chosen',
              'Administration']],
            'lll'),
      '',
      '**Fee options are not interchangeable.** A bus rider stops paying sooner than an',
      'athlete does, so the drop-off differs between them.',
      '')

    rows = []
    for l in levers.LEVERS:
        basis = num(l['basis']) if l['basis'] < 10_000 else usd(l['basis'])
        rows.append([l['name'], l['kind'], basis,
                     '' if l.get('basisKnown', True) else '`ours`', usd(l['cap'])])
    w('### Every option, its base and its ceiling',
      '',
      table(['option', 'kind', 'base (people, or dollars)', 'base is',
             'most it can raise'], rows, 'lllll'),
      '',
      '**The ceiling is the point of that table.** Every one of these is bounded, and',
      'several are bounded well below the thing they are meant to pay for. General',
      f'education transportation costs {usd(levers.TRANSPORT_GENED)} and bus fee revenue',
      'peaks near '
      f'{usd(next(l for l in levers.LEVERS if l["id"] == "bus_fees")["peakYield"])}.',
      f'Special education transportation, at {usd(levers.TRANSPORT_SPED)}, cannot be',
      'charged for at all.',
      '',
      '**Two of the bases are ours and are placeholders** — how many students take part in',
      'activities, and how many ride the bus. The district publishes neither. Any figure',
      'resting on them moves with counts nobody has confirmed, and the site marks them.',
      '')

    w('### Administration, and why it is a list rather than a percentage',
      '',
      '**A percentage of administration is not a decision anybody can take.** Nobody votes',
      'to reduce administration by a percentage. They vote to stop funding a Human Resource',
      'Specialist, or they do not. So this is a list of real budget lines from the adopted',
      'FY27 budget, ordered from what a district can genuinely absorb to what it legally',
      'cannot give up.',
      '',
      '**The amounts are the district’s. The ordering is ours**, and it is stated as such.',
      '',
      ledger([
        ('Administration, every line', usd(levers.ADMIN_TOTAL)),
        ('  as a share of the school appropriation',
         pct(levers.ADMIN_TOTAL / F['lps_appropriation'], 1)),
        ('  of which central office', usd(levers.ADMIN_CENTRAL)),
        ('  of which the four principals’ offices', usd(levers.ADMIN_BUILDING)),
        None,
        (f'Positions a lawful budget could cut '
         f'({len(levers.ADMIN_RUNGS_CUTTABLE)} of {len(levers.ADMIN_RUNGS)})',
         usd(levers.ADMIN_LADDER_CAP)),
        ('  as a share of all administration',
         pct(levers.ADMIN_LADDER_CAP / levers.ADMIN_TOTAL, 0)),
      ]),
      '',
      '**The positions that cannot lawfully be cut are shown anyway, and flagged.** A',
      'superintendent, a business manager, a special education administrator and four',
      'principals are roles the Commonwealth requires. Refusing to show what cutting them',
      'would save reads as evasion rather than rigour, and "what would that even save?" is',
      'a question a resident is entitled to an answer to.',
      '',
      '**One deliberate omission.** The two technology lines that sit inside administration',
      'belong to the technology option and are not counted here. Counting a line in two',
      'places is how a model quietly closes the same gap twice.',
      '')


# ===========================================================  10. THE CASCADE
def s_cascade():
    ps = cascade.PRESETS['school_committee']
    res = cascade.run(ps['order'])
    fl = cascade.FLOOR_NOTE
    w('---',
      '',
      '## 10. What happens if the gap is closed by cutting',
      '',
      '### How it works',
      '',
      'Each year, programmes are cut from the bottom of a priority ranking upward until',
      'that year’s gap is closed. A cut permanently reduces the salary base, so it also',
      'lowers every later year’s cost.',
      '',
      '**That last point is the whole lesson.** A cut lowers the cost curve once and the',
      'curve then climbs at exactly the rate it was climbing before. The money saved never',
      'gets its raise either — and the gap still grows.',
      '',
      '### The four rankings',
      '',
      table(['ranking', 'what it is'],
            [[p['name'], p['why']] for p in cascade.PRESETS.values()], 'll'),
      '',
      f'Worked below with **{ps["name"]}** — the order Lunenburg itself sacrificed things',
      'across its own four FY27 scenarios, which is a revealed preference rather than a',
      'stated one.',
      '',
      '**The gap column here is not the gap column in Section 1.** There, each year',
      'assumes nothing was ever done. Here, each year is what remains after every earlier',
      'year has already been cut — which is why the figures are so much smaller. That',
      'difference is the whole argument for acting early rather than late.',
      '',
      table(['FY', 'shortfall that year, after earlier years have been cut', 'cut',
             'cumulative positions lost', 'still unclosed'],
            [[f'FY{y["fy"]}', usd(y['deficit']), usd(y['cut_total']), y['cum_fte'],
              usd(y['unclosed']) if y['unclosed'] else '—'] for y in res],
            'lrrrr'),
      '',
      '### Where the cutting stops, which is ours',
      '',
      '**What actually happens in the model:** any programme we have classified as legally',
      'mandated is skipped entirely. It appears in the year’s list, marked as blocked, and',
      'its money never counts toward closing the gap. There is no partial cut of a mandated',
      'programme — it is all or nothing, and it is nothing.',
      '',
      f'**{fl["what"]}**',
      '',
      f'{fl["evidence"]} {fl["implication"]}',
      '',
      'So the honest statement is not "here is the floor". It is that every year the',
      'district has taken a little more out of something it is legally obliged to provide,',
      'and nobody has established where that stops.',
      '',
      '### What we assumed, and what would settle it',
      '',
      '- **The programme list is partly ours.** Some entries are priced from the district’s',
      '  own cut and restoration lists. Some are our estimates, and the site marks which.',
      '- **The rankings are preferences, not forecasts.** Three of the four are',
      '  reconstructions of somebody’s revealed order; one is explicitly what we would do.',
      '- **Cutting a service that is still legally owed does not save the money.** It moves',
      '  the cost somewhere a budget cannot see it, and nothing in this model can follow it',
      '  there.',
      '')


# ==========================================  11. TAX BASE, GROWTH AND OVERRIDES
def _cascade_gap(fy):
    """That year's shortfall once every earlier year has been cut — Section 10's figure."""
    order = cascade.PRESETS['school_committee']['order']
    return next(y['deficit'] for y in cascade.run(order) if y['fy'] == fy)


def _comp():
    """Unspent share of identified free cash, by town, 2025."""
    return {r['town']: r['unspentShare'] for r in freecash.peer_composition()}


def _comp_near():
    """The towns closest behind Lunenburg on composition, named rather than hand-waved."""
    rows = freecash.peer_composition()
    others = [r for r in rows if r['town'] != 'Lunenburg'][:3]
    return ', '.join(f"{r['town']} at {pct(r['unspentShare'], 1)}" for r in others)


def _ident(town):
    return next(r['identified'] for r in freecash.peer_composition()
                if r['town'] == town)


def _fresh_gaps():
    """How much of each year's gap is new, rather than last year's carried forward."""
    out, prev = [], None
    for i, r in enumerate(PROJ):
        f = r['deficit'] if i == 0 else r['deficit'] - prev * (1 + r['growth_rate'])
        out.append((r['fy'], round(f)))
        prev = r['deficit']
    return out


def s_taxbase():
    T = taxbase
    gap0 = PROJ[0]['deficit']
    w('---',
      '',
      '## 11. The tax base, new growth, and overrides',
      '',
      'Everything a resident meets on their own bill.',
      '',
      '### What goes in',
      '',
      table(['figure', 'value', 'label'],
            [['FY26 tax rate, single rate', f'${T.TAX_RATE} per $1,000',
              KIND_MARK['published']],
             ['FY26 levy', usd(T.LEVY), KIND_MARK['published']],
             ['Total taxable value', usd(T.TOTAL_VALUE), KIND_MARK['measured']],
             ['Residential share of value', pct(T.RESIDENTIAL_SHARE, 0),
              KIND_MARK['published']],
             ['Commercial, industrial and personal', pct(T.CIP_SHARE, 0),
              KIND_MARK['published']],
             ['Average single-family value', usd(T.AVG_HOME_VALUE),
              KIND_MARK['published']],
             ['Average tax bill', usd(T.AVG_HOME_BILL), KIND_MARK['published']],
             ['Chapter 70 aid, FY27', usd(T.CH70['aid']), KIND_MARK['published']],
             ['District enrollment', num(T.ENROLLMENT), KIND_MARK['published']]],
            'lrl'),
      '',
      formula(f'Total taxable value = levy ÷ tax rate × 1,000'),
      '',
      'It is not read off an assessment report. It reproduces the Assessors’ own class',
      'totals closely, but it is a calculation rather than a transcription.',
      '')

    w('### What one student costs the levy',
      '',
      ledger([
        ('School appropriation', usd(T.LPS_APPROPRIATION)),
        ('  less Chapter 70 aid', signed(-T.CH70['aid'])),
        None,
        ('Raised locally', usd(T.LPS_APPROPRIATION - T.CH70['aid'])),
        (f'  ÷ {num(T.ENROLLMENT)} students', ''),
        None,
        ('Local cost per pupil', usd(T.LOCAL_COST_PER_PUPIL)),
        None,
        ('Schools as a share of the omnibus budget', pct(T.SCHOOL_SHARE_OF_BUDGET)),
        ('School share of the average tax bill', usd(T.SCHOOL_SHARE_OF_BILL)),
        None,
        ('Average homes needed to educate one child', f'{T.HOMES_PER_PUPIL}'),
      ]),
      '',
      f'**It takes about {T.HOMES_PER_PUPIL:.0f} average homes, in school-tax terms, to',
      'educate one child.** That is the arithmetic behind why residential development does',
      'not pay for itself and commercial development does.',
      '')

    w('### New growth',
      '',
      '**New growth is permanent.** Value added to the tax rolls is added to the levy limit',
      'at the prior year’s rate, and it stays there and grows at the cap thereafter.',
      '',
      formula(f'Revenue = new taxable value × ${T.TAX_RATE} ÷ 1,000',
              f'So $1,000,000 of new value = {usd(T.new_growth_revenue(1_000_000))} '
              f'a year, permanently'),
      '',
      f'The town budgets {usd(T.CURRENT_NEW_GROWTH_REVENUE)} of new growth a year, which',
      f'implies about {usd(T.CURRENT_NEW_GROWTH_VALUE)} of new taxable value being added',
      'annually, most of it residential.',
      '')

    w('### The correction that halved this answer',
      '',
      '**The schools do not receive a levy dollar.** New growth is added to the *town’s*',
      'levy limit. The schools then receive their share of the town’s total available',
      'revenue. Comparing gross new-growth revenue against the school gap — as this tool',
      'once did — credits the schools with money that goes to the fire department, and',
      'roughly doubles what commercial development appears to be worth.',
      '',
      ledger([
        ('A dollar added to the town’s levy limit', '$1.00'),
        ('  of which reaches the schools', usd(SHARE, cents=True)),
        None,
        ('FY28 school gap', usd(gap0)),
        ('  levy needed to close it', usd(gap0 / SHARE)),
        ('  new taxable value needed, in one year',
         usd(gap0 / SHARE * 1000 / T.TAX_RATE)),
      ]),
      '')

    bn = T.businesses_needed(gap0)
    w('### The same requirement, in buildings',
      '',
      'Abstractions do not survive a public meeting, so the same figure is expressed in',
      'things a town actually permits.',
      '',
      table(['unit', 'assessed value', 'needed to close the FY28 gap in one year'],
            [['An average existing Lunenburg business', usd(T.AVG_COMMERCIAL_VALUE),
              f"{num(bn['businesses'])} of them"],
             ['A typical mixed development', usd(T.MIX_VALUE),
              f"{bn['developments']:.1f} of them"],
             ['The town’s entire recent annual new growth', usd(T.FY23_NEW_VALUE),
              f"{bn['vsActualNewGrowth']:.1f} times it"]],
            'lrr'),
      '',
      f'{num(bn["businesses"])} average businesses is {pct(bn["pctOfToday"] / 100, 0)} of',
      f'every business in town — there are {num(T.BUSINESSES)}, per the 2024 Census',
      'Business Patterns — added in a single year, and again the next year, because the gap',
      'grows.',
      '',
      '**The development values are ours**, order-of-magnitude estimates rather than',
      'Lunenburg assessments, and the site lets you change them. They exist so that people',
      'can reason in buildings rather than in millions. The one figure that is not ours is',
      f'the average existing business: {usd(T.FY23["cipValue"])} of commercial, industrial',
      f'and personal property across {num(T.BUSINESSES)} establishments, from the tax',
      'rolls.',
      '')

    w('### Does new growth lower my tax bill?',
      '',
      'Almost not at all, and the arithmetic says why. **New growth adds revenue and',
      'taxable value in nearly the same proportion**, so it barely moves the rate. The town',
      'levies essentially to its maximum every year — excess capacity has been single-digit',
      'thousands — so the levy rises by the cap plus new growth, and the rate is whatever',
      'satisfies levy divided by value.',
      '',
      formula('Tax rate = levy ÷ total taxable value × 1,000'),
      '',
      table(['new commercial value', 'rate without it', 'rate with it',
             'effect on the average bill', 'revenue raised', 'share of the FY28 gap'],
            [[usd(v), f"${T.taxpayer_view(v, gap0)['rateWithout']:.4f}",
              f"${T.taxpayer_view(v, gap0)['rateWith']:.4f}",
              ('-' if T.taxpayer_view(v, gap0)['billChange'] < 0 else '+')
              + usd(abs(T.taxpayer_view(v, gap0)['billChange']), cents=True),
              usd(T.new_growth_revenue(v)),
              f"{T.taxpayer_view(v, gap0)['shareOfGap']:.0f}%"]
             for v in (5_000_000, 15_000_000, 30_000_000)],
            'rrrrrr'),
      '',
      '**The benefit of commercial growth is not a lower rate. It is a bill that rises more',
      'slowly than it otherwise would**, because the alternative to new growth is an',
      'override or a cut.',
      '')

    w('### Overrides',
      '',
      'A Proposition 2½ override raises the levy limit **once, permanently**. The base then',
      f'grows at {pct(LEVY_CAP, 1)} a year like the rest of the levy.',
      '',
      formula('Cost to one household = the override amount ÷ total taxable value '
              '× that home’s value'),
      '',
      ledger([
        ('An override covering the whole FY28 school gap', usd(gap0)),
        ('  cost to the average home, per year',
         usd(T.override_cost_per_home(gap0), cents=True)),
        None,
        ('The same, if the question is town-wide rather than school-only',
         usd(gap0 / SHARE)),
        ('  cost to the average home, per year',
         usd(T.override_cost_per_home(gap0 / SHARE), cents=True)),
      ]),
      '',
      f'A general override has to be about {1 / SHARE:.1f} times the size to do the same',
      f'work for the schools, because the schools receive only {pct(SHARE)} of a levy',
      'dollar.',
      '',
      '### How much a new override would have to raise, every year',
      '',
      '**Residents hear "an override fixes it" and reasonably assume one ballot question.**',
      'What the arithmetic asks for is a new one every spring. This is the amount by which',
      'the gap grows in each year beyond what last year’s gap would have grown to on its',
      'own — the fresh hole, over and above the one already there.',
      '',
      formula('Fresh gap = this year’s gap − (last year’s gap × '
              '(1 + the town’s revenue growth))'),
      '',
      table(['FY', 'total gap', 'the fresh part of it',
             'town-wide question needed to raise that'],
            [[f'FY{fy}', usd(PROJ[i]['deficit']), usd(f), usd(f / SHARE)]
             for i, (fy, f) in enumerate(_fresh_gaps())],
            'lrrr'),
      '',
      f'Each town-wide question is about {1 / SHARE:.1f} times the fresh school gap,',
      'because the schools receive only a share of a levy dollar.',
      '',
      '**One warning about how overrides are often modelled, including by us.** It is easy',
      'to build a projection in which an override passes *every year*. That is a different',
      'and much rarer thing than one ballot question, and it overstates the effect by',
      'roughly the number of years projected. The figures on the site use the one-time',
      'model, which is what a ballot question actually does.',
      '',
      '### What we assumed, and what would settle it',
      '',
      f'- **The development values are ours.** The {pct(T.RESIDENTIAL_SHARE, 0)} residential',
      '  share, the rate, the levy and the average bill are the town’s own published',
      '  figures.',
      '- **Total taxable value is calculated, not transcribed.**',
      '- **The town levies to its maximum.** True in every year we hold. Not a law.',
      f'- **New growth is assumed flat at {usd(A["new_growth"])}.** The Assessors’ own',
      f'  series runs from {usd(taxbase.NEW_GROWTH_HISTORY[0]["amount"])} in',
      f'  FY{taxbase.NEW_GROWTH_HISTORY[0]["fy"]} to',
      f'  {usd(taxbase.NEW_GROWTH_HISTORY[-1]["amount"])} in',
      f'  FY{taxbase.NEW_GROWTH_HISTORY[-1]["fy"]} — not every year down, but ending well',
      '  below the assumption. And every commercial class **shrank in absolute dollars** in',
      '  the most recent year we hold. This is the assumption most likely to be optimistic.',
      '')


# ==============================================  12. THE ASSUMPTION REGISTER
ASSUMPTIONS = [
    ('salaries', 'Salary growth', 0.01, 'given',
     'The teachers’ agreement — scale increases plus steps'),
    ('levy_growth', 'Levy growth', 0.01, 'given', 'Proposition 2½. Fixed by statute'),
    ('sped', 'Special education, in district', 0.01, 'derived',
     'Two contracts and two measured trends, weighted by share — Section 4, with the '
     'trend tests and a five-point range published beside it'),
    ('health', 'Health insurance', 0.01, 'given',
     'The district’s own stated assumption for FY27'),
    ('state_aid_growth', 'State aid growth', 0.01, 'BARE',
     'Nothing. No stated source and no derivation — see below'),
    ('other', 'Everything else', 0.01, 'given',
     'The district’s own stated assumption for FY27'),
    ('new_growth', 'New growth per year', 100_000, 'given',
     'The town’s own FY27 estimate — though its own series has been falling, Section 11'),
    ('transport', 'Transportation', 0.01, 'judged',
     'The district assumed 10%. This is softer, and ours, and rests on no trend test'),
    ('sped_tuition', 'Out-of-district tuition', 0.01, 'derived',
     'Held flat because eleven budgets show no trend — Section 5. The risk is priced as '
     'scenarios instead'),
    ('local_receipts_growth', 'Local receipts growth', 0.01, 'BARE',
     'Nothing. No stated source and no derivation — see below'),
    ('utilities', 'Utilities', 0.01, 'given',
     'The district’s own stated assumption for FY27'),
]
GRADE_MARK = {'given': '`given`', 'derived': '`derived`', 'judged': '`judged`',
              'BARE': '**`BARE`**'}


def s_register():
    rows = []
    for key, label, delta, grade, warrant in ASSUMPTIONS:
        e1, e6 = _bump(key, delta), _bump(key, delta, 6)
        unit = f'+{usd(delta)}' if delta >= 1 else '+1 point'
        val = usd(A[key]) if delta >= 1 else pct(A[key])
        rows.append((abs(e1), [label, val, unit, signed(e1), signed(e6),
                               GRADE_MARK[grade], warrant]))
    rows.sort(key=lambda r: -r[0])

    w('---',
      '',
      '## 12. Every assumption, what it is worth, and what backs it',
      '',
      '**If you want to argue with this projection, start here.** A projection is',
      'assumptions — the question is never whether a figure is assumed, but whether the',
      'assumption is warranted and whether anything better is available.',
      '',
      'This is the whole list, sorted by how much each one moves the answer, so an argument',
      'can start where it matters rather than where it is easiest. The effects are the',
      'change in the gap from moving that one assumption and nothing else. They are',
      'produced by running the real projection twice, not estimated.',
      '',
      table(['assumption', 'currently', 'moved by', 'FY28 gap',
             f'FY{PROJ[-1]["fy"]} gap', 'grade', 'what backs it'],
            [r[1] for r in rows], 'lrrrrll'),
      '',
      table(['grade', 'means'],
            [['`given`', 'Somebody else’s figure — a contract, a statute, or a number the '
                         'town or district published. We transcribed it.'],
             ['`derived`', 'We calculated it from their data, and the calculation is set '
                           'out in this document with its own test.'],
             ['`judged`', 'Our estimate, with a stated argument behind it.'],
             ['**`BARE`**', 'A number with nothing behind it. Argue with these first — '
                            'so do we.']],
            'll'),
      '')

    w('### The two with nothing behind them',
      '',
      f'State aid is assumed to grow at {pct(A["state_aid_growth"], 1)} a year and local',
      f'receipts at {pct(A["local_receipts_growth"], 1)}. **Neither figure has a stated',
      'source or a derivation.** Every other rate in this model carries one. These two',
      'carry nothing, and we are naming them rather than waiting for somebody else to.',
      '',
      '**State aid is the more serious of the two.** It is worth',
      f'{usd(abs(_bump("state_aid_growth", 0.01)))} of FY28 gap for every point it moves —',
      'the second largest revenue lever in the model, and larger than the entire',
      'transportation growth rate by a factor of',
      f'{abs(_bump("state_aid_growth", 0.01)) / abs(_bump("transport", 0.01)):.0f}.',
      '',
      'It also governs the single largest figure the town does not control. Chapter 70 is',
      f'about {usd(taxbase.CH70["aid"])} of a {usd(F["lps_appropriation"])} school budget,',
      'and it is set in the Governor’s budget rather than by anything Lunenburg does. An',
      'assumption about it ought to look like the priced scenarios in Section 5 rather than',
      'a single figure with nothing beneath it.',
      '',
      '**Local receipts matter less**, but the same objection applies.',
      '',
      '**Neither has been changed.** Naming a weakness is not the same as fixing it, and',
      'changing a rate changes published figures — which is a decision for the people who',
      'have to defend them, not a correction we should make quietly.',
      '')

    w('### Assumptions that do not affect the projection',
      '',
      'These move individual pages rather than the gap. Every one of them is ours.',
      '',
      table(['assumption', 'currently', 'affects', 'standing'],
            [['Sibling mix in athletics',
              pct(athletics.MEASURED_SIBLING_SHARE, 1) + ' take a discount',
              'Every fee figure, Section 8',
              '**no longer an assumption** — counted over '
              f'{num(athletics.MEASURED_CATEGORY_TOTAL)} participations'],
             ['Athletic fee waivers', pct(athletics.WAIVER_ASSUMPTION, 0),
              'Every fee figure, Section 8',
              'still ours; two counts put it at '
              f'{pct(athletics.MEASURED_WAIVER_SHARE, 1)} and '
              f'{pct(athletics.FY26_COUNTED_WAIVER_SHARE, 1)}'],
             ['Drop-off as fees rise',
              f'{athletics.FEE_DROPOFF_PER_100:.0f}% per $100',
              'The fee curve, Section 8',
              'no local figure has ever been measured'],
             ['Health enrolment by plan and tier',
              f'{sum(health.DEFAULT_ENROLMENT.values())} enrollees',
              'The per-plan figures, Section 6',
              'the total reconciles to the budget; the mix is ours'],
             ['Development values', 'order of magnitude',
              'The buildings-per-gap figures, Section 11',
              'ours, and editable on the site'],
             ['Cut priority orders', 'four rankings',
              'Which programme falls, Section 10', 'preferences, not forecasts']],
            'llll'),
      '',
      '**The pattern worth naming.** How well an assumption is supported tracks how much it',
      'matters, almost everywhere in this model. The four largest levers are a signed',
      'contract, a statute, the district’s own figure, and the one rate we derived over ten',
      'budgets with its test published beside it. The weakly founded assumptions are mostly',
      'small ones. There are two exceptions, and they are named above: state aid, which is',
      'large and bare, and — until it was corrected — the sibling mix, which was small and',
      'wrong.',
      '')


# ============================================================  13. HOW IT IS CHECKED
def s_checks():
    w('---',
      '',
      '## 13. How this is checked',
      '',
      'Every claim above is checked by something that runs automatically, because this',
      'project’s own history is of checks that existed and were never run. The commands are',
      'in Appendix A. What they prove is here.',
      '',
      table(['what is checked', 'what it proves'],
            [['Budget figures never meet actual spending',
              'No part of the projection reads a column of actual spending. The build '
              'fails if one ever does.'],
             ['Free cash stays outside the growth rates',
              'Enabling free cash at nine different draw levels moves nothing except the '
              'free cash figures themselves.'],
             ['The assumptions against history',
              'Every growth rate compared with what that line actually did, budget to '
              'budget.'],
             ['The expense base rebuilds the appropriation',
              'The line items add back up to the published school appropriation, within '
              'rounding.'],
             ['Every source document is present',
              'Everything catalogued is actually there and downloadable.'],
             ['This document is not stale',
              'It is regenerated and compared. A stale copy fails the build.'],
             ['The published figures on the site match the model',
              'The site is rebuilt and the figures it serves are compared against the '
              'model that produced them.']],
            'll'),
      '',
      '### Three checks that refuse to publish rather than warn',
      '',
      '- **The capital plan extract must reproduce the plan’s own printed average**, for',
      '  free cash into capital and for the whole programme. It was two rows short of that',
      '  for a while and nothing noticed, because the average printed beside it had been',
      '  typed in rather than calculated.',
      '- **The restricted capital projects must come to exactly what the plan’s funding',
      '  page shows against that fund**, and the rest must come to free cash plus taxation.',
      '  Both are checked before anything is calculated from them.',
      '- **The town ledger extract must tie to the report’s own grand total.** It once',
      '  silently dropped 16 of 67 departments, because the accounting system prints a zero',
      '  as ".00" and our pattern expected a digit before the decimal point. $4,074,773 of',
      '  revised budget was invisible for weeks, including a $2.4 million assessment.',
      '  Nothing caught it because nothing compared the extract against the total the report',
      '  itself prints. It does now, and it refuses to save if it does not tie.',
      '',
      '**The general lesson, and the reason this section exists:** any instrument that',
      'reformats a document before you read it is part of the finding, and has to be',
      'checked like one.',
      '')


# ==========================================================  14. WHAT IT CANNOT DO
def s_limits():
    w('---',
      '',
      '## 14. What none of this can tell you',
      '',
      'Some figures would settle more than any amount of further analysis. They are not',
      'published, and no arithmetic on what *is* published substitutes for them.',
      '',
      '- **A count of out-of-district special education placements by year.** Dollars',
      '  cannot distinguish fewer children from a more honest estimate. Section 5 rests on',
      '  this.',
      '- **How grants and state funding map onto the budget lines.** The budget shows the',
      '  general fund and nothing else, so a line rising because a grant ended looks exactly',
      '  like a line rising because the district grew. **This is the one that carries the',
      '  most weight**: the special education growth rate in Section 4 rests on a',
      '  paraprofessional line, and it cannot currently be distinguished from grant money',
      '  unwinding. The state’s End of Year Financial Report would answer it.',
      '- **Whether budgeted positions were actually filled.** A budget line is an intention.',
      '- **Health insurance enrolment by plan and tier.** Section 6 is calibrated to a total',
      '  and guesses the shape.',
      '- **Athletic participation by fee category for the current year**, and the revolving',
      '  fund’s own ledger by object code.',
      '- **FY26 year-end figures.** Everything we hold for FY26 stops at 31 March 2026.',
      '',
      '### And the two mistakes this document exists to prevent',
      '',
      '**An explanation is not a measurement.** A number calculated from the data is a',
      'fact. An explanation for why that number moved is a hypothesis, however obvious it',
      'feels, and it has to be labelled as one every time. Dollars are not students. A',
      'budget line is not a filled position. A count of documents is not a count of',
      'decisions. Where the actual quantity is not published, the honest sentence is that we',
      'cannot say — not a number inferred from something adjacent to it.',
      '',
      '**Quote the source, never your own rendering of it.** Every serious error in this',
      'project has had the same shape: something we derived got quoted as though it had been',
      'observed. Not invented — derived, which is exactly why it survives review. A tidy',
      'table is for reading, never for quoting. If you cannot point to the page or the cell,',
      'you have not checked it.',
      '')


# ==================================================================  APPENDICES
def s_appendix():
    w('---',
      '',
      '## Appendix A — For anyone reproducing the arithmetic',
      '',
      'Nothing in this appendix is needed to follow the argument. It is here so that',
      'somebody who wants to rerun any figure above can find it.',
      '',
      '### Where each section is built',
      '',
      table(['section', 'built by', 'from'],
            [['1, 2, 3 — the projection', '`model/finance.py`',
              '`sources/data/lps-budget-lines.csv`'],
             ['4, 5 — special education', '`model/sped.py`',
              'the same file, plus the budget history extracts'],
             ['6 — health insurance', '`model/health.py`',
              'the Town’s open enrolment notice'],
             ['7 — free cash', '`model/freecash.py`',
              '`sources/state-dls/`, `sources/data/capital-plan-fy27.csv`'],
             ['8 — athletic fees', '`model/athletics.py`',
              '`sources/town-ledgers/account-details/`, `sources/data/athletics-by-sport.csv`'],
             ['9 — the options', '`model/levers.py`', 'the FY27 line-item budget'],
             ['10 — the cut cascade', '`model/cascade.py`', '`model/catalog.py`'],
             ['11 — tax base and overrides', '`model/taxbase.py`',
              'the FY2023 Tax Classification Hearing'],
             ['12 — the assumption register', 'this script',
              'the live model, run twice per assumption']],
            'lll'),
      '',
      '### Rebuilding and checking',
      '',
      '```',
      'python3 model/export.py                          regenerate the site’s data file',
      'python3 scripts/build_show_your_work.py           regenerate this document',
      'python3 scripts/build_show_your_work.py --check   fail if this document is stale',
      'python3 scripts/audit_provenance.py               budgets never meet actuals, free',
      '                                                  cash stays inert, and both of the',
      '                                                  above are fresh',
      'python3 scripts/backtest_rates.py                 assumptions against history',
      'python3 scripts/build_source_index.py             every source present, catalogued',
      'python3 scripts/verify_athletics.py               the athletics analysis, recomputed',
      'python3 scripts/verify_free_cash.py               the free cash analysis, recomputed',
      'npm run check:agents                              the live site matches the model',
      '```',
      '',
      '### The data, published directly',
      '',
      'Everything the site computes is available as files, without going through the pages:',
      '',
      table(['file', 'what it holds'],
            [['`/data/model.json`', 'every figure the site computes, including which are '
                                    'ours and which are published'],
             ['`/data/budget-lines.csv`', 'the district budget, line by line, every year '
                                          'and scenario'],
             ['`/data/sped-lines.csv`', 'every line counted as special education, and '
                                        'which rule caught it'],
             ['`/data/ood-tuition-history.csv`', 'out-of-district tuition, FY17 to FY27'],
             ['`/data/free-cash-proof.csv`',
              'the state’s free cash proof, nine towns, 2021–2025'],
             ['`/data/rate-register.csv`', 'every rate this project knows about, with the '
                                           'year it applies to and the document that set '
                                           'it'],
             ['`/data/athletics-by-sport.csv`',
              'the district’s own by-sport workbook, tidied'],
             ['`/data/sources.json`',
              'the whole document archive, with a checksum for each file']],
            'll'),
      '')

    w('---',
      '',
      '## Appendix B — The interactive tools, and why they agree with this',
      '',
      'Two pages on the site let you move the figures yourself: one that adjusts the growth',
      'rates, and one that models redirecting free cash away from capital projects.',
      '',
      'Both have to respond instantly to a dragged control, which means the arithmetic is',
      'written a second time, in the language the browser runs. **The same rule implemented',
      'twice is a discrepancy waiting to happen**, and this project has been caught by',
      'exactly that before.',
      '',
      'So each of them checks itself against the published model every time the page loads,',
      'and shows a visible warning in the interface if the two ever disagree. The rate page',
      'compares its projection year by year against the model’s and fails on a difference of',
      'more than a dollar. The capital page compares its answer against the model’s at every',
      'draw level the model publishes.',
      '',
      '**One of those checks existed as an uncalled function for months.** A check that does',
      'not run is not a check. Both now run on load, and both are also verified against the',
      'live site after every deployment.',
      '')


def s_footer():
    w('---',
      '',
      '## Where to go from here',
      '',
      table(['for', 'see'],
            [['The conclusions this arithmetic supports', 'the analyses on the site'],
             ['Every source document, with its address and a checksum', '`/sources`'],
             ['Every rate, with the year it applies to and who set it', '`/rate-register`'],
             ['What this project knows it does not know', 'Section 14 above']],
            'll'),
      '',
      '*Every figure in this document is generated from the model that produces the site.*',
      '*If a number here disagrees with a page on the site, one of the two is stale — and*',
      '*if a number here disagrees with a source document, the source document is right.*',
      '')


# ---------------------------------------------------------------------- driver
def build():
    S.clear()
    opening()
    s_projection()
    s_drivers()
    s_rate_sources()
    s_sped()
    s_tuition()
    s_health()
    s_freecash()
    s_athletics()
    s_levers()
    s_cascade()
    s_taxbase()
    s_register()
    s_checks()
    s_limits()
    s_appendix()
    s_footer()
    return '\n'.join(S).rstrip() + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true',
                    help='fail if the committed copy differs from what the model produces')
    args = ap.parse_args()
    text = build()
    if args.check:
        if not os.path.exists(OUT):
            print(f'FAIL: {os.path.relpath(OUT, ROOT)} does not exist')
            return 1
        if open(OUT).read() != text:
            print(f'FAIL: {os.path.relpath(OUT, ROOT)} is stale. '
                  f'Run: python3 scripts/build_show_your_work.py')
            return 1
        print(f'ok: {os.path.relpath(OUT, ROOT)} matches the model')
        return 0
    with open(OUT, 'w') as fh:
        fh.write(text)
    print(f'wrote {os.path.relpath(OUT, ROOT)}  '
          f'{len(text.splitlines()):,} lines, {len(text):,} bytes')
    return 0


if __name__ == '__main__':
    sys.exit(main())
