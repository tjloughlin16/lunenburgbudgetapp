#!/usr/bin/env python3
"""THE SCHOOL COMMITTEE'S LINE ITEM TRANSFERS, voted meeting by meeting, tallied by fiscal year.

    python3 scripts/build_school_transfers.py [--check]

TJ, 10 October 2026: *"build a page for the school committee that captures all the line item
transfers that were voted in a meeting ... part of the meeting fetch process ... a running
tally of the voted upon meeting transfers"*, and then: *"this needs to be associated to each
fiscal year so that I can look at all the line item transfers per fiscal year."*

NOTHING NEW IS READ HERE. The meeting process already reads every set of School Committee
minutes the town posts (`process_meeting.py` -> `extract_official_votes.py`), and each file
under `sources/data/official-votes/school-committee/` carries a `transfers` list: the
transfer as the minutes describe it, the amount as printed, the outcome, and a VERBATIM
quote that `extract_official_votes.py --check` holds to the minutes text. This file turns
those into one table and one page, so the tally moves the day new minutes are read, with no
step of its own to forget. `refresh.py` runs it after the meeting step.

TWO SOURCES, NEVER SUMMED TOGETHER.

  * THE TOWN'S MINUTES are the record. Only their rows are counted and totalled.
  * OUR NOTES FROM THE RECORDING (`recording-minutes/`, written from machine captions) are a
    FINDING AID. A meeting whose recording heard a transfer VOTED and whose minutes are not
    yet read is listed under its year as *awaiting the town's minutes*, with the video at
    the second -- never added to a total, because a caption model hears `$22,856.12` as
    `$22,85612`.

A ROW IS A TRANSFER AS THE MINUTES PRINT IT. Sometimes one line to another; sometimes one
total for a batch (`line item transfers totaling $127,786`); sometimes no amount at all,
when the committee approved transfers "as outlined" and the minutes kept only the vote. So
the count is of items the minutes record, not of ledger transfers, and the page says so.

WHICH FISCAL YEAR, AND HOW WE KNOW (rule 7). A transfer moves money within ONE year's
budget, and that is not always the year the vote fell in: 29 July 2026 approved the FY26
year-end transfers in FY27's first month. So `fy` is, in order:

  1. the year the transfer's own wording states (`FY 25 athletic dues and fees ...`);
  2. the year the meeting's transfer VOTE states, where it states exactly one;
  3. otherwise the fiscal year the meeting fell in (July-June) -- OURS, and labelled so.
     A July-September meeting under rule 3 is flagged: those months often close the year
     before, and the minutes do not say which.

WHAT IS NOT COUNTED, AND WHY, IS KEPT. Every row the minutes reader returned is in the CSV
with `counted` and `why_not`: tabled, still pending, reported rather than voted, a class or
scholarship account (student activity money, not a budget line), or the minutes recording
that there was no transfer. Nothing is dropped silently.

`from_line` / `to_line` are read off the minutes' own wording by pattern -- ours, blank where
the wording does not split cleanly. The description and the quote are the evidence.
"""
import argparse
import csv
import datetime
import glob
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOARD = 'school-committee'
OFFICIAL = os.path.join(ROOT, 'sources', 'data', 'official-votes', BOARD)
RECORDED = os.path.join(ROOT, 'sources', 'data', 'recording-minutes', BOARD)
OUT = os.path.join(ROOT, 'sources', 'data', 'school-committee-transfers.csv')
PAYLOAD = os.path.join(ROOT, 'fy28', 'public', 'data', 'school-committee-transfers.json')
# THE ACCOUNTS ON EACH DISTRICT SHEET, transcribed by eye from the page images and tied to each
# side's printed total (the OCR of these scans scrambles columns and drops lines). Optional:
# without it the sheets still give their totals, and no account is ever inferred.
SHEET_LINES = os.path.join(ROOT, 'sources', 'data', 'school-transfer-sheet-lines.csv')
# How long before a meeting the district's sheet may be dated and still be the one it voted.
SHEET_WINDOW_DAYS = 14
SITE = 'https://lunenburgbudgetproject.org'

COLS = ['fy', 'fy_basis', 'meeting_date', 'source', 'status', 'counted', 'why_not', 'description',
        'from_line', 'to_line', 'amount_as_printed', 'amount', 'amount_basis', 'outcome',
        'quote', 'minutes_url', 'our_copy', 'video_url']

