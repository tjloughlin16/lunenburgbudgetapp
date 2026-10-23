#!/usr/bin/env python3
"""What is NEW from DESE since the last look: a grant newly open to districts, an award list.

    python3 scripts/watch_grants.py --seed    # first run: adopt everything held, announce nothing
    python3 scripts/watch_grants.py           # record what the held snapshots show that is new
    python3 scripts/watch_grants.py --check   # the state holds together AND is current

TJ, 23 October 2026: *"if a grant shows up that's new, or an award, we need to call that on the
homepage too, as sort of a notification."*

NO NETWORK AND NO MODEL. Everything is read off what fetch_dese_grants.py and
fetch_dese_awards.py already landed: the dated copies of DESE's current-grants list
(sources/state-dese/grants/<date>/grants*.html) and the dated versions of every award document
(sources/state-dese/awards/fy<YYYY>/<date>/<code>.docx), joined to the two extracts. So every
date here is THE DAY OUR FETCHER LANDED THE BYTES, never the day DESE posted them -- DESE
publishes neither.

THE RULES, AND THEY ARE ALL OF THEM

  a grant      is NEW when the earliest dated list snapshot that lists it is not the first
               snapshot we hold -- i.e. an earlier snapshot existed and did not list it. It is
               ANNOUNCED only if build_grants_open.open_to_districts() is true of its row (the
               page's own lead group; one place). Identity: DESE's program page, which carries
               the fiscal year (`2027-0140`), so next year's round of the same fund code is a
               new grant.
  an award     document version is NEW when the dated version holding the working copy's bytes
               is later than our first look at DESE's award listings. It is ANNOUNCED if
               Lunenburg is a listed recipient, or else if at least one comparison district
               (build_grant_comparison_topics.load()) is. Identity: the document and its sha256,
               so a revised list is a new version and says so.

What an award notice may say, and only this (rule 7): Lunenburg is LISTED, with the amount
printed; or N comparison districts are listed and Lunenburg IS NOT LISTED. Never "lost" or
"did not apply": DESE lists winners only, and nothing it publishes says who applied.

THE MEMORY, LIKE watch_meetings.py. `sources/data/grant-watch-state.csv` is committed and
holds every item this has ever seen, so nothing is announced twice. `--seed` adopts everything
currently held as `seed`, announcing none of it; a normal run REFUSES if no state exists yet,
so the first run cannot flood the home page. An item that is not new by the rules above is
recorded as `carried`, silently. Only `observed` rows carry a notice, and the notice is FROZEN
at the moment it was observed -- it is what we said, not what a later extract would say.

EXPIRY is build_notices.py's: a notice is shown for NOTICE_DAYS after it was first seen, and a
grant notice stops on its due date.
"""
import argparse
import collections
import csv
import datetime as dt
import glob
import hashlib
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)
# ONE override, for the test (check_grant_watch.py): a temporary tree laid out like sources/.
SRC = os.environ.get('GRANT_WATCH_SOURCES') or os.path.join(ROOT, 'sources')
GRANTS_DIR = os.path.join(SRC, 'state-dese', 'grants')
AWARDS_DIR = os.path.join(SRC, 'state-dese', 'awards')
GRANTS_CSV = os.path.join(SRC, 'data', 'dese-grant-opportunities.csv')
AWARDS_CSV = os.path.join(SRC, 'data', 'dese-competitive-awards.csv')
STATE = os.path.join(SRC, 'data', 'grant-watch-state.csv')
FIELDS = ['kind', 'item', 'version', 'fy', 'fund_code', 'program', 'first_seen', 'basis',
          'about', 'due', 'notice', 'href', 'source_url', 'our_copy']
NOTICE_DAYS = 21
DATED = re.compile(r'^\d{4}-\d{2}-\d{2}$')
GRANTS_PAGE = '/grants-open-to-lunenburg'
AWARDS_PAGE = '/school-all-funds/grants-others-receive'


def fail(msg):
    raise SystemExit('watch_grants: ' + msg)


def sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def rows(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding='utf-8', newline='') as fh:
        return list(csv.DictReader(fh))


def dated_dirs(base):
    return sorted(d for d in os.listdir(base) if DATED.match(d)
                  and os.path.isdir(os.path.join(base, d))) if os.path.isdir(base) else []


def usd(v):
    v = float(v)
    return '${:,.0f}'.format(v) if v.is_integer() else '${:,.2f}'.format(v)


def anchor(code):
    """The card id GrantsOpen.tsx draws: `grant-` and the fund code, non-alphanumerics to `-`."""
    return 'grant-' + re.sub(r'[^A-Za-z0-9]+', '-', code)


