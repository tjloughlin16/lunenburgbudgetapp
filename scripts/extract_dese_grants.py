#!/usr/bin/env python3
"""DESE's current grant opportunities, one row per program, read off the held pages.

    python3 scripts/extract_dese_grants.py           # write sources/data/dese-grant-opportunities.csv
    python3 scripts/extract_dese_grants.py --check   # fail if it no longer reproduces

Reads the WORKING COPIES fetch_dese_grants.py keeps -- `sources/state-dese/grants/grants.html`
and one `detail/<FY>-<code>.html` per program -- and nothing on the network. The list gives
the columns DESE prints (fund code, program, posted, due, type, state or federal, unit,
contact); each program's own page gives the Eligibility text, a first sentence of Purpose and
of Funding, quoted, never paraphrased.

`district_reading` IS OURS, AND THE PAGE SAYS SO. It is a conservative reading of DESE's
eligibility text, by the fixed rules in `read_eligibility()`, into three values:

  districts eligible   the text names public school districts (or LEAs, or "all public
                       schools") as a class that may apply or that receives the money --
                       possibly with conditions, which the verbatim text beside it states;
  not districts        the text names only other kinds of applicant (colleges, state
                       agencies, workforce boards, non-profits, charter schools...) and no
                       district at all;
  unclear              everything else -- above all, a grant limited to NAMED or PRIOR
                       recipients (last year's grantees, a list of districts, the recipients
                       the state budget names) that does not name Lunenburg.

The rule that fired is written into `reading_basis`, so every row says why. When in doubt the
answer is `unclear`, never `not districts`: telling a school a grant is not for it is the
more expensive mistake.

`open_on_list_date` compares the due date to the date of the look that confirmed these bytes
(the last row of `sources/state-dese/grants/checked.csv`). DESE keeps a program on the list
for some time after it closes, so most rows are past their due date; that is DESE's list, not
a finding about anybody.
"""
import argparse
import csv
import datetime
import hashlib
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fetch_dese_grants import (_text, parse_list, detail_key, detail_url, LIST_KEY,  # noqa: E402
                               LOG_ROOT, SRC)

ROOT = os.path.dirname(HERE)
OUT = os.path.join(SRC, 'data', 'dese-grant-opportunities.csv')
FIELDS = ['fund_code', 'program', 'posted', 'due', 'grant_type', 'funding', 'unit', 'contact',
          'open_on_list_date', 'district_reading', 'reading_basis', 'names_lunenburg',
          'purpose', 'funding_text', 'eligibility', 'detail_url', 'fetched', 'list_sha256',
          'detail_sha256']

# ---------------------------------------------------------------- the reading, fixed rules
DISTRICTISH = re.compile(r'\bdistricts?\b|\bLEAs?\b|local educational? agenc|public[- ]schools?\b'
                         r'|school food authorit', re.I)
NOT_DISTRICT_CLASS = re.compile(
    r'\bcolleges\b|postsecondary institution|state agency|workforce boards?'
    r'|non-?profit organizations|test centers|charter schools?\b|charter high school', re.I)
# A grant limited to a closed set: last year's grantees, a named list, a prior designation,
# an intent already filed, the recipients the state budget names.
RESTRICTED = [
    (r'as listed in the state budget|as outlined in the fy\s?\d{4} state budget',
     'limited to recipients the state budget names'),
    (r'eligible districts include|the following massachusetts public school districts'
     r'|the following districts|eligible districts and schools',
     'limited to districts DESE lists by name'),
    (r'\bgrantees\b|continuation (year )?grant|previously received|received (prior )?funding'
     r'|that received|have received|who received|were awarded|recipients awarded',
     'limited to past recipients'),
    (r'participating currently|currently participating|currently implementing|currently funded as'
     r'|currently operating|currently eligible', 'limited to current participants'),
    (r'districts identified|only eligible|targeted to|\btargeted:', 'limited to targeted recipients'),
    (r'(those|that) (have )?submitted|submitted an intent|intent to apply',
     'limited to applicants who filed earlier'),
    (r'designated programs|designation from dese', 'limited to programs DESE has designated'),
]
OPEN_CLASS = [
    r'\ball (massachusetts )?(public[- ]school districts|public schools|local education agencies)',
    r'eligible applicants (are|include)[^.]{0,40}(public school districts|districts)',
    r'designed for districts', r'open to public schools? districts',
    r'any (massachusetts )?(public )?school districts?', r'\ba local educational agency',
    r'awarded (by formula )?to (each school district|districts|public school leas|leas)',
    r'allocated to leas', r'a district (or consortium )?is eligible',
    r'school districts? (that|which) (participate|offer)',
    r'\(local education agency or sponsoring organization\)',
]


