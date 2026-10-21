#!/usr/bin/env python3
"""VERIFY THE TOWN MEETING REGISTER AND ITS ARTICLES, BY A SECOND ROUTE.

    python3 scripts/verify_town_meetings.py

build_town_meetings.py reads each warrant's extracted text with one parser. This reads the
same warrants a different way and compares, so a parser defect shows up as a disagreement
instead of as a confident row:

  1. A DIFFERENT EXTRACTION where one exists. The PDF's own text layer, read with pdfplumber
     (the archive's text came through another reader). A scanned booklet has no text layer;
     for those the archive's text is read again with a different parser -- whitespace
     flattened, the article found by its "To see if" sentence rather than by its line -- and
     the report says which route each warrant got.
  2. WHAT THE WARRANT ITSELF NUMBERS. Every article number from 1 to the highest present, and
     where the booklet prints an index of its articles, the index's count.
  3. THE TOWN CLERK'S RECORD (town-meeting-votes.csv, 483 rows). How many rows reach a
     meeting in the register, and -- where our minutes of the recording also hold the same
     article's vote -- whether the two records agree on what happened.

Exit status 1 if an article the generator wrote is absent from the second route, or an
amount disagrees. Disagreements with the Clerk are REPORTED, never fatal: they are two
records of one vote, and either can be wrong.
"""
import collections
import csv
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
DATA = os.path.join(ROOT, 'sources', 'data')
CACHE = os.path.join(ROOT, 'build', 'cache', 'verify-town-meetings')


def read_csv(p):
    return list(csv.DictReader(open(p, encoding='utf-8')))


def plumber_text(pdf):
    """The PDF's own text layer through pdfplumber, cached by the file's size and mtime."""
    st = os.stat(pdf)
    key = os.path.join(CACHE, '%s-%d-%d.txt' % (os.path.basename(pdf), st.st_size, int(st.st_mtime)))
    if os.path.exists(key):
        return open(key, encoding='utf-8').read()
    import pdfplumber
    out = []
    with pdfplumber.open(pdf) as p:
        for i, pg in enumerate(p.pages, 1):
            out.append('===PAGE %d===\n%s' % (i, pg.extract_text() or ''))
    t = '\n'.join(out)
    os.makedirs(CACHE, exist_ok=True)
    open(key, 'w', encoding='utf-8').write(t)
    return t


def second_parse(text):
    """{article: amount} by the second route: flatten all whitespace, find every "ARTICLE N"
    followed within 400 characters by "To see if", keep the run that counts up from 1."""
    flat = re.sub(r'\s+', ' ', text)
    # rejoin a word the text layer split: "AR TICLE", "ARTIC LE"
    flat = re.sub(r'A ?R ?T ?I ?C ?L ?E (\d)', r'ARTICLE \1', flat)
    hits = []
    for m in re.finditer(r'\bARTICLE (\d{1,2})(?: (\d))?(?: ?[.:]| (?=To see))', flat):
        n = int(m.group(1))
        if m.group(2) and hits and int(m.group(1) + m.group(2)) == hits[-1][0] + 1:
            n = int(m.group(1) + m.group(2))
        if re.search(r'to see (?:if|whether)|\((?:submitted|sponsored) by|petition|recommendation',
                     flat[m.end():m.end() + 600], re.I):
            hits.append((n, m.end()))
    # the body: from the last "1" the run that ascends
    starts = [i for i, (n, _) in enumerate(hits) if n == 1]
    if not starts:
        return {}
    run = []
    for n, pos in hits[starts[0]:]:
        if run and n <= run[-1][0]:
            if n == 1:
                break
            continue
        run.append((n, pos))
    out = {}
    for i, (n, pos) in enumerate(run):
        end = run[i + 1][1] if i + 1 < len(run) else pos + 6000
        seg = flat[pos:end]
        w = re.search(r'to see (?:if|whether).*?(?:relative thereto|$)', seg, re.I)
        # the first sentence, cut by a different rule than the generator's: up to "relative
        # thereto" or the first semicolon, whichever comes first, and never past 600 characters
        first = re.split(r'relative thereto|;|:', w.group(0) if w else '', maxsplit=1)[0][:600]
        a = re.search(r'\$ ?\d[\d,]*(?:\.\d{2})?', first)
        out[n] = norm_amount(a.group(0)) if a else ''
    return out


def index_count(text):
    """How many articles the booklet's own INDEX lists, where it prints one ("INDEX OF MAY 5,
    2018 ANNUAL TOWN MEETING ARTICLES"), read as a list of numbered entries: each entry is a
    line that opens with its number, "Article 7:" or a bare "7", and the count is how far the
    numbers climb one at a time -- so a page number or an amount on a line of its own cannot
    extend it. The index ends where the warrant's ARTICLE 1 begins. None when there is no
    index; a table the text layer scattered beyond reading reports what it could read."""
    m = re.search(r'INDEX OF [^\n]*TOWN MEETING[^\n]*ARTICLES', text, re.I) or \
        re.search(r'TABLE OF CONTENTS FOR [^\n]*TOWN MEETING[^\n]*ARTICLES', text, re.I)
    if not m:
        return None
    end = re.search(r'(?m)^\s*ARTICLE\s+1\s*[.:]', text[m.end():])
    seg = text[m.end():m.end() + (end.start() if end else 15000)]
    last = 0
    for x in re.finditer(r'(?m)^\s*(?:Article\s+)?(\d{1,2})\s*[.:]?(?:\s|$)', seg):
        n = int(x.group(1))
        if n == last + 1:
            last = n
    return last or None


