#!/usr/bin/env python3
"""Every quoted passage and every figure on /special-education-class-size, re-derived.

    python3 scripts/verify_sped_regulation.py

WHY A SECOND ROUTE RATHER THAN A SECOND READING

`build_sped_regulation.py --check` proves the payload still reproduces from the generator.
That proves the generator agrees with itself. This reads the published payload -- what a
reader actually gets -- and checks it against the sources by a DIFFERENT PATH:

  * the quotations against DESE'S OWN HTML, tags stripped, rather than against the
    extracted text the generator read. The extract is our instrument; the HTML is the
    document. Rule 13: an instrument that reformats before you see it is part of the
    finding. Six district documents once looked like they had changed when the only thing
    wrong was our fetcher.
  * the group-size tiers by a plain regular expression over that same HTML, written
    independently of the generator's structural parser. A rival parser for one page's
    figures once found a definition error nothing else could have found.
  * the placement counts by SQL straight at `dese_sped_program`, not through the
    generator's helper.
  * THE PROHIBITION ITSELF, as an assertion. This page must not publish a required
    number of paraprofessionals for Lunenburg. So the payload is searched for the shapes
    that claim would take -- a division of the placement count by any tier size -- and
    the run fails if one is present. A rule kept by eye lasts until the next report.

RULE 2, STRUCTURALLY. Nothing in this file states a figure from the regulation. Every
number it compares is parsed out of the HTML on this run and compared to the number in
the payload, so this verifier cannot pass by agreeing with a value somebody typed here.
"""
import html
import json
import os
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAY = os.path.join(ROOT, 'fy28', 'public', 'data', 'sped-regulation.json')
REG = os.path.join(ROOT, 'sources', 'state-dese',
                   '603cmr28-special-education-regulations.html')
SIMS = os.path.join(ROOT, 'sources', 'state-dese', 'sims-datahandbook-current.docx')
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
GAPS = os.path.join(ROOT, 'sources', 'data', 'money-gaps.csv')
MINUTES = os.path.join(ROOT, 'sources', 'meetings', 'text')
LEA = '01620000'

FAILS = []
CHECKS = [0]


def ok(cond, msg):
    CHECKS[0] += 1
    if not cond:
        FAILS.append(msg)


def flat(s):
    return re.sub(r'\s+', ' ', s).strip()


def plain(path):
    """DESE's page as text, by a route the generator does not use: strip the markup,
    unescape the entities, collapse the whitespace. The visually-hidden spans that expand
    `CMR` are LEFT IN, because they are in the document and a reader's screen reader gets
    them -- removing them here would be this verifier quoting its own rendering."""
    raw = open(path, encoding='utf-8', errors='replace').read()
    raw = re.sub(r'(?is)<(script|style)[^>]*>.*?</\1>', ' ', raw)
    return flat(html.unescape(re.sub(r'<[^>]+>', ' ', raw)))