FY_RE = re.compile(r'\bFY\s?-?\s?(\d{4}|\d{2})\b', re.I)
MONEY = re.compile(r'\$?\s?(\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)')
PASSED = re.compile(r'approv|passed|accept|carried|so voted|voted', re.I)
NOT_VOTED = [
    (re.compile(r'\btabled?\b', re.I), 'tabled'),
    (re.compile(r'pending|deferred', re.I), 'not yet voted'),
    (re.compile(r'reported to this board|^reported|discussed only', re.I), 'reported or discussed, not voted by the committee'),
    (re.compile(r'none recorded|no line item transfers', re.I), 'the minutes record no transfer'),
]
NOT_LINE_ITEM = re.compile(r'class (?:of \d{4}|accounts?)|scholarship|Finance Committee transfer|'
                           r'reserve fund transfer|donat', re.I)


def school_fy(date):
    d = datetime.date.fromisoformat(date)
    return d.year + 1 if d.month >= 7 else d.year


def fys_in(text):
    out = set()
    for m in FY_RE.finditer(text or ''):
        n = int(m.group(1))
        out.add(n if n > 1000 else 2000 + n)
    return out


def amount_of(printed):
    """(number or '', basis). Several figures are summed -- `$16,063.77 and $7,136.41` is two
    sources into one line -- except `$X (from $a and $b)`, where X is already the total."""
    p = (printed or '').strip()
    if not p or p.lower() in ('none', 'none printed', 'not stated', 'none stated') or not MONEY.search(p):
        return '', 'no amount printed'
    if '(from' in p:
        p = p.split('(from')[0]
    nums = [float(x.replace(',', '')) for x in MONEY.findall(p)]
    if not nums:
        return '', 'no amount printed'
    total = round(sum(nums), 2)
    return ('%.2f' % total), ('as printed' if len(nums) == 1 else 'sum of %d figures printed' % len(nums))


def lines_of(description):
    # Parentheticals out first: `from Elementary Guidance salary (due to a resignation)`
    # otherwise splits on the `to` inside the aside.
    d = re.sub(r'\s+', ' ', re.sub(r'\([^)]*\)', '', description or '')).strip().rstrip('.')
    m = re.search(r'\bfrom (?:the )?(.+?)\s+(?:line(?: item)?s?\s+|accounts?\s+)?to (?:the )?(.+?)(?:\s+line(?: item)?s?\b|,|;|\(| to cover| for | at the |$)', d, re.I)
    if m:
        # `from multiple lines to cover expenses`: what follows `to` is a purpose, not a line.
        if re.match(r'(cover|pay|fund|meet|reconcile|represent)\b', m.group(2), re.I):
            return m.group(1).strip(), ''
        return m.group(1).strip(), m.group(2).strip()
    m = re.match(r'^([A-Z][^,;:]{2,80}?) to ([^,;:]{2,90}?)(?:,|;|$)', d)
    if m and 'transfer' not in m.group(1).lower():
        to = '' if re.match(r'(cover|pay|fund|meet|reconcile|represent)\b', m.group(2), re.I) else m.group(2)
        return m.group(1).strip(), to.strip()
    return '', ''


