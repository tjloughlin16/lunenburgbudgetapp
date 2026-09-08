#!/usr/bin/env python3
"""What each PEG-channel video IS -- our reading of the title, never the title.

    python3 scripts/build_youtube_classification.py [--check]

Reads:
  sources/data/youtube-videos.csv                  what the channel published
  sources/data/youtube-title-classification.csv    OUR judgment, one row per title stem
  sources/data/youtube-boards.csv                  the boards we named, and their basis
  sources/data/youtube-classification-overrides.csv  human corrections -- READ, NEVER WRITTEN

Writes:
  sources/data/youtube-video-classification.csv    one row per video
  sources/data/youtube-video-boards.csv            one row per (video, board) pair

WHY IT IS SHAPED LIKE THIS

**There is no `board` column on a video.** A tri-board meeting is filed under all three
boards, so the boards live in their own table: three rows, and not a special case. Anything
that puts a board on the video row forces the tri-board meeting to pick a winner or invent
a `board_2` column, and both are how the next unforeseen title format breaks it again.

**Three outcomes, and two of them are not the same thing.** `meeting` is a meeting of one
or more identifiable public bodies. `not_a_meeting` is a video we know is not one -- the
channel's sixth commonest title stem is `St. Boniface Mass`, and filing a Catholic mass as
town business would be a real error in a published dataset. `undetermined` is a video we
could not read, and it must stay cheap: the alternative to representing something correctly
is recording that we could not, never squeezing it into the nearest slot.

**HUMAN CORRECTIONS SURVIVE RE-CLASSIFICATION.** The overrides file is keyed on video id
and this script never writes it. Without that, every improvement to the classification
silently discards every correction anybody made, and nothing reports that it happened. The
count of overrides applied is printed on every run, including when it is zero.

**Every join asserts that it matched.** A join that matches nothing looks exactly like data
that is absent, which is the shape most of this repository's defects have had. So: every
board named in the classification must exist in the board registry, every registry folder
must exist under sources/meetings/, and a run that classifies no video as a meeting refuses
to write.

THE STEM IS OURS. 4,671 titles reduce to 1,594 distinct stems once the date is removed, and
the classification is keyed on the stem so a person can read the whole of it. The stem is a
grouping device we built. It is never a quotable form of the title, and the verbatim title
travels on every output row beside it.
"""
import argparse
import collections
import csv
import datetime as dt
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'sources', 'data')
VIDEOS = os.path.join(DATA, 'youtube-videos.csv')
DECISIONS = os.path.join(DATA, 'youtube-title-classification.csv')
BOARDS = os.path.join(DATA, 'youtube-boards.csv')
OVERRIDES = os.path.join(DATA, 'youtube-classification-overrides.csv')
MEETINGS = os.path.join(ROOT, 'sources', 'meetings')
OUT_VIDEO = os.path.join(DATA, 'youtube-video-classification.csv')
OUT_BOARDS = os.path.join(DATA, 'youtube-video-boards.csv')

# The model that made the judgment in youtube-title-classification.csv, and when. Rule 13:
# the classification is a MODEL'S JUDGMENT about a string, and it is marked as ours
# everywhere it appears.
CLASSIFIED_BY = 'claude-opus-5 (1M context)'
CLASSIFIED_AT = '2026-09-08'

KINDS = {'meeting', 'not_a_meeting', 'undetermined'}

# ---------------------------------------------------------------------------
# The date in the title.
#
# THE ORDER AND THE CENTURY WERE ESTABLISHED FROM THE DATA, NOT ASSUMED. Of the 3,685
# `NN.NN.NN` runs in these titles, 2,163 have a SECOND field greater than 12 and NONE has
# a first field greater than 12 -- so the form is MM.DD.YY and nothing else fits.
# Two-digit years run 07 to 27 and are read as 20xx.
#
# `_mk` refuses anything outside 2005-2035, so a episode number or a score cannot become a
# date. The month-name form requires a comma or an ordinal between the day and the year,
# because without it `Oct 2014` parses as 20 October 2014 -- which it did, 34 times, before
# this rule was added.
MONTHS = {m: i + 1 for i, m in enumerate(
    ['jan', 'feb', 'mar', 'apr', 'may', 'jun',
     'jul', 'aug', 'sep', 'oct', 'nov', 'dec'])}
