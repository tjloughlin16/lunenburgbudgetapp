#!/usr/bin/env python3
"""The acceptance test for the DESE grant watch: a new grant is ONE notice, unchanged is none,
and a baseline is none.

    python3 scripts/check_grant_watch.py

Nothing is stubbed but the inputs. `watch_grants.py` runs as a subprocess against a temporary
tree laid out like sources/ -- two dated copies of a fake DESE grants list, award documents in
dated version folders, and the two extracts that read them -- with GRANT_WATCH_DISTRICTS naming
Lunenburg and the comparison set, so the run does not need the real comparison report.

  1. NO STATE: a plain run refuses, and writes nothing -- the first run cannot flood.
  2. BASELINE: --seed over the first snapshot adopts everything and announces nothing.
  3. UNCHANGED: a second run adds nothing, and the state file is byte-identical.
  4. A SECOND SNAPSHOT lands with one new district-eligible grant, one new grant NOT open to
     districts, and one new award list naming Lunenburg. --check calls the state stale; the
     run announces exactly one grant and one award, with the measured wording.
  5. AGAIN: nothing new, byte-identical, --check passes.
  6. EXPIRY: the notices are live on the day, gone after NOTICE_DAYS, and a grant's at its
     due date.
"""
import csv
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
WATCH = os.path.join(HERE, 'watch_grants.py')
LUN, COMP = '0162', ['0001', '0002']
HEAD = ['Fund Code', 'Program Name', 'Date Posted', 'Date Due', 'Grant Type', 'Type of Funding',
        'Program Unit', 'Contact']
GCOLS = ['fund_code', 'program', 'posted', 'due', 'grant_type', 'funding', 'unit', 'contact',
         'open_on_list_date', 'district_reading', 'reading_basis', 'names_lunenburg', 'purpose',
         'funding_text', 'eligibility', 'detail_url', 'fetched', 'list_sha256', 'detail_sha256']
ACOLS = ['fy', 'fund_code', 'program', 'funding', 'funds_allocated', 'proposals_received',
         'proposals_recommended', 'recipients_n', 'recipients_sum', 'recipient', 'amount', 'joint',
         'district', 'district_code', 'match', 'source_url', 'our_copy', 'sha256']
GRANTS = {  # code: (program, due, grant type, reading)
    '0100': ('Old Grant', '2026-12-01', 'Competitive', 'districts eligible'),
    '0200': ('Brand New Grant', '2026-10-20', 'Competitive', 'districts eligible'),
    '0300': ('Colleges Only Grant', '2026-11-25', 'Competitive', 'not districts'),
}


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as fh:
        fh.write(data if isinstance(data, bytes) else data.encode('utf-8'))


def list_html(codes):
    th = ''.join('<th>%s</th>' % h for h in HEAD)
    trs = ''.join(
        '<tr><td>{c}</td><td><a href="/grants/2027/{c}/">{p}</a></td><td>10/01/2026</td>'
        '<td>{d}</td><td>{t}</td><td>State</td><td>Unit</td><td>x@doe</td></tr>'.format(
            c=c, p=GRANTS[c][0], d=GRANTS[c][1], t=GRANTS[c][2]) for c in codes)
    return '<html><table id="ctl_currentGrant">%s%s</table></html>' % (th, trs)


def snapshot(src, day, codes):
    html = list_html(codes)
    write(os.path.join(src, 'state-dese', 'grants', day, 'grants.html'), html)
    sha = hashlib.sha256(html.encode('utf-8')).hexdigest()
    with open(os.path.join(src, 'data', 'dese-grant-opportunities.csv'), 'w', newline='') as fh:
        w = csv.DictWriter(fh, GCOLS, lineterminator='\n')
        w.writeheader()
        for c in codes:
            p, due, t, reading = GRANTS[c]
            w.writerow(dict({k: '' for k in GCOLS}, fund_code=c, program=p, due=due, grant_type=t,
                            funding='state', open_on_list_date='yes', district_reading=reading,
                            detail_url='https://www.doe.mass.edu/grants/2027/%s/' % c,
                            fetched=day, list_sha256=sha))


def awards(src, docs):
    """docs: [(day, code, program, [(recipient, district code, amount)])]"""
    out = []
    for day, code, program, recips in docs:
        blob = ('fake award document %s %s' % (code, day)).encode()
        write(os.path.join(src, 'state-dese', 'awards', day, 'awards.html'), b'listing ' + day.encode())
        write(os.path.join(src, 'state-dese', 'awards', 'fy2026', day, code + '.docx'), blob)
        write(os.path.join(src, 'state-dese', 'awards', 'fy2026', code + '.docx'), blob)
        sha = hashlib.sha256(blob).hexdigest()
        for name, dc, amt in recips:
            out.append(dict({k: '' for k in ACOLS}, fy='2026', fund_code=code, program=program,
                            recipient=name, amount=amt, joint='1', district_code=dc,
                            source_url='https://www.doe.mass.edu/grants/2026/awards/%s.docx' % code,
                            our_copy='/docs/state-dese/awards/fy2026/%s.docx' % code, sha256=sha))
    with open(os.path.join(src, 'data', 'dese-competitive-awards.csv'), 'w', newline='') as fh:
        w = csv.DictWriter(fh, ACOLS, lineterminator='\n')
        w.writeheader()
        w.writerows(out)


