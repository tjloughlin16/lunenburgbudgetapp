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
        tag='v11',
        date='2026-08-30',
        title='What redirecting free cash actually costs the capital programme',
        short='the capital consequence, honestly',
        headline='Free cash is the capital programme’s largest source, so redirecting it '
                 'to the schools stops capital work. How much is arithmetic; WHICH '
                 'projects stop is a guess about a committee, and the site was reporting '
                 'the guess as though it were the arithmetic. Both ends are now given, a '
                 'third of the programme turns out not to be school money at all, and you '
                 'can defer projects yourself and watch the gap move.',
        changes=[
            'A third of the FY27 capital programme could never have gone to the schools. '
            '$594,000 of the $1,830,203 is the Vehicle Use Special Purpose Stabilization '
            'Fund, restricted to vehicles and equipment — the plan footnotes two projects '
            'as funded from it and they sum to exactly that figure. Not spending it there '
            'releases it to nothing. A redirect can reach $1,236,203, and the earlier '
            'version of this stranded a $259,000 front end loader with free cash that '
            'never paid for it.',

            'What a redirect costs capital is now given as a range rather than a number. '
            'Taken strictly off the bottom of the committee’s own ranking, $300,000 '
            'removed stops $693,949 of work, because rank 7 is a $494,500 roof and only '
            '$199,449 of items sit below it. Re-sequenced against the $1,437,005 of ranked '
            'work already unfunded, the same $300,000 stops $301,703. Nothing published '
            'says which the committee would do, and the site no longer picks.',

            'A button on the free cash control opens the capital plan itself: all 22 '
            'ranked projects, what stops at the amount you have chosen, and what is '
            'already below the line. It is the strict reading, so a reader can check it '
            'against the published plan line by line, with the other reading beside it.',

            'On Build your own budget, a new section for money you can only spend once. '
            'Defer capital projects by hand and the released money goes against FY28 — '
            'then comes straight back in FY29, because that is what one-time money does. '
            'The restricted projects are shown and cannot be picked.',

            'The headline free cash card now says where the money already is: free cash '
            'funded $655,424 of last year’s $1,225,000 capital plan, so the $794,872 '
            'ceiling is more than the whole of that year’s contribution — as it is in '
            'seven of the ten years the plan publishes.',

            'Two years missing from our capital funding extract, FY2019 and FY2020, are '
            'restored. With them the extract reproduces both of the capital plan’s own '
            'printed averages to the cent, and the model now refuses to publish if either '
            'stops tying.',

            'Release notes are collapsed by default, including this one. The panel was a '
            'wall of changes; it is now one sentence each until you ask for more.',
        ],
    ),
    dict(
        tag='v10',
        date='2026-08-30',
        title='Free cash as a standing policy — and why the level you hold barely matters',
        short='free cash as a lever',
        headline='"Be less conservative" is a policy, not a windfall. Modelled as one, it '
                 'is worth about $10 million of the next six years’ gap — and the balance '
                 'you choose to hold makes almost no difference to that. What matters is '
                 'appropriating the flow every year, and the flow is produced by the '
                 'over-appropriating a tighter budget would remove.',
        changes=[
            'A new lever, off by default and available on the free cash page and in the '
            'assumptions panel: appropriate this much free cash every year rather than '
            'accumulating it. The slider steps through the recommended band — above it, '
            'top, middle, bottom — then below it and down to holding nothing at all.',

            'Holding a lower balance turns out to be a one-off worth surprisingly little. '
            'Moving from 6.55% to the bottom of the band releases $794,872, once, and '
            'going lower than that releases more on paper and achieves nothing, because no '
            'year can absorb more free cash than its own gap and FY28’s gap is $680,870.',

            'Appropriating the annual flow is the policy, and it is worth far more: it '
            'takes the six-year gap from $15.2 million to $5.1 million. It also does not '
            'depend on the level you hold at all, which is the opposite of how the argument '
            'is usually made. A lower target does not generate more money.',

            'And the catch is the whole argument. That flow is about $2.0 million a year, '
            'which is 3.96% of the budget — below the bottom of the recommended band — and '
            'two thirds of it is money appropriated and never spent. Budget more tightly '
            'and the gap shrinks, but so does the free cash you were going to close it '
            'with. You cannot bank on both.',
        ],
    ),
    dict(
        tag='v9',
        date='2026-08-30',
        title='Free cash against an override — the same dollars, opposite effects',
        short='free cash vs override',
        headline='Spending free cash and passing an override are not the same thing. The '
                 'same $794,872 defers one year as free cash and is worth $4,396,563 more '
                 'over six as an override — and neither closes the gap, because both grow '
                 'slower than the cost of running the schools.',
        changes=[
            'The free cash page can now apply the money to the projected gap, and it is '
            'OFF until you switch it on. Nothing anywhere else on this site changes: the '
            'projection is built without free cash, and the figure it produces is '
            'unchanged whether the switch is on or off.',

            'Side by side with an override of the same size. Free cash closes FY28 and '
            'nothing after. An override lifts the levy limit permanently and the schools '
            'keep it every year, growing at the 2.5% cap. Over six years the override is '
            'worth $4,396,563 more from identical dollars.',

            'And the row that matters is the last one, not the total. Even the override '
            'leaves $3,740,932 of gap in FY33 and the shortfall grows every year, because '
            'an override rises at 2.5% and the cost of the schools rises faster. Permanent '
            'money loses ground more slowly than one-time money, and still loses ground.',
        ],
    ),
    dict(
        tag='v8',
        date='2026-08-30',
        title='Free cash, and what spending it would actually buy',
        short='free cash modelled',
        headline='A new page lets you draw the town’s free cash down to any level and see '
                 'what it covers. Emptying the reserve entirely — which nobody proposes — '
                 'defers the school budget gap two years and leaves the town with nothing.',
        changes=[
            'The state’s certified free cash for Lunenburg and eight comparable towns, 2021 '
            'to 2025, is published with the line-by-line calculation behind it. Lunenburg '
            'certified a record $3,354,370 for this year, 6.55% of the operating budget on '
            'our figures and 6.65% on the Town’s.',

            'Two claims are argued about locally — that the town is too conservative, and '
            'that free cash is not up to standard so the town is rebuilding. The Town’s own '
            'budget release contains both and both are true: a record year, and below the '
            'recommendation in seven of the last ten. They describe different windows.',

            'What the data adds is that a normal year does not refill it. The record exists '
            'because unspent appropriations were $2,457,761 against a four-year average of '
            '$986,340 — 2.49 times, the largest jump of nine towns, while two of them fell. '
            'Put that one line back at its own average and the town certifies 3.96%, below '
            'the bottom of the band it is measured against.',

            'And free cash cannot bend the curve. It is one-time money: a level, not a rate. '
            'Drawing down to the 5% floor releases $794,872, which covers FY28 and nothing '
            'after it. The page shows the whole ladder, including below the floor, because '
            '"what if we spent it all" is the question people actually ask.',
        ],
    ),
    dict(
        tag='v7',
        date='2026-08-30',
        title='Free cash, and what it can and cannot tell you',
        short='free cash, nine towns',
        headline='Two claims are being made about the same number — that the town is too '
                 'conservative with free cash, and that its free cash is not up to standard '
                 'and is being rebuilt. The state’s own calculation for Lunenburg and eight '
                 'comparable towns is now published. It does not settle the argument, and '
                 'the analysis says why in its first paragraph.',
        changes=[
            'The Division of Local Services publishes a free cash proof for every '
            'community — the year-end calculation of what a town may appropriate without '
            'raising taxes. Lunenburg’s and eight neighbours’, 2021 to 2025, are now in the '
            'archive with the line-by-line detail. They reconcile to themselves twice over, '
            'in 81 checks that all tie to the dollar.',

            'The disagreement cannot be settled from them, because a standard for free cash '
            'is a ratio and these files are a numerator. There is no population, budget or '
            'revenue figure anywhere in them. Lunenburg’s balance can be set against '
            'Lunenburg’s own budget — 6.51% of a $51,531,199 general fund — but not against '
            'any neighbour’s, and the standard being invoked is in a document this project '
            'has not read: the town’s own Financial Policies Manual.',

            'What the figures do show is the shape, and the shape has moved. Two thirds of '
            'Lunenburg’s 2025 free cash is money that was appropriated and never spent — '
            '$2,457,761, against $1,225,720 from revenue coming in above estimate. That '
            'share was 31% in 2023. A balance built from underspending is a different thing '
            'from one built from revenue beating forecast, and the two imply different '
            'remedies.',

            'None of that means waste, and none of it is the schools: every town turns money '
            'back, and this is a town-wide figure across all 67 departments with no '
            'breakdown published. Which departments turned back the money, and whether it is '
            'the same ones each year, is the difference between a pattern and a run of '
            'one-offs.',
        ],
    ),
    dict(
        tag='v6',
        date='2026-08-30',
        title='Every public meeting, in full, and a site an assistant can actually use',
        short='the meeting archive, published',
        headline='Two years of every town board’s agendas and minutes — 1,383 documents '
                 'across 40 boards — are now published as full text rather than as an index '
                 'of dates. Zoning, conservation, health, planning, cemeteries, the library, '
                 'housing, the schools. It is where the town argues, and none of it appears '
                 'in a budget document.',
        changes=[
            'The text of every agenda and set of minutes is readable and downloadable. '
            'Until this build the site published only an index pointing at the town’s '
            'scanned PDFs, which meant that somebody searching this site for what the '
            'School Committee said about a contract, or what the Zoning Board decided about '
            'a property, found nothing and reasonably concluded it was not here.',

            'Each board is also published as a single file — the whole School Committee in '
            'one 0.9MB document — because you cannot search a website but you can read one '
            'file. Every document inside carries its own permanent address, so anything '
            'found there can be cited to the document rather than to the bundle.',

            'The site now states, on every page, what it holds and which file answers which '
            'question. That is for anybody pointing an AI assistant at it: the assistant '
            'gets the inventory, the download addresses, and the one warning that matters — '
            'that this archive holds both what the town budgeted and what it spent, and '
            'mixing them produces a confident wrong answer.',

            'It also says plainly that this is not only a budget site. An assistant told '
            'otherwise will answer "this cannot help you" to a question about zoning or '
            'conservation that the archive answers completely.',
        ],
    ),
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