def official_rows():
    rows = []
    for f in sorted(glob.glob(os.path.join(OFFICIAL, '*.json'))):
        d = json.load(open(f, encoding='utf-8'))
        date = d['meeting_date']
        src = d.get('source') or {}
        votes = [v for v in d.get('votes') or [] if re.search(r'transfer', v.get('motion', ''), re.I)]
        vote_fys = set().union(*[fys_in(v['motion']) for v in votes]) if votes else set()
        items = d.get('transfers') or []
        # A transfer VOTE with no transfer itemised: the minutes kept the vote, not the lines.
        if not items and any(PASSED.search(v.get('outcome', '')) for v in votes) \
                and not any(NOT_LINE_ITEM.search(v['motion']) for v in votes):
            v = votes[0]
            items = [{'description': v['motion'] + ' (the minutes record the vote, not the lines)',
                      'amount_as_printed': '', 'outcome': v['outcome'], 'quote': v.get('quote', '')}]
        for t in items:
            desc, quote = t.get('description', ''), t.get('quote', '')
            own = fys_in(desc + ' ' + quote)
            if len(own) == 1:
                fy, basis = own.pop(), 'stated in the minutes for this transfer'
            elif len(vote_fys) == 1:
                fy, basis = next(iter(vote_fys)), 'stated in the minutes for the vote'
            else:
                fy = school_fy(date)
                basis = 'the fiscal year the meeting fell in (ours; the minutes do not say)'
                if datetime.date.fromisoformat(date).month in (7, 8, 9):
                    basis += ' -- a July-September vote may close the year before'
            why = ''
            outcome = t.get('outcome', '')
            for rx, reason in NOT_VOTED:
                if rx.search(outcome) or (reason == 'the minutes record no transfer' and rx.search(desc)):
                    why = reason
                    break
            if not why and NOT_LINE_ITEM.search(desc):
                why = 'not a budget line item transfer (a class, scholarship, donation or reserve-fund account)'
            if not why and (t.get('amount_as_printed') or '').strip().lower() in ('none', 'none printed') \
                    and not PASSED.search(outcome):
                why = 'the minutes record no transfer'
            if not why and not PASSED.search(outcome):
                why = 'no vote to approve recorded'
            amt, abasis = amount_of(t.get('amount_as_printed'))
            fl, tl = lines_of(desc)
            rows.append({
                'fy': str(fy), 'fy_basis': basis, 'meeting_date': date, 'source': 'town minutes',
                'counted': 'no' if why else 'yes', 'why_not': why,
                'description': desc, 'from_line': fl, 'to_line': tl,
                'amount_as_printed': t.get('amount_as_printed') or '', 'amount': amt,
                'amount_basis': abasis, 'outcome': outcome, 'quote': quote,
                'minutes_url': src.get('minutes_url', ''), 'our_copy': src.get('doc_url', ''),
                'video_url': '',
            })
    return rows


def recording_rows(have_minutes):
    """Transfers our notes heard VOTED at a meeting whose town minutes are not read. Listed,
    never counted: captions are a finding aid."""
    rows = []
    for f in sorted(glob.glob(os.path.join(RECORDED, '*.json'))):
        m = json.load(open(f, encoding='utf-8'))
        date = m['meeting_date']
        if date in have_minutes:
            continue
        for t in m['minutes'].get('transfers') or []:
            outcome = t.get('outcome', '')
            if not re.search(r'\bvoted\b|passed|approved', outcome, re.I) or re.search(r'discussed only|prior meeting', outcome, re.I):
                continue
            desc = t.get('description', '')
            if NOT_LINE_ITEM.search(desc):
                continue
            own = fys_in(desc)
            fy, basis = (own.pop(), 'stated in the recording') if len(own) == 1 else (
                school_fy(date), 'the fiscal year the meeting fell in (ours)')
            rows.append({
                'fy': str(fy), 'fy_basis': basis, 'meeting_date': date,
                'source': 'recording (machine captions)', 'counted': 'no',
                'why_not': 'awaiting the town’s minutes; heard in the recording only',
                'description': desc, 'from_line': '', 'to_line': '',
                'amount_as_printed': t.get('amount_as_heard') or '', 'amount': '',
                'amount_basis': 'as heard by a caption model -- not a figure',
                'outcome': outcome, 'quote': '', 'minutes_url': '', 'our_copy': '',
                'video_url': '%s&t=%ds' % (m['video_url'], int(t.get('t') or 0)),
            })
    return rows


# THE DISTRICT'S OWN TRANSFER SHEETS. The minutes keep the vote; the line detail -- org and
# object codes, original budget, the amount moved -- is on a form the district prepares and
# the committee is shown. Where the archive holds one, it is listed under its fiscal year as
# the line-level source. Found by label across every catalogue, never by folder (a sheet
# can arrive from the district's page or by another route), and the year is read off the
# sheet's own `FY:` / `Fiscal Year` / `FY22 LINE ITEM` printing, never guessed.
SHEET_LABEL = re.compile(r'line item transfer|budget transfer(?! authority)|reclassification of expenses', re.I)
SHEET_FY = [re.compile(r'\bFY:\s*(?:DATE:\s*)?(\d{4})'), re.compile(r'Fiscal Year\s+(\d{4})'),
            re.compile(r'\bFY(\d{2}) LINE ITEM')]