def run(src, *args):
    env = dict(os.environ, GRANT_WATCH_SOURCES=src, GRANT_WATCH_DISTRICTS='%s;%s' % (LUN, ','.join(COMP)))
    return subprocess.run([sys.executable, WATCH] + list(args), env=env, capture_output=True, text=True)


def state_rows(src):
    with open(os.path.join(src, 'data', 'grant-watch-state.csv'), encoding='utf-8') as fh:
        return list(csv.DictReader(fh))


def main():
    fails = []

    def expect(cond, what):
        print('  %s  %s' % ('ok  ' if cond else 'FAIL', what))
        if not cond:
            fails.append(what)

    tmp = tempfile.mkdtemp(prefix='grant-watch-')
    src = os.path.join(tmp, 'sources')
    state = os.path.join(src, 'data', 'grant-watch-state.csv')
    os.makedirs(os.path.dirname(state))
    try:
        doc1 = ('2026-10-01', '0001', 'Old Award', [('Hadley', '0001', '5000')])
        snapshot(src, '2026-10-01', ['0100'])
        awards(src, [doc1])

        r = run(src)
        expect(r.returncode != 0 and not os.path.exists(state), '1. no state: a plain run refuses and writes nothing')

        r = run(src, '--seed')
        rows = state_rows(src) if r.returncode == 0 else []
        expect(r.returncode == 0 and len(rows) == 2 and all(x['basis'] == 'seed' and not x['notice'] for x in rows),
               '2. baseline: --seed adopts 2 items and announces none')
        before = open(state, 'rb').read()

        r = run(src)
        expect(r.returncode == 0 and open(state, 'rb').read() == before, '3. unchanged: nothing added, byte-identical')
        expect(run(src, '--check').returncode == 0, '3. --check passes on the baseline')

        snapshot(src, '2026-10-08', ['0100', '0200', '0300'])
        awards(src, [doc1, ('2026-10-08', '0002', 'New Award', [('Lunenburg', LUN, '12500'),
                                                                ('Somewhere', '0002', '9000')])])
        expect(run(src, '--check').returncode != 0, '4. --check calls the state stale before the run')
        r = run(src)
        rows = state_rows(src)
        said = [x for x in rows if x['basis'] == 'observed']
        g = [x for x in said if x['kind'] == 'grant']
        a = [x for x in said if x['kind'] == 'award']
        expect(r.returncode == 0 and len(g) == 1, '4. a new grant open to districts: exactly ONE grant notice (%d)' % len(g))
        expect(g and g[0]['notice'] == 'New state grant open to districts: Brand New Grant, due 20 October 2026'
               and g[0]['href'] == '/grants-open-to-lunenburg#grant-0200' and g[0]['first_seen'] == '2026-10-08',
               '4. ...worded, linked to its card, and dated by the snapshot: %r' % (g[0]['notice'] if g else None))
        expect(any(x['item'] == '2027-0300' and x['basis'] == 'carried' for x in rows),
               '4. a new grant NOT open to districts is recorded silently')
        expect(len(a) == 1 and a[0]['notice'] == 'DESE award, FY2026 New Award: Lunenburg was awarded $12,500',
               '4. a new award list naming Lunenburg: one notice: %r' % (a[0]['notice'] if a else None))
        after = open(state, 'rb').read()

        r = run(src)
        expect(r.returncode == 0 and open(state, 'rb').read() == after, '5. again: nothing new, byte-identical')
        expect(run(src, '--check').returncode == 0, '5. --check passes')

        sys.path.insert(0, HERE)
        import watch_grants as W
        live = W.notices('2026-10-08', rows)
        expect(len(live) == 2, '6. both notices live on the day they were found')
        expect(len(W.notices('2026-10-20', rows)) == 2, '6. the grant notice holds through its due date')
        expect([n['kind'] for n in W.notices('2026-10-21', rows)] == ['award'], '6. ...and is gone the day after it')
        expect([n['kind'] for n in W.notices('2026-10-29', rows)] == ['award'], '6. the award notice holds for %d days' % W.NOTICE_DAYS)
        expect(not W.notices('2026-10-30', rows), '6. ...and is gone after them')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print('%d failed' % len(fails) if fails else 'ok: the grant watch announces once, and only what is new')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
