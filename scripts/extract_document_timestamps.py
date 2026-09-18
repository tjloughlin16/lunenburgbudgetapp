#!/usr/bin/env python3
"""When each agenda and each set of minutes was MADE, from the document's own metadata.

    python3 scripts/extract_document_timestamps.py          # write sources/data/meeting-document-timestamps.csv
    python3 scripts/extract_document_timestamps.py --check

TJ, 18 September 2026: "The 2 really important timestamps are: the meeting notice AND
agenda (by law they have to post 48 hours ahead of the meeting being held) and the date
of their official minutes being posted. Those 2 are governed by law and mean something."

THE PROBLEM THIS SOLVES. The AgendaCenter publishes no posting timestamp, and our own
`first_seen` exists for 24 documents out of 12,089 -- everything else was adopted when the
watch was seeded on 8 September 2026. So the two dates that carry legal weight were, until
now, unknown for the whole archive.

WHAT A CREATION DATE IS, AND IS NOT (rule 13). `/CreationDate` is when the FILE was made
on somebody's machine. It is not when the town posted it. It is a LOWER BOUND on posting:
a document cannot be published before it exists. Our `first_seen` is an UPPER bound. Where
we hold both, the posting is bracketed; where we hold only the creation date, a document
made three days before the meeting is CONSISTENT WITH the 48-hour notice and does not
prove it, and one made after the meeting began proves only that this FILE is later --
an amended agenda, a re-save, or a scan of a signed copy.

Two more limits worth stating before anybody quotes a figure from this:

  * the clock is the creating machine's, timezone offset included where the PDF gives one;
  * a file re-saved in place takes a new date, so `mod` is kept beside `created` and a
    document where they differ is flagged rather than averaged.

The honest headline this supports is therefore about MINUTES, where the gap is months
rather than hours and no bound is tight enough to explain it away.
"""
import argparse
import csv
import datetime as dt
import io
import logging
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, 'sources', 'meetings', 'index.csv')
MEET = os.path.join(ROOT, 'sources', 'meetings')
OUT = os.path.join(ROOT, 'sources', 'data', 'meeting-document-timestamps.csv')
FIELDS = ['board_slug', 'board', 'meeting_date', 'kind', 'file_id', 'path',
          'created', 'modified', 'creator', 'producer', 'resaved',
          'hours_before_meeting', 'days_after_meeting']
PDFDATE = re.compile(r"D:(\d{4})(\d{2})(\d{2})(\d{2})?(\d{2})?(\d{2})?(?:([+-Z])(\d{2})'?(\d{2})?)?")
logging.getLogger('pypdf').setLevel(logging.ERROR)


def parse(raw):
    """A PDF date string to an ISO-8601 local timestamp, or ''. The offset is kept as the
    document gives it: a town clerk's machine in Massachusetts is what wrote it."""
    if not raw:
        return ''
    m = PDFDATE.search(str(raw))
    if not m:
        return ''
    y, mo, d, hh, mm, ss, sign, oh, om = m.groups()
    try:
        stamp = dt.datetime(int(y), int(mo), int(d), int(hh or 0), int(mm or 0), int(ss or 0))
    except ValueError:
        return ''
    out = stamp.strftime('%Y-%m-%dT%H:%M:%S')
    if sign and sign != 'Z':
        out += '%s%s:%s' % (sign, oh, om or '00')
    elif sign == 'Z':
        out += '+00:00'
    return out


def metadata(path):
    if path.lower().endswith('.pdf'):
        from pypdf import PdfReader
        try:
            md = PdfReader(path).metadata or {}
        except Exception:
            return {}
        return {'created': parse(md.get('/CreationDate')), 'modified': parse(md.get('/ModDate')),
                'creator': (md.get('/Creator') or '')[:60], 'producer': (md.get('/Producer') or '')[:60]}
    if path.lower().endswith(('.docx', '.xlsx')):
        import zipfile
        try:
            with zipfile.ZipFile(path) as z:
                core = z.read('docProps/core.xml').decode('utf-8', 'replace')
        except Exception:
            return {}
        g = lambda t: (re.search(r'<%s[^>]*>([^<]+)</%s>' % (t, t), core) or [None, ''])[1]
        return {'created': (g('dcterms:created') or '')[:19], 'modified': (g('dcterms:modified') or '')[:19],
                'creator': (g('dc:creator') or '')[:60], 'producer': (g('Application') or '')[:60]}
    return {}


