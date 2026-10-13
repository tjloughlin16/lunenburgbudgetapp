#!/usr/bin/env python3
"""ONE TOPIC PAGE, validated. The payload every topic generator emits and Topic.tsx renders.

A topic answers one question in under five minutes (scripts/topics.py has the model). Its
parts, in reading order:

    title       from the registry -- descriptive, two to four words, never typed here
    finding     ONE line: what the page shows. The line under the title on the shelf too
    chart       an id in the site's chart registry, and the payload that feeds it -- so a
                chart is drawn once, by one component, wherever it appears
    facts       tiles (ladder.fact): a value and a label carrying its unit, with its kind
    conclusions two to four (ladder.conclusion), each naming the facts it rests on, and
                optionally `notes`: brief.step layers -- what is not known, a hypothesis, a
                link to the evidence. Only those three render; the facts carry the rest
    table       optional: FigureTable data -- the figures behind the chart
    said        optional: what was said in public meetings ABOUT THIS TOPIC ONLY
    sources     where the figures come from, by address

Every unit of prose goes through the same rule-2 check the brief and the ladder use
(brief.check_unit): a digit that is not a registered figure or a declared literal refuses
the page. The budgets are the ladder's: a finding is a conclusion's length, 110.
"""
from brief import _unit, check_unit, PRESCRIPTIVE
from conclusions import ConclusionError
import ladder as LD
import topics as REG

FINDING_MAX = 110
# A PAGE THAT IS TOO LONG IS TWO PAGES. TJ, 12 October 2026: "it's an indicator that we
# didn't hub and spoke it enough if the final reports are still too long." So length is
# not tuned by trimming prose: past these, the build refuses, and the remedy is to split the
# topic in the registry. Set just above the longest page on the day they were written.
TOPIC_WORDS_MAX = 320     # prose a reader meets: finding, labels, conclusions, notes, quotes
HUB_WORDS_MAX = 400
TABLE_ROWS_MAX = 30
FACTS = (2, 12)
CONCLUSIONS = (1, 4)
SAID_MAX = 4


def page(id, finding, facts, conclusions, chart=None, table=None, said=(), sources=(),
         finding_figures=None, finding_allow=()):
    if id not in REG.TOPICS:
        raise ConclusionError('topic %r is not in scripts/topics.py' % id)
    title, home, _ = REG.TOPICS[id]
    f = _unit(finding, finding_figures, finding_allow, FINDING_MAX, '%s finding' % id)
    if not FACTS[0] <= len(facts) <= FACTS[1]:
        raise ConclusionError('%s: %d facts; a topic holds %d to %d' % ((id, len(facts)) + FACTS))
    if not CONCLUSIONS[0] <= len(conclusions) <= CONCLUSIONS[1]:
        raise ConclusionError('%s: %d conclusions; a topic holds %d to %d'
                              % ((id, len(conclusions)) + CONCLUSIONS))
    if len(said) > SAID_MAX:
        raise ConclusionError('%s: %d quotations; a topic quotes at most %d -- the rest stay in '
                              'the full report' % (id, len(said), SAID_MAX))
    ids = [x['id'] for x in facts]
    if len(set(ids)) != len(ids):
        raise ConclusionError('%s: two facts share an id' % id)
    bad = check_unit(f, '%s finding' % id)
    for x in facts:
        bad += check_unit(x['label'], '%s %s label' % (id, x['id']))
    for i, c in enumerate(conclusions):
        bad += check_unit(c, '%s conclusion %d' % (id, i + 1))
        for r in c['rests_on']:
            if r not in ids:
                bad.append('%s conclusion %d rests on %r, not a fact on this page' % (id, i + 1, r))
        for n in c.get('notes', []):
            bad += check_unit(n, '%s conclusion %d note' % (id, i + 1))
        if PRESCRIPTIVE.search(c['text']):
            bad.append('%s conclusion %d tells the reader what to do' % (id, i + 1))
    if not sources:
        bad.append('%s: no sources -- rule 12' % id)
    n = _words([f] + [x['label'] for x in facts] + list(conclusions)
               + [nn for c in conclusions for nn in c.get('notes', [])]
               + [dict(text=q['quote']) for q in said])
    if n > TOPIC_WORDS_MAX:
        bad.append('%s: %d words of prose, the limit is %d -- this is two topics; split it in '
                   'the registry rather than trimming it' % (id, n, TOPIC_WORDS_MAX))
    if table and any(len(v['rows']) > TABLE_ROWS_MAX for v in table['views']):
        bad.append('%s: a table runs past %d rows -- split it by period or by group'
                   % (id, TABLE_ROWS_MAX))
    if bad:
        raise ConclusionError('topic %s did not pass:\n  %s' % (id, '\n  '.join(bad)))
    return dict(
        id=id, kind='topic', title=title, category=home, path=REG.path(id),
        shelves=REG.shelves_of(id), finding=f, chart=chart, facts=list(facts),
        conclusions=list(conclusions), table=table, said=list(said), sources=list(sources),
        full_report=_full(home))


def _words(units):
    return sum(len(u['text'].split()) for u in units)


def conclusion(text, rests_on, figures=None, allow=(), notes=()):
    """A topic conclusion: ladder.conclusion plus `notes`, the brief.step layers under it."""
    c = LD.conclusion(text, rests_on, figures, allow)
    if notes:
        c['notes'] = list(notes)
    return c


def hub(cid, answer, ladder, chains=(), chart=None, table=None, answer_figures=None,
        answer_allow=()):
    """A category's hub: the answer, the signature chart, the matrix and conclusions, and --
    added by build_topics_index.py from the registry -- a card per topic."""
    cat = REG.category(cid)
    a = _unit(answer, answer_figures, answer_allow, 260, '%s answer' % cid)
    bad = check_unit(a, '%s answer' % cid)
    n = _words([a] + [f['label'] for t in ladder['tiers'] for f in t['facts']]
               + ladder['conclusions'])
    if n > HUB_WORDS_MAX:
        bad.append('hub %s: %d words, the limit is %d -- move detail down to a topic'
                   % (cid, n, HUB_WORDS_MAX))
    if bad:
        raise ConclusionError('hub %s did not pass:\n  %s' % (cid, '\n  '.join(bad)))
    return dict(id=cid, kind='hub', title=cat['title'], category=cid, path=REG.path(cid),
                shelves=[cid], answer=a, chart=chart, ladder=ladder, chains=list(chains),
                table=table, full_report=_full(cid))


def _full(cid):
    """The old long report a category came from, if it had one. Not promoted anywhere --
    TJ: "we dont need FULL reports" -- but a note's evidence link may still land in it."""
    fr = REG.category(cid).get('full_report')
    return dict(href=fr[0], label=fr[1]) if fr else dict(href='', label='')
