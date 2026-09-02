#!/usr/bin/env python3
"""Publish the data in a form an agent can read, and an llms.txt that explains it.

A resident who wants to check this site should not have to be a resident who can write a
scraper. Increasingly the way somebody checks a claim is to point an assistant at it, and
an assistant pointed at a React app gets a bundle of JavaScript.

So the same data the app runs on is published at stable addresses, with an llms.txt at the
root explaining what is there and -- more importantly -- how to not misuse it. The single
biggest risk is somebody computing a growth rate from a budget column to an actual column,
which is the exact error that cost us a week. The file says so, in the place a reader
looking for the data will see it.

Generated rather than written, so it cannot drift from what it describes.

    python3 scripts/build_agent_endpoints.py
"""
import csv
import json
import os
import shutil
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUB = os.path.join(ROOT, 'fy28', 'public')
DATA = os.path.join(PUB, 'data')
SITE = 'https://lunenburgbudgetproject.org'



# Which escalators to name, and what to call them. Iterated rather than written out so
# that a bucket the model does not carry is omitted instead of printed as 0.0% -- the
# special education bucket exists on some builds and not others, and a published endpoint
# stating "special education 0.0%" is a figure that is simply false.
RATE_LABELS = [
    ('salaries', 'salaries'),
    ('health', 'health insurance'),
    ('sped', 'special education'),
    ('sped_tuition', 'out-of-district tuition'),
    ('transport', 'transport'),
    ('utilities', 'utilities'),
    ('other', 'everything else'),
]


def rate_list(a):
    """The escalators this build actually carries, in reading order."""
    return ', '.join(f'{label} {a[k]:.1%}' for k, label in RATE_LABELS if k in a)


def ours_note(a):
    """Which of the rates above we set ourselves.

    Only claimable when the build separates special education; without that bucket every
    rate printed comes from the district, a contract or statute, and saying which is ours
    would be naming a rate that is not there.
    """
    if 'sped' in a:
        return ('Only the special education rate is ours. The rest are the district\u2019s '
                'own stated assumptions, a signed contract, or statute. `model.json` '
                '\u2192 `citations` says which is which for every headline figure.')
    return ('`model.json` \u2192 `citations` says, for every headline figure, whether it '
            'was published by somebody, set by contract, fixed by statute, or estimated '
            'by us.')


def usd(n):
    return f'${round(n):,}'