# The separator is back-referenced: `02,22,22` is a date, `Part 2, 11.13.23` is not.
NUM = re.compile(r'(?<!\d)(\d{1,2})\s*([.,/-])\s*(\d{1,2})\s*\2\s*(\d{2,4})(?!\d)')
SPC = re.compile(r'(?<![\d./-])(\d{1,2})\s+(\d{1,2})\s+(\d{2})(?![\d./-])')
GLUE8 = re.compile(r'(?<!\d)(\d{2})(\d{2})(\d{4})(?!\d)')
GLUE = re.compile(r'(?<!\d)(\d{2})(\d{2})(\d{2})(?!\d)')
NAME = re.compile(r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+'
                  r'(\d{1,2})(?:(?:st|nd|rd|th)\s*,?|\s*,)\s*(\d{4}|\d{2})\b', re.I)


def _mk(mo, d, y):
    if y < 100:
        y += 2000
    if not (2005 <= y <= 2035):
        return None
    try:
        return dt.date(y, mo, d)
    except ValueError:
        return None


def find_date(title):
    """(date, (start, end), form) for the LAST date-looking run in a title, or None."""
    cands = []
    for m in NUM.finditer(title):
        cands.append((m.start(), m,
                      _mk(int(m.group(1)), int(m.group(3)), int(m.group(4))), 'mm.dd.yy'))
    for m in SPC.finditer(title):
        a, b, c = (int(x) for x in m.groups())
        cands.append((m.start(), m, _mk(a, b, c), 'mm dd yy'))
    for m in GLUE8.finditer(title):
        a, b, c = (int(x) for x in m.groups())
        cands.append((m.start(), m, _mk(a, b, c), 'mmddyyyy'))
    for m in GLUE.finditer(title):
        a, b, c = (int(x) for x in m.groups())
        cands.append((m.start(), m, _mk(a, b, c), 'mmddyy'))
    for m in NAME.finditer(title):
        cands.append((m.start(), m,
                      _mk(MONTHS[m.group(1).lower()[:3]], int(m.group(2)),
                          int(m.group(3))), 'month name'))
    cands = [c for c in cands if c[2]]
    if not cands:
        return None
    cands.sort(key=lambda c: -c[0])
    _, m, d, form = cands[0]
    return d, (m.start(), m.end()), form


def stem_of(title):
    """The title with its date removed. OURS -- a grouping device, never a quotable title."""
    f = find_date(title)
    s = title if not f else title[:f[1][0]] + ' ' + title[f[1][1]:]
    return re.sub(r'\s+', ' ', s).strip(' -–—,.|:')


def read_csv(path):
    with open(path, newline='') as fh:
        return list(csv.DictReader(fh))