SHEET_DATE = [re.compile(r'DATE:\s*(?:\d{4}\s+)?(\d{1,2}/\d{1,2}/\d{4})'),
              re.compile(r'Date:\s*([A-Z][a-z]+ \d{1,2}, \d{4})'),
              re.compile(r'presented on \w+, ([A-Z][a-z]+ \d{1,2}, \d{4})')]


def sheet_pages():
    """{sheet path: [page dict]} from the transcription, each page with its from and to
    accounts. A page whose sides do not sum to its printed totals is kept and FLAGGED --
    the transcription says what is printed; this says whether it adds up."""
    if not os.path.exists(SHEET_LINES):
        return {}
    pages = {}
    for r in csv.DictReader(open(SHEET_LINES, encoding='utf-8')):
        key = (r['sheet'], r['page'])
        pg = pages.setdefault(key, {'page': r['page'], 'form': r['form'], 'explanation': r['explanation'],
                                    'from': [], 'to': [], 'totals': {}})
        pg[r['side']].append({'org': r['org'], 'object': r['object'], 'description': r['description'],
                              'amount_as_printed': r['amount_as_printed']})
        pg['totals'][r['side']] = r['total_as_printed']
    out = {}
    for (sheet, _), pg in sorted(pages.items(), key=lambda kv: (kv[0][0], int(kv[0][1] or 0))):
        for side in ('from', 'to'):
            got = sum(float(amount_of(x['amount_as_printed'])[0] or 0) for x in pg[side])
            want = amount_of(pg['totals'].get(side, ''))[0]
            pg['ties_' + side] = bool(want) and abs(got - float(want)) < 0.005
        pg['total'] = amount_of(pg['totals'].get('from') or pg['totals'].get('to') or '')[0]
        del pg['totals']
        out.setdefault(sheet, []).append(pg)
    return out


def sheets():
    out, seen = [], set()
    lines = sheet_pages()
    for idx in sorted(glob.glob(os.path.join(ROOT, 'sources', '*', 'index.csv'))):
        for r in csv.DictReader(open(idx, encoding='utf-8', errors='replace')):
            local, text = r.get('local') or '', r.get('text') or ''
            if not SHEET_LABEL.search(r.get('label') or '') or local in seen or not text:
                continue
            tp = os.path.join(ROOT, text)
            if not os.path.exists(tp):
                continue
            body = open(tp, encoding='utf-8', errors='replace').read()
            fy = ''
            for rx in SHEET_FY:
                m = rx.search(body)
                if m:
                    fy = m.group(1) if len(m.group(1)) == 4 else '20' + m.group(1)
                    break
            if not fy:
                continue
            dated = ''
            for rx in SHEET_DATE:
                m = rx.search(body)
                if m:
                    dated = m.group(1)
                    break
            seen.add(local)
            note = ''
            for fmt in ('%m/%d/%Y', '%B %d, %Y'):
                try:
                    when = datetime.datetime.strptime(dated, fmt).date().isoformat()
                except ValueError:
                    continue
                if str(school_fy(when)) != fy:
                    note = ('the sheet prints FY%s and is dated %s, which falls in FY%d; listed under '
                            'the year it prints' % (fy, dated, school_fy(when)))
                break
            # EVERY transfer on the sheet, not the first: the 7 October 2026 sheet carries two
            # (pages 2 and 3) and a reclassification (page 1), and reading only the first total
            # showed $18,703.94 of $41,560.06. TJ found it by reading the meeting.
            totals = re.findall(r'TOTAL AMOUNT FROM\s*-?\$\s?([\d,]+\.\d{2})', body)
            reclass = re.findall(r'Reclassification of expenses.*?AMOUNT\s*\n?\s*\$?\s*([\d,]+\.\d{2})', body, re.S)
            when_iso = ''
            for fmt in ('%m/%d/%Y', '%B %d, %Y'):
                try:
                    when_iso = datetime.datetime.strptime(dated, fmt).date().isoformat()
                    break
                except ValueError:
                    pass
            out.append({'fy': fy, 'label': r['label'], 'dated_as_printed': dated, 'note': note,
                        'dated': when_iso, 'pages': lines.get(local, []),
                        'transfers_as_printed': ['$' + t for t in totals],
                        'reclassifications_as_printed': ['$' + t for t in reclass],
                        'url': '/docs/' + local[len('sources/'):],
                        'publisher_url': r.get('upstream') or ''})
    return sorted(out, key=lambda x: (x['fy'], x['url']))


