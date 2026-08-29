"""What changed between public builds, and when.

Somebody who read this site in August and comes back in October is owed one sentence
telling them what to read differently. Without it every returning reader has to diff the
site against their memory of it, and the ones who do that badly are the ones who quote a
figure that has since moved.

Two rules this file exists to keep:

**A release note describes what a reader should interpret differently.** Not what was
committed. "The archive grew" is a changelog entry; "every figure now names the document
it came from, and you can download that document" is a release note. If a change does not
alter what somebody should believe or check, it does not belong here.

**Numbers here are written, not computed, and that is a deliberate exception.** A release
note is a historical claim about a build that has already shipped -- interpolating today's
model into it would silently rewrite the past every time a rate moved. Everything else in
this project derives its figures; this file must not, and any figure typed here has to be
true of the build it describes rather than of the current one.

The newest entry is the current build. `CURRENT` is the tag `scripts/` and the footer
read, and it has to match the git tag actually deployed.
"""

RELEASES = [
    dict(
        tag='v3',
        date='2026-08-28',
        title='Special education, separated out and measured',
        short='special education measured',
        headline='About a fifth of the school budget was folded in with salaries and '
                 'escalated at the teachers’ contract rate. It now has its own section, '
                 'and a rate measured across eight to eleven of the district’s own '
                 'budgets rather than taken from a contract.',
        changes=[
            'A section on Bend the Curve, and two findings on the front page. The '
            'district’s published cost increase for next year is 3.98%. Inside it, '
            'out-of-district tuition falls 46% in a single year — a one-time drop, '
            'not a slower rate of growth. Hold that line where FY26 had it and the same '
            'budget rises 6.23%. That is the rate to plan against.',

            'A contract sets what one person is paid. It says nothing about how many '
            'people are employed — and on this line, that is where the movement is. '
            'Special education paras are on an agreement giving 2.0% a year and their '
            'budget has grown 12.78% for 10 budgets. Teachers are on one giving 3.5% and '
            'theirs has grown 2.67%. Both bargained, both wrong, in opposite directions.',

            'Out-of-district tuition is no longer escalated at all. Eleven budgets run '
            'from $489,918 to $1,291,293 with no direction — the compound rate swings '
            'from -46% to +12% depending only on which year you start counting. '
            'There is no rate to measure, so the line is held flat and what it would cost '
            'to be wrong is published as a table of priced scenarios.',

            'Every budget line counted as special education is now listed, with the reason '
            'each was counted, because the state has no account code for it and the total '
            'is therefore ours. Publishing that list found English Language Learner costs '
            'inside it, which are now removed.',

            'The rate this line carries has changed four times in a day, and every version '
            'is on the page with the reason it was wrong. A number whose history you '
            'cannot see is one you have to take on trust.',
        ],
    ),
    dict(
        tag='v2',
        date='2026-08-28',
        title='Every figure is sourced, and every source is published',
        # Three or four words, shown in the bar at the top of every page. It shares that
        # line with a date and a link, so anything longer wraps on a phone and the bar
        # becomes two rows of furniture above the actual page.
        short='sources now published',
        # The longer form, shown in the dialog. Says what to do differently rather than
        # what we did.
        headline='Every headline figure now names the document it came from, and that '
                 'document is here to download. If you checked a number before and could '
                 'not see where it came from, you can now.',
        changes=[
            'A sources page listing every document this analysis reads. Each one is '
            'downloadable, and the archive is split three ways: published by the town, '
            'the district and the state; held for reference but feeding no figure; and '
            'written by this project. The third section is the one to read skeptically.',

            'Citation markers beside the figures themselves, saying for each whether it '
            'was published by somebody, set by contract, fixed by statute, or estimated '
            'by us. The estimates are marked as estimates wherever they appear.',

            'The district’s budget page and the town’s finance pages mirrored in '
            'full, back to FY18, so a document nobody kept is still checkable. Most of it '
            'feeds nothing on this site and is labeled that way.',

            'Machine-readable copies of the model, the sources index and the budget lines, '
            'announced at /llms.txt, so anybody checking this with a tool of their own '
            'does not have to scrape the pages.',
        ],
    ),
    dict(
        tag='v1',
        date='2026-08-27',
        title='The projection, first published',
        short='first public build',
        headline='The original build: the FY28 gap, the cut cascade, the levers and the '
                 'override arithmetic.',
        changes=[
            'The five-year projection from the FY27 adopted budget, the priority cascade, '
            'the fee and administration levers, and the tax-base pages.',
            'Figures were stated without saying which document each came from. That is '
            'what v2 fixes.',
        ],
    ),
]

CURRENT = RELEASES[0]['tag']
UPDATED = RELEASES[0]['date']


def export():
    """Shape the app reads. Newest first; the app never reorders it."""
    return dict(current=CURRENT, updated=UPDATED, items=RELEASES)


if __name__ == '__main__':
    for r in RELEASES:
        print(f"{r['tag']}  {r['date']}  {r['title']}")
        print(f"    {r['headline']}")
        for c in r['changes']:
            print(f"      - {c[:96]}")
