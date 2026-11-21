#!/usr/bin/env python3
"""A BUDGET SEASON AS A STATUS BOARD -- the state view, backed by the event log.

    python3 scripts/build_budget_season.py fy27            # -> fy28/public/data/budget-season-fy27.json
    python3 scripts/build_budget_season.py fy27-summer-governors-budget   # an episode, the same way
    python3 scripts/build_budget_season.py fy27 --check    # ...and fail if it is stale or a citation is dead

notes/process/BUDGET-SEASON-MODEL.md is the model. TJ, 14 September 2026: "the event log
should back up the state view. So we have the state view, then it can be 'built' or
reviewed/audited from the event log."

The state view is sources/data/budget-seasons/<fy>.csv, written by hand (retro) or from
rows the refresh proposes (live): block, item, scope, status, figure, fte, date, who, why,
evidence, note. The event log is what the evidence column points at, and EVERY citation is
resolved here or the build fails:

    board/date@seconds   our record of that meeting -- the budget-state file for that
                         recording (write_budget_state.py), or our minutes of it where the
                         extraction has not run (2025); resolved to the minutes page and the
                         video at that second
    doc:<path>           a document in the archive, resolved to its /docs/ address
    ballot:<date>        rows in sources/data/ballot-questions.csv for that election

<fy>-lines.csv (extract_scenario_lines.py) rides along: every budget line the scenarios
differ on, footed to the documents, so the cut list can be checked against it.
"""
import argparse
import csv
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEASONS = os.path.join(ROOT, 'sources', 'data', 'budget-seasons')
STATE = os.path.join(ROOT, 'sources', 'data', 'budget-state')
MINUTES = os.path.join(ROOT, 'sources', 'data', 'recording-minutes')
BALLOT = os.path.join(ROOT, 'sources', 'data', 'ballot-questions.csv')
OUTDIR = os.path.join(ROOT, 'fy28', 'public', 'data')
BLOCKS = ['deficit', 'proposals', 'cuts', 'override', 'late', 'final']
# A 'meta' row renames a block for one season: item = block, why = title, note = subtitle.
# The summer episode's 'override' block is the warrant articles; its 'deficit' is the new money.


def read_csv(p):
    return list(csv.DictReader(open(p, encoding='utf-8')))


def doc_label(rel):
    """The publisher's own title from the folder's index, so a reader sees 'FY27 Budget
    Projections as of 3-23-26' rather than a filename. Our analyses are labelled as ours."""
    if rel.startswith('sources/analyses/'):
        return 'our analysis: ' + os.path.basename(rel).replace('.md', '').replace('-', ' ')
    m = re.match(r'^sources/meetings/text/([a-z0-9-]+)/(\d{4}-\d{2}-\d{2})-(agenda|minutes)-\d+\.txt$', rel)
    if m:                                    # the town's own minutes or agenda, named as a reader would
        board = ' '.join(w.capitalize() for w in m.group(1).split('-'))
        d = m.group(2)
        return '%s %s, %s' % (board, m.group(3), __import__('datetime').date.fromisoformat(d).strftime('%-d %b %Y'))
    folder = rel.split('/')[1]
    idx = os.path.join(ROOT, 'sources', folder, 'index.csv')
    if os.path.exists(idx):
        for r in read_csv(idx):
            if r.get('local') == rel:
                return __import__('html').unescape(r.get('label') or os.path.basename(rel)).replace('&nbsp;', '').strip()
    return os.path.basename(rel)


