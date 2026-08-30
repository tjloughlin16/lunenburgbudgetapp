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
        tag='v5',
        date='2026-08-30',
        title='Every rate now carries the year it applies to',
        short='rates dated and corrected',
        headline='Athletic fees for FY26 were modelled at $250 a season when the district '
                 'had voted $325. Not a wrong number — a right number from the wrong year, '
                 'taken from a fee schedule that states its rates and never states which '
                 'year they cover. Every fee figure on the site has moved.',
        changes=[
            'A new page, Rates, fees and contracts, listing every rate this analysis knows '
            'about with the fiscal year it applies to, the document that set it and the '
            'date it was set. 62 rates; 37 of them checked against a spreadsheet cell or a '
            'direct quotation. It deliberately includes the ten rates we cannot state at '
            'all, because a fee the town charges and does not publish is a finding rather '
            'than a blank.',

            'The correction came from a School Committee vote nobody had connected to the '
            'model. On 26 February 2025 the committee approved athletic fees of $325 for '
            'high school and $275 for middle school, a 25% sibling discount, reduced fees '
            'of $50 and $40, and a $1,500 family cap. A fee voted in February 2025 applies '
            'to the following school year, which is FY26. The schedule the model was using '
            'was correct — for FY24 and FY25.',

            'Two figures that had been recorded as unexplained turn out to be the same '
            'error. $314.28 per high school participation is impossible under a $250 fee '
            'and unremarkable under $325; $233.60 per middle school participation is '
            'impossible under $200 and fine under $275. The model needed a 1.452x '
            'calibration constant to reconcile its own arithmetic with what the fund '
            'actually collected. That constant is now 1.132x, and the remaining gap is '
            'stated rather than absorbed.',

            'The note on athletic transportation said the line was "budgeted well above '
            'what athletics has ever actually spent". That was wrong, and it is the error '
            'this project is most careful about elsewhere: those figures are the town’s net '
            'appropriation, not what athletics spent. The district’s own workbook puts FY24 '
            'athletic transportation at $117,555.00 against a $40,000 line — budgeted BELOW '
            'the cost, with the revolving fund carrying the difference.',

            'Bus fees are published here for the first time, from the Superintendent’s own '
            'emails: $180 for one student, $270 for a family, with reduced and waived '
            'tiers. These are fees for getting to school, not to games. They matter to the '
            'budget because a bus fee nets down the general education transportation line — '
            'so that line can fall without any cost falling.',
        ],
    ),
    dict(
        tag='v4',
        date='2026-08-29',
        title='A ledger, and a site a machine can read',
        short='the athletics ledger',
        headline='Three years of the athletics revolving fund’s cashbook arrived from the '
                 'Town — the first complete fiscal years of ledger data this project has '
                 'held for anything touching school money. Every receipt and payment, with '
                 'a date.',
        changes=[
            'A new analysis, The athletics ledger, reading the fund’s cash for FY2024, '
            'FY2025 and FY2026. The years chain end to end against the opening balances '
            'the town itself prints. In FY2025, four general journal entries described only '
            'as an adjustment "per memo" account for $254,121.18 — 65% of everything that '
            'came into the fund that year. What they were for is not established, and the '
            'analysis says so rather than guessing.',

            'Figures that had been carried as unproven are now sourced. Athletic '
            'transportation cost $117,555.00 in FY24 and $91,066.06 in FY25, and both '
            'reproduce to the cent from a workbook the Town supplied. What changed is the '
            'provenance, not the arithmetic.',

            'A missing document now returns a real error instead of quietly showing the '
            'home page. Until this build, asking for a source document that was not there '
            'answered as though it were — so nothing, and nobody, could tell a document '
            'that exists from one that does not. For an archive whose promise is "here is '
            'our copy, check it yourself", that was the worst available failure.',

            'Every page now sends its content as HTML rather than building it in the '
            'browser. A reader with JavaScript sees no difference. A search engine, a link '
            'preview, or somebody pointing an assistant at a page to check a figure now '
            'gets the page instead of an empty shell.',
        ],
    ),
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

            'And the decision to hold out-of-district tuition flat now shows its working. '
            'It was reached three separate times from sources with nothing in common — '
            'eleven budgets, five years of actual spending, and the two halves of the line '
            'measured apart — and all three say the same thing: no rate describes it.',
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