def sheet_for(fy, meeting_date, sh):
    """The district sheet a meeting most plausibly voted: same fiscal year, dated on or up to
    SHEET_WINDOW_DAYS before the meeting. Ours, a match by date; said so on every row."""
    m = datetime.date.fromisoformat(meeting_date)
    hits = [x for x in sh if x['fy'] == fy and x['dated']
            and 0 <= (m - datetime.date.fromisoformat(x['dated'])).days <= SHEET_WINDOW_DAYS]
    return max(hits, key=lambda x: x['dated']) if hits else None


def tentative_rows(rec, sh):
    """TENTATIVE: a transfer vote heard in a RECORDING, at a meeting whose minutes the town
    has not posted, with the amounts and accounts taken from the district's sheet for it. TJ,
    10 October 2026: *"we should show these transfers as 'tentative' ... interpreted from the
    transcript, until we get the official minutes report."* Each row says all three: the vote
    is interpreted, the figures are the sheet's, the minutes are awaited. A reclassification
    page on the sheet is listed but not totalled -- the motion named the transfers."""
    out, used = [], set()
    for r in rec:
        s_ = sheet_for(r['fy'], r['meeting_date'], sh)
        if not s_:
            continue
        used.add(id(r))
        pages = s_['pages'] or [{'page': '', 'form': 'budget transfer', 'explanation': '', 'from': [], 'to': [],
                                 'total': amount_of(t)[0], 'ties_from': False, 'ties_to': False}
                                for t in s_['transfers_as_printed']]
        for pg in pages:
            reclass = pg['form'] == 'reclassification'
            out.append(dict(r, status='tentative', counted='no',
                            why_not=('a reclassification on the sheet, not in the motion' if reclass else
                                     'tentative: vote heard in the recording; amounts and accounts from the '
                                     'district\u2019s sheet; awaiting the town\u2019s minutes'),
                            source='recording + district sheet',
                            description=pg['explanation'] or r['description'],
                            from_line='; '.join(x['description'] for x in pg['from']),
                            to_line='; '.join(x['description'] for x in pg['to']),
                            amount_as_printed=('$' + '{:,.2f}'.format(float(pg['total']))) if pg['total'] else '',
                            amount='' if reclass else pg['total'],
                            amount_basis='the district sheet\u2019s printed total',
                            sheet=s_['url'], sheet_page=pg['page'], form=pg['form'],
                            accounts={'from': pg['from'], 'to': pg['to']},
                            ties=pg['ties_from'] and pg['ties_to']))
    return out, [r for r in rec if id(r) not in used]


def attach_accounts(rows, sh):
    """A transfer in the MINUTES whose amount equals a sheet page's total, from a sheet dated
    in the window before the meeting, gets that page's accounts. Equal to the cent, or nothing."""
    for r in rows:
        if r['counted'] != 'yes' or not r['amount']:
            continue
        s_ = sheet_for(r['fy'], r['meeting_date'], sh)
        for pg in (s_ or {}).get('pages', []):
            if pg['total'] and abs(float(pg['total']) - float(r['amount'])) < 0.005:
                r['accounts'] = {'from': pg['from'], 'to': pg['to']}
                r['sheet'] = s_['url']
                r['sheet_page'] = pg['page']
                break


def build():
    off = official_rows()
    have = {r['meeting_date'] for r in off} | {
        json.load(open(f, encoding='utf-8'))['meeting_date'] for f in glob.glob(os.path.join(OFFICIAL, '*.json'))}
    sh = sheets()
    for r in off:
        r['status'] = 'confirmed' if r['counted'] == 'yes' else 'not counted'
    attach_accounts(off, sh)
    rec = recording_rows(have)
    for r in rec:
        r['status'] = 'heard only'
    tent, rec = tentative_rows(rec, sh)
    rows = off + tent + rec
    rows.sort(key=lambda r: (r['fy'], r['meeting_date'], r['source'] != 'town minutes'))
    return rows, sorted(have)