def build():
    videos = read_csv(VIDEOS)
    decisions = read_csv(DECISIONS)
    boards = read_csv(BOARDS)
    overrides = read_csv(OVERRIDES)

    if not videos:
        raise SystemExit('REFUSING: youtube-videos.csv is empty')
    if not decisions:
        raise SystemExit('REFUSING: youtube-title-classification.csv is empty')
    if not boards:
        raise SystemExit('REFUSING: youtube-boards.csv is empty')

    by_slug = {b['board_slug']: b for b in boards}
    if len(by_slug) != len(boards):
        raise SystemExit('REFUSING: duplicate board_slug in youtube-boards.csv')

    # Every folder the registry names must exist. A registry pointing at nothing reads as
    # coverage, which is worse than no registry.
    for b in boards:
        folder = b['meetings_folder'].strip()
        if folder and not os.path.isdir(os.path.join(MEETINGS, folder)):
            raise SystemExit(f'REFUSING: board {b["board_slug"]} names meetings folder '
                             f'{folder!r}, which does not exist')

    dec = {}
    for d in decisions:
        stem = d['title_stem']
        if stem in dec:
            raise SystemExit(f'REFUSING: duplicate title_stem {stem!r}')
        if d['kind'] not in KINDS:
            raise SystemExit(f'REFUSING: unknown kind {d["kind"]!r} for {stem!r}')
        slugs = [s for s in d['boards'].split('|') if s]
        for s in slugs:
            if s not in by_slug:
                raise SystemExit(f'REFUSING: {stem!r} names board {s!r}, which is not in '
                                 f'youtube-boards.csv')
        if d['kind'] == 'meeting' and not slugs:
            raise SystemExit(f'REFUSING: {stem!r} is a meeting with no board')
        if d['kind'] != 'meeting' and slugs:
            raise SystemExit(f'REFUSING: {stem!r} is {d["kind"]} and names a board')
        dec[stem] = d

    ov = {}
    for o in overrides:
        vid = o['video_id'].strip()
        if not vid:
            continue
        if vid in ov:
            raise SystemExit(f'REFUSING: duplicate override for video {vid}')
        if o.get('kind') and o['kind'] not in KINDS:
            raise SystemExit(f'REFUSING: override for {vid} has unknown kind {o["kind"]!r}')
        for s in [s for s in (o.get('boards') or '').split('|') if s]:
            if s not in by_slug:
                raise SystemExit(f'REFUSING: override for {vid} names board {s!r}, which '
                                 f'is not in youtube-boards.csv')
        ov[vid] = o

    indexed = max((v['indexed_at'] for v in videos if v.get('indexed_at')), default='')
    horizon = None
    if indexed:
        try:
            horizon = dt.date.fromisoformat(indexed[:10])
        except ValueError:
            horizon = None

    vrows, brows = [], []
    applied, unknown_stems = set(), collections.Counter()
    for v in videos:
        title = v['title']
        stem = stem_of(title)
        f = find_date(title)
        meeting_date = f[0].isoformat() if f else ''
        date_source = f'title ({f[2]})' if f else 'unknown'
        date_flag = ''
        if f and horizon and f[0] > horizon:
            # The title states a date after the day the channel was indexed. Two titles do
            # this -- 01.16.27 and 11.06.27 -- and both sit among videos the channel puts
            # in 2025 and 2024. Flagged rather than corrected: the title is the observed
            # thing and a correction is somebody's judgment, which belongs in the overrides.
            date_flag = 'after the index date; the title may carry a typo'

        d = dec.get(stem)
        if d is None:
            unknown_stems[stem] += 1
            kind, slugs, category, note = 'undetermined', [], '', 'no decision recorded'
            source = 'no decision recorded'
        else:
            kind = d['kind']
            slugs = [s for s in d['boards'].split('|') if s]
            category, note = d['category'], d['note']
            source = 'model'

        by, at = CLASSIFIED_BY, CLASSIFIED_AT
        o = ov.get(v['video_id'])
        if o:
            applied.add(v['video_id'])
            if o.get('kind'):
                kind = o['kind']
                slugs = [s for s in (o.get('boards') or '').split('|') if s]
            elif o.get('boards'):
                slugs = [s for s in o['boards'].split('|') if s]
            if o.get('category'):
                category = o['category']
            if o.get('meeting_date'):
                meeting_date = o['meeting_date']
                date_source = 'human override'
                date_flag = ''
            note = (o.get('why') or note)
            source = 'human override'
            # The row is no longer the model's judgment, so it stops claiming to be.
            by, at = (o.get('corrected_by') or 'human'), (o.get('corrected_at') or '')

        vrows.append({
            'video_id': v['video_id'],
            'channel_rank': v['channel_rank'],
            'title': title,
            'url': v['url'],
            'title_stem': stem,
            'kind': kind,
            'category': category,
            'board_count': len(slugs),
            'meeting_date': meeting_date,
            'date_source': date_source,
            'date_flag': date_flag,
            'note': note,
            'classification_source': source,
            'classified_by': by,
            'classified_at': at,
        })
        for s in slugs:
            brows.append({
                'video_id': v['video_id'],
                'board_slug': s,
                'board_name': by_slug[s]['board_name'],
                'title_stem': stem,
                'meetings_folder': by_slug[s]['meetings_folder'],
                'in_agenda_center': 'yes' if by_slug[s]['meetings_folder'] else 'NO',
                'meeting_date': next(r['meeting_date'] for r in vrows
                                     if r['video_id'] == v['video_id']),
                'classification_source': source,
                'classified_by': by,
                'classified_at': at,
            })

    if len(vrows) != len(videos):
        raise SystemExit('REFUSING: lost a video somewhere')
    if not any(r['kind'] == 'meeting' for r in vrows):
        raise SystemExit('REFUSING: no video classified as a meeting -- the join to the '
                         'decisions matched nothing, which looks exactly like data absent')
    if not brows:
        raise SystemExit('REFUSING: no (video, board) rows')

    return vrows, brows, boards, applied, unknown_stems, len(ov)


