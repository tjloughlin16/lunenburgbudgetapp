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

THE BUDGETS ARE DERIVED FROM THE CARD, NOT CHOSEN. At the headline size the collaborator's
template runs about 48 characters to the line and the design holds two lines, so 95 -- which
is also, not by coincidence, the limit `scripts/conclusions.py` already enforces on a
claim. The supporting block is smaller type and gets two to three lines. An impact line is
ONE line. Everything that does not fit belongs under the expander, which is not a demotion:
a reader who wants the mechanism opens it, and a reader who wants the point has already
had it.

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

# Per format, because a Myth vs Fact carries two statements where a Did You Know carries
# one, and an Analysis Spotlight is a teaser rather than a finding.
# PROVISIONAL, AND THE NUMBERS ARE MEASURED RATHER THAN CHOSEN -- they are the lengths of
# the four template cards the collaborator actually supplied, rounded up a little:
#
#   analysis spotlight   headline  16   support 116
#   did you know         headline  68   support  91
#   myth vs fact         headline 129   support   0
#   new finding          headline  77   support 136
#
# THEY ARE PLACEHOLDERS AND THIS COMMENT IS THE POINT. TJ: "lets build out the pages and
# the entryways for all the format types. Then we can figure out how the content fills
# those in. Then we know our real restrictions." He is right: a budget derived from a
# screenshot is a guess about a rendering that does not exist yet. Once the card
# components ship, RE-DERIVE these from what actually fits at 390px and 1280px -- measure
# the rendered box, do not read the design.
#
# Note how different the four are. A Myth vs Fact headline is 129 characters because it
# has to state a complete corrected fact; an Analysis Spotlight headline is 16 because it
# is a question, with the work done by the support line. One budget for all four would be
# wrong for three of them.
BUDGETS = {
    'did you know':       dict(headline=80,  support=110),
    'new finding':        dict(headline=90,  support=150),
    'myth vs fact':       dict(headline=135, support=120),
    'analysis spotlight': dict(headline=60,  support=130),
}
# Shared across every format.
IMPACT_EACH = 140          # one line, in the reader's own terms
TAKEAWAY = 260             # two sentences: what to conclude, and what NOT to
DEFAULT = dict(headline=95, support=160)


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