def payload(rows, read_dates):
    years = {}
    for sh in [dict(x) for x in sheets()]:
        sh.pop('pages', None); sh.pop('dated', None)
        years.setdefault(sh['fy'], {'fy': int(sh['fy']), 'counted': [], 'tentative': [], 'awaiting': [],
                                    'not_counted': [], 'sheets': []}).setdefault('sheets', []).append(sh)
    for r in rows:
        y = years.setdefault(r['fy'], {'fy': int(r['fy']), 'counted': [], 'tentative': [], 'awaiting': [],
                                       'not_counted': [], 'sheets': []})
        item = {k: r[k] for k in ('meeting_date', 'description', 'from_line', 'to_line',
                                  'amount_as_printed', 'amount', 'amount_basis', 'outcome',
                                  'quote', 'minutes_url', 'our_copy', 'video_url', 'fy_basis', 'why_not')}
        item['fy_ours'] = r['fy_basis'].startswith('the fiscal year the meeting')
        for k in ('accounts', 'sheet', 'sheet_page', 'form', 'ties'):
            if k in r:
                item[k] = r[k]
        if r['counted'] == 'yes':
            y['counted'].append(item)
        elif r['status'] == 'tentative':
            y.setdefault('tentative', []).append(item)
        elif r['source'] != 'town minutes':
            y['awaiting'].append(item)
        else:
            y['not_counted'].append(item)
    out = []
    for fy in sorted(years, reverse=True):
        y = years[fy]
        y.setdefault('sheets', [])
        y.setdefault('tentative', [])
        y['tentative_total'] = '%.2f' % sum(float(t['amount']) for t in y['tentative'] if t['amount'])
        running = 0.0
        for it in y['counted']:
            if it['amount']:
                running += float(it['amount'])
            it['running_total'] = '%.2f' % running
        y['total'] = '%.2f' % running
        # NEWEST FIRST ON THE PAGE (TJ, 10 October 2026). The running total is still summed
        # in date order, so each row's figure is the year's total THROUGH that meeting.
        for k in ('counted', 'tentative', 'awaiting', 'not_counted'):
            y[k] = list(reversed(y[k]))
        y['n'] = len(y['counted'])
        y['n_no_amount'] = sum(1 for it in y['counted'] if not it['amount'])
        y['meetings'] = len({it['meeting_date'] for it in y['counted']})
        y['n_fy_ours'] = sum(1 for it in y['counted'] if it['fy_ours'])
        out.append(y)
    first, last = read_dates[0], read_dates[-1]
    return {
        'board': 'School Committee',
        'minutes_read': len(read_dates), 'minutes_from': first, 'minutes_to': last,
        'years': out,
        'grain': ('A row is a line item transfer as the School Committee’s minutes record it: '
                  'sometimes one line to another, sometimes one total for a batch, sometimes only '
                  'the vote. Totals add the amounts the minutes print; a transfer approved with no '
                  'amount printed is counted and adds nothing. The fiscal year is the one the '
                  'minutes state where they state one, otherwise the year the meeting fell in, '
                  'marked as ours.'),
        'sources': [
            {'label': 'Every row, counted or not, with the reason', 'url': '/docs/data/school-committee-transfers.csv'},
            {'label': 'The town’s minutes, as read for votes and transfers',
             'url': '/docs/data/official-votes/school-committee/'},
        ],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    rows, read = build()
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLS, lineterminator='\n', extrasaction='ignore')
    w.writeheader()
    w.writerows(rows)
    p = payload(rows, read)
    outs = [(OUT, buf.getvalue()),
            (PAYLOAD, json.dumps(p, indent=1, sort_keys=True, ensure_ascii=False) + '\n')]
    if a.check:
        bad = 0
        for path, want in outs:
            have = open(path, encoding='utf-8', newline='').read() if os.path.exists(path) else None
            if have != want:
                print('STALE -- %s; run scripts/build_school_transfers.py' % os.path.relpath(path, ROOT))
                bad = 1
        if not bad:
            print('ok -- %d transfer rows across %d fiscal years reproduce' % (len(rows), len(p['years'])))
        return bad
    for path, want in outs:
        tmp = path + '.tmp'
        open(tmp, 'w', encoding='utf-8', newline='').write(want)
        os.replace(tmp, path)
    for y in p['years']:
        print('FY%d: %d transfer(s) at %d meeting(s), $%s printed (%d with no amount; %d year by meeting '
              'date); %d awaiting minutes; %d not counted'
              % (y['fy'], y['n'], y['meetings'], '{:,.2f}'.format(float(y['total'])), y['n_no_amount'],
                 y['n_fy_ours'], len(y['awaiting']), len(y['not_counted'])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
