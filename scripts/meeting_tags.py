"""MEETING TAGS: short, safe flags on a meeting, each one a measured fact about the ONLINE record.

TJ, 13 November 2026: "TAGS on the meetings ... not to suggest legal violations. just sort of
'helpful' flags ... if a meeting is less than the OML required posting ... if we know it was
amended 'AMENDED'." And: "make sure on the dash we dont show no recording and minutes not
posted. those are post-meeting labels."

THE RULE EVERY TAG KEEPS: it states something measured, a script decides it (never a model),
and it reads the same whether or not anything was wrong. A tag that fires on nearly every
meeting carries no information, which is why HYBRID (most are) and "no posting time on the
agenda" (0 of 122 School Committee agendas show one) are not tags.

TIMING IS ABOUT THE ONLINE COPY. The official notice may be the paper posted at Town Hall,
whose posting time is not published (940 CMR 29.03(1)(d) requires it recorded "thereon or
therewith"). So SHORT NOTICE says the online copy was made under 48 counted hours before the
meeting -- the earliest that copy could have gone up -- and says so in its detail.

Computed here, at build time, from the agenda alone (these do not change after a meeting):
    amended, late-addition, short-notice, emergency, executive-session, cancelled
NOT here: minutes-not-posted and no-recording. Those turn true the day a window closes, so the
page judges them on the reader's clock from the meeting's `record` (components/MeetingTags.tsx),
exactly as RecordCell already does, and never before the meeting.

The agenda-version logic is oml_review.py's, imported rather than copied, so the review page
and the tags cannot disagree about which agenda was posted when.
"""
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import oml_review as R  # noqa: E402

TAGS = [
    ('cancelled', 'Cancelled'),
    ('emergency', 'Emergency meeting'),
    ('short-notice', 'Short notice'),
    ('late-addition', 'Late addition'),
    ('amended', 'Amended agenda'),
    ('executive-session', 'Executive session'),
]
LABEL = dict(TAGS)

_AGENDAS = None
_STAMPS = None
ENUM = re.compile(r'^\s*(?:[a-z]|\d{1,2}|[ivx]+)[.)]\s+\S', re.I)
REVISED = re.compile(r'\b(REVISED|AMENDED)\b')
# "Emergency" as the KIND of meeting -- never "Emergency Management", a department.
EMERGENCY = re.compile(r'\bemergency\s+(meeting|session|posting|notice)\b|^\s*emergency\s*$', re.I | re.M)
CANCELLED = re.compile(r'\b(CANCELL?ED|POSTPONED)\b', re.I)


def _load():
    global _AGENDAS, _STAMPS
    if _AGENDAS is None:
        _AGENDAS = {}
        for r in csv.DictReader(open(R.MEETINGS_INDEX, encoding='utf-8')):
            if r['kind'] == 'agenda':
                _AGENDAS.setdefault((r['path'].split('/')[0], r['date']), []).append(r)
        _STAMPS = {r['path']: r for r in csv.DictReader(open(R.STAMPS, encoding='utf-8')) if r['kind'] == 'agenda'}


def versions(slug, date):
    """The online agendas for one meeting, oldest first: text, title, creation time, counted
    hours. Agendas printing a different start time are another meeting that day and are left
    out, as oml_review.gather does."""
    _load()
    out = []
    for r in _AGENDAS.get((slug, date), []):
        tp, txt = R.text_for(r['path'])
        if not txt:
            continue
        st = _STAMPS.get(r['path'])
        start, _ = R.meeting_start(txt, date)
        nf = R.notice_facts(slug, date, txt, st) if st else {}
        # A copy made AFTER the meeting began cannot be its notice (4 Feb 2026 holds the March
        # agenda, made after the February meeting): set aside, as oml_review does.
        if (nf.get('clock_hours_file_to_meeting') or 0) < 0:
            continue
        hrs = nf.get('counted_hours_file_to_meeting')
        out.append({'file_id': r['file_id'], 'title': r.get('title') or '', 'text': txt,
                    'created': (st or {}).get('created', ''), 'start': start, 'hours': hrs})
    out.sort(key=lambda v: (v['created'] or '9', v['file_id']))
    if out:
        last = out[-1]['start']
        out = [v for v in out if not v['start'] or not last or v['start'] == last]
    return out


def agenda_tags(slug, date):
    """[{key, label, detail}] for one meeting, in display order. Empty when no agenda is held."""
    vs = versions(slug, date)
    if not vs:
        return []
    found = {}
    head = lambda v: v['title'] + '\n' + v['text'][:700]  # noqa: E731
    last = vs[-1]
    if any(CANCELLED.search(head(v)) for v in vs[-1:]):
        found['cancelled'] = 'the online agenda is marked cancelled or postponed'
    if any(EMERGENCY.search(head(v)) for v in vs):
        found['emergency'] = 'the online agenda calls it an emergency meeting'
    first = vs[0]
    # A copy MARKED REVISED replaced an earlier one in place, so its creation time is the
    # revision's, not the meeting's first notice: it is AMENDED, never SHORT NOTICE
    # (13 Nov 2026: 2025-02-26 read "6.2 hours" off a revision).
    first_is_revision = bool(REVISED.search(head(first)))
    if first['hours'] is not None and first['hours'] < 48 and not first_is_revision:
        found['short-notice'] = ('the online copy was made %.1f counted hours before the meeting; '
                                 'the official notice may be the paper at Town Hall' % first['hours'])
    if len(vs) > 1:
        added = []
        for v in vs[:-1]:
            _, add = R.version_diff(v['text'], last['text'])
            added += [a for a in add if ENUM.match(a) and len(a) > 12]
        if added and last['hours'] is not None and last['hours'] < 48:
            found['late-addition'] = ('%s added in an online copy made %.1f counted hours before the meeting'
                                      % ('; '.join('“%s”' % re.sub(r'^\s*\S+[.)]\s+', '', a)[:70] for a in added[:2]),
                                         last['hours']))
        found['amended'] = '%d agendas posted online for this meeting' % len(vs)
    elif REVISED.search(head(last)):
        found['amended'] = ('the online agenda is marked revised%s' %
                            ('; the revised online copy was made %.1f counted hours before the meeting'
                             % last['hours'] if last['hours'] is not None else ''))
    if any('executive session' in ln.lower() and 'minutes' not in ln.lower()
           for ln in last['text'].splitlines()):
        found['executive-session'] = 'the agenda lists an executive session'
    return [{'key': k, 'label': LABEL[k], 'detail': found[k]} for k, _ in TAGS if k in found]


if __name__ == '__main__':
    import collections
    slug = sys.argv[1] if len(sys.argv) > 1 else 'school-committee'
    _load()
    dates = sorted({d for (s, d) in _AGENDAS if s == slug})
    c = collections.Counter()
    for d in dates:
        t = agenda_tags(slug, d)
        for x in t:
            c[x['key']] += 1
        if t and (len(sys.argv) > 2):
            print(d, ' | '.join('%s: %s' % (x['label'], x['detail']) for x in t))
    print('%s: %d dated agendas; %s' % (slug, len(dates), dict(c)))