def districts():
    """(Lunenburg's code, {comparison codes}). The test names them; the run reads the
    comparison report's own sets, the same ones /school-all-funds/grants-others-receive uses."""
    env = os.environ.get('GRANT_WATCH_DISTRICTS')
    if env:
        lun, comp = env.split(';')
        return lun, set(c for c in comp.split(',') if c)
    import build_grant_comparison_topics as G
    D = G.load()
    return D['lun'], set(D['members'])


# ---------------------------------------------------------------- grants
def grant_item(url, code):
    from fetch_dese_grants import detail_key
    k = detail_key(url) if url else None
    return os.path.basename(k)[:-len('.html')] if k else 'code-' + code


def observe_grants():
    from fetch_dese_grants import parse_list, detail_url
    from build_grants_open import open_to_districts, long_date
    snaps = []
    for d in dated_dirs(GRANTS_DIR):
        for p in sorted(glob.glob(os.path.join(GRANTS_DIR, d, 'grants*.html'))):
            snaps.append((d, p))
    current = rows(GRANTS_CSV)
    if not current:
        return []
    if not snaps:
        fail('an extract exists but no dated copy of the grants list does')
    shas = {r['list_sha256'] for r in current}
    if len(shas) != 1:
        fail('the grants extract is from more than one list')
    newest = [d for d, p in snaps if sha(p) in shas]
    if not newest:
        fail('the grants extract matches no dated copy of the list: run extract_dese_grants.py')
    first_seen = {}
    for d, p in snaps:
        if d > newest[-1]:
            break
        for r in parse_list(open(p, encoding='utf-8', errors='replace').read()):
            first_seen.setdefault(grant_item(detail_url(r['href']) if r['href'] else '',
                                             r['Fund Code']), d)
    first_look = snaps[0][0]
    out = []
    for r in current:
        item = grant_item(r['detail_url'], r['fund_code'])
        if item not in first_seen:
            fail('%s is in the extract and in no dated list: the join broke' % item)
        seen = first_seen[item]
        new = seen > first_look
        notice = ''
        if new and open_to_districts(r):
            kind = r['funding'] + ' grant' if r['funding'] in ('state', 'federal') else 'grant'
            notice = 'New %s open to districts: %s, due %s' % (
                kind, r['program'], long_date(r['due']) if r['due'] else 'date not printed')
        out.append(dict(kind='grant', item=item, version='', fy='', fund_code=r['fund_code'],
                        program=r['program'], first_seen=seen, new=new, about='',
                        due=r['due'], notice=notice,
                        href='%s#%s' % (GRANTS_PAGE, anchor(r['fund_code'])),
                        source_url=r['detail_url'], our_copy=''))
    return out


# ---------------------------------------------------------------- awards
def observe_awards(lun, comparison):
    current = rows(AWARDS_CSV)
    if not current:
        return []
    looks = dated_dirs(AWARDS_DIR)
    by_doc = collections.OrderedDict()
    for r in current:
        by_doc.setdefault((r['fy'], r['fund_code'], r['sha256'], r['our_copy']), []).append(r)
    found = []
    for (fy, code, version, copy), rs in by_doc.items():
        working = os.path.join(SRC, copy[len('/docs/'):])
        folder, name = os.path.split(working)
        stem, ext = os.path.splitext(name)
        dates = []
        for d in dated_dirs(folder):
            for p in glob.glob(os.path.join(folder, d, stem + '*' + ext)):
                dates.append((d, sha(p) == version))
        mine = sorted(d for d, same in dates if same)
        if not mine:
            fail('%s: no dated version holds the bytes the extract read' % copy)
        found.append((fy, code, version, copy, rs, mine[0], any(d < mine[0] for d, _ in dates)))
    first_look = min(looks + [f[5] for f in found])
    out = []
    for fy, code, version, copy, rs, seen, revised in found:
        program = 'DESE award, FY%s %s' % (fy, rs[0]['program'])
        ours = [r for r in rs if r['district_code'] == lun]
        comp = sorted({r['district_code'] for r in rs if r['district_code'] in comparison})
        notice, about = '', ''
        if ours:
            about = 'lunenburg'
            amt = sum(float(r['amount']) for r in ours)
            joint = max(int(r['joint'] or 1) for r in ours)
            notice = '%s: Lunenburg was awarded %s%s' % (
                program, usd(amt), ', a joint award shared by %d districts' % joint if joint > 1 else '')
        elif comp:
            about = 'comparison'
            notice = '%s: %d comparison district%s listed; Lunenburg is not listed' % (
                program, len(comp), '' if len(comp) == 1 else 's')
        if notice and revised:
            notice = 'DESE revised its award list. ' + notice
        out.append(dict(kind='award', item='fy%s/%s' % (fy, code), version=version, fy=fy,
                        fund_code=code, program=rs[0]['program'], first_seen=seen,
                        new=seen > first_look, about=about, due='', notice=notice,
                        href=AWARDS_PAGE, source_url=rs[0]['source_url'], our_copy=copy))
    return out


