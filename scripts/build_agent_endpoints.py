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


# What this site cannot answer -- and the check that stops the list going stale.
#
# THIS IS THE ONE KIND OF CLAIM THAT ROTS SILENTLY. A "we do not have X" line is only
# falsified by somebody FINDING X, and finding X is exactly the moment nobody thinks to go
# back and edit a disclaimer. Two of the three entries here were wrong for weeks:
#
#   * placement counts were extracted to placement-counts.csv, FY2011-FY2025
#   * per-school staff rosters were extracted to staff-roster-entries.csv, 3,815 rows
#
# and this file went on telling agents neither existed. An agent asked about
# paraprofessionals read "Whether budgeted positions were filled. A budget line is an
# intention", repeated it back almost verbatim, and stopped -- while the same file, four
# sections earlier, handed it a queryable database with a `staff_roster_entries` table in
# it. The disclaimer did not merely fail to help; it contradicted what the site had
# already offered.
#
# So each entry names the dataset that would settle it, and `not_known_lines()` REFUSES TO
# BUILD if that dataset exists and the sentence does not cite its published URL. You cannot
# satisfy the guard without telling the reader where the data is.
NOT_KNOWN = [
    dict(
        settled_by='sources/data/placement-counts.csv',
        text='Out-of-district special education **placement counts** by year — '
             'PARTLY ANSWERED. The town publishes them inside each annual report, sourced '
             'to SIMS Report 7 and measured on 1 March: '
             '`{SITE}/data/placement-counts.csv`, FY2013–FY2025, split into '
             'collaborative, day and residential. **It does not settle the money.** A '
             'placement count is children placed; it says nothing about which fund paid '
             'or what any placement cost, so dollars still cannot distinguish fewer '
             'children from a more honest estimate.'),
    dict(
        settled_by='sources/data/staff-roster-entries.csv',
        text='Whether budgeted positions were **filled** — BOUNDED, not settled. The town '
             'prints per-school staff rosters, by name and position, in every annual '
             'report from FY2011 to FY2025: `{SITE}/api/staff_roster_entries`, 3,815 '
             'rows as one file per fiscal year, and `{SITE}/data/staff-roster-counts.csv` '
             'for the counts. But a roster '
             'carries **no FTE**, so a 0.4 music teacher and a full-timer are one row '
             'each; **no funding source**, which is the question that actually matters; '
             'and it is a point in time, undated within the year. A count of names the '
             'town printed is a real quantity and it is not a staffing level. Grade level '
             'appears only where the roster happens to print it — most paraprofessionals '
             'are grouped by programme (Special Education, Achieve, TLC, Pre-School) '
             'rather than by grade.'),
    dict(
        settled_by='sources/town-ledgers/expenses/'
                   'glytdbud-expense-fy2026-p13-gf-all.xlsx',
        text='FY26 **final** figures. What is held reaches period 12 — 30 June 2026 — '
             'which is before purchase orders are cleared. Period 13 is the one that '
             'closes the year, and nobody has published it.'),
]


def not_known_lines():
    """The "does not know" list, refusing to build once one of its claims is false."""
    stale = []
    for e in NOT_KNOWN:
        settled = os.path.join(ROOT, e['settled_by'])
        if not os.path.exists(settled):
            continue
        # Either address satisfies this: the CSV, or the API resource that publishes the
        # same rows in pieces. What must not happen is the sentence naming neither.
        base = os.path.basename(e['settled_by'])
        forms = ['/data/' + base,
                 '/api/' + os.path.splitext(base)[0].replace('-', '_')]
        public = forms[0]
        if not any(f in e['text'] for f in forms):
            stale.append(f"{e['settled_by']} now exists, and the entry that says this "
                         f"site does not have it never mentions {public}")
    if stale:
        raise SystemExit(
            'llms.txt claims this site does not know something it now does:\n  '
            + '\n  '.join(stale)
            + '\n\n  Rewrite the entry in NOT_KNOWN to say what the data IS and what it '
              'still is not,\n  and cite its published URL. A disclaimer nobody revisits '
              'is how an assistant\n  gets told the archive is empty while standing on '
              'top of it.')
    return [f"- {e['text'].format(SITE=SITE)}" for e in NOT_KNOWN]


