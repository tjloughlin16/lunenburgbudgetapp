#!/usr/bin/env python3
"""One row per MEETING, and what we hold for it.

TJ, 8 September 2026: "join those with the meeting information we have (agendas/minutes)
and create a single meeting set of data to know what we have data for. Meaning, for a
single meeting, do we have agenda, minutes, video, transcript, and processed transcript?"

THE POINT IS THE EMPTY CELLS. Everything this project has learned about the meeting record
has come from measuring a denominator: the harvest that found 1,734 missing documents was
invisible until somebody counted what the town lists, and a quarter of what we hold turned
out to be photographs of pages rather than pages. Both were found by asking "of what?".

This is that question asked once, at the grain a resident actually cares about. Not "how
many minutes do we hold" but "for the Select Board meeting on 3 June 2025, what is there?"

WHAT A ROW IS. A meeting occasion: one board, one date. That is a DERIVED grain and it is
worth being honest about why -- the town does not publish a list of meetings held. It
publishes documents, and a document implies a meeting. So a row here means *at least one
artefact exists that says this board met on this day*, which is not the same as the set of
meetings that happened. A meeting with no agenda, no minutes and no recording leaves no
trace and cannot appear.

THE JOIN IS ON (board, date) AND THAT IS THE WEAK POINT. The document side gets its board
from the folder the town filed it in and its date from the filename. The video side gets
its board and date from a MODEL READING A TITLE. Those are different kinds of evidence and
the register says which one it had for every row, because a video matched to the wrong
day is worse than a video matched to nothing.

FIVE THINGS PER MEETING, and two of them are always false today:

    agenda                the town posted one and we hold it
    minutes               likewise
    searchable            ...and the text can actually be read, rather than being a scan
    video                 the PEG channel has a recording we have identified
    transcript            NOT YET FETCHED FOR ANY MEETING -- the column exists so the
                          backlog is visible rather than absent
    transcript_processed  likewise. A transcript is a finding aid; a processed one is
                          whatever we later derive from it, and neither exists yet

Columns that are false everywhere are kept deliberately. A column nobody has filled in is
a measurable gap; a column nobody added is an invisible one.

    python3 scripts/build_meeting_register.py
    python3 scripts/build_meeting_register.py --check
"""
import argparse
import collections
import csv
import datetime as dt
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEET_INDEX = os.path.join(ROOT, 'sources', 'meetings', 'index.csv')
TEXT_DIR = os.path.join(ROOT, 'sources', 'meetings', 'text')
VIDEO_BOARDS = os.path.join(ROOT, 'sources', 'data', 'youtube-video-boards.csv')
VIDEOS = os.path.join(ROOT, 'sources', 'data', 'youtube-videos.csv')
OUT = os.path.join(ROOT, 'sources', 'data', 'meeting-register.csv')