# ---------------------------------------------------------------- the memory
def ident(r):
    return (r['kind'], r['item'], r['version'])


def observe():
    lun, comparison = districts()
    return observe_grants() + observe_awards(lun, comparison)


def step(state, seen, seed):
    """The rows `seen` adds to `state`. A row already known is skipped; nothing is removed."""
    known = {ident(r) for r in state}
    add = []
    for o in seen:
        if ident(o) in known:
            continue
        known.add(ident(o))
        r = {k: o.get(k, '') for k in FIELDS}
        r['basis'] = 'seed' if seed else ('observed' if o['new'] and o['notice'] else 'carried')
        if r['basis'] != 'observed':
            r['notice'] = ''
        add.append(r)
    return add


def render(state):
    buf = io.StringIO()
    w = csv.DictWriter(buf, FIELDS, lineterminator='\n')
    w.writeheader()
    w.writerows(sorted(state, key=lambda r: (r['kind'], r['item'], r['first_seen'], r['version'])))
    return buf.getvalue()


def consistency(state):
    bad, seen = [], set()
    for r in state:
        if ident(r) in seen:
            bad.append('duplicate: %s' % (ident(r),))
        seen.add(ident(r))
        if r['basis'] not in ('seed', 'carried', 'observed'):
            bad.append('unknown basis %r: %s' % (r['basis'], ident(r)))
        if r['basis'] != 'observed' and r['notice']:
            bad.append('a %s row carries a notice, and only an observed one may: %s'
                       % (r['basis'], ident(r)))
        if r['basis'] == 'observed' and not (r['notice'] and r['first_seen'] and r['href']):
            bad.append('an observed row without its notice, date or link: %s' % (ident(r),))
    return bad


def notices(as_of, state=None):
    """The notices still live on `as_of`, newest first: what build_notices.py publishes."""
    state = rows(STATE) if state is None else state
    out = []
    for r in state:
        if r['basis'] != 'observed':
            continue
        expires = (dt.date.fromisoformat(r['first_seen']) + dt.timedelta(days=NOTICE_DAYS)).isoformat()
        if r['due']:
            expires = min(expires, r['due'])
        if as_of > expires:
            continue
        out.append(dict(kind=r['kind'], about=r['about'], first_seen=r['first_seen'],
                        expires=expires, text=r['notice'], href=r['href'],
                        source_url=r['source_url'], our_copy=r['our_copy'],
                        fund_code=r['fund_code'], due=r['due']))
    return sorted(out, key=lambda n: (n['first_seen'], n['kind'], n['text']), reverse=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seed', action='store_true', help='adopt everything held, announce nothing')
    ap.add_argument('--check', action='store_true', help='state consistent, and current')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    exists = os.path.exists(STATE)
    state = rows(STATE)
    if a.check:
        bad = consistency(state) if exists else ['no state: run watch_grants.py --seed']
        if exists and not bad:
            later = step(state, observe(), False)
            bad += ['not yet recorded: %s %s -- run watch_grants.py' % (r['kind'], r['item'])
                    for r in later]
            if open(STATE, encoding='utf-8').read() != render(state):
                bad.append('the state file is not in canonical order: run watch_grants.py')
        for b in bad:
            print('  !!', b)
        if bad:
            return 1
        print('ok: %d items watched, %d announced, nothing unrecorded'
              % (len(state), sum(r['basis'] == 'observed' for r in state)))
        return 0
    if not exists and not a.seed:
        fail('no %s yet: run --seed first, or the first run announces everything held'
             % os.path.relpath(STATE, ROOT))
    add = step(state, observe(), a.seed)
    for r in add:
        if r['basis'] == 'observed':
            print('  NEW  %s  %s' % (r['first_seen'], r['notice']))
    print('%d new item%s: %d announced, %d %s' % (
        len(add), '' if len(add) == 1 else 's', sum(r['basis'] == 'observed' for r in add),
        sum(r['basis'] != 'observed' for r in add), 'seeded' if a.seed else 'carried silently'))
    if a.dry_run:
        print('dry run: nothing written')
        return 0
    state += add
    bad = consistency(state)
    if bad:
        fail('would write an inconsistent state: ' + '; '.join(bad))
    text = render(state)
    if not exists or open(STATE, encoding='utf-8').read() != text:
        tmp = STATE + '.tmp'
        with open(tmp, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        os.replace(tmp, STATE)
    print('state -> %s (%d items)' % (os.path.relpath(STATE, ROOT), len(state)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