def build(quiet=False):
    rows = []
    src = list(csv.DictReader(open(INDEX, encoding='utf-8')))
    for i, r in enumerate(src):
        p = (r.get('path') or '').strip()
        if not p or r.get('kind') not in ('agenda', 'minutes'):
            continue
        full = os.path.join(MEET, p)
        if not os.path.exists(full):
            continue
        md = metadata(full)
        created, modified = md.get('created', ''), md.get('modified', '')
        hours = days = ''
        if created and r.get('date'):
            try:
                made = dt.datetime.fromisoformat(created[:19])
                meeting = dt.datetime.fromisoformat(r['date'] + 'T00:00:00')
                delta = (meeting - made).total_seconds() / 3600.0
                hours = '%.1f' % delta
                if delta < 0:
                    days = '%.1f' % (-delta / 24.0)
            except ValueError:
                pass
        rows.append({'board_slug': p.split('/')[0], 'board': r.get('board', ''), 'meeting_date': r.get('date', ''),
                     'kind': r['kind'], 'file_id': r.get('file_id', ''), 'path': p,
                     'created': created, 'modified': modified, 'creator': md.get('creator', ''),
                     'producer': md.get('producer', ''),
                     'resaved': '1' if created and modified and created[:16] != modified[:16] else '0',
                     'hours_before_meeting': hours, 'days_after_meeting': days})
        if not quiet and i and i % 2000 == 0:
            print('  %d/%d' % (i, len(src)), flush=True)
    if not rows:
        raise SystemExit('no agenda or minutes document read. Refusing to write.')
    got = sum(1 for r in rows if r['created'])
    if got < len(rows) * 0.5:
        raise SystemExit('only %d of %d documents carry a creation date; that is not the '
                         'archive this script was calibrated on. Refusing to write.' % (got, len(rows)))
    rows.sort(key=lambda r: (r['meeting_date'], r['board_slug'], r['kind']), reverse=True)
    return rows


def render(rows):
    b = io.StringIO()
    w = csv.DictWriter(b, fieldnames=FIELDS, lineterminator='\n')
    w.writeheader()
    w.writerows(rows)
    return b.getvalue()


def report(rows):
    ag = [r for r in rows if r['kind'] == 'agenda' and r['hours_before_meeting']]
    mi = [r for r in rows if r['kind'] == 'minutes' and r['days_after_meeting']]
    print('%s: %d documents, %d with a creation date' % (os.path.relpath(OUT, ROOT), len(rows), sum(1 for r in rows if r['created'])))
    if ag:
        ahead = sorted(float(r['hours_before_meeting']) for r in ag)
        n48 = sum(1 for h in ahead if h >= 48)
        late = sum(1 for h in ahead if h < 0)
        print('  agendas   %5d dated; median %.0f h before the meeting; %d (%.1f%%) made 48 h or more ahead; %d made after it'
              % (len(ag), ahead[len(ahead) // 2], n48, 100.0 * n48 / len(ag), late))
    if mi:
        after = sorted(float(r['days_after_meeting']) for r in mi)
        print('  minutes   %5d dated; median %.0f days after the meeting; %d took more than 30'
              % (len(mi), after[len(after) // 2], sum(1 for d in after if d > 30)))
    print('  A creation date is a LOWER bound on posting, never the posting date itself.')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--quiet', action='store_true')
    a = ap.parse_args()
    rows = build(quiet=a.quiet or a.check)
    text = render(rows)
    if a.check:
        if not os.path.exists(OUT) or open(OUT, encoding='utf-8').read() != text:
            raise SystemExit('STALE %s — run: python3 scripts/extract_document_timestamps.py' % os.path.relpath(OUT, ROOT))
        print('ok — %d meeting documents, timestamps reproduce' % len(rows))
        return
    open(OUT, 'w', encoding='utf-8').write(text)
    report(rows)


if __name__ == '__main__':
    main()