def render(rows, cols):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols)
    w.writeheader()
    for r in rows:
        w.writerow({c: r[c] for c in cols})
    return buf.getvalue()


VIDEO_COLS = ['video_id', 'channel_rank', 'title', 'url', 'title_stem', 'kind', 'category',
              'board_count', 'meeting_date', 'date_source', 'date_flag', 'note',
              'classification_source', 'classified_by', 'classified_at']
BOARD_COLS = ['video_id', 'board_slug', 'board_name', 'title_stem',
              'meetings_folder', 'in_agenda_center', 'meeting_date',
              'classification_source', 'classified_by', 'classified_at']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()

    vrows, brows, boards, applied, unknown, n_overrides = build()
    video_csv = render(vrows, VIDEO_COLS)
    board_csv = render(brows, BOARD_COLS)

    if args.check:
        stale = []
        for path, body in ((OUT_VIDEO, video_csv), (OUT_BOARDS, board_csv)):
            current = open(path, newline='').read() if os.path.exists(path) else ''
            if current != body:
                stale.append(os.path.basename(path))
        if stale:
            print('STALE  ' + ', '.join(stale) +
                  ' — run: python3 scripts/build_youtube_classification.py')
            return 1
        print('ok: the YouTube classification matches the titles and the decisions')
        return 0

    with open(OUT_VIDEO, 'w', newline='') as fh:
        fh.write(video_csv)
    with open(OUT_BOARDS, 'w', newline='') as fh:
        fh.write(board_csv)

    total = len(vrows)
    kinds = collections.Counter(r['kind'] for r in vrows)
    dated = sum(1 for r in vrows if r['meeting_date'])
    print(f'{total:,} videos')
    for k in ('meeting', 'not_a_meeting', 'undetermined'):
        print(f'  {k:16s} {kinds[k]:>5,}  ({kinds[k] / total:.1%})')
    print(f'\n  UNDETERMINED IS THE DENOMINATOR: {kinds["undetermined"]:,} of {total:,}. '
          f'Publish it wherever this index is used.')
    print(f'\n  meeting date from the title  {dated:,} of {total:,} '
          f'({dated / total:.1%}); the rest are `unknown`')
    flagged = [r for r in vrows if r['date_flag']]
    if flagged:
        print(f'  dates flagged as implausible {len(flagged)}: '
              + ', '.join(r['title'] for r in flagged))

    print(f'\n  overrides in the file {n_overrides}, applied {len(applied)}'
          + ('  (the file is empty -- it is read on every run and never written)'
             if not n_overrides else ''))

    per = collections.Counter(r['board_slug'] for r in brows)
    print(f'\n{len(brows):,} (video, board) rows over {len(per)} boards')
    outside = [b for b in boards if not b['meetings_folder']]
    print(f'\nBOARDS NOT AMONG THE AGENDACENTER FOLDERS — {len(outside)}, '
          f'FOR REVIEW:')
    for b in sorted(outside, key=lambda b: -per[b['board_slug']]):
        print(f'  {per[b["board_slug"]]:>4}  {b["board_name"]}  [{b["body_type"]}]')

    if unknown:
        print(f'\n{sum(unknown.values())} videos on {len(unknown)} title stems have no '
              f'decision recorded and are undetermined:')
        for s, n in unknown.most_common(20):
            print(f'  {n:>4}  {s!r}')

    print(f'\nwrote {os.path.relpath(OUT_VIDEO, ROOT)}')
    print(f'wrote {os.path.relpath(OUT_BOARDS, ROOT)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