def a_real_bundle():
    """A board bundle that exists, with its size — read off disk, never typed.

    `school-committee.txt` was named in three places here and in the /minutes 404 body.
    Splitting the big boards by year so a caller could finish one deleted that exact file,
    and every one of those references became a 404 pointing an agent at nothing. The
    check that caught it is the same one that caught the word index: fetch what you
    advertise.
    """
    import glob as _g
    files = sorted(_g.glob(os.path.join(PUB, 'minutes', 'school-committee*.txt')))
    if not files:
        files = sorted(_g.glob(os.path.join(PUB, 'minutes', '*.txt')))
    if not files:
        return dict(name='INDEX.txt', kb=0)
    f = files[0]
    return dict(name=os.path.basename(f), kb=round(os.path.getsize(f) / 1024))


def worked_example():
    """The three-step search example in llms.txt, read out of the index it describes.

    It used to be typed: *position 1070 is the School Committee minutes of 24 June 2026*.
    Republishing the index renumbers every document, and on 5 September that document
    became 1091 while the sentence went on saying 1070 -- an instruction to an agent to
    look in the wrong place, in the one file written for agents. Rule 2, in the smallest
    possible form: derive it, never type it.
    """
    find = os.path.join(PUB, 'minutes', 'find')
    shard = json.load(open(os.path.join(find, 'je.json')))
    docs = json.load(open(os.path.join(find, 'documents.json')))
    n = shard['jerseys'][0]
    d = docs[n]
    board = d['board'].replace('-', ' ').title()
    when = date.fromisoformat(d['date']).strftime('%-d %B %Y')
    local = os.path.join(ROOT, 'fy28', 'public', d['path'].lstrip('/'))
    return {
        'n': n,
        'path': d['path'],
        'what': f"{board} {d['kind']} of {when}",
        'kb': round(os.path.getsize(local) / 1024) if os.path.exists(local) else 0,
        'docs_kb': round(os.path.getsize(os.path.join(find, 'documents.json')) / 1024),
    }