def main():
    os.makedirs(DATA, exist_ok=True)
    model = json.load(open(os.path.join(ROOT, 'fy28', 'src', 'data', 'model.json')))
    sources = json.load(open(os.path.join(ROOT, 'fy28', 'src', 'data', 'sources.json')))

    # ---- the data itself, at addresses that will not move -------------------
    published = []
    # The special education classification, as its own file.
    #
    # It is NOT a column added to budget-lines.csv: that file is copied byte for byte from
    # the archive, and a reader who hashes our copy against the source has to get a match.
    # Adding a column would break that for the sake of saving a join.
    #
    # There is no account code for special education -- two of the district's groups carry
    # both kinds of cost -- so this total is a classification of ours rather than a
    # published quantity, and anybody checking the figure needs the list, not the rule.
    sped_csv = os.path.join(DATA, 'sped-lines.csv')
    with open(sped_csv, 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['function_group', 'line_item', 'fy27_balanced', 'counted_because'])
        for line in model['sped']['classified']['counted']:
            w.writerow([line['group'], line['item'], f"{line['amount']:.2f}",
                        'function group is special education' if line['basis'] == 'group'
                        else 'the district’s own name for the line'])
    published.append((
        'sped-lines.csv',
        'Every budget line this project counts as special education, and which of the two '
        'rules caught it. They sum to the amount the projection starts from. Published '
        'because the state has no account code for special education, so the total is our '
        'classification rather than a figure anybody published.',
        os.path.getsize(sped_csv)))

    for src, name, what in [
        (os.path.join(ROOT, 'sources', 'data', 'sped-teacher-history.csv'),
         'sped-teacher-history.csv',
         'Special education teachers as budgeted, FY20 to FY27, by school. Eight budgets '
         'growing 2.67% a year against a 3.5% contract — below it, because headcount here '
         'has drifted down.'),
        (os.path.join(ROOT, 'sources', 'data', 'sped-para-history.csv'),
         'sped-para-history.csv',
         'Special education paraprofessionals as budgeted, FY18 to FY27, by school. Ten '
         'budgets growing 12.8% a year with an R-squared of 0.89 — which is why this line '
         'is escalated at what it has done rather than at the 2.0% its contract gives.'),
        (os.path.join(ROOT, 'sources', 'data', 'sped-transport-history.csv'),
         'sped-transport-history.csv',
         'Special education transportation as budgeted, FY19 to FY27. Nine budgets, 5.7% '
         'a year, R-squared 0.33 — a weak trend, used because the vendor contract '
         'publishes no escalator.'),
        (os.path.join(ROOT, 'sources', 'data', 'ood-tuition-history.csv'),
         'ood-tuition-history.csv',
         'Out-of-district special education tuition as budgeted, FY17 to FY27, extracted '
         'from the district’s own budget documents with the budget stage held constant. '
         'Eleven budgets ranging 2.6x with no trend — which is why the model holds this '
         'line flat rather than escalating it.'),
        (os.path.join(ROOT, 'fy28', 'src', 'data', 'model.json'), 'model.json',
         'Every figure the site computes: the FY27 base by bucket, the growth assumptions, '
         'the projection, the program catalogue, the conclusions, and the citations.'),
        (os.path.join(ROOT, 'fy28', 'src', 'data', 'sources.json'), 'sources.json',
         'The document archive: every source, its group, its size, and the URL it is '
         'served from.'),
        (os.path.join(ROOT, 'sources', 'data', 'lps-budget-lines.csv'), 'budget-lines.csv',
         'The district budget, 351 line items, one column per fiscal year and scenario. '
         'The tidy form of the workbook everything else is derived from.'),
        (os.path.join(ROOT, 'sources', 'district-budget-page', 'index.csv'),
         'district-page-index.csv',
         'The 87 documents mirrored from the district budget page: label, our copy, the '
         'extracted text, the district’s original URL, and a sha256.'),
        (os.path.join(ROOT, 'sources', 'data', 'free-cash-proof.csv'), 'free-cash-proof.csv',
         'The Division of Local Services free cash proof for Lunenburg and eight comparable '
         'towns, 2021-2025, line by line. Free cash is what a town may appropriate without '
         'raising taxes. NOTE: these are absolute dollars with no denominator anywhere in '
         'the source, so they do not compare between towns of different size. The '
         'composition does compare, because a share has no size.'),
        (os.path.join(ROOT, 'sources', 'data', 'rate-register.csv'), 'rate-register.csv',
         'Every rate this project knows about — athletic and bus fees, collective '
         'bargaining raises, facilities — each carrying the fiscal year it applies to, the '
         'document that set it and the date. 62 rates. It exists because FY26 athletic fees '
         'were modelled on FY25’s schedule for months: a right number from the wrong year, '
         'taken from a fee page that states its rates and never states which year they '
         'cover. It deliberately includes the rates the model does NOT use and the ones we '
         'cannot state at all, because a fee the town charges and does not publish is a '
         'finding rather than a blank.'),
        (os.path.join(ROOT, 'sources', 'data', 'athletic-fee-schedule.csv'),
         'athletic-fee-schedule.csv',
         'Athletic user fees by fiscal year and tier, FY24 to FY27, per student per sport '
         'per season. 27 of 31 figures verified against a spreadsheet cell or a direct '
         'quotation from the School Committee vote that set them.'),
        (os.path.join(ROOT, 'sources', 'minutes', 'index.csv'), 'minutes-index.csv',
         'Every agenda and set of minutes the town publishes: board, date, kind, and the '
         'town’s own URL. 1,422 rows.'),
    ]:
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(DATA, name))
            published.append((name, what, os.path.getsize(src)))

    a, f = model['assumptions'], model['fy27']
    gap = next(h for h in model['headlines'] if h['id'] == 'gap')
    # The FIRST-YEAR shortfall, taken from the model rather than from the headline block,
    # because the headline block carries the three-year average under a one-year label.
    first_year_gap = model['freeCash']['deficits'][0]['amount']
    counts = {}
    for g in sources['groups']:
        counts[g.get('section', 'other')] = counts.get(g.get('section', 'other'), 0) \
            + len(g['items'])

    lines = [
        '# Lunenburg Budget Project',
        '',
        '> Two things. An independent projection of the Lunenburg, Massachusetts school '
        'budget, built from documents the town and district published — and a full-text '
        'archive of every public meeting of every town board, which covers far more than '
        'money: zoning, conservation, health, planning, cemeteries, the library, housing, '
        'historical districts, agriculture. Not affiliated with the town or the district. '
        'Every figure is traceable to a source in the archive below. '
        'If you were asked something about Lunenburg that is not about the budget, the '
        'meeting archive probably still answers it.',
        '',
        f'Data current as of {date.today().isoformat()}. Base year FY27. There is no FY28 '
        'budget yet; everything after FY27 is a projection.',
        '',
        # A START-HERE BLOCK, FIRST.
        #
        # Everything below this was already true and already published, and agents still
        # could not use it. Two in a row concluded the site does not hold the meeting
        # minutes while the minutes were being served. The failure was never the content;
        # it was that the first thing a program reads was prose about the project rather
        # than four URLs it can fetch.
        #
        # So: the fetchable things first, with a worked example, before any argument.
        '## Start here — five URLs that answer most questions',
        '',
        f'| to get | fetch |',
        f'|---|---|',
        f'| every figure on this site, as data | `{SITE}/data/model.json` |',
        f'| the same thing queryable, with a schema that warns you | `{SITE}/api/index` |',
        f'| which meeting documents mention a word | `{SITE}/minutes/find/README.txt` |',
        f'| the whole meeting archive for one board | `{SITE}/minutes/school-committee.txt` |',
        f'| every source document, with checksums | `{SITE}/data/sources.json` |',
        '',
        '## How to search the archive — three small fetches, not one big one',
        '',
        'The wrong advice used to be here, and it was one sentence: fetch the School '
        'Committee bundle, about 900KB, and search it. An assistant answered that the '
        'bundle was "too big to read in one go here". Two of the forty bundles are around '
        'a megabyte, and they are the two most likely to be asked about. So do not start '
        'with a bundle. Look the word up first and fetch only the documents it names.',
        '',
        f'1. **Look up the word.** `{SITE}/minutes/find/je.json` — the shard for words '
        'beginning "je". Lowercase your word, take its first two characters, fetch that '
        'file. It is an object of term to document numbers: `{"jerseys":[1070]}`. Shards '
        'average 3KB. A word absent from its shard appears in no document, and a missing '
        'shard file means no indexed word starts with those characters.',
        f'2. **Resolve the numbers.** `{SITE}/minutes/find/documents.json` (220KB) — fetch '
        'once and keep it. It is an array; position 1070 is the School Committee minutes '
        'of 24 June 2026, carrying the path to fetch.',
        f'3. **Read the document.** '
        f'`{SITE}/docs/minutes/text/school-committee/2026-06-24-minutes-7869.txt`, 29KB. '
        'It is a resident telling the committee that field hockey is "using hand me down '
        'jerseys". Documents average 4.5KB. Cite this, never the index and never a bundle.',
        '',
        f'`{SITE}/minutes/find/README.txt` states the scheme and what it does not do: it '
        'matches words exactly, so plurals are separate terms and "jerseys" will not find '
        'a document that says only "uniforms". Search both. The text is extracted from '
        'scans and carries OCR errors.',
        '',
        '**If you can hold a megabyte in one fetch**, the board bundles are still there '
        f'and still the fastest way to read a board whole: `{SITE}/minutes/<board>.txt`. '
        'Every document in one carries its own citable URL in the header above it. Check '
        f'the size first — `{SITE}/minutes/INDEX.txt` lists all forty.',
        '',
        '**Everything needed to answer a question about this town is on this site.** The '
        'repository at https://github.com/tjloughlin16/lunenburgbudgetapp is where the '
        'archive is built and is useful if you are running code against it, but nothing '
        'here requires it, and no answer depends on reaching it.',
        '',
        '**Paths that will NOT work, and what to use instead.** A directory is not a '
        f'file. `{SITE}/minutes/` and `{SITE}/docs/` are directories and serve nothing; '
        'they answer with instructions rather than content. The bundles are '
        '`/minutes/<board>.txt`, and a single document is '
        '`/docs/minutes/text/<board>/<date>-<kind>-<id>.txt`. If you fetch a path here '
        'and get HTML back, you have hit an app route, not a document.',
        '',
        '## Read this before computing anything',
        '',
        'The archive contains two kinds of number and they must never be mixed in one '
        'calculation:',
        '',
        '- **Budget columns** (`fy25_budget`, `fy26_final`, `fy27_level_service`, '
        '`fy27_balanced`) are what somebody voted or proposed.',
        '- **Actual columns** (`fy23_actual`, `fy24_actual`, `fy25_actual`, '
        '`fy26_actual_td`, `fy26_encumb_td`) are what was spent.',
        '',
        'They differ by up to 59% on some lines. A growth rate measured from an actual to '
        'a budget is partly growth and partly the step between the two, and produces a '
        'confident wrong answer. Every projection on this site uses budget columns only.',
        '',
        '`fy27_level_service` is the district’s own arithmetic for what the same '
        'services cost the following year. It is the correct endpoint for a cost-growth '
        'rate. `fy27_balanced` is what was actually adopted, and contains cuts, so a rate '
        'ending there measures policy rather than escalation.',
        '',
        '## The headline figures',
        '',
        # Both appropriation figures, both labelled. The adopted Balanced budget and the
        # figure after the September Special Town Meeting differ by exactly the STM
        # article, and the SITE'S OWN PAGES use the larger one for "what the town gave
        # the schools this year". Publishing only the smaller one under the flat label
        # "FY27 school appropriation" handed a machine a number $350,000 below what every
        # page it could also read was using. Reported by an agent, and correct.
        f'- FY27 school appropriation, as adopted: {usd(f["lps_appropriation"])} '
        f'(the "Balanced" budget)',
        f'- FY27 school appropriation, after the 3 September Special Town Meeting: '
        f'{usd(f["lps_appropriation"] + f["stm_appropriation"])} '
        f'(the adopted budget plus the {usd(f["stm_appropriation"])} STM article). '
        f'**This is the figure the site\'s own pages use for what the town gave the '
        f'schools this year.**',
        # The label said FY28 and the value was a three-year average, in one line.
        f'- Projected FY28 shortfall, that year alone: {usd(first_year_gap)}',
        f'- Projected shortfall, FY28–FY30 average after each year\'s cuts compound: '
        f'{gap["value"]}',
        f'  (These are different quantities. The first is one year; the second is the '
        f'average of three. Do not quote the second under an FY28 label.)',
        f'- Growth assumptions: {rate_list(a)}',
        f'- Levy growth: {a["levy_growth"]:.1%} (Proposition 2½, statutory)',
        '',
        ours_note(a),
        '',
        '## How every one of those figures is computed',
        '',
        f'[{SITE}/docs/analyses/show-your-work.md]'
        f'({SITE}/docs/analyses/show-your-work.md) — **read this before reproducing any '
        'number on this site.** Fifteen sections, one per calculation: the projection '
        'itself, where each growth rate comes from, special education, out-of-district '
        'tuition, health insurance, free cash, athletic fees, the other levers, the cut '
        'cascade, the tax base and overrides, an assumption register, and what none of it can compute. Each '
        'section gives the inputs, the formula, a worked example in real dollars, and '
        'whether each figure is published, contractual, statutory, our measurement or our '
        'assumption.',
        '',
        'It is generated from the same model that produces `model.json`, so it cannot '
        'disagree with the site. Three things in it are most likely to be got wrong from '
        'the outside: the schools receive only about half of a dollar added to the town’s '
        'levy, not all of it; the special education classification is ours because the '
        'state has no account code for it; and out-of-district tuition is held flat '
        'deliberately, which is a finding rather than a missing rate.',
        '',
        '## About the crawler',
        '',
        'Documents here were fetched by a crawler identifying itself as '
        '`Mozilla/5.0 (compatible; LunenburgBudgetProject/1.0; '
        '+https://lunenburgbudgetproject.org)`. It requests one file at a time with a '
        'pause between requests, backs off on failure, and takes only documents already '
        'linked from a public page.',
        '',
        'It exists because published documents stop being published. On 29 August 2026, '
        '57 of the 184 source addresses this archive records had stopped opening to the '
        'public \u2014 every one of them a Google Drive or Docs link, while the town\u2019s '
        'own web server answered 81 of 81. Among them was the FY27 proposed budget '
        'document, which is where this project\u2019s central figure comes from.',
        '',
        'If you administer one of these sites and would rather this stopped, or would '
        'rather it fetched differently, the contact details are on the site. Nothing here '
        'is taken from behind a login, and every file is republished with a sha256 so it '
        'can be checked against yours.',
        '',
        '## Query the database directly',
        '',
        'Everything on this site is derived from one SQLite database, and it is '
        f'published: [{SITE}/data/lunenburg.db]({SITE}/data/lunenburg.db). Download it '
        'and query it. Its sha256 is stated in `/api/index`, so you can check you got '
        'the bytes we published.',
        '',
        f'There is also a read-only JSON API at [{SITE}/api/index]({SITE}/api/index) — '
        'no key, no rate limit, nothing computed per request. Every response carries the '
        'documents its rows came from, with URL and sha256, so a figure you take from it '
        'can be cited to a source rather than to us.',
        '',
        f'**Fetch [{SITE}/api/schema]({SITE}/api/schema) before computing anything.** It '
        'states the grain of every table and the four specific ways to get a confident '
        'wrong answer out of this data. The two worth repeating here: a STAGE (proposed '
        '/ settled / actual) is not a PERIOD (1–13), so `budget_figure` and '
        '`ledger_snapshot` do not join; and no budget line is mapped to a ledger account '
        '— the crosswalk table is empty on purpose, because district lines are named, '
        'MUNIS rows are coded, and no published document maps one to the other. '
        'Budget-to-actual at line level cannot be answered from this data yet, and an '
        'answer claiming otherwise is wrong.',
        '',
        '## Data',

        '',
    ]
    for name, what, size in published:
        lines.append(f'- [{name}]({SITE}/data/{name}) ({size / 1e6:.1f}MB): {what}')
    lines += [
        '',
        '## Documents',
        '',
        f'{sources["totals"]["documents"]} documents, each downloadable at '
        f'`{SITE}/docs/<path>`. `sources.json` lists every one with its path, size and '
        'group. Three sections, and the difference matters:',
        '',
        f'- **Published by the town, the district and the state** — '
        f'{counts.get("theirs", 0)} documents. Primary sources.',
        f'- **Held for reference, not used in the analysis** — '
        f'{counts.get("reference", 0)} documents, the district’s whole budget page '
        f'mirrored back to FY18. Nothing here feeds a figure on the site.',
        f'- **Written by this project** — {counts.get("ours", 0)} documents. Our '
        f'analyses and machine-readable extracts. These are arguments, not sources.',
        '',
        'Fifteen documents came from the Town by records request rather than off a '
        'website; they carry `byRequest` in `sources.json` and are the only ones recording '
        'money actually spent.',
        '',
        'Text has been extracted from nearly every document, including scans that had no '
        'text layer. Where a document has extracted text, `sources.json` gives a '
        '`textUrl`. Reading the text is usually faster than the PDF.',
        '',
        '## Meeting archive',
        '',
        f'{sources["corpus"]["fetched"]:,} agendas and sets of minutes across '
        f'{sources["corpus"]["boardCount"]} town boards, '
        f'{sources["corpus"]["from"]} to {sources["corpus"]["to"]}. '
        f'**The full text of every one of them is published here and is readable without '
        f'JavaScript.** This is where the town argues about fees, contracts, staffing and '
        f'overrides, and it is not in any budget document.',
        '',
        f'- **To search a board, fetch one file.** [{SITE}/minutes/INDEX.txt]'
        f'({SITE}/minutes/INDEX.txt) lists a bundle per board — every document for that '
        f'board concatenated, largest 1MB. The School Committee is '
        f'[{SITE}/minutes/school-committee.txt]({SITE}/minutes/school-committee.txt). '
        f'You cannot grep a website; you can read one file.',
        f'- **To cite, use the individual document.** Each is at '
        f'`{SITE}/docs/minutes/text/<board>/<date>-<kind>-<id>.txt`, and every bundle '
        f'entry carries that address in its header alongside the town’s scanned original.',
        f'- **To filter by date or board first**, [minutes-index.csv]'
        f'({SITE}/data/minutes-index.csv) has board, date, kind and the town’s own URL.',
        '',
        'An earlier version of this file said the extracted text was "in the repository", '
        'which was true and no use to anybody who was not holding the repository. An '
        'assistant asked to find the School Committee’s discussion of the paraprofessional '
        'contract read this site and concluded it holds "budget documents, not School '
        'Committee minutes". It was wrong, and nothing it could reach showed otherwise. '
        'That is why the text is served now.',
        '',
        '## What this site does not know',
        '',
        '- Out-of-district special education **placement counts** by year. Dollars cannot '
        'distinguish fewer children from a more honest estimate.',
        '- FY26 **year-end** figures. Everything held for FY26 stops at 31 March 2026.',
        '- Whether budgeted positions were **filled**. A budget line is an intention.',
        '',
        '## Provenance',
        '',
        'Source: https://github.com/tjloughlin16/lunenburgbudgetapp. Documents are served '
        'byte-identical to the archive; the build verifies this by hash. One file, a 53MB '
        'scan of the teachers’ agreement, is served from separate storage because it '
        'exceeds the host’s per-file limit, and its `url` in `sources.json` is '
        'absolute.',
    ]

    with open(os.path.join(PUB, 'llms.txt'), 'w') as fh:
        fh.write('\n'.join(lines) + '\n')

    # The same list, for the /agents page to render as LINKS.
    #
    # llms.txt names every one of these and that was not enough: it is text/plain, and
    # assistants commonly refuse to fetch a URL that has not appeared as a link in
    # something they already loaded. So the descriptions written above have to reach the
    # link graph too, and they are written once, here, rather than retyped in a component
    # that would then drift from what llms.txt says these files are.
    df = os.path.join(ROOT, 'fy28', 'src', 'data', 'agent-data-files.json')
    json.dump([dict(name=n, note=w, bytes=b) for n, w, b in published],
              open(df, 'w'), indent=1)
    print(f'  wrote {os.path.relpath(df, ROOT)} for the /agents page')

    print(f'wrote {os.path.relpath(os.path.join(PUB, "llms.txt"), ROOT)}')
    for name, _, size in published:
        print(f'  data/{name:<28}{size / 1e6:>7.1f}MB')


if __name__ == '__main__':
    main()