def read_eligibility(text):
    """(reading, basis) from DESE's eligibility text. The order is the point:

      1. the text names Lunenburg;
      2. it names only other kinds of applicant, and no school district anywhere;
      3. its OPENING SENTENCE opens the grant to districts as a class, with no restriction in
         that sentence -- later sentences are conditions and permissions ("applicants that
         have received this grant in the past are eligible"), which the verbatim text shows;
      4. a restriction to a closed set anywhere (a two-option grant whose first option is for
         prior grantees is not, as a whole, open);
      5. an open-class phrase anywhere;
      6. otherwise `unclear`."""
    t = ' '.join(text.split())
    if 'lunenburg' in t.lower():
        return 'districts eligible', 'the eligibility text names Lunenburg'
    if not DISTRICTISH.search(t):
        m = NOT_DISTRICT_CLASS.search(t)
        if m:
            return 'not districts', 'names only other applicants (%s), no school district' % m.group(0).lower()
    first = re.split(r'(?<=[.:!?])\s', t, maxsplit=1)[0]
    if not any(re.search(p, first, re.I) for p, _ in RESTRICTED):
        for pat in OPEN_CLASS:
            m = re.search(pat, first, re.I)
            if m:
                return 'districts eligible', 'opens with school districts as eligible (“%s”)' % m.group(0)
    for pat, why in RESTRICTED:
        if re.search(pat, t, re.I):
            return 'unclear', why + '; Lunenburg is not named'
    for pat in OPEN_CLASS:
        m = re.search(pat, t, re.I)
        if m:
            return 'districts eligible', 'names school districts as eligible (“%s”)' % m.group(0)
    if not DISTRICTISH.search(t):
        return 'unclear', 'names no school district and no other kind of applicant we recognise'
    return 'unclear', 'mentions districts, but not as a class that may apply'


# ---------------------------------------------------------------- parsing
def _iso_long(s):
    """'Friday, October 23, 2026' -> '2026-10-23'; '' when DESE printed no date."""
    m = re.search(r'([A-Z][a-z]+) (\d{1,2}), (\d{4})', s)
    if not m:
        return ''
    return datetime.datetime.strptime(' '.join(m.groups()), '%B %d %Y').date().isoformat()


def _iso_short(s):
    m = re.match(r'(\d{1,2})/(\d{1,2})/(\d{4})$', s.strip())
    return '%s-%02d-%02d' % (m.group(3), int(m.group(1)), int(m.group(2))) if m else ''


def sections(page):
    """{dt label: dd text} from a program page's definition list."""
    dl = re.findall(r'<dt\b[^>]*>(.*?)</dt>\s*<dd\b[^>]*>(.*?)</dd>', page, re.S)
    out = {}
    for k, v in dl:
        out.setdefault(_text(k).rstrip(':').strip(), _text(v))
    return out


def first_sentence(text, cap=240):
    t = ' '.join(text.replace('\n- ', '; ').split())
    m = re.match(r'(.+?[.!?])(\s|$)', t)
    s = m.group(1) if m else t
    if len(s) > cap:
        s = s[:cap].rsplit(' ', 1)[0].rstrip(',;:') + ' …'
    return s


def last_look():
    p = os.path.join(LOG_ROOT, 'checked.csv')
    rows = list(csv.DictReader(open(p, encoding='utf-8')))
    return rows[-1]['checked']


def sha_file(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def build():
    lp = os.path.join(SRC, LIST_KEY)
    rows = parse_list(open(lp, encoding='utf-8').read())
    list_sha = sha_file(lp)
    looked = last_look()
    out = []
    for r in rows:
        key = detail_key(r['href'])
        p = os.path.join(SRC, key) if key else None
        if not p or not os.path.exists(p):
            raise SystemExit('no held page for %s (%s): run fetch_dese_grants.py'
                             % (r['Program Name'], r['href']))
        page = open(p, encoding='utf-8').read()
        s = sections(page)
        elig = s.get('Eligibility', '')
        if not elig:
            raise SystemExit('%s: the page has no Eligibility section' % key)
        reading, basis = read_eligibility(elig)
        due = _iso_long(r['Date Due'])
        funding = r['Type of Funding'].strip().lower()
        if not funding:
            raise SystemExit('%s: no Type of Funding printed' % key)
        out.append(dict(
            fund_code=r['Fund Code'], program=r['Program Name'], posted=_iso_short(r['Date Posted']),
            due=due, grant_type=r['Grant Type'], funding=funding,
            unit=' '.join(r['Program Unit'].split()), contact=r['Contact'],
            open_on_list_date='yes' if due and due >= looked else ('no' if due else 'unknown'),
            district_reading=reading, reading_basis=basis,
            names_lunenburg='yes' if 'lunenburg' in page.lower() else 'no',
            purpose=first_sentence(s.get('Purpose', s.get('Purpose/Priorities', ''))),
            funding_text=first_sentence(s.get('Funding', '')),
            eligibility=elig.strip(), detail_url=detail_url(r['href']), fetched=looked,
            list_sha256=list_sha, detail_sha256=sha_file(p)))
    return out


def render(rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator='\n')
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    rows = build()
    text = render(rows)
    if a.check:
        have = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        if have != text:
            print('STALE: %s does not reproduce from the held pages' % os.path.relpath(OUT, ROOT))
            return 1
        print('ok: %d programs reproduce' % len(rows))
        return 0
    tmp = OUT + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='') as fh:
        fh.write(text)
    os.replace(tmp, OUT)
    from collections import Counter
    c = Counter((r['open_on_list_date'], r['district_reading']) for r in rows)
    print('%d programs -> %s' % (len(rows), os.path.relpath(OUT, ROOT)))
    for k, n in sorted(c.items()):
        print('  open=%-3s %-20s %d' % (k[0], k[1], n))
    return 0


if __name__ == '__main__':
    sys.exit(main())