COLS = ['board', 'board_slug', 'date', 'agenda', 'minutes', 'searchable_docs',
        'unsearchable_docs', 'video', 'video_ids', 'transcript', 'transcript_processed',
        'evidence',
        # THE CANONICAL RECORD. TJ, 18 September 2026: "each meeting has ONE record for
        # it. That record knows which artifacts have been produced." Every artifact we hold
        # for the meeting, by its address, so a page joins THIS and never re-derives the
        # meeting from five sources. Empty means we do not hold it.
        'agenda_path', 'agenda_url', 'agenda_first_seen',
        'minutes_path', 'minutes_url', 'minutes_first_seen', 'minutes_lag_upper_bound', 'minutes_ocr',
        'video_urls', 'video_uploaded', 'video_first_seen', 'captions_disabled',
        'transcript_paths', 'transcript_fetched',
        'our_minutes_path', 'our_minutes_url', 'our_minutes_written', 'our_minutes_headline', 'our_votes',
        'official_votes_path', 'official_votes', 'last_activity', 'noticed',
        # WHEN THE DOCUMENTS WERE MADE -- never when they were posted. From their own
        # metadata (scripts/extract_document_timestamps.py). The column names say
        # `created` because TJ, 18 September 2026: "we have to make sure the 'created'
        # timestamps are labeled that way, not treated as the 'posted' date. they could
        # have created them way ahead and waited to post, right?" -- yes, and that is
        # why the bound runs one way only:
        #
        #   created EARLY proves nothing. A notice written a week ahead can still be
        #     posted an hour before the meeting, and nothing in the file would show it.
        #   created LATE is evidence. A file made 6 hours before the meeting cannot have
        #     been posted 48 hours before it -- unless an earlier version was posted and
        #     this one replaced it in place, which the AgendaCenter allows.
        #
        # What they DO measure, and it is a real quantity: THE MOST NOTICE THAT WAS
        # POSSIBLE -- the meeting, minus the moment the file was made. Under 48 hours
        # means the 48-hour notice was not possible for this file; 48 or more means it
        # was possible and nothing here says it happened.
        'agenda_created', 'agenda_created_hours_before_meeting',
        'minutes_created', 'minutes_created_days_after_meeting',
        # HOW COMPLETE THE RECORD OF THIS MEETING IS. TJ, 18 September 2026: "we can list
        # a 'completion' percent per meeting, based on which artifacts are available ...
        # completion is across all artifacts, towns and ours. not two scores, no."
        #
        # SEVEN THINGS, counted once each, whoever made them: the AgendaCenter listing,
        # the agenda file, the town's minutes, the recording, our transcript of it, our
        # minutes of it, and the votes read out of the town's minutes. The question the
        # score answers is a reader's -- how much of this meeting can I get at -- and a
        # reader does not care whose job each piece was. `complete_of` names the parts so
        # the number can always be unpacked into which ones are missing.
        'complete', 'complete_pct', 'complete_of', 'missing',
        # ONE OCCASION, LISTED TWICE. The AgendaCenter lists "Planning Board Public
        # Hearing" beside "Planning Board" for the same evening: the hearing is an item
        # inside the meeting, not a second meeting. 67 of 69 such rows fall on a date
        # their parent board also met. The row stays -- the town listed it, and a
        # resident searching for the hearing must find it -- but it names its parent, so
        # nothing counts the evening twice or marks the hearing short of a recording the
        # parent's row already has.
        'part_of']
STAMPS = os.path.join(ROOT, 'sources', 'data', 'meeting-document-timestamps.csv')
EVENTS = os.path.join(ROOT, 'sources', 'data', 'meeting-watch-events.csv')
VIDEO_EVENTS = os.path.join(ROOT, 'sources', 'data', 'youtube-watch-events.csv')
TRANSCRIPTS = os.path.join(ROOT, 'sources', 'data', 'youtube-transcript-index.csv')
NO_CAPTIONS = os.path.join(ROOT, 'sources', 'data', 'youtube-no-captions.csv')
OURS = os.path.join(ROOT, 'sources', 'data', 'recording-minutes')
VOTES = os.path.join(ROOT, 'sources', 'data', 'official-votes')
OCR_MARK = '===OCR'
WATCH_STATE = os.path.join(ROOT, 'sources', 'data', 'meeting-watch-state.csv')

PAGE = re.compile(r'===PAGE \d+===')


def searchable(path):
    """Does this document carry text a search can match?

    ZERO IS THE THRESHOLD, and it is not a guess. `build_minutes_searchable.py` calibrated
    it against a signal independent of our extractor -- whether the PDF carries a font
    resource at all -- and the two agree at zero characters and nowhere else. An earlier
    <40 character cut would have swept in 362 one-line AgendaCenter stubs that DO have a
    text layer and whose substance is in a separate attachment: a different gap with a
    different remedy.
    """
    try:
        with open(path, encoding='utf-8', errors='replace') as fh:
            return bool(PAGE.sub('', fh.read()).strip())
    except OSError:
        return False