def resolve(ev):
    """One citation -> where a reader goes. Fails loudly on a dead one."""
    ev = (ev or '').strip()
    if not ev:
        return None
    if ev.startswith('doc:'):
        rel = ev[4:]
        if not os.path.exists(os.path.join(ROOT, rel)):
            raise SystemExit('dead citation: %s' % ev)
        return dict(kind='document', href='/docs/' + rel.split('sources/', 1)[1], label=doc_label(rel))
    if ev.startswith('ballot:'):
        date = ev[7:]
        qs = [r for r in read_csv(BALLOT) if r['date'] == date]
        if not qs:
            raise SystemExit('dead citation: %s (no ballot rows)' % ev)
        return dict(kind='ballot', href='/data/ballot-questions.csv', label='%s, %s' % (qs[0]['election'], date))
    m = re.match(r'^([a-z0-9-]+)/(\d{4}-\d{2}-\d{2})@(\d+)$', ev)
    if not m:
        raise SystemExit('unreadable citation: %s' % ev)
    board, date, t = m.group(1), m.group(2), int(m.group(3))
    # our record of the meeting: the budget-state file (2026 on) or our minutes of the recording
    files = glob.glob(os.path.join(STATE, board, '%s-*.json' % date)) or glob.glob(os.path.join(MINUTES, board, '%s-*.json' % date))
    if not files:
        raise SystemExit('dead citation: %s (no budget-state file and no minutes of ours for that meeting)' % ev)
    d = json.load(open(files[0], encoding='utf-8'))
    return dict(kind='meeting', board=d['board'], board_slug=board, date=date, t=t,
                href='%s&t=%ds' % (d['video_url'], t) if t else d['video_url'],
                page='/meeting-minutes/%s/%s-%s' % (board, date, d['video_id']),
                label='%s, %s%s' % (d['board'], date, (' · %d:%02d' % (t // 60, t % 60)) if t else ''))


# A staff-authored DOCUMENT -- the budget book, the slides, the manager's message -- ranks
# with the staff who wrote it (write_document_budget_state.py names the author by role).
RANK = [(r'superintendent|business administrator|business manager|town manager|finance director|accountant|assistant town manager|budget (book|slides|message|document|presentation)|district\'s|town\'s', 3), (r'chair', 2), (r'member|committee|board', 1)]


def rank(who):
    w = (who or '').lower()
    return next((n for rx, n in RANK if re.search(rx, w)), 0)


def live_rows(fy, opens, have):
    """A LIVE SEASON, fed from the record. TJ: "it has to work LIVE and in retro" -- "you
    can figure out 'hey it looks like something is started'... I can confirm."

    Two streams out of the budget-state files dated from the season's opening:
      * AUTO -- rows the board shows without confirmation, because they are low-stakes and
        labelled for what they are: WARNINGS (predictions with no figure) as 'warned' rows in
        the cuts block, cited to the second.
      * PROPOSED -- rows a person confirms by copying them into <fy>.csv: a deficit figure
        put on the record by staff or the chair, a cut named by staff, an override figure.
        Written to <fy>.proposed.csv (never rendered) and counted by the refresh.
    A proposed row already in the file (same evidence) is not proposed again."""
    auto, proposed = [], []
    seen = {e.strip() for r in have for e in (r['evidence'] or '').split(' ; ')}
    season = int(fy[2:4]) + 2000
    # A statement ABOUT ANOTHER YEAR is not this season's, whatever day it was said: the
    # November Special Town Meeting's FY27 adjustments were being proposed onto the FY28
    # board. The extraction names the year (sometimes as 27); no year stated stays in.
    other_year = lambda x: x.get('fiscal_year') not in (None, '') and (int(x['fiscal_year']) % 100) + 2000 != season
    # By the file's own date, not its name: a document's file is named for the document.
    loaded = [(f, json.load(open(f, encoding='utf-8'))) for f in sorted(glob.glob(os.path.join(STATE, '*', '*.json')))]
    for f, d in sorted((x for x in loaded if x[1]['meeting_date'] >= opens), key=lambda x: x[1]['meeting_date']):
        board = os.path.basename(os.path.dirname(f))
        base = dict(scope='school', fte='', date=d['meeting_date'], note='')
        # A document's rows cite the document (`doc:` -- resolve() already reads it); a
        # meeting's cite the board, date and second.
        evidence = (lambda t: 'doc:' + d['source']['document']) if d.get('document') else (lambda t: '%s/%s@%d' % (board, d['meeting_date'], t))
        for w in d['state'].get('warnings') or []:
            if other_year(w):
                continue
            ev = evidence(w['t'])
            auto.append(dict(base, block='cuts', item=w['about'], scope=w.get('scope') or 'school', status='warned', figure='', who=w['who'],
                             why=w['prediction'] + (' — ' + w['condition'] if w.get('condition') else ''), evidence=ev))
        for st in d['state'].get('statements') or []:
            ev = evidence(st['t'])
            if ev in seen or rank(st.get('who')) < 2 or st['status'] == 'withdrawn' or other_year(st):
                continue
            if st['kind'] in ('deficit', 'override', 'budget_total') and st.get('amount_as_heard'):
                # A budget TOTAL is a proposal (Version 1, a tier), not an override: until 20 Nov
                # 2026 every total went to 'override', so the FY28 Version 1 figure was proposed there.
                proposed.append(dict(base, block={'deficit': 'deficit', 'budget_total': 'proposals'}.get(st['kind'], 'override'), item=st['statement'][:80], scope=st['scope'],
                                     status='path' if st['kind'] == 'deficit' else 'step', figure=st['amount_as_heard'], who=st['who'], why=st['statement'], evidence=ev))
        for c in d['state'].get('cuts') or []:
            ev = evidence(c['t'])
            if ev in seen or rank(c.get('who')) < 2 or other_year(c):
                continue
            proposed.append(dict(base, block='cuts', item=c['item'], scope=c['scope'], status='proposed' if c['status'] in ('proposed', 'announced') else c['status'],
                                 figure=c.get('amount_as_heard') or '', fte=c.get('fte_as_heard') or '', who=c['who'], why='', evidence=ev))
    return auto, proposed


# ---------------------------------------------------------------------------------------
# VERSIONS. notes/process/BUDGET-SEASON-MODEL.md §6. TJ, 20 November 2026: "we need to
# consider VERSIONS... each version has new cuts, deficits, etc." A version is a budget put on
# the record by somebody with standing (a draft, a target, a vote, a scenarios document, the
# adopted budget): a `block=version` row. Every other row belongs to the newest version of its
# side dated on or before it, so a row the refresh proposes lands in the current draft with no
# new column. The override track is not a draft and stays a season-wide strand; an `expected`
# row is a moment still to come; a row older than the first version is 'before the first
# version'. Nothing is dropped: the build fails if a row lands nowhere.

KEY_GAP = ('started', 'corrected', 'to_cut')     # a gap as a version states it; 'now' is how a season closed, and path rows are said in passing
APPROX = re.compile(r'about|roughly|slightly|north of|around|nearly|almost|~|as heard', re.I)


def money(figure):
    """The first dollar amount in a figure as printed, and whether it was stated loosely.
    '$1.98 million (as captioned: ...)' -> 1980000; 'slightly north of $3 million' -> 3000000,
    approximate. None where there is no amount."""
    m = re.search(r'([+-]?)\$\s?([\d,]+(?:\.\d+)?)\s*(million|m\b)?', figure or '', re.I)
    if not m:
        return None
    v = float(m.group(2).replace(',', '')) * (1e6 if m.group(3) else 1)
    return dict(v=-v if m.group(1) == '-' else v, approx=bool(APPROX.search(figure) or m.group(3)), signed=bool(m.group(1)))


def side_ok(row_scope, v_scope):
    """A school row belongs to a school version or a whole-town one; a town row to a town or
    whole-town one; a whole-town row to a whole-town version."""
    if row_scope == 'both':
        return v_scope == 'both'
    return v_scope in (row_scope, 'both')


def build_versions(fy, vrows, blocks):
    if not vrows:
        return [], None
    on = sorted([v for v in vrows if v['status'] != 'expected'], key=lambda v: v['date'])
    coming = sorted([v for v in vrows if v['status'] == 'expected'], key=lambda v: v['date'])
    slots = {i: dict(rows=[]) for i in range(len(on))}
    before, strand, upcoming = [], [], []
    for b, rs in blocks.items():
        for r in rs:
            if r['status'] == 'expected':
                upcoming.append(r)
                continue
            if b == 'override':
                strand.append(r)
                continue
            fit = [i for i, v in enumerate(on) if v['date'] <= r['date'] and side_ok(r['scope'] or 'school', v['scope'])]
            if not fit:                       # a whole-town row with no whole-town version: the newest of any side
                fit = [i for i, v in enumerate(on) if v['date'] <= r['date']] if (r['scope'] or '') == 'both' else []
            if fit:
                slots[fit[-1]]['rows'].append(r)
            else:
                before.append(r)
    placed = sum(len(s['rows']) for s in slots.values()) + len(before) + len(strand) + len(upcoming)
    total = sum(len(rs) for rs in blocks.values())
    if placed != total:
        raise SystemExit('%s: %d of %d rows placed in a version, a strand or the upcoming list' % (fy, placed, total))

    out, last_gap = [], {}
    last_stated = {}                          # scope -> the latest deficit any version stated, for a version that restates none
    tm_target = None
    on_table, off_so_far = 0, 0
    for i, v in enumerate(on):
        rs = slots[i]['rows']
        by = lambda blk: [r for r in rs if r['block'] == blk]
        deficit = by('deficit')
        key = [r for r in deficit if r['status'] in KEY_GAP and r['scope'] == v['scope']] or [r for r in deficit if r['status'] in KEY_GAP]
        gap = key[-1] if key else None
        closed = [r for r in deficit if r['status'] == 'now']
        cuts = [r for r in by('cuts') if r['status'] != 'warned']
        added = [r for r in cuts if r['status'] in ('decided', 'proposed', 'tier_only')]
        came_off = [r for r in cuts if r['status'] == 'came_off']
        on_table += len([r for r in added if r['status'] != 'tier_only'])
        off_so_far += len(came_off)
        moved = None
        if gap:
            g = money(gap['figure'])
            prev = last_gap.get(gap['scope'])
            # A DELTA ONLY BETWEEN TWO STATEMENTS OF ONE QUANTITY: the gap as announced and as
            # corrected. 'Left to cut on the night of the vote' is what remained after other
            # measures -- a different quantity, so it is shown beside the gap, never subtracted.
            if g and prev and not g['signed'] and gap['status'] in ('started', 'corrected') and prev['status'] in ('started', 'corrected'):
                moved = dict(by=round(g['v'] - prev['v'], 2), approx=g['approx'] or prev['approx'], from_figure=prev['figure'], from_version=prev['version'])
            if g and not g['signed']:
                last_gap[gap['scope']] = dict(v=g['v'], approx=g['approx'], figure=gap['figure'], version=v['item'], status=gap['status'])
        # THE PROJECTED DEFICIT ON THE MAIN LINE. TJ, 20 November 2026: "bump the projected
        # deficit up to the main line near the top of each draft". This version's own figure
        # if it states one (the gap, what was left to cut, or how it closed); otherwise the
        # last one stated, named with the version it came from. Never derived: where nothing
        # has been stated (FY28 Version 1) it stays None and the page says so.
        # A 'now' row printed as a TOTAL ('$25,787,474 approved') is how the season closed,
        # not a deficit, and is never carried as one.
        deficits = [r for r in closed if not re.search(r'approved|adopted', r['figure'], re.I)]
        own = gap or next((r for r in deficits if r['scope'] == v['scope']), None) or (deficits[0] if deficits else None)
        for r in ([gap] if gap else []) + deficits:
            if r['date'] >= last_stated.get(r['scope'], {}).get('date', ''):
                last_stated[r['scope']] = dict(figure=r['figure'], status=r['status'], scope=r['scope'], date=r['date'], who=r['who'], cite=r['cite'], carried_from=v['item'], basis='stated')
        if own:
            stated = dict(figure=own['figure'], status=own['status'], scope=own['scope'], date=own['date'], who=own['who'], cite=own['cite'], carried_from=None, basis='stated')
        elif v.get('total') and v.get('base'):
            # OURS, AND SAID SO. TJ, 20 November 2026: "i want US to derive it but say that"
            # ... "prop 2.5% increase max". A draft with no deficit on the record gets one:
            # the draft's total against last year's budget grown by 2.5%, the most Prop 2½ lets
            # the levy rise without an override. Prop 2½ caps the LEVY, not the school budget,
            # so the 2.5% for the schools is our assumption, and the page says that too.
            total, base = float(v['total']), float(v['base'])
            allowed = round(base * 1.025, 2)
            stated = dict(basis='derived', v=round(total - allowed, 2), total=total, base=base, allowed=allowed, rate=0.025, carried_from=None)
        else:
            # the last deficit stated on a side this version answers for, newest by date
            sides = {'both': ('school', 'town', 'both'), 'school': ('school', 'both'), 'town': ('town', 'both')}[v['scope']]
            cands = [last_stated[s] for s in sides if s in last_stated]
            stated = max(cands, key=lambda c: c['date']) if cands else None
        if re.search(r'Town Manager.s target', v['item']):
            t = next((r for r in by('proposals') if re.search(r'target', r['item'], re.I)), None)
            tm_target = dict(figure=t['figure'], why=t['why'], version=v['item'], date=v['date'], cite=t['cite']) if t else dict(figure=v['figure'], why=v['why'], version=v['item'], date=v['date'], cite=v['cite'])
        rise = money(v['figure'])
        out.append(dict(item=v['item'], scope=v['scope'], status=v['status'], figure=v['figure'], date=v['date'], who=v['who'], why=v['why'], note=v['note'],
                        cite=v['cite'], also=v['also'], n=i + 1, lines=v.get('lines'),
                        gap=gap, gap_moved=moved, deficit=stated, closed=closed, path=[r for r in deficit if r is not gap and r['status'] != 'now'],
                        proposals=by('proposals'), cuts_added=added, came_off=came_off, warned=[r for r in by('cuts') if r['status'] == 'warned'],
                        notes=[r for r in cuts if r['status'] not in ('decided', 'proposed', 'tier_only', 'came_off')],
                        late=by('late'), final=by('final'),
                        rise=rise['v'] if rise and rise['signed'] else None,
                        on_table=on_table, off_so_far=off_so_far,
                        # NO SCHOOL SHARE UNTIL THE TOWN MANAGER'S TARGET IS ON RECORD: before it,
                        # any split of the town's room between schools and town would be ours.
                        school_share=tm_target if (tm_target and v['scope'] in ('school', 'both')) else None))
    out.reverse()                             # newest first
    coming_out = [dict(item=v['item'], scope=v['scope'], status='expected', date=v['date'], who=v['who'], why=v['why'], cite=v['cite'], version=True) for v in coming]
    coming_out += [dict(item=r['item'], scope=r['scope'], status='expected', date=r['date'], who=r['who'], why=r['why'], cite=r['cite'], version=False) for r in upcoming]
    coming_out.sort(key=lambda r: r['date'])
    return out, dict(override=strand, before=before, coming=coming_out)


# ---------------------------------------------------------------------------------------
# THE DISTRICT'S LINE-BY-LINE DRAFTS. notes/process/BUDGET-SEASON-MODEL.md §7. TJ, 20 November
# 2026: "as the schools give more line budgets, we need to process them and do the same,
# automatically without me asking." Every draft scripts/build_school_drafts.py knows (one that
# footed; extract_fy28_draft_lines.py holds any other) is tied to a version card, in this order:
#   1. the version row whose evidence cites the draft's document -- a row somebody wrote;
#   2. else the season's EXPECTED row for that version number on the school side, which the
#      draft now fulfils: it takes the draft's date, figure and document;
#   3. else a new version row, built from the draft's own totals and said to be built so.
# The card then carries `lines`: the page, and what changed line by line against the version
# before. A draft is never left without a card.

def attach_drafts(fy, version_rows):
    import build_school_drafts as BSD
    out = []
    for d in [x for x in BSD.drafts() if x['fy'] == fy]:
        doc = 'doc:' + d['document']
        lines = dict(path=d['path'], short=d['short'], version=d['version'], lines=d['lines'], diff=d['diff'])
        # A card takes one draft: the first row citing the document that no earlier draft took.
        v = next((r for r in version_rows if not r.get('lines')
                  and doc in [e.strip() for e in (r['evidence'] or '').split(' ; ')]), None)
        how = 'cited'
        rise = '+$%s (%s%%)' % (format(d['change'], ',.2f'), '%.2f' % (100 * d['change'] / d['prior_total']))
        why = ('to $%s, against $%s for FY%d; salaries up $%s, everything else up $%s -- read off the district\'s '
               'line-by-line draft' % (format(d['total'], ',.2f'), format(d['prior_total'], ',.2f'), fy - 1,
                                         format(d['salaries'][1] - d['salaries'][0], ',.2f'),
                                         format(d['expenses'][1] - d['expenses'][0], ',.2f')))
        if not v:
            v = next((r for r in version_rows if not r.get('lines') and r['status'] == 'expected' and (r['scope'] or 'school') == 'school'
                      and re.match(r'^Version %d\b' % d['version'], r['item'])), None)
            if v:
                how = 'fulfilled'
                v.update(status='preliminary', figure=rise, date=d['date'] or v['date'], why=why,
                         evidence=doc, cite=resolve(doc), also=[], total=str(d['total']), base=str(d['prior_total']),
                         note='Filled in by the refresh from the district\'s draft when it arrived.')
        if not v:
            how = 'built'
            if not d['date']:
                raise SystemExit('FY%d version %d: no date in the catalogue or on a memo -- add the meeting date '
                                 'to sources/district-budget/index.csv' % (fy % 100, d['version']))
            v = dict(block='version', item='Version %d — line by line' % d['version'], scope='school',
                     status='preliminary', figure=rise, fte='', date=d['date'], who='the superintendent', why=why,
                     evidence=doc, note='Built by the refresh from the district\'s draft; no row was written for it.',
                     total=str(d['total']), base=str(d['prior_total']), cite=resolve(doc), also=[])
            version_rows.append(v)
        v['lines'] = lines
        out.append(dict(version=d['version'], page=d['path'], how=how))
    return out


LEVY = os.path.join(ROOT, 'sources', 'data', 'dls-levy-limits.csv')


def prop25(fy):
    """THE PROP 2½ STEP for a season: how far the WHOLE TOWN's levy may rise without an
    override -- 2.5% of the prior year's levy limit, plus new growth -- from the state's own
    levy limit file. Our arithmetic on the state's figures; the Town Manager's FY27 preliminary
    budget prints the same 2.5% step ($822,770.28), which is how this was checked. Where the
    prior year's limit is not yet certified, the floor is the year before grown by 2.5%, and
    says so. This is the LEVY only: state aid and local receipts move separately."""
    rows = {int(r['fy']): r for r in read_csv(LEVY)}
    num = lambda r, k: float(r[k]) if r and r.get(k) not in (None, '') else None
    prior = rows.get(fy - 1)
    src = '/docs/data/dls-levy-limits.csv'
    if prior and num(prior, 'levy_limit') is not None:
        lim = num(prior, 'levy_limit')
        ng = num(rows.get(fy), 'new_growth')
        return dict(fy=fy, prior_fy=fy - 1, prior_limit=lim, step=round(lim * 0.025, 2), new_growth=ng, room=round(lim * 0.025 + ng, 2) if ng is not None else None,
                    certified=True, floor=False, source=src)
    pp = rows.get(fy - 2)
    if pp and num(pp, 'levy_limit') is not None:
        lim = num(pp, 'levy_limit') * 1.025      # the prior limit before its own new growth and any override
        return dict(fy=fy, prior_fy=fy - 1, prior_limit=round(lim, 2), step=round(lim * 0.025, 2), new_growth=None, room=None, certified=False, floor=True,
                    basis_fy=fy - 2, basis_limit=num(pp, 'levy_limit'), source=src)
    return None


def build(fy):
    rows = read_csv(os.path.join(SEASONS, '%s.csv' % fy))
    live = next((r for r in rows if r['block'] == 'meta' and r['item'] == 'live'), None)
    if live:
        opens = re.search(r'opens (\d{4}-\d{2}-\d{2})', live['note']).group(1)
        auto, proposed = live_rows(fy, opens, rows)
        rows = rows + auto
        pp = os.path.join(SEASONS, '%s.proposed.csv' % fy)
        with open(pp, 'w', newline='', encoding='utf-8') as fh:
            w = csv.DictWriter(fh, fieldnames=['block', 'item', 'scope', 'status', 'figure', 'fte', 'date', 'who', 'why', 'evidence', 'note'], lineterminator='\n')
            w.writeheader()
            for r in proposed:
                w.writerow({k: r.get(k, '') for k in w.fieldnames})
    blocks = {b: [] for b in BLOCKS}
    titles = {}
    version_rows = []
    for i, r in enumerate(rows):
        if r['block'] == 'meta':
            titles[r['item']] = dict(title=r['why'], sub=r['note'])
            continue
        if r['block'] == 'version':
            evs = [e.strip() for e in (r['evidence'] or '').split(' ; ') if e.strip()]
            version_rows.append(dict(r, cite=resolve(evs[0]) if evs else None, also=[resolve(e) for e in evs[1:]]))
            continue
        if r['block'] not in blocks:
            raise SystemExit('row %d: unknown block %r' % (i + 2, r['block']))
        # Evidence may name more than one source, ' ; ' between them: a card resting on the
        # district's workbook for its figures and on the superintendent's memo for what the
        # draft is. The first is `cite`; the rest are `also`, each resolved or the build fails.
        evs = [e.strip() for e in (r['evidence'] or '').split(' ; ')]
        blocks[r['block']].append(dict(r, fte=float(r['fte']) if r['fte'] else None, cite=resolve(evs[0]),
                                       **({'also': [resolve(e) for e in evs[1:]]} if len(evs) > 1 else {})))
    for b in blocks:
        if b != 'proposals':                 # proposals stay in the order the publisher printed them
            blocks[b].sort(key=lambda r: r['date'])
    lines_p = os.path.join(SEASONS, '%s-lines.csv' % fy)
    lines = read_csv(lines_p) if os.path.exists(lines_p) else []
    for r in lines:
        for k in ('level_service', 'balanced', 'tier1_core', 'tier2_restoration', 'cut', 'tier1_restores', 'tier2_restores'):
            r[k] = float(r[k]) if r[k] else None
    linked = attach_drafts(int(fy[2:4]) + 2000, version_rows)
    versions, strands = build_versions(fy, version_rows, blocks)
    return dict(id=fy, fy=int(fy[2:4]) + 2000, source='sources/data/budget-seasons/%s.csv' % fy, rows=len(rows) - len(titles), blocks=blocks, lines=lines,
                versions=versions, strands=strands, drafts_linked=linked, prop25=prop25(int(fy[2:4]) + 2000) if versions else None,
                titles=titles, live=bool(live), proposed=len(proposed) if live else 0, as_of=__import__('datetime').date.today().isoformat() if live else None,
                model='notes/process/BUDGET-SEASON-MODEL.md')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('fy')
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    out = os.path.join(OUTDIR, 'budget-season-%s.json' % a.fy)
    text = json.dumps(build(a.fy), indent=1, sort_keys=True, ensure_ascii=False) + '\n'
    if a.check:
        have = open(out, encoding='utf-8').read() if os.path.exists(out) else ''
        strip = lambda t: re.sub(r'"as_of": "[^"]*"', '"as_of": ""', t)
        same = strip(have) == strip(text)
        print('ok — %s reproduces; every citation resolves' % os.path.relpath(out, ROOT) if same else 'STALE ' + out)
        return 0 if same else 1
    open(out, 'w', encoding='utf-8').write(text)
    d = json.loads(text)
    print('%s: %d rows — %s%s' % (os.path.relpath(out, ROOT), d['rows'], ', '.join('%s %d' % (b, len(d['blocks'][b])) for b in BLOCKS),
                                   ('; LIVE — %d row(s) proposed in %s.proposed.csv' % (d['proposed'], a.fy)) if d.get('live') else ''))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
