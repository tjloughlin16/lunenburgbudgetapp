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
        tag='v9.2.1',
        date='2026-09-03',
        title='The minutes search now says how much of the archive it searched',
        short='every document searchable, and the denominator published',
        headline='v9.2 made the archive searchable. Thirty-nine of its 1,422 documents '
                 'had no extracted text and so could not be searched, and nothing said '
                 'so — meaning a search that found nothing could not be told apart from '
                 'a subject nobody had raised. All 1,422 are now searchable, and the '
                 'count is published so a null result can be read for what it is.',
        changes=[
            'Every document the town has published is now searchable: 1,422 indexed '
            'against 1,422 published. /minutes/find/coverage.json states both numbers and '
            'lists anything that cannot be searched, so an empty result means "not said '
            'in the archive" rather than "not in the part of it we can read".',

            'One of the thirty-nine was School Committee minutes from the middle of '
            'FY2026. This project had already written, in a document addressed to the '
            'Town, that those minutes carried no readable text and that "probably nothing '
            'was moved" — inferred from the agenda. They record two transfers, and both '
            'tie to the town ledger to the dollar. The claim was an inference standing in '
            'for a document that could not be read.',

            'A search that cannot state what it covered produces a null result nobody can '
            'interpret. That is why the denominator is published beside the index rather '
            'than left for each reader to work out.',

            'No figure has moved and nothing a person reads has changed.',
        ],
    ),
    dict(
        tag='v9.2',
        date='2026-09-02',
        title='You can now find a word in two years of meetings without downloading them',
        short='search the minutes, three small fetches',
        headline='The archive holds 1,383 agendas and sets of minutes. Until now the only '
                 'way to search a board was to download the whole board — a megabyte for '
                 'the two people most often ask about — and there is now a word index that '
                 'points straight at the documents that mention it.',
        changes=[
            'Every word in the archive is indexed to the documents containing it. Look up '
            'the word, get back a short list of documents, read those. The documents '
            'average 4.5KB against a megabyte for a whole board, and the lookup itself is '
            'about 3KB.',

            'This was found the way these things usually are: an assistant asked when the '
            'School Committee discussed spending money on new jerseys could not read the '
            'bundle — "too big to read in one go" — and had no other way in. The index '
            'answers it in three fetches: a resident telling the committee on 24 June 2026 '
            'that field hockey is "using hand me down jerseys".',

            'The advice this site gave was itself the problem, and it is corrected in the '
            'three places it appeared. It said to fetch a board bundle and search it. That '
            'works for a caller that can hold a megabyte and fails for one that cannot, so '
            'both cases are now named, and the small path is given first.',

            'The index reports which documents contain a word. It does not rank them, does '
            'not do phrases, and does not know that two words mean the same thing — '
            'searching "jerseys" will not find a document that says only "uniforms". It '
            'says so itself, at /minutes/find/README.txt, because a search that quietly '
            'misses things is worse than one whose limits are stated.',

            'No figure has moved and nothing a person reads has changed.',
        ],
    ),
    dict(
        tag='v9.1',
        date='2026-09-02',
        title='The archive was described to assistants but not linked to them',
        short='every published address, as a link',
        headline='Every file this site publishes is now reachable by following links from '
                 'any page. It sounds like nothing and it was the whole reason assistants '
                 'kept reporting that this site does not hold the meeting minutes.',
        changes=[
            'An assistant asked to look up what a board discussed would read /llms.txt, '
            'find the exact file it needed named there, and then not fetch it. Assistants '
            'commonly refuse to request a URL that has not appeared in something they '
            'already loaded — a sensible protection, since it is what stops a fetched page '
            'from talking one into requesting somewhere else. /llms.txt is plain text, so '
            'the addresses in it were text rather than links, and authorised nothing.',

            'So the site described its archive thoroughly and linked almost none of it. '
            'Measured across all eighteen pages before this build: the School Committee '
            'bundle and the board index appeared in no link anywhere on the site, and the '
            'only /minutes link that existed pointed at a directory, which correctly '
            'returns an error. The one site-wide pointer at the meeting archive was a dead '
            'end.',

            'There is now a page — /agents — listing every published address as a link: '
            'all forty board bundles with their document counts, every data file, the API, '
            'and the archive itself. It is linked from the footer of every page, so '
            'anything that can read one page can reach all of it in two steps.',

            'The error page for a mistaken /minutes address now answers in HTML when the '
            'caller reads HTML. It said the right thing before and said it in plain text, '
            'which meant it told an assistant exactly what to fetch while leaving it unable '
            'to act on the answer.',

            'Nothing a person sees has changed, and no figure has moved. This is a fix to '
            'who can read what was already published.',
        ],
    ),
    dict(
        tag='v9',
        date='2026-09-02',
        title='The town’s own ledger, account by account — and a site an agent can use',
        short='the ledger, read line by line',
        headline='The Town Manager sent the FY26 books at account level, the first time '
                 'this project has held the school department as anything but a single '
                 'row. Two analyses read it, a data room shows what is still missing, and '
                 'the whole database is published and queryable.',
        changes=[
            'The FY26 year-to-date report arrived on 2 September at ACCOUNT level. Every '
            'previous copy was a department rollup, which renders the entire school '
            'district as one line. This one is 258 school accounts and 376 town accounts, '
            'each with what was appropriated, moved, spent and committed.',

            'Read this before quoting anything from it: the figures are period 12, June, '
            'with the books open. The Town Manager’s own framing is the right one — '
            '"current FY26 report, figures likely to continue to adjust as we continue '
            'the year-end reconciliation process." What can still move is bounded by what '
            'is encumbered: the school department’s final unspent figure lands between '
            '$482,101 and $718,885, the town’s between $858,462 and $1,141,003. Current, '
            'not final, and not doubtful either.',

            'The school department was $482,101 under budget — and that is a residue, not '
            'a result. It is $1,683,534 unspent across 160 accounts netted against '
            '$1,201,434 overspent across 56. The district spent 97.3% of what it was '
            'given. Reading the headline as half a million of slack describes the '
            'arithmetic correctly and the year not at all.',

            'One open question is set out at length and not resolved. The FY26 approved '
            'budget cut the kindergarten paraprofessional line and published it as a '
            '−100% cut, in those words, on page 7. $99,064 was then spent on kindergarten '
            'paraprofessionals with no appropriation and no transfer covering it, while '
            'six other zero-budget accounts did receive transfers. Three readings fit the '
            'record equally well and the analysis gives all three. It is not presented as '
            'an impropriety, and the document that would settle it — the year-end '
            'transfer schedule — is named.',

            'On the town side, snow removal cost $1,038,092 against an appropriation of '
            '$355,571, and the $185,000 Reserve Fund was never touched. $1,262,376 of '
            'school retiree health insurance sits in a town department and appears '
            'nowhere in the school budget, which is the first time this project has been '
            'able to point in the ledger at any of the gap between the state’s all-funds '
            'figure for Lunenburg and the appropriation.',

            'Reports and analyses is a new page. Twelve documents this project has '
            'written, each as a web page, a PDF and its source text with a checksum, most '
            'checked by a script that recomputes every figure from the database. It leads '
            'with the caveat rather than footnoting it: none of it is official, none of '
            'it has been reviewed or endorsed by the town or the district.',

            'The whole database is published. /data/lunenburg.db is every figure on the '
            'site in one SQLite file, and /api/index is the same thing as JSON with no '
            'key and no rate limit. /api/schema states the grain of every table and the '
            'four ways to get a confident wrong answer out of it.',

            'Two figures in llms.txt were wrong and were found by an outside agent, not '
            'by us. It gave the FY27 appropriation as the adopted budget while every page '
            'uses the figure after the September Special Town Meeting — $350,000 apart — '
            'and it labelled the FY28–FY30 average as the FY28 gap, which is $680,870. '
            'Both are fixed, both figures are now published with their definitions, and '
            'the build fails if either drifts from the model again.',

            'And /minutes/ used to answer 200 with the app shell. An agent asked to '
            'review the meeting minutes concluded the site did not serve them, while '
            '/minutes/school-committee.txt was serving 920KB of exactly what it wanted. '
            'It now returns a real 404 whose body names the three URL patterns that work. '
            'For a program that message is the only one it will ever read.',
        ],
    ),
    dict(
        tag='v8',
        date='2026-08-30',
        title='Show your work — every calculation, and every assumption behind it',
        short='the method, written out',
        headline='A single document sets out how every figure on this site is arrived at, '
                 'names each one as published, contractual, statutory, measured or ours, '
                 'and ranks every assumption by how much the answer moves if it is wrong.',
        changes=[
            'Show your work is written for the people who have to decide something with '
            'it — Finance Committee, Town Manager, Select Board, School Committee. '
            'Fifteen sections and two appendices: the projection worked through line by '
            'line, where each growth rate comes from, special education, out-of-district '
            'tuition, health insurance, free cash, athletic fees, the cut cascade, the tax '
            'base and overrides. Every section ends with what we assumed and what would '
            'settle it.',

            'It is generated from the model rather than written beside it, so it cannot '
            'drift from the figures the site publishes. A stale copy fails the build '
            'rather than being discovered by a reader.',

            'Section 12 is the one to read if you read nothing else: every assumption in '
            'the model, sorted by how much it moves the gap, with a plain statement of '
            'what backs each. Two of them are backed by nothing, and are labelled that '
            'way. State aid is assumed to grow at 2% and local receipts at 1%, and '
            'neither figure has a stated source or a derivation. State aid is worth '
            '$63,992 of FY28 gap for every point it moves — the second largest revenue '
            'lever in the model. Nothing about it has been changed; it has been named.',

            'The athletics sibling discount is no longer an assumption. It was 30% of '
            'participations, invented and supported by nothing — the School Committee '
            'vote of 26 February 2025 sets the discount RATE at 25% and says nothing '
            'about how many families receive it. The district’s own by-sport workbook '
            'records the fee category of every participation, and across 1,266 of them it '
            'is 9.5%. The average fee per participation moves from $366 to $390, and '
            'self-funding athletics with the buses put back moves from $730–$845 a season '
            'to $785–$855.',

            'That correction barely moved the revenue figures, and the reason is worth '
            'knowing: the fee model is anchored to what the athletics fund actually '
            'collected, so an input wrong by a factor of four was being absorbed by the '
            'adjustment sitting next to it. Nothing in the output looked wrong. The figure '
            'that did improve is the part of the fund’s income the published fee schedule '
            'cannot explain, which is now 6.73% rather than 13.2%.',

            'Two pages — free cash and the rate register — were shipping without the '
            'site’s layout: text ran to the edge of the window and headings rendered as '
            'body text. Both are rebuilt. And the rate register’s own introduction had '
            'gone stale in the way the register exists to prevent, describing the FY26 '
            'athletic fee error as costing "31% of modelled fee revenue" — true before '
            'the fee was corrected and of nothing since. It now states the understatement '
            'in the rate, derived from the register rather than typed.',

            'A published conclusion had been rendering the words "$None" where a figure '
            'should have been. No fee reaches the cost of the full athletics programme — '
            'revenue peaks near $373,322 at about $1,185 a season, against $451,830 — so '
            'the honest sentence is that it is unreachable at any price, and that is what '
            'it now says.',
        ],
    ),
    # Five builds shipped free cash over two days -- the state's proof, the draw-down page,
    # the override contrast, the standing policy, and what it costs capital. They are one
    # release note, not five. A reader coming back does not care which afternoon a piece of
    # it landed, and five entries describing one body of work is a commit log wearing a
    # release note's clothes -- which is the thing the docstring above says not to do.
    #
    # The five builds carried the tags v7 to v11. Collapsing the notes without collapsing
    # the numbering would have left the panel reading v11 then v6, so the tags went with
    # them: v7 through v10 were deleted and this build is tagged v7. What each retired tag
    # pointed at is recorded in notes/HANDOFF.md, because "tag what is live" is a rule here
    # and a deleted tag is a deleted answer to "which build is that".
    dict(
        tag='v7',
        date='2026-08-30',
        title='Free cash — what it is, what it would buy, and what it costs',
        short='free cash, end to end',
        headline='The state’s own free cash figures are published, the site can spend '
                 'them down to any level, and it now shows which capital projects stop '
                 'when you do.',
        changes=[
            'The Division of Local Services free cash proof for Lunenburg and eight '
            'comparable towns, 2021 to 2025, is in the archive with the line-by-line '
            'calculation and 81 reconciliations that all tie to the dollar. Lunenburg '
            'certified a record $3,354,370 this year — 6.55% of the operating budget '
            'on our figures, 6.65% on the Town’s.',

            'Two claims are argued about locally and both are true about different '
            'windows: this is a record year, and the town was below the recommendation in '
            'seven of the last ten. The Town’s own budget release contains both.',

            'The standard being invoked is single-sourced. 5–7% appears in one '
            'document in the archive — the Town’s press release, quoting DLS. We '
            'hold no DLS publication saying it, and the threshold decides the answer, so '
            'it travels with that caveat wherever it is used.',

            'A normal year does not refill it. The record exists because unspent '
            'appropriations were $2,457,761 against a four-year average of $986,340 — '
            '2.49 times, the largest jump of nine towns. Put that one line back at its own '
            'average and the town certifies 3.96%, below the bottom of the band.',

            'A page and a control that draw the balance down to any level, off until you '
            'switch them on. Drawing to the 5% floor releases $794,872, which covers FY28 '
            'and nothing after it — and the ladder goes below the floor to zero, '
            'because "what if we spent it all" is the question people actually ask.',

            'The level you hold barely matters; the policy does. Appropriating the annual '
            'flow every year takes the six-year gap from $15.2 million to $5.1 million, '
            'and that figure does not depend on the target balance at all — which is '
            'the opposite of how the argument is usually made.',

            'Free cash and an override are opposites, and the contrast is the clearest '
            'statement this site has. The same $794,872 defers one year as free cash and '
            'is worth $4,396,563 more over six as an override. Neither closes the gap: '
            'both grow slower than the cost of running the schools.',

            'Free cash is the capital programme’s money — it funded $655,424 of '
            'last year’s $1,225,000 capital plan, so the $794,872 ceiling is more '
            'than that whole year’s contribution, as it is in seven of the ten years '
            'the plan publishes. A third of the FY27 programme is restricted stabilization '
            'money that could never have gone to the schools.',

            'What that costs in projects is a range, not a number, and you can now settle '
            'it yourself. A button opens the capital plan with what stops struck through; '
            'Build your own budget lets you defer projects by hand, and adds the money '
            'straight back in FY29, because that is what one-time money does.',

            'And the catch, which is the whole argument. That flow is produced by the '
            'over-appropriating a tighter budget would remove: two thirds of the balance '
            'is money voted and never spent. Budget more tightly and the gap shrinks, but '
            'so does the free cash you were going to close it with. You cannot bank on '
            'both.',

            'Five builds over two days carried this work, and they are one entry here '
            'rather than five. The version numbering was closed up to match, so this is '
            'v7 rather than v11.',
        ],
    ),
    dict(
        tag='v6',
        date='2026-08-30',
        title='Every public meeting, in full, and a site an assistant can actually use',
        short='the meeting archive, published',
        headline='Two years of every town board’s agendas and minutes — 1,383 '
                 'documents across 40 boards — are published as full text. It is where '
                 'the town argues, and none of it is in a budget document.',
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
        headline='Athletic fees for FY26 were modelled at $250 when the district had '
                 'voted $325: a right number from the wrong year. Every fee figure on '
                 'the site has moved.',
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
        headline='Three years of the athletics revolving fund’s cashbook arrived from '
                 'the Town — the first complete years of ledger data this project has '
                 'held for school money.',
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
                 'escalated at the teachers’ contract rate. It now has its own section '
                 'and its own measured rate.',
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
                 'document is here to download.',
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
        headline='The original build: the FY28 gap, the cut cascade, the levers and '
                 'the override arithmetic.',
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