def load_documents():
    """(board_slug, date) -> what the town posted, from the meeting archive."""
    if not os.path.exists(MEET_INDEX):
        raise SystemExit('%s is missing. Run scripts/fetch_agendas.py.' % MEET_INDEX)
    out, names = {}, {}
    with open(MEET_INDEX, newline='', encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            slug = r['path'].split('/')[0]
            names[slug] = r['board']
            key = (slug, r['date'])
            m = out.setdefault(key, {'agenda': 0, 'minutes': 0, 'ok': 0, 'bad': 0, 'paths': {}, 'urls': {}, 'ocr': 0})
            if r['kind'] in ('agenda', 'minutes'):
                m[r['kind']] = 1
                m['paths'].setdefault(r['kind'], r['path'])
                m['urls'].setdefault(r['kind'], r.get('url', ''))
            txt = os.path.join(TEXT_DIR, os.path.splitext(r['path'])[0] + '.txt')
            if os.path.exists(txt):
                m['ok' if searchable(txt) else 'bad'] += 1
                if r['kind'] == 'minutes':
                    try:
                        with open(txt, encoding='utf-8', errors='replace') as fh:
                            if fh.read(8).startswith(OCR_MARK):
                                m['ocr'] = 1
                    except OSError:
                        pass
    return out, names


def load_videos():
    """(board_slug, date) -> video ids, from the classification.

    Only rows that have BOTH a meetings folder and a date can join. The rest are counted
    and reported rather than dropped: 242 board rows belong to bodies with no folder in
    the town's AgendaCenter -- the Water District, Town Meeting -- and a video we cannot
    place is a different fact from a meeting with no video.
    """
    if not os.path.exists(VIDEO_BOARDS):
        raise SystemExit('%s is missing. Run scripts/build_youtube_classification.py.'
                         % VIDEO_BOARDS)
    out, nofolder, nodate = {}, 0, 0
    with open(VIDEO_BOARDS, newline='', encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            slug, date = r.get('meetings_folder', ''), r.get('meeting_date', '')
            if not slug:
                nofolder += 1
                continue
            if not date:
                nodate += 1
                continue
            out.setdefault((slug, date), []).append(r['video_id'])
    return out, nofolder, nodate


def read(p):
    if not os.path.exists(p):
        return []
    with open(p, newline='', encoding='utf-8') as fh:
        return list(csv.DictReader(fh))


def listed_meetings():
    """Every meeting the town LISTED on its AgendaCenter, by (board, date).

    TJ, 18 September 2026: "just the POSTING on the agenda center makes the meeting real
    too." The listing is the legal notice (M.G.L. c.30A §20 asks for 48 hours of it); the
    agenda FILE is a document attached to that listing, and the two are not the same
    thing -- the watch state holds listings we hold no file for. So `noticed` rests on the
    listing, and a fetch we failed can never read as a notice the town never gave.
    """
    out = {}
    for r in read(WATCH_STATE):
        k = (r['board_slug'], r['date'])
        cur = out.get(k)
        if not cur or (r['kind'] == 'agenda' and cur['kind'] != 'agenda') or (r['first_seen'] and r['first_seen'] < (cur['first_seen'] or '9')):
            out[k] = r
    return out


def load_artifacts():
    """Everything else we hold, keyed the same way."""
    import glob
    import json
    ev = {}
    for e in read(EVENTS):
        k = (e['board_slug'], e['meeting_date'], e['kind'])
        if k not in ev or e['first_seen'] < ev[k]['first_seen']:
            ev[k] = e
    vev = {e['video_id']: e for e in read(VIDEO_EVENTS)}
    vmeta = {r['video_id']: r for r in read(VIDEOS)}
    nocap = {r['video_id'] for r in read(NO_CAPTIONS)}
    tr = {}
    for t in read(TRANSCRIPTS):
        tr.setdefault((t['board_slug'], t['meeting_date']), []).append(t)
    ours = {}
    for f in glob.glob(os.path.join(OURS, '*', '*.json')):
        m = json.load(open(f, encoding='utf-8'))
        ours[(m['board_slug'], m['meeting_date'])] = dict(
            path=os.path.relpath(f, ROOT), url='/meeting-minutes/%s/%s-%s' % (m['board_slug'], m['meeting_date'], m['video_id']),
            written=(m.get('written') or {}).get('at', '')[:10],
            # The headline lives inside `minutes`, not at the top level: the top-level
            # key exists on the payload the SITE builds, not on the file.
            headline=(m.get('minutes') or {}).get('headline') or m.get('headline') or '',
            summary=(m.get('minutes') or {}).get('summary') or '',
            votes=sum(1 for v in (m.get('minutes') or {}).get('votes') or [] if not v.get('procedural')))
    ov = {}
    for f in glob.glob(os.path.join(VOTES, '*', '*.json')):
        d = json.load(open(f, encoding='utf-8'))
        ov[(d['board_slug'], d['meeting_date'])] = dict(path=os.path.relpath(f, ROOT), votes=len(d.get('votes') or []))
    return ev, vev, vmeta, nocap, tr, ours, ov


def build():
    docs, names = load_documents()
    vids, nofolder, nodate = load_videos()
    if not docs:
        raise SystemExit('the meeting index yielded no documents. Nothing written.')
    if not vids:
        raise SystemExit('no video joined to a board and a date. Nothing written.')

    # THE JOIN MUST MATCH SOMETHING. A (board, date) key that lines up for nobody looks
    # exactly like a town that never records its meetings -- the third defect shape in
    # CLAUDE.md, and the one that wrote 24,033 blank addresses earlier today.
    overlap = set(docs) & set(vids)
    if not overlap:
        raise SystemExit(
            'not one meeting has both a document and a video. The two sides key on '
            '(board folder, date) and something has stopped lining up. Nothing written.')

    ev, vev, vmeta, nocap, tr, ours, ov = load_artifacts()
    listed = listed_meetings()
    stamps = {}
    for r in read(STAMPS):
        k = (r['board_slug'], r['meeting_date'], r['kind'])
        cur = stamps.get(k)
        # The EARLIEST file wins: an amended agenda re-saved the day of the meeting must
        # not erase the one made a week ahead.
        if r['created'] and (not cur or r['created'] < cur['created']):
            stamps[k] = r
    rows = []
    for key in sorted(set(docs) | set(vids)):
        slug, date = key
        d = docs.get(key, {'agenda': 0, 'minutes': 0, 'ok': 0, 'bad': 0, 'paths': {}, 'urls': {}, 'ocr': 0})
        v = vids.get(key, [])
        have_doc = bool(docs.get(key))
        ea, em = ev.get((slug, date, 'agenda'), {}), ev.get((slug, date, 'minutes'), {})
        vs = sorted(v)
        ts = tr.get(key, [])
        o, votes = ours.get(key, {}), ov.get(key, {})
        parts = [('notice', 1 if ((slug, date) in listed or d['agenda']) else 0), ('agenda', d['agenda']),
                 ('minutes', d['minutes']), ('recording', 1 if v else 0), ('transcript', 1 if ts else 0),
                 ('our-minutes', 1 if o else 0), ('votes-read', 1 if votes else 0)]
        acts = [x for x in (ea.get('first_seen'), em.get('first_seen'), *(vev.get(i, {}).get('first_seen') for i in vs),
                            *((t.get('fetched_at') or '')[:10] for t in ts), o.get('written')) if x]
        rows.append({
            'board': names.get(slug, slug),
            'board_slug': slug,
            'date': date,
            'agenda': d['agenda'],
            'minutes': d['minutes'],
            'searchable_docs': d['ok'],
            'unsearchable_docs': d['bad'],
            'video': 1 if v else 0,
            'video_ids': ' '.join(sorted(v)),
            'transcript': 1 if ts else 0,
            'transcript_processed': 1 if o else 0,
            # WHICH KIND OF EVIDENCE PUT THIS ROW HERE. The document side is the town's
            # own filing; the video side is a model reading a title. Saying so per row is
            # what stops the second being read as the first.
            'evidence': ('document+video' if have_doc and v
                         else 'document' if have_doc else 'video only'),
            'agenda_path': d['paths'].get('agenda', ''), 'agenda_url': d['urls'].get('agenda', ''), 'agenda_first_seen': ea.get('first_seen', ''),
            'minutes_path': d['paths'].get('minutes', ''), 'minutes_url': d['urls'].get('minutes', ''), 'minutes_first_seen': em.get('first_seen', ''),
            'minutes_lag_upper_bound': em.get('days_after_meeting_upper_bound', ''), 'minutes_ocr': d['ocr'],
            'video_urls': ' '.join('https://www.youtube.com/watch?v=' + i for i in vs),
            'video_uploaded': ' '.join((vev.get(i) or vmeta.get(i) or {}).get('uploaded', '') or '-' for i in vs),
            'video_first_seen': ' '.join(vev.get(i, {}).get('first_seen', '') or '-' for i in vs),
            'captions_disabled': 1 if vs and all(i in nocap for i in vs) else 0,
            'transcript_paths': ' '.join(t['path'] for t in ts), 'transcript_fetched': max(((t.get('fetched_at') or '')[:10] for t in ts), default=''),
            'our_minutes_path': o.get('path', ''), 'our_minutes_url': o.get('url', ''), 'our_minutes_written': o.get('written', ''),
            'our_minutes_headline': o.get('headline', ''), 'our_votes': o.get('votes', '') if o else '',
            'official_votes_path': votes.get('path', ''), 'official_votes': votes.get('votes', '') if votes else '',
            'last_activity': max(acts) if acts else '',
            # THE AGENDA IS WHERE A MEETING BECOMES REAL. TJ, 18 September 2026: "in 99% of
            # cases, the town has to legally post on the agenda board. that's the true first
            # place a meeting will become 'real' ... and if it's not there, they likely are
            # breaking the law." The Open Meeting Law (M.G.L. c.30A §20) requires notice 48
            # hours ahead, so an agenda is the legal birth of a meeting and everything else
            # is a later artifact of one.
            #
            # WHAT THIS COLUMN DOES AND DOES NOT SAY (rule 7). `noticed: 0` means WE HOLD NO
            # AGENDA, which is not the same as none was posted: the town can re-file or
            # remove a document, a joint meeting is filed under one board, an emergency
            # meeting is noticed differently, our harvest of older years is thinner than of
            # recent ones, and the board and date on a video are a MODEL READING A TITLE.
            # So this is a list to check, never a finding. `--unnoticed` prints it.
            'noticed': 1 if (slug, date) in listed or d['agenda'] else 0,
            'agenda_created': stamps.get((slug, date, 'agenda'), {}).get('created', ''),
            'agenda_created_hours_before_meeting': stamps.get((slug, date, 'agenda'), {}).get('hours_before_meeting', ''),
            'minutes_created': stamps.get((slug, date, 'minutes'), {}).get('created', ''),
            'minutes_created_days_after_meeting': stamps.get((slug, date, 'minutes'), {}).get('days_after_meeting', ''),
            'complete': sum(1 for _, got in parts if got), 'complete_pct': int(round(100.0 * sum(1 for _, got in parts if got) / len(parts))),
            'complete_of': len(parts), 'missing': ' '.join(name for name, got in parts if not got),
            'part_of': '',
        })
    seen = {(r['board_slug'], r['date']) for r in rows}
    for r in rows:
        for suffix in ('-public-hearing', '-meeting'):
            if r['board_slug'].endswith(suffix):
                parent = r['board_slug'][:-len(suffix)]
                if (parent, r['date']) in seen:
                    r['part_of'] = parent
    return rows, nofolder, nodate, len(overlap)


def write(rows):
    tmp = OUT + '.tmp'
    with open(tmp, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        for r in sorted(rows, key=lambda r: (r['date'], r['board_slug']), reverse=True):
            w.writerow(r)
    os.replace(tmp, OUT)


def report(rows, nofolder, nodate, overlap):
    n = len(rows)
    def pc(k):
        c = sum(1 for r in rows if r[k])
        return c, 100.0 * c / n if n else 0
    print('%s: %d meeting occasions (one board, one date)'
          % (os.path.relpath(OUT, ROOT), n))
    for label, key in (('agenda', 'agenda'), ('minutes', 'minutes'), ('video', 'video'),
                       ('transcript', 'transcript'),
                       ('processed transcript', 'transcript_processed')):
        c, p = pc(key)
        print('  %-22s %6d  %5.1f%%' % (label, c, p))
    both = sum(1 for r in rows if r['agenda'] and r['minutes'])
    vonly = sum(1 for r in rows if r['evidence'] == 'video only')
    novid = sum(1 for r in rows if r['evidence'] == 'document')
    print('\n  agenda AND minutes     %6d  %5.1f%%' % (both, 100.0*both/n))
    print('  document AND video     %6d  %5.1f%%' % (overlap, 100.0*overlap/n))
    print('  VIDEO ONLY             %6d  %5.1f%%   <- the town filed no agenda or minutes'
          % (vonly, 100.0*vonly/n))
    print('  document, no video     %6d  %5.1f%%' % (novid, 100.0*novid/n))
    print('\n  how complete the record is, out of 7 (notice, agenda, minutes, recording,')
    print('  transcript, our minutes, votes read):')
    own = [r for r in rows if not r['part_of']]
    dist = collections.Counter(r['complete'] for r in own)
    for k in sorted(dist, reverse=True):
        print('    %d of 7  %6d  %5.1f%%' % (k, dist[k], 100.0 * dist[k] / len(own)))
    print('  (%d occasions; %d more rows are a hearing listed inside one of them)'
          % (len(own), len(rows) - len(own)))
    miss = collections.Counter(m for r in own for m in r['missing'].split())
    print('  most often missing: %s' % ', '.join('%s %d' % (k, v) for k, v in miss.most_common(4)))
    print('\n  %d video board rows have no AgendaCenter folder and cannot join '
          '(Water District, Town Meeting and the rest); %d have no date.'
          % (nofolder, nodate))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--unnoticed', action='store_true',
                    help='meetings we hold no agenda for — to CHECK against the town’s AgendaCenter, not to conclude from')
    ap.add_argument('--since', help='with --unnoticed: only meetings on or after this date')
    args = ap.parse_args()

    rows, nofolder, nodate, overlap = build()
    if args.unnoticed:
        un = [r for r in rows if not r['noticed'] and (not args.since or r['date'] >= args.since)]
        un.sort(key=lambda r: r['date'], reverse=True)
        print('%d meeting(s) the town’s AgendaCenter does not list%s. An agenda is the legal notice '
              '(M.G.L. c.30A §20), so each of these is worth checking on the town’s '
              'AgendaCenter — our crawl not holding the listing is not proof none was given.\n'
              % (len(un), ' since ' + args.since if args.since else ''))
        for r in un:
            print('  %s  %-42s %s' % (r['date'], r['board'][:42], r['video_urls'] or '(no recording either)'))
        return 0
    if args.check:
        if not os.path.exists(OUT):
            print('MISSING %s' % os.path.relpath(OUT, ROOT))
            return 1
        with open(OUT, newline='', encoding='utf-8') as fh:
            have = list(csv.DictReader(fh))
        want = [{k: str(r[k]) for k in COLS} for r in
                sorted(rows, key=lambda r: (r['date'], r['board_slug']), reverse=True)]
        if have != want:
            print('STALE %s — %d rows on disk, %d from the sources. '
                  'Run: python3 scripts/build_meeting_register.py'
                  % (os.path.relpath(OUT, ROOT), len(have), len(want)))
            return 1
        print('ok — %d meeting occasions, register matches its sources' % len(rows))
        return 0

    write(rows)
    report(rows, nofolder, nodate, overlap)
    return 0


if __name__ == '__main__':
    sys.exit(main())
