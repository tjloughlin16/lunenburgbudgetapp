"""Every content card fits on the card. Enforced, not eyeballed.

    python3 scripts/check_content_cards.py
    python3 scripts/check_content_cards.py --worst 15

WHY. `notes/process/CONTENT-CANDIDATES.md` is the copy for cards that are 1200x630 pixels
and get a second and a half of somebody's attention on a phone. Nothing was stopping an
item growing, and one did: item 1.1 reached 3,202 characters against a median of 1,111,
with a 279-character headline, because every correction made to it ADDED. TJ: *"the content
for 1.1 is now VERY LONG.... we need content restrictions per 'format'"*.

CLAUDE.md already says how this has to work, and says it from experience:

    the METRIC, with its unit          93 of 132 budget items
    one line: what it is               when the school budget stops funding something
    one line: what follows             it usually comes back
    ---- everything else expands ----

and then: **"Enforce the length in the generator, not by eye -- a character budget derived
from the card's real width, and a build that fails past it. A rule checked by reading lasts
until the next report."**

THE BUDGETS WERE MEASURED FROM A CARD, NOT CHOSEN. They used to be four template images,
and the comment on BUDGETS below said so and said to replace them the moment a real card
existed. One did: /worth-knowing drew all 48, and `fy28/scripts/measure-card-budgets.mjs`
read the rendered box at 390px and at 1280px and divided it by the advance width of the
copy actually set in it. The numbers below are that measurement.

THAT PAGE AND THAT SCRIPT ARE BOTH GONE, and this is what stands in their place. The card
that has a real constraint now is the 1200x630 SHARE IMAGE -- the thing that actually gets
posted -- and `python3 scripts/build_blog.py --measure` renders every one of them and
fails if any element's copy overflows the box, which is a stronger check than a character
budget because it measures the artefact rather than a proxy for it. What survives here is
the WORKLIST: a per-format character budget is still the cheapest way to see, at a
terminal, which items are long before anybody renders anything.

AND THE MEASUREMENT MOVED THE ANSWER. The templates implied four very different headline
budgets, 16 to 129 characters. The rendered card gives 123 to 126 for all four, because
they are all the same card in the same 350px box -- what differs between the formats is the
COPY, not the space. A budget read off a screenshot was measuring the sentence somebody had
chosen to put in the picture.

THE HARD PART IS NOT THE TRIMMING. Cutting the context forces the HEADLINE to carry its own
meaning, and that usually means picking a different figure rather than writing shorter prose
around the same one. `93` needs a paragraph; `93 of 132 budget items` needs one line. Where
a figure cannot be made self-explanatory in a few words it is the wrong figure for the card
-- which is how "95 of the 171 pairs of years" was caught: true, derived, checked, and
unreadable, because "pairs of years" is combinatorics and nobody speaks it.

WHAT THIS DOES NOT CHECK, and it matters more than length: whether the card is worth
reading. A card can pass every budget here and still say nothing. The three tests for that
-- a contrast, an impact a reader recognises as theirs, and a takeaway they can use -- live
in the document itself and in a person's judgement.
"""
import argparse
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(ROOT, 'notes', 'process', 'CONTENT-CANDIDATES.md')

# MEASURED FROM THE RENDERED CARD, at 390px and at 1280px, on 11 September 2026.
#
# These were provisional and this comment used to say so: the first budgets were the
# lengths of the four template IMAGES a collaborator supplied, which is a guess about a
# rendering that did not yet exist. TJ: "lets build out the pages and the entryways for
# all the format types. Then we can figure out how the content fills those in. Then we
# know our real restrictions." The cards exist now, so these are the real restrictions.
#
# HOW THEY WERE DERIVED, on 11 September 2026, by a script that no longer exists (see the
# docstring). It served the built site, opened /worth-knowing -- the page that drew all 48
# as cards -- in headless Chrome at each width, and for every rendered field
# reads the content-box width, the computed font and the line-height off the DOM, then
# measures the average advance width of THAT ITEM'S OWN TEXT with a canvas in the same
# font. Characters are not interchangeable -- a headline of dollar figures sets wider than
# one of prose -- so the published figure is the MEDIAN over the real items of that
# format, and the spread is printed beside it.
#
#     budget = characters per line x the lines the field is allotted
#
# The lines allotted -- headline 3, support 3, one impact line 2, takeaway 4 -- are the one
# DESIGN decision in the chain and they are declared in that script. Everything else is
# measured.
#
# THE 390px FIGURE IS THE BUDGET. A card has to work on a phone. The desktop box is about
# 45% wider and its figures are in the script's output, not here, because a budget that
# only holds on a laptop is not a budget.
#
#   format               headline (390 / 1280)   support         impact    takeaway
#   new finding             126 / 183            162 / 234       110/160   224/324
#   myth vs fact            126 / 183            156 / 225       112/162   224/328
#   did you know            126 / 183            162 / 234       110/158   224/324
#   analysis spotlight      123 / 180            141 / 207       108/158   224/324
#
# WHAT THE MEASUREMENT SAYS THAT THE TEMPLATES DID NOT. The four headline budgets are
# nearly the same -- 123 to 126 -- where the template images implied 16 to 129. That is
# because they are all the same card in the same 350px box; what differs between formats
# is not the space, it is the COPY set in it. The old spread was measuring four
# screenshots of four different sentences and calling it four formats.
#
# `analysis-spotlight` rests on a single item, which is all the copy there is in that
# format today. It is the tightest of the four and it is the least well established; if
# more spotlights are written, re-run the script.
BUDGETS = {
    'did you know':       dict(headline=126, support=162),
    'new finding':        dict(headline=126, support=162),
    'myth vs fact':       dict(headline=126, support=156),
    'analysis spotlight': dict(headline=123, support=141),
}
# Shared across every format, so each takes the NARROWEST measurement of the four: a
# budget that holds for three formats and not the fourth is not a shared budget.
IMPACT_EACH = 108          # one line, in the reader's own terms -- two rendered lines
TAKEAWAY = 224             # what to conclude, and what NOT to -- four rendered lines
# For a format that does not exist yet: the tightest measured card, because an unmeasured
# thing should not be given the most generous number available.
DEFAULT = dict(headline=123, support=141)