def main():
    for p in (PAY, REG, SIMS, DB, GAPS):
        if not os.path.exists(p):
            print('missing: %s' % os.path.relpath(p, ROOT))
            return 1
    d = json.load(open(PAY, encoding='utf-8'))
    doc = plain(REG)

    # 1. EVERY QUOTED PASSAGE IS IN DESE'S OWN PAGE, EXACTLY ONCE.
    for key, cl in sorted(d['clauses'].items()):
        t = flat(cl['text'])
        ok(doc.count(t) == 1,
           '%s: the passage the page prints appears %d times in DESE’s own HTML, not '
           'once — %r' % (key, doc.count(t), t[:70]))

    # 2. THE TIERS, RE-PARSED FROM THE HTML BY A DIFFERENT EXPRESSION.
    c = re.search(r'group size shall not exceed (.{0,260}?)\.', doc)
    dd = re.search(r'instructional groupings that do not exceed (.{0,220}?)\.', doc)
    ok(bool(c) and bool(dd), 'the two sentences that state the group sizes are no longer '
                             'in DESE’s page in the form this reads')
    words = {'one': 1, 'two': 2, 'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9}
    n = lambda t: int(t) if t.isdigit() else words[t.lower()]      # noqa: E731
    if c and dd:
        part = [(n(a), 0 if b else n(x))
                for a, b, x in re.findall(
                    r'([A-Za-z0-9]+) students (?:(with a certified special educator)|'
                    r'if the certified special educator is assisted by ([a-z]+) aides?)',
                    c.group(1))]
        subs = [(n(a), 0 if b == 'one certified special educator' else 1)
                for a, b in re.findall(
                    r'([A-Za-z0-9]+) students to (one certified special educator|'
                    r'a certified special educator and an aide)', dd.group(1))]
        want = [(t['students'], t['aides']) for t in d['tiers']]
        ok(part + subs == want,
           'the tiers this verifier reads out of the HTML are %s; the page publishes %s'
           % (part + subs, want))
        ok(all(t['educators'] == 1 for t in d['tiers']),
           'a published tier names more than one certified special educator, which is the '
           'shape the whole scenario table is built to show')
        ok(max(a for _s, a in subs) == 1 and max(a for _s, a in part) == 2,
           'the asymmetry the page is built on has moved: the substantially separate '
           'clause should stop at one aide and the partly separate one should reach two')
        ok(doc.count('two aides') == 1,
           '"two aides" occurs %d times in DESE’s page, and the claim that the third '
           'tier belongs to one clause only rests on it occurring once'
           % doc.count('two aides'))

    # The two provisions that qualify every row.
    mid = re.search(r'by no more than ([a-z]+) additional students', doc)
    age = re.search(r'shall not differ by more than (\d+) months', doc)
    ok(bool(mid) and n(mid.group(1)) == d['midyear_extra'],
       'the mid-year allowance in the regulation is not what the page publishes')
    ok(bool(age) and int(age.group(1)) == d['age_months'],
       'the 48-month age range in the regulation is not what the page publishes')
    thr = re.search(r'for more than (\d+)% of the students', doc)
    ok(bool(thr) and int(thr.group(1)) == d['threshold_pct'],
       'the threshold that separates the two settings is not what the page publishes')

    # The young-children rows, likewise.
    for row in d['young']:
        ok(('%d' % row['students']) in doc or
           any(w for w, v in words.items() if v == row['students'] and w in doc),
           'the young-children row for %d students is not findable in the regulation'
           % row['students'])

    # 3. WHAT DESE'S LABELS MEAN, out of the SIMS handbook, by a second read.
    import zipfile
    sims = flat(re.sub(r'<[^>]+>', ' ',
                       zipfile.ZipFile(SIMS).read('word/document.xml').decode('utf-8')))
    for code in d['codes']:
        ok(flat(code['definition']) in sims,
           'the SIMS handbook no longer defines %s the way the page prints it'
           % code['label'])
        m = re.search(r'(\d+)%', code['definition'])
        ok(bool(m), '%s: the definition states no percentage, and the percentage is the '
                    'axis the whole join is made on' % code['label'])
    sub = [c for c in d['codes'] if c['code'] == '40']
    ok(len(sub) == 1 and str(d['threshold_pct']) + '%' in sub[0]['definition'],
       'DOE034 value 40 and 603 CMR 28.06(6)(d) no longer turn on the same threshold, '
       'which is the only thing that makes the two halves of this page comparable')

    # 4. THE PLACEMENT COUNTS, straight at the table.
    db = sqlite3.connect(DB)
    p = d['placement']
    rows = db.execute(
        "SELECT indicator, indicator_level, measure_cnt FROM dese_sped_program "
        "WHERE lea=? AND geo_level='district' AND indicator_category='Placement' AND fy=?",
        (LEA, p['fy'])).fetchall()
    tot = [int(r[2]) for r in rows if r[1] == 'total']
    mem = {r[0]: int(r[2]) for r in rows if r[1] == 'member'}
    ok(tot == [p['total']], 'the published total (%s) is not the total DESE prints (%s)'
       % (p['total'], tot))
    ok(sum(mem.values()) == p['named'],
       'the four printed categories sum to %d, and the page says %d'
       % (sum(mem.values()), p['named']))
    ok(p['total'] - p['named'] == p['unnamed'],
       'the count of children in no printed category does not reconcile')
    ok(mem.get('Substantially Separate') == p['sub']['count'],
       'the substantially separate count is not what DESE publishes')
    ok(p['fy'] == db.execute("SELECT MAX(fy) FROM dese_sped_program WHERE lea=? AND "
                             "indicator_category='Placement'", (LEA,)).fetchone()[0],
       'the page is not reading the most recent year DESE publishes')
    for r in p['rows']:
        ok(abs(r['pct'] - round(100.0 * r['count'] / p['total'], 1)) < 0.05,
           '%s: the share does not recompute from its own count and total' % r['label'])

    # 5. THE PROHIBITION. Nothing on this page may be a required staffing number for
    # Lunenburg, so the arithmetic that would produce one must not appear in the payload.
    blob = json.dumps(d, ensure_ascii=False)
    # NOT by looking for the QUOTIENT. `8` is a tier size, `5` is a preschool cap and
    # `41` is a published count, so every digit that division would produce is already
    # legitimately on the page. What must not appear is one of them presented as a count
    # of staff -- so the search is for the phrasing that would do it.
    for word in ('paraprofessionals required', 'paraprofessionals needed',
                 'staff required', 'would require', 'needs at least',
                 'should have at least', 'must employ'):
        ok(word not in blob.lower(),
           'the payload contains %r. This page states the rule and the counts; it does '
           'not compute a staffing requirement for Lunenburg, and the reason is a '
           'registered gap' % word)
    ok(any('four groups or seven' in c.get('so_what', '') + c['detail']
           for c in d['conclusions']),
       'the page no longer says that the same count of children is lawful at very '
       'different staffing levels, which is the whole reason it stops where it does')

    # 6. THE GAP ROW IS STILL REGISTERED, and the page quotes it rather than paraphrasing.
    import csv
    reg = [r for r in csv.DictReader(open(GAPS, encoding='utf-8'))
           if r['what'].strip() == d['gap']['what'].strip()]
    ok(len(reg) == 1,
       'the limit this page is built around is not a row in money-gaps.csv. Rule 7c: the '
       'registry outranks the page')
    if reg:
        ok(reg[0]['why'].strip() == d['gap']['why'].strip(),
           'the page and the gap registry no longer say the same thing about why no '
           'staffing number follows')
        ok(reg[0]['side'].strip() == d['gap']['side'].strip(),
           'the gap row has changed side')
    # AND THE TWO THIS PAGE ADDED. Rule 7c: a limit written in one paragraph of one page
    # is invisible to everyone who did not read that page, so writing this one registered
    # two more -- the aide/paraprofessional definitional gap and the children in no
    # printed placement category. Both are quoted, not paraphrased.
    all_gaps = {r['what'].strip(): r for r in
                csv.DictReader(open(GAPS, encoding='utf-8'))}
    ok(len(d['gaps_also']) == 2,
       'the page publishes %d further registered gaps; it was written with two'
       % len(d['gaps_also']))
    for g in d['gaps_also']:
        row = all_gaps.get(g['what'].strip())
        ok(row is not None,
           'money-gaps.csv no longer registers %r, which this page quotes as a row in it'
           % g['what'][:70])
        if row:
            ok(row['why'].strip() == g['why'].strip(),
               '%r: the page and the registry no longer say the same thing'
               % g['what'][:70])

    # 7. EVERY QUOTE IS STILL IN THE MEETING DOCUMENT IT NAMES.
    for q in d['said']:
        rel = q['cite'].replace('/docs/', 'sources/')
        path = os.path.join(ROOT, rel)
        ok(os.path.exists(path), '%s: the document this quote cites is not here' % rel)
        if os.path.exists(path):
            body = flat(open(path, encoding='utf-8', errors='replace').read())
            ok(flat(q['quote']) in body,
               '%s %s: the quote is no longer in %s' % (q['board'], q['date'], rel))

    # 8. THE COVERAGE DENOMINATOR IS PRESENT AND NON-TRIVIAL. A grep that found nothing
    # printed beside no denominator reads as "nobody said it", and two of this page's
    # search terms legitimately return zero.
    m = d['minutes']
    ok(m['held'] == m['searchable'] + m['unsearchable'] and m['searchable'] > 0,
       'the meeting coverage figures do not reconcile, and this page publishes two '
       'searches that return zero')
    ok(any(s['documents'] == 0 for s in d['searched']),
       'no search on this page returns zero any more — if the town has started using '
       'the regulation’s vocabulary that is a finding, and the prose beside it needs '
       'rewriting rather than the check relaxing')

    # 9. WHAT THE PERSONA REVIEW ADDED, asserted rather than remembered.
    # notes/process/PERSONAS.md, 10 September 2026. Three readers failed on the first pass
    # and three things were added to the page. Prose is the one thing on this site nothing
    # recomputes, so each fix is pinned here -- the cut-register precedent, where six
    # review-added phrases are asserted for the same reason.
    ids = [c['id'] for c in d['conclusions']]
    ok(ids and ids[1] == 'no-required-number',
       'reader 1: the limit — that no staffing number for Lunenburg follows from any '
       'of this — was moved to the second conclusion so it sits under the ratio rather '
       'than behind five confident statements of the rule. It is now %r'
       % (ids[1] if len(ids) > 1 else None))
    ok(ids and ids[0] == 'eight-to-one',
       'reader 2 and TJ both: the ratio leads. The first conclusion is %r'
       % (ids[0] if ids else None))
    pull = [q for q in d['said'] if 'paraprofessional rather than a certified' in q['quote']]
    ok(len(pull) == 1 and 'provide, design, or supervise' in pull[0]['why'],
       'reader 3: the note on the pull-out quote must point at 28.02(3)’s "provide, '
       'design, or supervise", which is what stops a teacher’s public statement being '
       'read as an allegation of non-compliance')
    if pull:
        ok(flat('may provide, design, or supervise special education services') in doc,
           'the clause that note rests on is no longer in the regulation')
    ok(flat(d['clauses']['28.06(6)']['text']).lower().startswith(
        '(6) instructional grouping requirements'),
       'reader 2: the grain box quotes 28.06(6)’s own opening to say this is not a '
       'general class-size rule, and that clause is no longer what the payload holds')
    ok('aged five and older' in d['clauses']['28.06(6)']['text'],
       'reader 2: the scope sentence the grain box rests on — eligible students aged '
       'five and older, outside the general education environment — has moved')

    # 10. EVERY PHRASE THE PAGE ITSELF PUTS IN QUOTATION MARKS.
    #
    # Rule 13's hardest half: check what a READER sees, not only what the payload holds.
    # Most of this page's quotation is rendered from `clauses`, which section 1 already
    # checked against DESE's HTML -- but a handful of phrases are set inside the page's
    # own prose, in `&ldquo;...&rdquo;`, and nothing else on this run would notice one
    # drifting. So the component is read as text, every such phrase is pulled out, and
    # each is looked for in the regulation. A phrase this finds that is NOT a quotation
    # of the regulation belongs in `ALLOWED` with a reason, rather than being matched
    # loosely -- an exception written down is reviewable and a loose match is not.
    page = os.path.join(ROOT, 'fy28', 'src', 'pages', 'ClassSize.tsx')
    ALLOWED = {
        # DESE's own labels, from the SIMS handbook rather than from the regulation.
        'Substantially Separate', 'Full Inclusion', 'Partial Inclusion',
        'aide', 'paraprofessional',   # the two words, discussed AS words
        # The vocabulary the town does not use -- rendered from `searched`, and checked
        # there.
        '603 CMR', 'substantially separate',
    }
    if os.path.exists(page):
        src = flat(open(page, encoding='utf-8').read())
        quoted = re.findall(r'&ldquo;(.*?)&rdquo;', src)
        ok(len(quoted) > 0,
           'the page quotes nothing in its own prose any more, and this check has '
           'silently stopped having anything to check')
        checked = 0
        for qt in quoted:
            # A quotation whose whole content is an interpolation -- the search terms the
            # town does not use -- is checked where it is COMPUTED, not here. Skipped
            # explicitly, because stripping it would leave an empty string and an empty
            # string is a substring of everything: a check that passes on nothing.
            if re.fullmatch(r'\s*\{[^}]*\}\s*', qt):
                continue
            t = flat(re.sub(r'\{[^}]*\}|<[^>]+>|&rsquo;', "'", qt)).replace("''", "'")
            if not t or t in ALLOWED:
                continue
            checked += 1
            hit = t in doc or t.replace("'", '\u2019') in doc
            ok(hit,
               'the page sets %r in quotation marks and that string is not in DESE\u2019s '
               'text of the regulation. Quote the source, never your rendering of it '
               '\u2014 or add it to ALLOWED here with a reason' % t[:90])
        ok(checked >= 2,
           'only %d quotation(s) in the page\u2019s own prose were checked against the '
           'regulation. This check earns nothing if the page has stopped quoting, so it '
           'says so rather than passing quietly' % checked)

    print('%d checks' % CHECKS[0])
    if FAILS:
        for f in FAILS:
            print('FAIL  %s' % f)
        return 1
    print('ok — every quoted passage, every tier and every count on '
          '/special-education-class-size re-derives from the source')
    return 0


if __name__ == '__main__':
    sys.exit(main())
