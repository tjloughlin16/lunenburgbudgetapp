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