def items(text):
    parts = re.split(r'^### (\d+\.\d+ .+)$', text, flags=re.M)
    for i in range(1, len(parts), 2):
        yield parts[i], parts[i + 1]


def measure(body):
    """Only what a reader sees on the card. The expander is deliberately unbounded."""
    visible = body.split('<details>')[0]
    head = re.search(r'^> ### (.+)$', visible, re.M)
    support = [l[2:].rstrip() for l in visible.split('\n')
               if l.startswith('> ') and not l.startswith('> ###')
               and not l.strip().lstrip('> ').startswith('*—')]
    impacts = re.findall(r'^\*\*If you are ([^:]+):\*\* (.+)$', visible, re.M)
    take = re.search(r'\*\*What we expect the reader to take away\*\*\s*(.*?)(?=\n\n|\Z)',
                     visible, re.S)
    fmt = re.search(r'\*\*Format\*\*\s*—\s*([A-Za-z ]+)', body)
    return dict(
        headline=head.group(1).strip() if head else '',
        support=' '.join(x for x in support if x.strip()),
        impacts=[(who.strip(), txt.strip()) for who, txt in impacts],
        takeaway=re.sub(r'\s+', ' ', take.group(1)).strip() if take else '',
        fmt=(fmt.group(1).strip().lower() if fmt else ''),
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--worst', type=int, default=0,
                    help='list the N longest items rather than only the failures')
    args = ap.parse_args()

    if not os.path.exists(DOC):
        raise SystemExit('missing %s' % os.path.relpath(DOC, ROOT))
    text = io.open(DOC, encoding='utf-8').read()

    fails, sizes = [], []
    n = 0
    for title, body in items(text):
        n += 1
        m = measure(body)
        key = title.split()[0]
        b = BUDGETS.get(m['fmt'], DEFAULT)
        sizes.append((len(m['headline']) + len(m['support']), key, m))
        if len(m['headline']) > b['headline']:
            fails.append('%s headline %d > %d  %s…'
                         % (key, len(m['headline']), b['headline'], m['headline'][:58]))
        if len(m['support']) > b['support']:
            fails.append('%s support  %d > %d  %s…'
                         % (key, len(m['support']), b['support'], m['support'][:58]))
        for who, txt in m['impacts']:
            if len(txt) > IMPACT_EACH:
                fails.append('%s impact (%s) %d > %d  %s…'
                             % (key, who[:22], len(txt), IMPACT_EACH, txt[:48]))
        if len(m['takeaway']) > TAKEAWAY:
            fails.append('%s takeaway %d > %d'
                         % (key, len(m['takeaway']), TAKEAWAY))
        if not m['headline']:
            fails.append('%s has no headline' % key)
        if not m['takeaway']:
            fails.append('%s has no takeaway' % key)

    if not n:
        raise SystemExit('parsed zero items from %s — refusing to report a pass'
                         % os.path.relpath(DOC, ROOT))

    if args.worst:
        print('longest %d of %d items, headline + support:\n' % (args.worst, n))
        for total, key, m in sorted(sizes, reverse=True)[:args.worst]:
            print('  %-6s %4d   %s…' % (key, total, m['headline'][:64]))
        print()

    if fails:
        print('%d card(s) over budget, of %d items:\n' % (
            len({f.split()[0] for f in fails}), n))
        for f in fails:
            print('  ' + f)
        print('\nThe fix is usually NOT shorter prose around the same figure. It is a '
              'different\nfigure — one that carries its own meaning — with the rest moved '
              'under the expander.')
        return 1

    print('ok: %d cards, every headline, supporting line, impact line and takeaway '
          'within budget' % n)
    return 0


if __name__ == '__main__':
    sys.exit(main())
