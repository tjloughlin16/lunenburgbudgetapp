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
import csv
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
        'evidence']

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
            m = out.setdefault(key, {'agenda': 0, 'minutes': 0, 'ok': 0, 'bad': 0})
            if r['kind'] in ('agenda', 'minutes'):
                m[r['kind']] = 1
            txt = os.path.join(TEXT_DIR, os.path.splitext(r['path'])[0] + '.txt')
            if os.path.exists(txt):
                m['ok' if searchable(txt) else 'bad'] += 1
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

    rows = []
    for key in sorted(set(docs) | set(vids)):
        slug, date = key
        d = docs.get(key, {'agenda': 0, 'minutes': 0, 'ok': 0, 'bad': 0})
        v = vids.get(key, [])
        have_doc = bool(docs.get(key))
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
            'transcript': 0,             # nothing fetched yet, on purpose
            'transcript_processed': 0,
            # WHICH KIND OF EVIDENCE PUT THIS ROW HERE. The document side is the town's
            # own filing; the video side is a model reading a title. Saying so per row is
            # what stops the second being read as the first.
            'evidence': ('document+video' if have_doc and v
                         else 'document' if have_doc else 'video only'),
        })
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
    print('\n  %d video board rows have no AgendaCenter folder and cannot join '
          '(Water District, Town Meeting and the rest); %d have no date.'
          % (nofolder, nodate))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()

    rows, nofolder, nodate, overlap = build()
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