def norm_amount(a):
    """'$1,600.00' and '$1,600' are one amount; '$25,000' is not '$25'."""
    x = re.sub(r'[^\d.]', '', a or '')
    return x[:-3] if x.endswith('.00') else x


def main():
    import build_town_meetings as TM
    meetings = read_csv(os.path.join(DATA, 'town-meetings.csv'))
    arts = read_csv(os.path.join(DATA, 'warrant-articles.csv'))
    by_m = collections.defaultdict(dict)
    for a in arts:
        if a['article']:
            by_m[a['meeting']][int(a['article'])] = a
    fails, notes = [], []
    print('1-2. THE WARRANTS, READ TWICE')
    print('  %-16s %-8s %5s %5s %5s %6s  %s' % ('meeting', 'route', 'ours', 'other', 'index', 'amount', 'note'))
    for m in meetings:
        if not m['warrant_doc']:
            continue
        text_rel = m['warrant_doc'].replace('/docs/', '/text/').rsplit('.', 1)[0] + '.txt'
        stored = open(os.path.join(ROOT, text_rel), encoding='utf-8', errors='replace').read()
        pdf = os.path.join(ROOT, m['warrant_doc'])
        route, other = 'text', None
        if os.path.exists(pdf):
            pt = plumber_text(pdf)
            if len(re.sub(r'===PAGE \d+===|\s', '', pt)) > 2000:
                route, other = 'pdf', second_parse(pt)
        if other is None or not other:
            route, other = 'text', second_parse(stored)
        mine = {n: a for n, a in by_m[m['id']].items() if a['details_doc']}
        missing = sorted(set(mine) - set(other))
        extra = sorted(set(other) - set(mine))
        bad_amt = [n for n, a in mine.items() if n in other and norm_amount(a['amount']) != other[n]]
        idx = index_count(TM.normalise(stored))
        top = max(list(mine) + [0])
        gaps = sorted(set(range(1, top + 1)) - set(mine))
        note = []
        if missing:
            note.append('second route lacks %s' % missing)
            # a scan whose text layer is empty is not a disagreement about the warrant
            fails.append('%s: articles %s not found by the second route (%s)' % (m['id'], missing, route))
        if extra:
            note.append('second route also finds %s' % extra)
        if bad_amt:
            note.append('amount differs on %s' % bad_amt)
            fails.append('%s: amounts differ on %s' % (m['id'], bad_amt))
        if gaps:
            note.append('the warrant numbers to %d; no heading read for %s' % (top, gaps))
        # MORE in the index than we parsed is articles we missed. FEWER is the index reader
        # stopping where the table's layout scattered -- noted, not a failure.
        if idx is not None and idx > top:
            note.append('its index lists %d' % idx)
            fails.append('%s: index lists %d articles, parse reached %d' % (m['id'], idx, top))
        elif idx is not None and idx < top:
            note.append('the index could be read only to %d' % idx)
        print('  %-16s %-8s %5d %5d %5s %6s  %s' % (m['id'], route, len(mine), len(other),
                                                   idx if idx is not None else '-',
                                                   'ok' if not bad_amt else 'DIFF', '; '.join(note)))

    print()
    print('3. THE TOWN CLERK\'S RECORD')
    clerk = read_csv(os.path.join(DATA, 'town-meeting-votes.csv'))
    placed = [a for a in arts if a['recorded_ref']]
    undated = [r for r in clerk if not r['meeting_date']]
    print('  %d Clerk rows; %d reach an article in the register; %d carry no meeting date in what we hold '
          '(FY%s) and are not placed' % (len(clerk), len(placed), len(undated),
                                         ', FY'.join(sorted({r['fy'] + ' ' + r['meeting'] for r in undated}))))
    if len(placed) + len(undated) != len(clerk):
        fails.append('%d Clerk rows neither placed nor undated' % (len(clerk) - len(placed) - len(undated)))
    # warrant numbering against the Clerk's: does every Clerk article exist on the warrant?
    off = []
    for a in arts:
        if a['recorded_ref'] and not a['details_doc'] and any(x['details_doc'] for x in by_m[a['meeting']].values()):
            off.append('%s art %s' % (a['meeting'], a['article']))
    print('  Clerk articles missing from a warrant we hold: %d %s' % (len(off), off[:12]))
    # ours against the Clerk's, where both hold the vote
    import build_threads as BT
    record, _ = BT.the_record()
    agree, differ = 0, []
    for m in meetings:
        rec = record.get(('town-meeting', m['date']))
        if not rec:
            continue
        ours = TM.our_article_votes(rec)
        for r in clerk:
            if r['meeting_date'] and r['meeting_date'] == m['date'] and int(r['article']) in ours \
                    and ('atm' if r['meeting'] == 'annual' else 'stm') == m['id'][:3]:
                o = ours[int(r['article'])]['main']
                if not o:
                    continue
                a, b = TM.outcome_word(r['result']), TM.our_result(o)
                same = a == b or {a, b} <= {'passed', 'amended and passed'}
                if b == 'not clear in the record':
                    continue
                if same:
                    agree += 1
                else:
                    differ.append('%s art %s: Clerk %s, ours %s -- %s' % (m['id'], r['article'], a, b, o['motion'][:90]))
    tot = agree + len(differ)
    print('  where both records hold the vote: %d of %d agree on the outcome (%.0f%%)'
          % (agree, tot, 100 * agree / tot if tot else 0))
    for d in differ:
        print('    DIFFERS  ' + d)
    print()
    if fails:
        print('FAILED: %d' % len(fails))
        for f in fails:
            print('  ' + f)
        raise SystemExit(1)
    print('ok')


if __name__ == '__main__':
    main()