def main():
    os.makedirs(DATA, exist_ok=True)
    ex = worked_example()
    bundle = a_real_bundle()
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
        (os.path.join(ROOT, 'sources', 'district-budget', 'index.csv'),
         'district-page-index.csv',
         'The 87 documents mirrored from the district budget page: label, our copy, the '
         'extracted text, the district’s original URL, and a sha256.'),
        (os.path.join(ROOT, 'sources', 'data', 'staff-roster-entries.csv'),
         'staff-roster-entries.csv',
         'Every name and position the town printed in its per-school staff rosters, '
         'FY2011 to FY2025 — 3,815 rows across 51 roster blocks, with the school, the '
         'page it came from and the heading it sat under. Published because it is the '
         'only published quantity that bears on whether budgeted positions were filled. '
         'At 435KB this file is more than some callers can fetch in one piece; '
         'https://lunenburgbudgetproject.org/api/staff_roster_entries is the same rows '
         'as one file per fiscal year, about 60KB each. '
         'It is NOT a staffing level: there is no FTE, so a 0.4 music teacher and a '
         'full-timer are one row each; there is no funding source, which is the question '
         'that actually matters; and it is a point in time, undated within the year. '
         'POSITION IS OUR CLASSIFICATION AND IT FAILS IN SOME YEARS. It is mapped from the printed job title, and the print changes: FY2012 says "Tutor", FY2013 "Aide", FY2014 "Paraprofessional" — and once "Paraprotessional", an OCR typo that drops that person from the count. FY2015 printed the page in two columns, which the extractor collapsed, leaving five people with no title at all. So a series counting paraprofessionals in the Kindergarten section reads 0, 5, 4, 4, 0 for FY2011–FY2015 across roughly the same five people. THE ZEROS ARE EXTRACTION FAILURES, NOT STAFFING. Found by an assistant reading the rows, not by any check here. Use `role_raw`, which is what the report actually printed, before trusting `position`.'),
        (os.path.join(ROOT, 'sources', 'data', 'staff-roster-counts.csv'),
         'staff-roster-counts.csv',
         'The same rosters counted by year, school and position — 699 rows. Use this '
         'rather than counting the entries yourself, and read the caveats on '
         'staff-roster-entries.csv before treating any of it as headcount.'),
        (os.path.join(ROOT, 'sources', 'data', 'placement-counts.csv'),
         'placement-counts.csv',
         'Out-of-district special education placements by year, FY2013 to FY2025, split '
         'into collaborative, day and residential. From the Special Services report '
         'inside each annual town report, sourced to SIMS Report 7 and measured on '
         '1 March. Two checks come with it: the parts sum to the total, and each year '
         'states the previous year’s figure. It is a count of children placed and says '
         'nothing about which fund paid or what a placement cost.'),
        (os.path.join(ROOT, 'sources', 'data', 'archive-manifest.csv'),
         'archive-manifest.csv',
         'Every file in the archive — 3,876 of them — with its size, its sha256, and the '
         'publisher’s own URL where one is recorded. The documents themselves are no '
         'longer in the repository: they are in a public, locked R2 bucket and are served '
         'under the /docs/<path> URLs they have always had, so this is the index that '
         'makes a download checkable and the list a fresh clone works from. The bucket '
         'holds no copy of this file, deliberately — an object there cannot be updated '
         'once written, so a manifest inside it would be permanently out of date about '
         'its own contents.'),
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
    ]:
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(DATA, name))
            published.append((name, what, os.path.getsize(src)))

    # NOTHING PUBLISHED HERE MAY BE TOO BIG TO READ.
    #
    # `model.json` is 263KB and is the endpoint this very file tells an agent to fetch
    # first. Three assistants in one day gave up part-way through a published file --
    # `minutes-index.csv` at 242KB, `school-committee.txt` at 907KB -- and a truncated
    # JSON fetch is worse than a truncated CSV, because it does not parse at all. So the
    # big ones are also published in pieces, and the pieces are what gets advertised.
    #
    # 38 top-level keys, each a coherent section: the projection, the programme catalogue,
    # the conclusions, the citations. One file each, plus an index carrying every size so
    # a caller can choose before fetching. The whole file stays where it is for callers
    # that can take it.
    for whole, folder, about in (
        ('model.json', 'model',
         'Every figure the site computes, one section per file.'),
        ('sources.json', 'sources',
         'The document archive: every source, its group, its size and its URL.'),
    ):
        src = os.path.join(DATA, whole)
        if not os.path.exists(src):
            continue
        blob = json.load(open(src))
        out_dir = os.path.join(DATA, folder)
        os.makedirs(out_dir, exist_ok=True)
        parts = []
        for key, value in blob.items():
            with open(os.path.join(out_dir, f'{key}.json'), 'w') as fh:
                json.dump(value, fh, separators=(',', ':'))
            parts.append(dict(
                key=key, url=f'{SITE}/data/{folder}/{key}.json',
                bytes=os.path.getsize(os.path.join(out_dir, f'{key}.json'))))
        with open(os.path.join(out_dir, 'index.json'), 'w') as fh:
            json.dump(dict(
                resource=folder, about=about,
                note=f'{whole} is {os.path.getsize(src) // 1024}KB, which is more than '
                     f'some callers can fetch in one piece. Each section below is a '
                     f'separate file. The whole thing is still at {SITE}/data/{whole}.',
                whole=dict(url=f'{SITE}/data/{whole}',
                           bytes=os.path.getsize(src)),
                count=len(parts),
                parts=sorted(parts, key=lambda p: p['key'])), fh, indent=1)
        published.append((f'{folder}/index.json',
                          about + ' An index; each section is its own file, sized.',
                          os.path.getsize(os.path.join(out_dir, 'index.json'))))

    # The meeting index gets one column the source file does not have: has_text.
    #
    # It is DERIVED here, from what is on disk at publish time, rather than stored
    # upstream -- a stored coverage flag is a claim, and a claim goes stale silently,
    # which is the exact failure this column exists to prevent. 39 documents were once
    # absent from the text tree while every published count said 1,422, so a search
    # returning nothing could not be distinguished from a subject nobody discussed. A
    # caller can now compute its own denominator without probing anything.
    mi_src = os.path.join(ROOT, 'sources', 'meetings', 'index.csv')
    if os.path.exists(mi_src):
        mi_out = os.path.join(DATA, 'minutes-index.csv')
        rows = list(csv.DictReader(open(mi_src)))
        for r in rows:
            stem = os.path.splitext(r['path'])[0] if r['path'].strip() else ''
            r['has_text'] = 'Y' if stem and os.path.exists(
                os.path.join(ROOT, 'sources', 'meetings', 'text', stem + '.txt')) else 'N'
        with open(mi_out, 'w', newline='') as fh:
            w = csv.DictWriter(fh, list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        readable = sum(1 for r in rows if r['has_text'] == 'Y')
        published.append((
            'minutes-index.csv',
            'Every agenda and set of minutes the town publishes: board, date, kind, the '
            f'town’s own URL, and has_text. {len(rows):,} rows, of which {readable:,} '
            'have extracted text a search can reach. Check has_text before concluding '
            'that something was never discussed: a document nothing can read and a '
            'subject nobody raised are different facts and produce the same empty result.',
            os.path.getsize(mi_out)))

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
        f'| the whole meeting archive for one board | `{SITE}/minutes/{bundle["name"]}` |',
        f'| every source document, with checksums | `{SITE}/data/sources.json` |',
        f'| what build you are looking at | `{SITE}/version.json` |',
        '',
        '## If you are unsure whether what you fetched is current',
        '',
        f'Fetch [{SITE}/version.json]({SITE}/version.json) — a few hundred bytes stating '
        'this build’s tag, commit and the document counts that several other files here '
        'repeat. **Compare it with anything else you hold from this site. If another file '
        'disagrees with it, your copy of that file is cached rather than wrong.**',
        '',
        'This exists because you cannot tell otherwise, and neither can we. Caching happens '
        'in your fetch layer, not in HTTP, and a cache-busting query parameter is not '
        'dependable: an assistant sent `?v=923` on eight requests to this site and its tool '
        'reported the parameter stripped from seven of them — seven fetches that looked '
        'fresh and were not. `version.json` is served `no-store`; nothing else here is.',
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
        f'file. It is an object of term to document numbers: `{{"jerseys":[{ex["n"]}]}}`. '
        'Shards average 3KB. A word absent from its shard appears in no document, and a '
        'missing shard file means no indexed word starts with those characters.',
        f'2. **Resolve the numbers.** Document N is in block N // 250 at position '
        f'N % 250, so {ex["n"]} is `{SITE}/minutes/find/documents/{ex["n"] // 250}.json` '
        f'at `documents[{ex["n"] % 250}]` — about 40KB — and it is the {ex["what"]}, '
        f'carrying the path to fetch. The whole table is at '
        f'`{SITE}/minutes/find/documents.json` ({ex["docs_kb"]}KB) if you can hold it; a '
        f'truncated fetch of that gives JSON that does not parse, which is why the blocks '
        f'exist.',
        f'3. **Read the document.** `{SITE}{ex["path"]}`, {ex["kb"]}KB. '
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
        '**To answer a date or board question without reading any text**, fetch that '
        f'board’s index rather than its bundle: `{SITE}/minutes/school-committee.csv` — '
        'same name, `.csv` rather than `.txt`, a few KB, newest first. Date, kind, our '
        'permanent address for each document and the town’s own PDF. Every board has one. '
        f'`{SITE}/data/minutes-index.csv` is all forty in one file and is '
        f'{os.path.getsize(os.path.join(ROOT, "sources", "meetings", "index.csv"))//1024}KB '
        'sorted by board — large enough that a truncating fetcher loses every board past '
        'the letter L, which is why the per-board files exist.',
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
        '## Query the data',
        '',
        f'**Start at the API: [{SITE}/api/index]({SITE}/api/index).** Static JSON, no key, '
        'no rate limit, nothing computed per request. Every response carries the documents '
        'its rows came from, with URL and sha256, so a figure you take from it can be '
        'cited to a source rather than to us. Every endpoint states its own size in '
        '`bytes`, so you can decide before fetching.',
        '',
        f'**Every dataset is fetchable: [{SITE}/api/tables]({SITE}/api/tables).** One '
        'entry per table with its row count and size. The named endpoints are joins and '
        'roll-ups; this is the raw grain — staff rosters, out-of-district placement '
        'counts, fifteen years of annual-report extracts. A table too large for one '
        'fetch is published as an index plus one file per fiscal year, so nothing here '
        'requires a request you cannot afford. This exists because an assistant read an '
        'endpoint list of eight, saw nothing about staffing, and reported that this '
        'project holds no headcount while `staff_roster_entries` had 3,815 rows in it.',
        '',
        'The whole thing is also downloadable as SQLite — '
        f'[{SITE}/data/lunenburg.db]({SITE}/data/lunenburg.db), 16MB, sha256 in '
        '`/api/index` — but that is the fallback, not the front door. Most callers cannot '
        'fetch 16MB of binary, and nothing in it is unreachable through the API.',
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
        f'**The annual town reports are TABLES, and flat text is the wrong artefact for '
        f'them.** 47 of the FY2022 report\u2019s 194 pages are essentially blank in the '
        f'extracted text, because those pages are scans with no text layer \u2014 and '
        f'they are the pages carrying the figures. Two routes work and this one does not:',
        '',
        f'1. **The figures, already extracted.** `{SITE}/api/tables` lists '
        f'`report_appropriations`, `report_gross_wages`, `report_debt` and the rest, one '
        f'file per fiscal year. This is what to use for a number.',
        f'2. **The page as printed**, with its columns intact \u2014 the OCR geometry '
        f'rebuilt into a fixed-width page. 853KB for FY2022, so read it in parts: '
        f'[{SITE}/docs/town-budget/pages/FY2022.ocr.parts/index.json]'
        f'({SITE}/docs/town-budget/pages/FY2022.ocr.parts/index.json). '
        f'Use this to read a table the way a person would.',
        '',
        f'**A document too long to read in one fetch is published in parts.** Any '
        f'`.txt` over 140KB has a folder beside it: append `.parts/index.json` to its '
        f'address for the list, or `.parts/001.txt` for the first piece. The FY2022 '
        f'annual town report is 444KB of text and four parts of about 140KB, each split '
        f'on a page boundary with the pages it covers stated: '
        f'[{SITE}/docs/town-annual-reports/text/4129-fy-2022-annual-town-report.parts/index.json]'
        f'({SITE}/docs/town-annual-reports/text/4129-fy-2022-annual-town-report.parts/index.json). '
        f'The scanned PDF behind it is 16.8MB, is not in the git repository, and is '
        f'served from object storage under the same `/docs/` prefix \u2014 fetch it only '
        f'if you can hold 16.8MB, and read the parts otherwise.',
        '',
        f'**Ask a question instead of downloading a table.** '
        f'[{SITE}/api/query]({SITE}/api/query) takes one read-only SQL statement and '
        f'answers it, with the documents its rows came from. '
        f'**It answers a plain GET, so a fetch tool that cannot POST still works** \u2014 '
        f'put the query in a `sql=` parameter and URL-encode it. A worked example, which '
        f'returns 13 rows in about a kilobyte: '
        f'[{SITE}/api/query?sql=SELECT%20fy%2C%20COUNT%28%2A%29%20AS%20k_paras%20FROM%20'
        f'v_staff_roster%20WHERE%20role_category%3D%27paraprofessional%27%20AND%20'
        f'role_grade%3D%27K%27%20GROUP%20BY%20fy%20ORDER%20BY%20fy]'
        f'({SITE}/api/query?sql=SELECT%20fy%2C%20COUNT%28%2A%29%20AS%20k_paras%20FROM%20'
        f'v_staff_roster%20WHERE%20role_category%3D%27paraprofessional%27%20AND%20'
        f'role_grade%3D%27K%27%20GROUP%20BY%20fy%20ORDER%20BY%20fy). '
        f'[{SITE}/api/questions]({SITE}/api/questions) is 107 worked examples \u2014 a '
        f'question, the query that answers it, and the columns it returns \u2014 every one '
        f'executed on each build, so none of them is a claim. Start there and edit one.',
        '',
        f'**Every dataset is in the API, and the API is the route to take.** '
        f'[{SITE}/api/tables]({SITE}/api/tables) lists all of them with row counts and '
        f'byte sizes; anything too large for one fetch is published as one file per '
        f'fiscal year. The CSVs below are the same data as whole files, and several are '
        f'large enough that a truncating fetcher will stop part-way through them without '
        f'saying so.',
        '',
    ]
    # THE API FIRST, THE FILE SECOND.
    #
    # This listed the CSV as the link and mentioned the API inside the description. An
    # assistant scanning the list fetched `staff-roster-entries.csv`, 435KB, and its
    # response was cut off at about 40% with no marker saying so -- mid-name, mid-2015 --
    # so it reported ten fiscal years as unreachable. `/api/staff_roster_entries/2022`
    # is 73KB and was exactly what it wanted. It never saw it, because the line put the
    # unreadable form in the link position and the readable one in prose.
    api_dir = os.path.join(PUB, 'api')
    for name, what, size in published:
        table = os.path.splitext(name)[0].replace('-', '_')
        split = os.path.isdir(os.path.join(api_dir, table))
        has_api = os.path.exists(os.path.join(api_dir, table + '.json'))
        if has_api and split:
            years = sorted(f[:-5] for f in os.listdir(os.path.join(api_dir, table)))
            lines.append(
                f'- [{table}]({SITE}/api/{table}) — **fetch this, not the CSV.** '
                f'{what} One file per fiscal year, {years[0]}–{years[-1]}, e.g. '
                f'`{SITE}/api/{table}/{years[-1]}`. The whole thing as one CSV is '
                f'[{name}]({SITE}/data/{name}) at {size / 1e6:.1f}MB, which truncating '
                f'fetchers do not finish.')
        elif has_api:
            lines.append(
                f'- [{table}]({SITE}/api/{table}) ({size / 1e6:.1f}MB as CSV): {what} '
                f'Also at [{name}]({SITE}/data/{name}).')
        else:
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
        f'[{SITE}/minutes/{bundle["name"]}]({SITE}/minutes/{bundle["name"]}). '
        f'You cannot grep a website; you can read one file.',
        f'- **To cite, use the individual document.** Each is at '
        f'`{SITE}/docs/minutes/text/<board>/<date>-<kind>-<id>.txt`, and every bundle '
        f'entry carries that address in its header alongside the town’s scanned original.',
        f'- **To filter by date or board first**, fetch that board’s own index: '
        f'[{SITE}/minutes/school-committee.csv]({SITE}/minutes/school-committee.csv) '
        f'— same name as the bundle, `.csv` rather than `.txt`, a few KB, newest first. '
        f'Date, kind, our permanent address for each document and the town’s own PDF. '
        f'Every board has one. '
        f'[All boards in one file]({SITE}/data/minutes-index.csv) is '
        f'{os.path.getsize(os.path.join(ROOT, "sources", "meetings", "index.csv"))//1024}KB '
        f'and sorted by '
        f'board, which some callers cannot read whole — that is why the per-board files '
        f'exist.',
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
        *not_known_lines(),
        '',
        '## Provenance',
        '',
        'Source: https://github.com/tjloughlin16/lunenburgbudgetapp. Documents are served '
        'byte-identical to the archive; the build verifies this by hash, and '
        '`/data/archive-manifest.csv` carries the sha256 of every file so you can check '
        'a download yourself. Every document is at `/docs/<path>` — there are no '
        'exceptions and nothing is too large to serve. The published documents are not in '
        'the git repository: they are in a public, locked object store and streamed under '
        'those same URLs, so cite the `/docs/` address rather than any storage URL you '
        'may see in a response header.',
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

    # /version.json -- what this build is, small enough that nothing truncates it.
    #
    # You cannot stop an agent caching. The cache is in its fetch layer, not in HTTP:
    # Claude Code's own tool documents "responses are cached for 15 minutes per URL" and
    # does not consult cache-control at all. A cache-busting query parameter is not
    # reliable either -- an assistant sent `?v=923` on eight requests here and the tool
    # reported it stripped from seven, so seven looked fresh and were not.
    #
    # So staleness is made DETECTABLE rather than prevented. This file states the build
    # and the counts that other files repeat. One fetch, then compare: if INDEX.txt or
    # /agents disagrees with this, that copy is cached. It was found exactly that way and
    # by accident -- INDEX.txt said one document count and the bundle it indexes said
    # another, and only their overlap made it visible. This makes the check deliberate,
    # and it works from a single file rather than needing two to happen to overlap.
    #
    # It is served no-store by functions/version.js. A cached canary is worse than none:
    # it confirms a stale view as current.
    import subprocess
    def git(*a):
        try:
            return subprocess.run(['git', *a], cwd=ROOT, capture_output=True,
                                  text=True, check=True).stdout.strip()
        except Exception:
            return None
    # The PUBLISHED copy, not the source: has_text is derived when that file is written
    # a few lines above, so reading the source here reported 0 searchable documents out of
    # 1,422 -- a canary stating a false count, which is worse than no canary.
    mi_pub = os.path.join(DATA, 'minutes-index.csv')
    minutes_rows = list(csv.DictReader(open(mi_pub))) if os.path.exists(mi_pub) else []
    boards = {}
    for r in minutes_rows:
        boards[r['board']] = boards.get(r['board'], 0) + 1
    # `builtFrom`, not `commit`, and the rename is the whole fix.
    #
    # This file is written by the build, so the commit that CONTAINS it does not exist yet
    # when it is written -- it is necessarily the child of whatever HEAD was. Calling the
    # field `commit` therefore published a hash that was always one behind, in the one
    # file whose stated job is telling a caller "compare this with anything else you hold;
    # if they disagree, your copy is cached". An agent checking that hash against GitHub
    # would conclude it held a stale copy when it did not.
    #
    # The value was never wrong, only its name. It is the commit the working tree stood at
    # when the build ran, which is exactly what somebody tracing a figure back wants.
    version = dict(
        tag=model.get('releases', {}).get('current'),
        builtFrom=git('rev-parse', '--short', 'HEAD'),
        builtFromNote='The commit this build was made FROM. The commit that contains this '
                      'file is its child, because the file is written before it is '
                      'committed. Use `tag` to identify a release.',
        built=date.today().isoformat(),
        note=('What this build is. Fetch this FIRST and compare it with anything else you '
              'hold from this site: if another file disagrees with these counts, your copy '
              'of that file is cached, not wrong. This file is served no-store.'),
        counts=dict(
            minutes_documents=len(minutes_rows),
            minutes_boards=len(boards),
            minutes_searchable=sum(1 for r in minutes_rows if r.get('has_text') == 'Y'),
            school_committee_documents=boards.get('School Committee'),
            source_documents=sources['totals']['documents'],
        ),
        elsewhere={
            f'{SITE}/minutes/INDEX.txt': 'repeats minutes_documents and the per-board counts',
            f'{SITE}/agents': 'repeats minutes_documents and the per-board counts',
            f'{SITE}/minutes/find/coverage.json': 'repeats minutes_documents and minutes_searchable',
            f'{SITE}/data/minutes-index.csv': 'one row per minutes document, with has_text',
        },
    )
    with open(os.path.join(PUB, 'version.json'), 'w') as fh:
        json.dump(version, fh, indent=1)
    print(f'  wrote public/version.json  {version["tag"]} {version["builtFrom"]} '
          f'({version["counts"]["minutes_documents"]} minutes documents)')

    print(f'wrote {os.path.relpath(os.path.join(PUB, "llms.txt"), ROOT)}')
    for name, _, size in published:
        print(f'  data/{name:<28}{size / 1e6:>7.1f}MB')


if __name__ == '__main__':
    main()
