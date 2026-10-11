#!/usr/bin/env python3
"""EVERY BOARD'S TRANSFERS, voted meeting by meeting, tallied by fiscal year -- with how good the
evidence for each one is, and, where a district form gives the accounts, which school and which
program the money left and reached.

    python3 scripts/build_board_transfers.py [--check]

Built first for the School Committee and generalised the same day (TJ, 10 October 2026: *"we
need a link on each board page for their TRANSFER link"*): the town's minutes of every board are
read for transfers by the meeting process, so every board that has voted one gets a page at
/boards/<slug>/transfers. The School Committee's is the deep one, because only the school
district publishes a transfer FORM with account numbers.

THE EVIDENCE, GRADED (TJ: *"we need to say whether or not these transfers have the GOLD STANDARD
for each. flag when not"*). Three records can speak for a transfer, and they are not equal:

  * THE DISTRICT'S TRANSFER FORM -- `Budget Transfer` or `Reclassification of expenses`, signed,
    with every account's org and object code and the amount. The GOLD STANDARD: it says exactly
    what moved where. Held for very few.
  * THE TOWN'S MINUTES -- the official record that the vote happened, naming the lines in WORDS
    and never by account number. Good, and far less detailed.
  * OUR NOTES FROM THE RECORDING -- machine captions, a finding aid. Least dependable.

Every row carries which of the three exist for it, and `gold` is true only with the form.

THE ACCOUNTS, LOOKED UP IN OUR OWN RECORDS. A form's org and object code are found in the
school department's MUNIS ledger (`munis-school-ytd.csv`), whose full account string carries the
DESE function code (segment 4, named from DESE's own list) and the BUILDING (segment 6). The
building reading is OURS, measured: in the ledger every account name with a school prefix sits
in one value of that segment -- E.S. in 4, M.S. in 5, H.S. in 6, P.S. and kindergarten in 2 --
with no exception, and the support is printed with it. A transfer whose sides differ in building
or function is flagged as crossing schools or programs. An org the ledger does not hold is said
to be not found, never guessed.

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
SCHOOL = 'school-committee'
OFFICIAL_ROOT = os.path.join(ROOT, 'sources', 'data', 'official-votes')
RECORDED_ROOT = os.path.join(ROOT, 'sources', 'data', 'recording-minutes')
OUT = os.path.join(ROOT, 'sources', 'data', 'board-transfers.csv')
PAYLOAD_DIR = os.path.join(ROOT, 'fy28', 'public', 'data', 'transfers')
BOARDS_JSON = os.path.join(ROOT, 'fy28', 'public', 'data', 'boards.json')
MUNIS_SCHOOL = os.path.join(ROOT, 'sources', 'data', 'munis-school-ytd.csv')
DESE_FUNCTIONS = os.path.join(ROOT, 'sources', 'data', 'dese-function-expenditure.csv')
# THE ACCOUNTS ON EACH DISTRICT SHEET, transcribed by eye from the page images and tied to each
# side's printed total (the OCR of these scans scrambles columns and drops lines). Optional:
# without it the sheets still give their totals, and no account is ever inferred.
SHEET_LINES = os.path.join(ROOT, 'sources', 'data', 'school-transfer-sheet-lines.csv')
# How long before a meeting the district's sheet may be dated and still be the one it voted.
SHEET_WINDOW_DAYS = 14
SITE = 'https://lunenburgbudgetproject.org'

COLS = ['board', 'kind', 'fy', 'fy_basis', 'meeting_date', 'source', 'status', 'counted', 'gold', 'has_form',
        'has_minutes', 'has_recording', 'crosses', 'why_not', 'description',
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
# For any other board a reserve fund transfer IS a transfer it votes -- the Finance Committee's
# main one -- so only student-activity and gift money is set aside there.
NOT_TRANSFER_ANY = re.compile(r'class (?:of \d{4}|accounts?)|scholarship|donat', re.I)


def not_line_item(board):
    return NOT_LINE_ITEM if board == SCHOOL else NOT_TRANSFER_ANY


# WHAT KIND OF TRANSFER, for the boards whose minutes say "transfer" about more than one thing.
# Read on 10 October 2026 from a sample of the Select Board's and Finance Committee's rows: a
# LICENCE transfer moves no money at all, and a town meeting ARTICLE is a transfer the board
# only recommends -- town meeting votes it. Both are kept in the table with the reason and
# kept out of the board's total. Ours, by the minutes' own words; a row that matches nothing
# is `other` and counted, because the minutes recorded a transfer vote.
NOT_MONEY = re.compile(r'licen[cs]e|ownership|deed|easement', re.I)
ARTICLE = re.compile(r'\barticle\b|\bwarrant\b|town meeting|recommend', re.I)
KINDS = [(re.compile(r'reserve fund', re.I), 'reserve fund'),
         (re.compile(r'stabili[sz]ation', re.I), 'stabilization fund'),
         (re.compile(r'line item|line-item', re.I), 'line item')]


def kind_of(board, text):
    if board == SCHOOL:
        return 'line item'
    for rx, k in KINDS:
        if rx.search(text):
            return k
    return 'other'


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


def official_rows(board):
    rows = []
    NLI = not_line_item(board)
    for f in sorted(glob.glob(os.path.join(OFFICIAL_ROOT, board, '*.json'))):
        d = json.load(open(f, encoding='utf-8'))
        date = d['meeting_date']
        src = d.get('source') or {}
        votes = [v for v in d.get('votes') or [] if re.search(r'transfer', v.get('motion', ''), re.I)]
        vote_fys = set().union(*[fys_in(v['motion']) for v in votes]) if votes else set()
        items = d.get('transfers') or []
        # A transfer VOTE with no transfer itemised: the minutes kept the vote, not the lines.
        if not items and any(PASSED.search(v.get('outcome', '')) for v in votes) \
                and not any(NLI.search(v['motion']) for v in votes):
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
            if not why and NLI.search(desc):
                why = 'not a budget line item transfer (a class, scholarship, donation or reserve-fund account)'
            if not why and board != SCHOOL and NOT_MONEY.search(desc):
                why = 'not a transfer of money (a licence or property transfer)'
            if not why and board != SCHOOL and ARTICLE.search(desc + ' ' + t.get('outcome', '')):
                why = 'a town meeting article the board acted on; town meeting votes the transfer'
            if not why and (t.get('amount_as_printed') or '').strip().lower() in ('none', 'none printed') \
                    and not PASSED.search(outcome):
                why = 'the minutes record no transfer'
            if not why and not PASSED.search(outcome):
                why = 'no vote to approve recorded'
            amt, abasis = amount_of(t.get('amount_as_printed'))
            fl, tl = lines_of(desc)
            rows.append({
                'board': board, 'kind': kind_of(board, desc),
                'fy': str(fy), 'fy_basis': basis, 'meeting_date': date, 'source': 'town minutes',
                'counted': 'no' if why else 'yes', 'why_not': why,
                'description': desc, 'from_line': fl, 'to_line': tl,
                'amount_as_printed': t.get('amount_as_printed') or '', 'amount': amt,
                'amount_basis': abasis, 'outcome': outcome, 'quote': quote,
                'minutes_url': src.get('minutes_url', ''), 'our_copy': src.get('doc_url', ''),
                'video_url': '',
            })
    return rows


def recording_dates(board):
    """Meetings whose recording our notes say discussed or voted a transfer -- the third, least
    dependable kind of evidence, recorded per meeting."""
    out = set()
    for f in glob.glob(os.path.join(RECORDED_ROOT, board, '*.json')):
        m = json.load(open(f, encoding='utf-8'))
        if any(t.get('amount_as_heard') not in ('none', 'none reported') for t in m['minutes'].get('transfers') or []):
            out.add(m['meeting_date'])
    return out


def recording_rows(board, have_minutes):
    """Transfers our notes heard VOTED at a meeting whose town minutes are not read. Listed,
    never counted: captions are a finding aid."""
    rows = []
    NLI = not_line_item(board)
    for f in sorted(glob.glob(os.path.join(RECORDED_ROOT, board, '*.json'))):
        m = json.load(open(f, encoding='utf-8'))
        date = m['meeting_date']
        if date in have_minutes:
            continue
        for t in m['minutes'].get('transfers') or []:
            outcome = t.get('outcome', '')
            if not re.search(r'\bvoted\b|passed|approved', outcome, re.I) or re.search(r'discussed only|prior meeting', outcome, re.I):
                continue
            desc = t.get('description', '')
            if NLI.search(desc):
                continue
            own = fys_in(desc)
            fy, basis = (own.pop(), 'stated in the recording') if len(own) == 1 else (
                school_fy(date), 'the fiscal year the meeting fell in (ours)')
            if board != SCHOOL and (NOT_MONEY.search(desc) or ARTICLE.search(desc)):
                continue
            rows.append({
                'board': board, 'kind': kind_of(board, desc),
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


# ------------------------------------------------------------------ accounts, looked up

def munis_accounts():
    """{(org, object): account} from the school department's MUNIS ledger, the latest year
    each pair appears, with its full account string, the ledger's own name, the DESE function
    and the building. Plus the support for the building reading, measured on this ledger."""
    if not os.path.exists(MUNIS_SCHOOL):
        return {}, {}
    fnames = {}
    if os.path.exists(DESE_FUNCTIONS):
        for r in csv.DictReader(open(DESE_FUNCTIONS, encoding='utf-8')):
            if r.get('level') == 'detail' and r.get('func_code', '').isdigit():
                fnames[r['func_code']] = r['func_desc']
    rows = [r for r in csv.DictReader(open(MUNIS_SCHOOL, encoding='utf-8'))
            if r['fund'] == '0100' and r['account'].count('-') == 8]
    # THE BUILDING SEGMENT, read off the ledger itself: which school prefix the names in each
    # value carry. A value whose names carry none is district-wide -- also our reading.
    prefix = re.compile(r'^(P\.S\.|E\.S\.|M\.S\.|H\.S\.|KIND)', re.I)
    votes = {}
    for r in rows:
        m = prefix.match(r['description'].replace('M.S.PARA', 'M.S. PARA'))
        if m:
            votes.setdefault(r['account'].split('-')[5], {}).setdefault(m.group(1).upper(), set()).add(r['account'])
    label = {'P.S.': 'Primary School', 'KIND': 'Primary School', 'E.S.': 'Elementary School',
             'M.S.': 'Middle School', 'H.S.': 'High School'}
    building = {}
    for seg, by in votes.items():
        names = {label[k] for k in by}
        n = sum(len(v) for v in by.values())
        if len(names) == 1:
            building[seg] = (names.pop(), 'ours: all %d account names in this building code carry its prefix' % n)
    out = {}
    for r in sorted(rows, key=lambda r: r['fiscal_year']):
        seg = r['account'].split('-')
        b = building.get(seg[5], ('District-wide', 'ours: no account name in this code carries a school prefix'))
        out[(r['org'], r['obj'])] = {
            'munis_account': r['account'], 'munis_name': r['description'], 'munis_fy': r['fiscal_year'],
            'building': b[0], 'building_basis': b[1],
            'function_code': seg[3], 'function_name': fnames.get(seg[3], ''),
        }
    return out, building


def enrich(accounts, look):
    """Each account line gets what our ledger says about it, or `found: False`."""
    for side in ('from', 'to'):
        for a in accounts.get(side, []):
            hit = look.get((a['org'], a['object']))
            a['found'] = bool(hit)
            if hit:
                a.update(hit)
    return accounts


def crosses(accounts):
    """['schools', 'programs'] where the money changes building or DESE function on the way."""
    out = []
    for key, word in (('building', 'schools'), ('function_code', 'programs')):
        f = {a.get(key) for a in accounts.get('from', []) if a.get('found')}
        t = {a.get(key) for a in accounts.get('to', []) if a.get('found')}
        if f and t and f != t:
            out.append(word)
    return out


def build(board):
    off = official_rows(board)
    have = {json.load(open(f, encoding='utf-8'))['meeting_date']
            for f in glob.glob(os.path.join(OFFICIAL_ROOT, board, '*.json'))}
    sh = sheets() if board == SCHOOL else []
    for r in off:
        r['status'] = 'confirmed' if r['counted'] == 'yes' else 'not counted'
    attach_accounts(off, sh)
    rec = recording_rows(board, have)
    for r in rec:
        r['status'] = 'heard only'
    tent, rec = tentative_rows(rec, sh)
    rows = off + tent + rec
    heard = recording_dates(board)
    look, _ = munis_accounts() if board == SCHOOL else ({}, {})
    for r in rows:
        if r.get('accounts'):
            enrich(r['accounts'], look)
        r['has_form'] = 'yes' if r.get('accounts') else 'no'
        r['has_minutes'] = 'yes' if r['source'] == 'town minutes' else 'no'
        r['has_recording'] = 'yes' if r['meeting_date'] in heard else 'no'
        r['gold'] = r['has_form']
        r['crosses'] = ' '.join(crosses(r['accounts'])) if r.get('accounts') else ''
    rows.sort(key=lambda r: (r['fy'], r['meeting_date'], r['source'] != 'town minutes'))
    return rows, sorted(have)


def payload(board, name, rows, read_dates):
    years = {}
    for sh in ([dict(x) for x in sheets()] if board == SCHOOL else []):
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
        item['evidence'] = {'form': r['has_form'] == 'yes', 'minutes': r['has_minutes'] == 'yes',
                            'recording': r['has_recording'] == 'yes'}
        item['crosses'] = r['crosses'].split() if r['crosses'] else []
        item['kind'] = r.get('kind', '')
        for k in ('accounts', 'sheet', 'sheet_page', 'form', 'ties'):
            if k in r:
                item[k] = r[k]
        if r['counted'] == 'yes':
            y['counted'].append(item)
        elif r['status'] == 'tentative':
            y['tentative'].append(item)
        elif r['source'] != 'town minutes':
            y['awaiting'].append(item)
        else:
            y['not_counted'].append(item)
    out = []
    for fy in sorted(years, reverse=True):
        y = years[fy]
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
        y['n_gold'] = sum(1 for it in y['counted'] if it['evidence']['form'])
        y['n_no_amount'] = sum(1 for it in y['counted'] if not it['amount'])
        y['meetings'] = len({it['meeting_date'] for it in y['counted']})
        y['n_fy_ours'] = sum(1 for it in y['counted'] if it['fy_ours'])
        out.append(y)
    school = board == SCHOOL
    return {
        'board': name, 'slug': board,
        'what': 'line item transfers' if school else 'transfers',
        'has_forms': school,
        'minutes_read': len(read_dates),
        'minutes_from': read_dates[0] if read_dates else '', 'minutes_to': read_dates[-1] if read_dates else '',
        'years': out,
        'grain': ('A row is a transfer as the %s\u2019s minutes record it: sometimes one line to another, '
                  'sometimes one total for a batch, sometimes only the vote. Totals add the amounts the '
                  'minutes print; a transfer approved with no amount printed is counted and adds nothing. '
                  'The fiscal year is the one the minutes state where they state one, otherwise the year '
                  'the meeting fell in, marked as ours.' % name),
        'sources': [
            {'label': 'Every row for every board, counted or not, with the reason and the evidence',
             'url': '/docs/data/board-transfers.csv'},
        ] + ([{'label': 'Every account line on the district\u2019s transfer forms',
               'url': '/docs/data/school-transfer-sheet-lines.csv'}] if school else []),
    }


def boards():
    """Every board whose minutes or recordings hold a transfer, with its name from the site."""
    names = {}
    if os.path.exists(BOARDS_JSON):
        names = {b['slug']: b['name'] for b in json.load(open(BOARDS_JSON, encoding='utf-8'))['boards']}
    slugs = set()
    for root in (OFFICIAL_ROOT, RECORDED_ROOT):
        for d in glob.glob(os.path.join(root, '*')):
            if os.path.isdir(d):
                slugs.add(os.path.basename(d))
    return sorted((s, names[s]) for s in slugs if s in names)


def render(obj):
    return json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    all_rows, outs, index = [], [], []
    for slug, name in boards():
        rows, read = build(slug)
        if not any(r['counted'] == 'yes' or r['status'] in ('tentative', 'heard only') for r in rows):
            continue
        p = payload(slug, name, rows, read)
        all_rows += rows
        outs.append((os.path.join(PAYLOAD_DIR, slug + '.json'), render(p)))
        latest = p['years'][0]
        index.append({'slug': slug, 'name': name, 'what': p['what'],
                      'transfers': sum(y['n'] for y in p['years']),
                      'latest_fy': latest['fy'], 'latest_n': latest['n'],
                      'latest_tentative': latest['tentative_total'],
                      'url': '/boards/%s/transfers' % slug})
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLS, lineterminator='\n', extrasaction='ignore')
    w.writeheader()
    w.writerows(all_rows)
    outs += [(OUT, buf.getvalue()),
             (os.path.join(PAYLOAD_DIR, 'index.json'), render({'boards': index}))]
    if a.check:
        bad = 0
        for path, want in outs:
            have = open(path, encoding='utf-8', newline='').read() if os.path.exists(path) else None
            if have != want:
                print('STALE -- %s; run scripts/build_board_transfers.py' % os.path.relpath(path, ROOT))
                bad = 1
        if not bad:
            print('ok -- %d transfer rows across %d boards reproduce' % (len(all_rows), len(index)))
        return bad
    os.makedirs(PAYLOAD_DIR, exist_ok=True)
    for path, want in outs:
        tmp = path + '.tmp'
        open(tmp, 'w', encoding='utf-8', newline='').write(want)
        os.replace(tmp, path)
    for b in index:
        print('%-40s %3d transfers; FY%d: %d%s' % (b['name'], b['transfers'], b['latest_fy'], b['latest_n'],
              ', $%s tentative' % b['latest_tentative'] if float(b['latest_tentative']) else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
