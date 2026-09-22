"""Publish the index of analyses this project has written.

    python3 scripts/build_reports_index.py

Writes `fy28/public/data/reports.json`, which the /reports page renders.

TWO KINDS OF ANALYSIS, AND FOR MONTHS THIS SAW ONLY ONE

Every analysis used to be a Markdown document, so scanning `sources/analyses/` scanned
everything and the comment on `AREA_HOME` in routes.ts could say /reports "is the generated
index of every analysis on disk". Then eight analyses were built as React pages in a single
day, and the sentence stopped being true without anything failing: /reports is the front
door of the whole Analyses area and it listed the documents and none of the pages.

So this reads BOTH, and from the tables that decide them rather than from a list kept
beside them:

  - the DOCUMENTS from `sources/analyses/*.md`, as before;
  - the PAGES from `AREA_TABS.analyses` in `fy28/src/routes.ts` -- the same table the app's
    own navigation is drawn from -- joined to the page component that declares that tab.

`--check` fails if either goes missing, which is the promise that comment was making.

WHY A PAGE OF ITS OWN

These documents were buried as one group inside the source catalogue, between the town's
mirrored PDFs and the district's spreadsheets. That is the wrong shelf. Everything else in
that catalogue was written by somebody else and is republished here unchanged; these were
written HERE, and the distinction is the single most important thing a reader needs.

So the page leads with the caveat rather than footnoting it, and every row carries the
three things that make a claim checkable: the document, the data underneath it, and the
script that recomputes every figure in it.

Generated rather than maintained. A hand-written index of one's own analyses is exactly
the artefact that goes stale first and is least likely to be noticed doing it.
"""
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'sources', 'analyses')
PDF = os.path.join(ROOT, 'fy28', 'public', 'docs', 'analyses')
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'reports.json')
SITE = 'https://lunenburgbudgetproject.org'

# Order the reader should meet them in, not alphabetical. Anything not listed is appended
# in alphabetical order rather than dropped -- a new analysis appears without being added
# here, and appears in the wrong place, which is a visible prompt to order it.
ORDER = [
    'fy26-closeout', 'fy26-closeout-town', 'budget-vs-actual', 'free-cash',
    'stabilization-option',
    'athletics', 'athletics-ledger', 'sped-and-the-curve', 'sped-and-funds',
    'fy27-and-the-override', 'fy27-cut-reconciliation', 'per-pupil-spending',
    'peer-districts', 'spending-compared', 'stabilization-funds',
    'hiring-here-or-placing-there',
    'connecting-the-budget', 'show-your-work',
]

# --- how a READER groups these, which is not how we built them ----------------------
#
# The index was split into "routed reports" and "written analyses", which is a fact about
# our implementation and nothing a resident cares about. It also DUPLICATED subjects:
# Monty Tech appeared twice and special education three times, because each has both a
# page and a document. TJ, seeing it: "monty tech being in the 'written' section seems
# wrong. I think a breakdown of school vs town to start is good, then subcategories
# might help."
#
# So: grouped by SUBJECT, and one entry per subject. Where a page and a document cover
# the same ground the PAGE wins and the document is offered from it, because the page is
# current, computed on every build, and the document is what it was written from.
#
# THE LEVERS on a shelf of their own first (TJ, 17 September 2026); SCHOOL next, because
# that is where the money and the argument are; TOWN after; the live pages and METHOD
# last, for the reader who has a reason to check rather than a question to answer.
CATEGORIES = [
    # THE LEVERS, ON A SHELF OF THEIR OWN, FIRST. TJ, 16 September 2026: "we need
    # individual reports for the big concepts in the budget crisis" -- and, 17 September:
    # they "are not to go under the Town page, and need to be moved independently higher
    # up the page ... in some special section". They are the two things the town can
    # actually do about the gap, and a reader who came from the crisis page is looking
    # for exactly these before any filing question.
    # THE HEADING IS A NOUN, NOT A SENTENCE. TJ, 21 September 2026, on "What the
    # town can do": *"the sentence is not memborable"*. It is the same correction
    # that renamed every page on this shelf -- "having sentences as page links is
    # not a good model at all ... I want people to say 'go to lburg.org and go to
    # health insurance or fees'" -- arriving one level up, at the shelf those
    # pages sit on. A predicate cannot be said or pointed at; a noun phrase can,
    # and the other three headings here are already nouns, so this one read as the
    # odd one out as well as the long one.
    #
    # `Solution options` is TJ's phrase and it is the right one for the shelf: it
    # says these are OPTIONS -- things that could be done -- without saying which
    # to do, which is rule 8 exactly. `The levers` was tried first and is this
    # project's internal word for them; a reader is not inside the project.
    #
    # The report that used to hold this name is now `The stabilization option`,
    # since a shelf and an item on it cannot be called the same thing.
    ('levers', 'Solution options', [
        # In the order a resident weighs them: the two that move the revenue side, the
        # two that move the cost RATE, then the amounts -- free cash, fees, the extras --
        # and last the one every other page exists to avoid.
        # `stabilization-option` sits directly after free cash because it is the same
        # KIND of lever and fails the same way: money the town has ONCE, set
        # against a cost it has EVERY year. TJ, 21 September 2026: "i expected
        # that page to go under 'What the town can do'". It had been filed under
        # the town's ledger beside the report it is the companion to -- which is
        # where it was WRITTEN, not where a reader looking for what can be done
        # would go, and this index exists to tell those two apart.
        ('', ['override', 'growth', 'healthlever', 'salarylever', 'freecashlever',
              'stabilization-option', 'feelever', 'extraslever', 'positionslever']),
    ]),
    # A SHELF WITH ONE THING ON IT, FIRST, AND THE ARGUMENT FOR IT.
    #
    # Every other shelf here answers "is this about the schools, the town, the rules or
    # the method" -- a filing question, which a reader can only ask once they know what
    # they want. /blog is the entry for a reader who does not: one finding at a time, two
    # minutes each, every one opening onto the report that computed it. Filing it under one
    # of the four would promise a subject, and it has no subject; it has all of them.
    #
    # It is first for the reason rule 7a gives: it needs no budget knowledge to read, and
    # a reader who has arrived at an INDEX and does not know which report they want is
    # exactly the reader it was built for. It is not in UNCATEGORISED with `addsup` and
    # `show-your-work` because those two are about the reports; this is a way IN to them.
    ('school', 'The schools', [
        ('what the money buys', [
            'sped', 'circuitbreaker', 'courses', 'ap', 'cuts', 'sportsmoney', 'stopped', 'unwind',
            'insurance',
            'athletics-ledger',
        ]),
        # TJ, 10 September 2026: this belongs "under The Schools, and just above 'the
        # students'". It had been a top-level shelf of its own, and the correction is
        # right for a reason the shelf version missed: a reader browsing the schools is
        # already in the place where "who works in them" is the obvious next question.
        # A top-level shelf made it a peer of "The town", which it is not — it is one
        # aspect of the schools, and the order adults-then-children reads the way a
        # person would ask it.
        ('who works in them', [
            'staffing', 'schoolstaff', 'parastaff',
        ]),
        ('the students', [
            'enrollment', 'attrition', 'outflow', 'montytech', 'leaving', 'families',
        ]),
        ('where the money comes from, and how it compares', [
            'minaid', 'required', 'peers', 'spending-compared', 'variance',
        ]),
        # THE RULES EVERYONE ARGUES UNDER, as a subsection here rather than a shelf of
        # their own. TJ, 17 September 2026: "should go under the schools as a subsection".
        # The note that used to introduce a fourth shelf still holds for what these ARE
        # -- a state rule quoted and explained, stopping before any Lunenburg finding --
        # and the index now says so in the subsection title rather than by distance.
        # THE FIELDS AND THE LEAGUES THAT PAY THE SCHOOLS. TJ, 17 September 2026: "it's
        # not a town thing for this report ... the point of that report is the ones that
        # pay the schools. others pay Parks and Rec." So it shelves with the schools; a
        # Parks and Recreation counterpart would be the town's.
        ('the fields, and the funds that run them', ['youthsports']),
        ('every fund and line the School Committee owns', ['schoolfinance']),
        ('the rules everyone argues under', ['classsize', 'formula']),
    ]),
    ('town', 'The town', [
        # WHO LIVES HERE, FIRST, and above the ledger on purpose. Every other report on
        # this shelf measures the town's money; this one measures the town. A reader who
        # does not yet know the place cannot weigh anything below it, and it is the one
        # report in the index that needs no budget knowledge at all to read.
        ('who lives here', ['bythenumbers', 'owners', 'homestudents']),
        ('the ledger, read', [
            'fy26-closeout', 'fy26-closeout-town', 'free-cash', 'stabilization-funds',
        ]),
        ('what the votes decided', [
            'fy27-and-the-override', 'fy27-cut-reconciliation',
        ]),
        # THE BOARDS THEMSELVES, as a subject. TJ, 17 September 2026: "a sort of 'board
        # analysis' page" -- what each board posts, measured on the town's own site.
        ('the boards, compared', ['boardcompare', 'board-composition', 'open-seats']),
        # A DEPARTMENT, READ WHOLE. TJ, 17 September 2026: "a report for parks, under 'the
        # town' for whatever data you got."
        ('a department, whole: parks and recreation', ['parks']),
    ]),
    # A FOURTH SHELF, AND THE ARGUMENT FOR IT.
    #
    # The first three answer "is this about the schools, the town, or how to check it",
    # and every report fits one because every report MEASURES Lunenburg. The class-size
    # rule does not. It quotes a state regulation that binds every district in
    # Massachusetts, and its whole discipline is that it stops before saying anything
    # about this town's staffing -- so filing it under "the schools / what the money buys"
    # would promise a Lunenburg finding the page deliberately refuses to make, and a
    # reader who opened it expecting one would leave thinking the page had failed.
    #
    # TJ asked for a new section and this is why one is right rather than merely asked
    # for: a rule everybody argues under is a different KIND of document from a
    # measurement, and the index is the one place a reader learns which they are getting.
    #
    # The shelf is expected to fill. Chapter 70's formula, the net school spending
    # requirement and Proposition 2 1/2's levy limit are all rules this town argues under
    # and all currently sit under headings about where money comes from -- which is right
    # for them TODAY, because each of those pages measures Lunenburg against the rule.
    # Nothing is moved here: an address that has been shared once keeps landing where it
    # landed, and a category is not a reason to move a page.
    # `formula` is the second entry on this shelf and it is the case the note above
    # forecast. It explains Chapter 70 — a statute that binds every district in
    # Massachusetts — in eight plain steps, and its discipline is that it stops at the
    # mechanism. `minaid` stays under "where the money comes from" because that page
    # MEASURES Lunenburg against the rule; this one explains the rule. Two pages, two
    # shelves, and neither is moved.
    # THE LIVE PAGES, LAST. Neither the blog nor the week is an analysis; both were at
    # the top of this index and TJ, 17 September 2026, found them "very misplaced" there.
    # They stay listed so the index is complete, at the end, under a heading that says
    # what they are.
    # BUDGETS ACROSS TOWN. TJ asked for this shelf by name: "We may need a new section on
    # the reports page for 'Budgets Across Town' and show each department, plus an
    # individual report that crosses across all deparmtents and draws overall insights."
    #
    # The cross-department report goes FIRST and alone, because it is the one that answers
    # the question people arrive with and the twelve beneath it are reference. A reader who
    # opens `Public Works` first learns what Public Works was voted; a reader who opens the
    # cross-department report first learns that ten of twelve departments outgrew the levy
    # cap, which is the thing that changes how they read all twelve.
    #
    # The departments are listed in the town's own printed order rather than by size or by
    # pull. Ranking them here would make the shelf an argument, and the ranking already
    # has a page of its own directly above it.
    ('townbudgets', 'Budgets across town', [
        ('', ['town-budgets']),
        # PERSONNEL SITS ON THIS SHELF and not on a shelf of its own, because it is here
        # to answer a question the budget pages raise and cannot answer: a line that falls
        # is not a cut, and a cut is a service reduction. Filed anywhere else, a reader who
        # has just seen twelve departments' dollars would never meet the one page that
        # says what those departments are made of.
        ('', ['town-personnel']),
        ('Department by department, as Town Meeting voted it',
         ['town-budget-maturing-debt', 'town-budget-unclassified', 'town-budget-general-government', 'town-budget-central-purchasing', 'town-budget-protection', 'town-budget-health-sanitation', 'town-budget-public-works', 'town-budget-facilities-grounds', 'town-budget-solid-waste', 'town-budget-assistance', 'town-budget-schools', 'town-budget-library']),
    ]),
    ('live', 'Not reports — the pages that change every day', [
        ('', ['blog', 'budgetfeed', 'thisweek', 'boards', 'recorded']),
    ]),
    ('method', 'How to check any of it', [
        ('', ['connecting-the-budget', 'what-you-can-ask', 'questions']),
    ]),
]

# A page and a document covering the same subject. The page is what the index offers.
SUPERSEDED = {
    'monty-tech': 'montytech',
    'sped-and-the-curve': 'sped',
    'sped-and-funds': 'sped',
    'per-pupil-spending': 'peers',
    'peer-districts': 'peers',
    # Same subject as per-pupil-spending and dependent on it: that report establishes the
    # rank, this one turns the rank into what closing it would cost.
    'spending-compared': 'peers',
    # The ledger read for what the town HOLDS rather than what it spent, so it belongs
    # beside free cash rather than under the schools -- these are town reserves, and only
    # one of them could lawfully reach a school deficit.
    'stabilization-funds': 'free-cash',
    # A SCOPING NOTE rather than a finished analysis, and filed under special education
    # because that is its subject. It reaches no conclusion by design: it records why the
    # in-district-staffing-against-placements question cannot be modelled from anything
    # published, and what would be needed.
    'hiring-here-or-placing-there': 'sped',
    'athletics': 'sportsmoney',
    'budget-vs-actual': 'variance',
}

# `show-your-work` is deliberately in no category: the page gives it a section of its own,
# last, because it is the document that makes every figure on every other report checkable
# rather than another report about money.
#
# `addsup` (/what-it-all-adds-up-to) is likewise outside the grouping, at the other end:
# it is the synthesis of what every other report concludes, so it belongs ABOVE the
# categories rather than inside one. The page renders it first and on its own.
#
# `threads` is outside it for a third reason: it reports the STATE of matters still being
# argued across the boards, not a conclusion about one subject. Filing it under a category
# would claim the town has settled something it has not, and filing it under all of them
# is what a tracker already does.
UNCATEGORISED = {'show-your-work', 'addsup', 'threads'}

# One line on what each answers. Editorial, so written here rather than derived -- but
# every one is checked against the document's own opening below.
ABOUT = {
    'open-seats':
        'Which of the town’s boards and committees has a seat going spare, and when the '
        'filled ones come up. A list rather than a report: the one page here somebody '
        'reads and then does something about. Regenerated by the daily refresh.',
    'board-composition':
        'How the town’s boards are made up — which are biggest, how fast each turns over, '
        'and whether the establishment is growing. The seats barely move; about a third '
        'of the people in them change every year.',
    'town-personnel':
        'Every elected seat, appointed board seat and appointed officer the town prints '
        'in its annual report, FY2022 to FY2025. Two thirds of the posts are unpaid seats '
        'on boards. It is not a headcount of town employees, and it says so: the wage '
        'list that would give one stopped naming departments after FY2016.',
    'town-budgets':
        'What Town Meeting voted for each of the twelve town departments, and which '
        'of them actually move the total. It refuses the question it is most often '
        'asked — an omnibus budget cannot show a deficit, because a town may not vote '
        'one — and answers the useful version: ten of twelve departments grew faster '
        'than the levy cap, and the biggest line is not the fastest.',
    'town-budget-maturing-debt':
        "The town’s debt service — the only line in the voted budget that falls, and it falls by a third in three years. Where that room went is the cross-department report’s question, not this page’s. "
        "Every budget line the town prints beneath it, FY2023 to FY2025, reconciled "
        "against the department total on the same page.",
    'town-budget-unclassified':
        "Printed `Gen Gov Unclassified`, and seven tenths of it is group health insurance. The fastest-growing large line in the budget, and the one that moves the total more than the schools do. "
        "Every budget line the town prints beneath it, FY2023 to FY2025, reconciled "
        "against the department total on the same page.",
    'town-budget-general-government':
        "The town’s own administration — the Select Board, the Town Manager, the Accountant, the Clerk, the Assessors, IT and legal. "
        "Every budget line the town prints beneath it, FY2023 to FY2025, reconciled "
        "against the department total on the same page.",
    'town-budget-central-purchasing':
        "The smallest line in the budget and the flattest. It is here because a department that does not move is a finding about the ones that do. "
        "Every budget line the town prints beneath it, FY2023 to FY2025, reconciled "
        "against the department total on the same page.",
    'town-budget-protection':
        "Police, Fire, Radio Watch and the inspectors, each with its own printed subtotal beneath the department total. "
        "Every budget line the town prints beneath it, FY2023 to FY2025, reconciled "
        "against the department total on the same page.",
    'town-budget-health-sanitation':
        "Board of Health, the Nashoba association, nursing and mental health — under a fifth of a percent of the budget. "
        "Every budget line the town prints beneath it, FY2023 to FY2025, reconciled "
        "against the department total on the same page.",
    'town-budget-public-works':
        "Highway, vehicle maintenance for three departments, the Park and Cemetery departments, and snow removal. "
        "Every budget line the town prints beneath it, FY2023 to FY2025, reconciled "
        "against the department total on the same page.",
    'town-budget-facilities-grounds':
        "The buildings the town owns and the grounds around them. "
        "Every budget line the town prints beneath it, FY2023 to FY2025, reconciled "
        "against the department total on the same page.",
    'town-budget-solid-waste':
        "Trash and recycling — the fastest-growing line in the budget by rate, and small enough that the rate moves the total very little. "
        "Every budget line the town prints beneath it, FY2023 to FY2025, reconciled "
        "against the department total on the same page.",
    'town-budget-assistance':
        "The Council on Aging and Veterans’ services, each with its own printed subtotal. "
        "Every budget line the town prints beneath it, FY2023 to FY2025, reconciled "
        "against the department total on the same page.",
    'town-budget-schools':
        "The largest line in the town budget by a long way, and not the fastest growing one. Lunenburg Public Schools and the Monty Tech assessment. "
        "Every budget line the town prints beneath it, FY2023 to FY2025, reconciled "
        "against the department total on the same page.",
    'town-budget-library':
        "One line, one library. "
        "Every budget line the town prints beneath it, FY2023 to FY2025, reconciled "
        "against the department total on the same page.",
    'what-you-can-ask':
        'Every question this archive can answer, in plain English and without a line of '
        'SQL. The list a resident should start from: pick the question you actually have '
        'and follow it to the figure and the document behind it.',
    'questions':
        'The same questions with the query that answers each one, run against the '
        'database on every build — so none of them is a claim about what this data can '
        'do. If one stops answering, the build fails.',
    'monty-tech':
        'The larger of the two routes out of Lunenburg’s own schools, and the only school '
        'line the town cannot vote on. What sets the assessment, why 95% of it is a figure '
        'the state calculates, and which parts of the twenty-year series are established.',
    'connecting-the-budget':
        'What can be followed from the school budget to the town’s books, and where it '
        'stops. Two levels join, the third cannot, and the format a report arrives in '
        'decides which.',
    'fy26-closeout':
        'The school department’s FY26, read line by line from the town’s own ledger. '
        'What the $482,101 headline actually is, and three things it cannot explain.',
    'fy26-closeout-town':
        'The same ledger read for the other 67 departments. Snow at 292% of its '
        'appropriation, a Reserve Fund never touched, and school costs sitting on the '
        'town’s books.',
    'budget-vs-actual':
        'Did the money the town budgeted match the money it spent? Careful about what '
        'the documents can and cannot support.',
    'hiring-here-or-placing-there':
        'The district\u2019s own argument \u2014 that hiring special education staff in '
        'district avoids out-of-district placements \u2014 and why this archive cannot yet '
        'test it. A scoping note, not a finding: what it would take to answer is the '
        'whole point of it.',
    'stabilization-option':
        'What the stabilization funds could actually do about the school budget gap. '
        'Spending the whole spendable balance buys two years; stopping the deposits is '
        'permanent and covers a quarter of the first year. Neither closes it, and they '
        'fail differently.',
    'stabilization-funds':
        'The town\u2019s savings, fund by fund: what each one holds, who may spend it, '
        'what it may be spent ON, and the meeting that created it. Whether any of it can '
        'cover a school deficit is a question of purpose and of vote, not of balance.',
    'spending-compared':
        'Lunenburg beside the districts people name at meetings \u2014 including the '
        'regional ones, because "regionalize and we get more money" is a top-five talking '
        'point about this deficit. Per-pupil spending, what the state pays, what the '
        'district itself funds, and what the tax bill is in each town.',
    'free-cash':
        'How much of Lunenburg’s certified free cash is genuinely spendable, built from '
        'the state’s own proofs for nine towns.',
    'athletics':
        'The one programme where both sides of the money are visible, and therefore the '
        'only place the net-versus-gross problem can be measured rather than described.',
    'athletics-ledger':
        'Three years of the athletics revolving fund at transaction level, from a records '
        'request. Includes $254,121.18 described only as “per memo”.',
    'sped-and-the-curve':
        'Special education is about 22% of the budget and the largest single driver of '
        'the gap. What the rates rest on.',
    'sped-and-funds':
        'Whether the special education escalator can be distinguished from grant money '
        'unwinding. It currently cannot, and this says why.',
    'fy27-and-the-override':
        'What the FY27 budget did, what the override would have done, and what the votes '
        'actually decided.',
    'fy27-cut-reconciliation':
        'Reconciling the district’s published cut list against its own budget columns.',
    'peer-districts':
        'What six neighbouring districts did with the same year, and what that does and '
        'does not tell you about Lunenburg.',
    'per-pupil-spending':
        'What DESE says Lunenburg spends for each pupil, against every district in '
        'Massachusetts and against five neighbours — and the arithmetic that says how '
        'much of the difference is money and how much is children.',
    'show-your-work':
        'Every calculation the site publishes, with its inputs, its formula, a worked '
        'example, and whether each figure is published, contractual, statutory, our '
        'measurement or our assumption.',
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def git_date(path):
    try:
        out = subprocess.run(
            ['git', 'log', '-1', '--format=%cs', '--', path],
            cwd=ROOT, capture_output=True, text=True).stdout.strip()
        return out or None
    except Exception:
        return None


ROUTES_TS = os.path.join(ROOT, 'fy28', 'src', 'routes.ts')
PAGES_DIR = os.path.join(ROOT, 'fy28', 'src', 'pages')
DATA_DIR = os.path.join(ROOT, 'fy28', 'public', 'data')

# One line on what each ROUTED report answers, for the pages whose payload does not carry
# an `about` of its own. Editorial, so written here rather than derived -- and the build
# prints which pages fell back to their own title, so a new page is visible rather than
# silently described by nothing.
ABOUT_PAGES = {
    'healthlever':
        'What a slower-growing health line is worth to the gap, and the three routes to '
        'one — a narrower plan, a smaller pool, a larger employee share — each priced, '
        'each landing on somebody.',
    'freecashlever':
        'Whether free cash can fill the gap: yes, once, inside the town’s own guideline — '
        'for one year, out of the capital plan’s money, and budgeting tighter moves the same '
        'dollars a year earlier.',
    'salarylever':
        'What the next teachers’ settlement is worth to the gap per half a point, what '
        'holding the line to the cap means in positions, and what smaller raises would have '
        'changed.',
    'feelever':
        'What athletic, activity and bus fees can add at the most each can ever raise — every '
        'fee has a peak — and how many years that covers.',
    'extraslever':
        'Every sport, the band, the clubs and the art supplies still funded, eliminated: what '
        'it saves, and that it buys one year.',
    'positionslever':
        'The gap in classroom positions at the district’s own cost per post, what is already '
        'cut, and why this is the line every other option exists to avoid.',
    'override':
        'What an override actually is — permanent, compounding, a ceiling rather than a '
        'bill — what one of a given size buys and for how long, and why a school-only '
        'question is worth nearly twice a townwide one.',
    'growth':
        'What “grow our way out of it” would have to look like: the new commercial value '
        'a year that holds the gap, in buildings, against the best year the town has ever '
        'had — and the share of each new dollar the schools actually keep.',
    'sportsmoney':
        'Athletics with both sides of the money visible at once — the town’s '
        'appropriation, the fee-funded revolving fund, and three district documents that '
        'state three different costs for the same team in the same year.',
    'variance':
        'What the district budgeted against what it later reported spending, line by '
        'line — and why nothing before FY2026 is an accounting record.',
    'insurance':
        'School health insurance that is appropriated to a department which is not the '
        'schools, with the account number on it.',
    'leaving':
        'What it would cost the town if more children left under school choice — a '
        'scenario with dials, priced against DESE’s own counts.',
    'staffing':
        'Whether school staffing went up, over any span of years you choose — with the '
        'four quantities the archive holds kept apart: names the town printed, FTE and '
        'headcount the state published, and dollars.',
    'ap':
        'Advanced Placement at the high school, SY2007 to today: who sits the exams, '
        'in what subjects, and how the tests score — three in four sittings are English '
        'or history, and the pass rate is the highest in the file.',
    'circuitbreaker':
        'What the state reimburses for the costliest special education placements, '
        'FY2006 to today: the threshold deducted per child, the share the Legislature '
        'actually funded each year, and nine children whose placements now cost twice '
        'what twenty-nine did.',
    'enrollment':
        'Who is in the schools: DESE’s headcount, FY1994 to today, by grade band and '
        'student group — the fall that stopped a decade ago, the high school that did '
        'the shrinking, and the count of children with disabilities that never moved.',
    'attrition':
        'Which grades Lunenburg children leave in, seventeen years of it — one '
        'grade does almost all of it, and no published record says where any of them '
        'went.',
    'courses':
        'How many classes actually ran in each subject at the high school, year by '
        'year — the one measure here of what was taught rather than who was '
        'employed to teach it.',
    'stopped':
        'Every time a school budget line went to a printed zero, and how many of them '
        'came back.',
    'bythenumbers':
        'Who lives in Lunenburg — age, households, income by age of householder and '
        'owner against renter, from the Census Bureau’s five-year estimates. Every '
        'figure carries its margin of error, because a town this size is a small sample '
        'and the margins decide what may be said.',
    'owners':
        'Lunenburg’s homes and the tax bill: how many there are, what the average one is worth '
        'and pays, every year the state has published and against ten neighbours — and how the '
        'rate can fall while the bill rises. Then who has owned them how long, from the Census '
        'and from the assessor’s own parcel file.',
    'cuts':
        'Every reduction the district named in its own budget documents, cycle by cycle, '
        'quoted at its page — and, where a state series reaches it, whether the count '
        'moved with it.',
    'funds':
        'The money the town holds and spends outside the budget Town Meeting votes — '
        'grants, revolving funds, gifts and the enterprise funds.',
    'stateaid':
        'The share of the school budget that arrives from the State House, and the '
        'difference between Chapter 70 and total state aid.',
    'families':
        'Every school fee a Lunenburg household can be charged, priced for one to four '
        'children, and the three places the published record runs out.',
    'sped':
        'Four special education reports behind one door, and the reason they must not be '
        'combined: each counts a different thing.',
    'thisweek':
        'Meetings coming up for the Select Board, Finance Committee and School Committee '
        'with what is on each agenda, minutes just posted, recordings just published, and '
        'what happened at the last recorded meetings. Refreshed daily.',
    'budgetfeed':
        'Every board, one page: budget meetings coming up, where this cycle stands against the '
        'last five, what was said about money in the last ninety days, and what was posted.',
    'boards':
        'Every board and committee, one page each: what is coming, what happened, every vote '
        'we have minutes for in recency order, where the board’s time goes, and when budget '
        'season has fallen on its agendas in past years.',
    'recorded':
        'Our minutes of recorded meetings, written from the captions: votes, transfers, '
        'budget items, decisions and public comment, every item linked to the video at '
        'that second, and checked against the town’s minutes where they exist.',
    'blog':
        'Every finding this project has published as a post: the figures, what it means '
        'for a resident, a Finance Committee member and a School Committee member, and '
        'the links to the report underneath it. About two minutes each.',
    # NOT `classsize`. Its payload carries its own `about`, which wins here -- and a
    # second description of the same page in this file is the artefact that goes stale
    # first. The generated one is the one the index prints.
}


def analyses_area_tabs():
    """Every tab the app files in the ANALYSES area, whether or not it is in the bar.

    `AREA_TABS.analyses` is the bar, and the bar is deliberately shorter than the area:
    the four special education reports sit behind one `sped` entry because a bar with
    fourteen entries is a sitemap. `AREA_OF` is the full membership, and anything that
    means to cover the area rather than the bar has to read this one --
    /what-it-all-adds-up-to does, which is how it reaches
    /what-special-education-costs at all.
    """
    src = open(ROUTES_TS, encoding='utf-8').read()
    m = re.search(r'const AREA_OF: Partial<Record<Tab, Area>> = \{(.*?)\n\}', src, re.S)
    if not m:
        raise SystemExit('routes.ts: could not find the AREA_OF table')
    tabs = [t for t, a in re.findall(r"(\w+): '(\w+)'", m.group(1)) if a == 'analyses']
    # `analysis` is the ONE tab that renders all seventeen Markdown documents at
    # /analysis/<id>. It owns no single report, declares no `const TAB`, and has no
    # payload, so it is not a row anywhere reports are enumerated.
    tabs = [t for t in tabs if t != 'analysis']
    if not tabs:
        raise SystemExit('routes.ts: AREA_OF names no analyses tabs, which has never '
                         'been true')
    return tabs


def parents():
    """`PARENT` in routes.ts: which page a drill-in sits under.

    Used for ORDERING here, not for navigation. It is the table that already records
    which door each hidden report is behind, so reading it is how the master report can
    place the four special education reports where the bar puts special education without
    anybody keeping a second list in step with the first.
    """
    src = open(ROUTES_TS, encoding='utf-8').read()
    m = re.search(r'export const PARENT: Partial<Record<Tab, Tab>> = \{(.*?)\n\}',
                  src, re.S)
    if not m:
        raise SystemExit('routes.ts: could not find the PARENT table')
    out = dict(re.findall(r"(\w+): '(\w+)'", m.group(1)))
    if not out:
        raise SystemExit('routes.ts: the PARENT table parsed to nothing')
    return out


def routed_reports(all_of_area=False):
    """Every report the app routes to, read off the table the app itself routes on.

    `all_of_area=True` covers the whole Analyses AREA rather than its tab bar -- see
    `analyses_area_tabs`. The bar is the default because /reports is a navigation index
    and the bar is what a reader navigates.

    `AREA_TABS.analyses` in routes.ts is the Analyses area's own tab list. Parsed rather
    than imported, for the same reason `prerender.mjs` parses it: this is a TypeScript file
    and we are running plain Python. The parse asserts what it found, because a regex that
    matches nothing looks exactly like an area with no reports in it.
    """
    src = open(ROUTES_TS, encoding='utf-8').read()

    m = re.search(r'^\s*analyses: \[(.*?)\],\n', src, re.S | re.M)
    if not m:
        raise SystemExit('routes.ts: could not find AREA_TABS.analyses')
    tabs = re.findall(r"'([a-z]+)'", m.group(1))
    if not tabs:
        raise SystemExit('routes.ts: AREA_TABS.analyses parsed to nothing')
    if all_of_area:
        # THE BAR'S ORDER, WITH EACH HIDDEN REPORT PUT WHERE ITS DOOR IS.
        #
        # The bar draws `sped` -- one entry for four reports -- and the four are not in it.
        # Appending them produced a page that ended on special education, which is the
        # subject this town argues about most; the bar itself says where that subject
        # sits, second, and `PARENT` in routes.ts says which door each of the four is
        # behind. So each report the bar does not draw is inserted directly after its
        # parent rather than at the end. Both facts are read off routes.ts: the ordering
        # decision stays where the ordering decisions already are.
        parent = parents()
        for t in analyses_area_tabs():
            if t in tabs:
                continue
            pt = parent.get(t)
            at = tabs.index(pt) + 1 if pt in tabs else len(tabs)
            # ...and successive children keep their own order rather than reversing.
            while at < len(tabs) and parent.get(tabs[at]) == pt:
                at += 1
            tabs.insert(at, t)

    block = re.search(r'export const SLUG: Record<Tab, string> = \{(.*?)\n\}', src, re.S)
    slug = dict(re.findall(r"^\s*(\w+): '([^']*)',", block.group(1), re.M))
    lab = re.search(r'export const LABEL: Record<Tab, string> = \{(.*?)\n\}', src, re.S)
    if not lab:
        raise SystemExit('routes.ts: could not find the LABEL table')
    label = dict(re.findall(r"^\s*(\w+): '(.*?)',$", lab.group(1), re.M))

    # tab -> the page component that declares it, and the payload it draws.
    owner, payload = {}, {}
    for f in sorted(os.listdir(PAGES_DIR)):
        if not f.endswith('.tsx'):
            continue
        text = open(os.path.join(PAGES_DIR, f), encoding='utf-8').read()
        t = re.search(r"^const TAB: Tab = '([a-z]+)'", text, re.M)
        if not t:
            continue
        owner[t.group(1)] = 'fy28/src/pages/' + f
        d = (re.search(r"^const DATA = '/data/([^']+)'", text, re.M)
             or re.search(r"useReport<[^>]*>\('([^']+)'\)", text))
        if d:
            payload[t.group(1)] = d.group(1)

    missing = [t for t in tabs if t != 'reports' and t not in owner]
    if missing:
        raise SystemExit(
            'These reports are routed in AREA_TABS.analyses and no page component claims '
            'them:\n  %s\nEvery report page declares `const TAB: Tab = ...` so this index '
            'cannot silently omit it.' % ', '.join(missing))

    out, undescribed = [], []
    for t in tabs:
        if t == 'reports':      # the index itself is not a row in the index
            continue
        about = ABOUT_PAGES.get(t)
        data = None
        if t in payload:
            fp = os.path.join(DATA_DIR, payload[t])
            if os.path.exists(fp):
                data = dict(url='/data/' + payload[t], bytes=os.path.getsize(fp),
                            sha256=sha256(fp))
                # Prefer the payload's OWN description where it carries one: it is written
                # by the generator that computes the figures, so it cannot describe a
                # report the data no longer supports.
                try:
                    about = json.load(open(fp, encoding='utf-8')).get('about') or about
                except (ValueError, OSError):
                    pass
        if not about:
            undescribed.append(t)
        out.append(dict(
            id=t, kind='page', title=label.get(t, t), url='/' + slug[t],
            about=about or label.get(t, t), component=owner[t],
            data=data, generator=generator_for(payload.get(t))))
    return out, undescribed


def generator_for(payload_name):
    """The script that writes a page's payload, found by looking for it.

    Derived rather than tabulated: /reports promises a reader the script that recomputes
    every figure, and a hand-kept mapping from page to script is the thing that goes stale
    the first time one is renamed.
    """
    if not payload_name:
        return None
    hits = []
    for p in sorted(glob.glob(os.path.join(ROOT, 'scripts', 'build_*.py'))):
        with open(p, encoding='utf-8') as fh:
            if payload_name in fh.read():
                hits.append('scripts/' + os.path.basename(p))
    return hits[0] if len(hits) == 1 else (hits[0] if hits else None)


def finance_index():
    """Every board and department that owns money, with the address of its finances.

    THE ANALYSES PAGE IS THE DOOR TO THE DATA, NOT ONLY TO THE WRITE-UPS. TJ, 18 September
    2026: "having a board list at the bottom in a new section, plus a direct link to the
    Financials will at least give people a way to find these without knowing to go
    directly to each board ... use this page as a way to find all 'data' not just the
    individual reports."

    Before this, a board's finance page was reachable only from that board's own page --
    so a reader had to already know the board existed, and know it had a finance tab, to
    find the one thing on this site that says what that board spends. That is discovery
    by prior knowledge, which is the same failure as an index that omits a report.

    Derived from the two payloads that already decide what exists: boards.json says which
    boards have a finance tab (the same flag the prerenderer routes on) and finance.json
    carries the departments and the account counts. Nothing here is tabulated by hand, so
    a board that gains an account appears the day its account does.
    """
    fb = os.path.join(DATA_DIR, 'finance.json')
    bb = os.path.join(DATA_DIR, 'boards.json')
    for f in (fb, bb):
        if not os.path.exists(f):
            raise SystemExit('missing %s -- run build_finance.py and build_boards.py '
                             'before this' % os.path.relpath(f, ROOT))
    with open(fb, encoding='utf-8') as fh:
        fin = json.load(fh)
    with open(bb, encoding='utf-8') as fh:
        boards = json.load(fh)['boards']

    owners = fin['owners']

    def measures(slug):
        o = owners.get(slug)
        return sum((o or {}).get('counts', {}).values())

    # THE MAGNITUDE IS TWO FIGURES AND THEY MAY NOT BE ADDED.
    #
    # TJ, 18 September 2026: "is there a way to put a magnitude for each board/department?
    # Like, total budget or total funds available per year or something?"
    #
    # There is, and the honest answer is a pair rather than a single number, because the
    # two quantities are different KINDS. An appropriation is a FLOW -- what Town Meeting
    # authorised this board or department to spend across FY2026, and it resets every
    # year. A revolving fund or trust balance is a STOCK -- what sat in the account on one
    # day, accumulated across years and not voted at all. Adding them produces a figure
    # that is neither: a year of spending plus a pile of savings, with no unit anybody
    # could name. Rule 7's grain problem in its arithmetic form.
    #
    # So both are carried, both are labelled, and the page prints them in separate
    # columns. Six owners have no appropriation at all and exist only as held funds --
    # which is itself worth seeing, and would be invisible in a single blended number.
    #
    # Rule 11 still applies to the appropriation: it is NET of whatever grants, fees and
    # reimbursements pay for the same thing, so it is what the town had to raise, not what
    # the department costs. The page says so where the figure is.
    #
    # `agency_held` is deliberately excluded from the stock. Agency funds are money the
    # town holds FOR SOMEBODY ELSE -- deposits, withholdings, the school lunch clearing
    # account -- and one of them is negative. It is not this owner's money to spend and
    # counting it as magnitude would overstate three owners and understate one.
    def magnitude(slug):
        t = (owners.get(slug) or {}).get('totals') or {}
        held = [t.get('special_revenue_held'), t.get('trust_held')]
        stock = sum(x for x in held if x)
        return dict(
            appropriation=t.get('appropriation_revised'),
            expended=t.get('appropriation_expended'),
            period=t.get('appropriation_period'),
            held=stock or None,
            held_parts=dict(special_revenue=t.get('special_revenue_held'),
                            trust=t.get('trust_held')),
        )

    bs = []
    for b in boards:
        if not b.get('finance'):
            continue
        # The School Committee's finance page is a top-level route; every other board's
        # is a tab under the board. routes.ts is the authority on both, and the
        # prerenderer special-cases the same slug.
        url = ('/boards/school-committee/finance' if b['slug'] == 'school-committee'
               else '/boards/%s/finance' % b['slug'])
        bs.append(dict(slug=b['slug'], name=b['name'], url=url,
                       board_url='/boards/' + b['slug'],
                       accounts=b['finance'].get('accounts') or measures(b['slug']),
                       **magnitude(b['slug'])))

    ds = []
    for d in fin['departments']:
        if d['slug'] not in owners:
            continue        # no measure of its own: it has no page to link to
        # `external` is not a department at all: Worcester Regional Retirement, Monty
        # Tech, the regional planning commission and the cherry sheet are ASSESSMENTS the
        # town is billed for, appropriated under the Town Manager's book because the money
        # has to leave from somewhere. Filing them under "Town Manager departments" would
        # say the Town Manager runs them, which is the kind of quiet wrongness a label
        # gets away with for years. The page splits on this.
        ds.append(dict(slug=d['slug'], name=d['name'],
                       url='/departments/' + d['slug'], kind=d.get('kind') or 'department',
                       head=d.get('head') or '', accounts=measures(d['slug']),
                       **magnitude(d['slug'])))

    # A JOIN THAT MATCHES NOTHING LOOKS EXACTLY LIKE DATA THAT IS ABSENT.
    if not bs or not ds:
        raise SystemExit('finance index resolved %d boards and %d departments -- one of '
                         'the payloads changed shape' % (len(bs), len(ds)))

    # LARGEST FIRST. A magnitude column that is sorted alphabetically is a magnitude
    # nobody reads -- the whole reason to print the figure is that $26.4M and $500 are
    # not the same kind of body, and the order is what says so at a glance. Owners with
    # no appropriation sort on what they hold instead, and land at the foot.
    def rank(x):
        return (-(x['appropriation'] or 0), -(x['held'] or 0), x['name'])

    return dict(
        boards=sorted(bs, key=rank),
        departments=sorted(ds, key=rank),
        # THE GRAIN, in the words the page prints beside the figures. Every appropriation
        # here is FY2026 period 12 -- year end, unaudited -- and every balance is the one
        # struck on 31 March 2026. Typed nowhere: read from the payload that computed them.
        appropriation_as_of=fin.get('as_of', {}).get('ledger', ''),
        held_as_of=fin.get('as_of', {}).get('special_revenue', ''),
        measures=len(fin['measures']),
        as_of=fin.get('as_of', {}),
        doors=[
            dict(url='/accounts', title='Every account, once',
                 about='The registry underneath all of this: every fund, appropriation, '
                       'revolving fund, grant and trust the town\u2019s own reports '
                       'print, each one assigned to whoever answers for it.'),
            dict(url='/departments', title='The departments',
                 about='The Town Manager\u2019s departments, each with the lines it '
                       'spends and what it held at the close of the period.'),
        ],
        generated_by='scripts/build_finance.py',
    )


def main():
    names = sorted(f[:-3] for f in os.listdir(SRC) if f.endswith('.md'))
    ordered = [n for n in ORDER if n in names] + [n for n in names if n not in ORDER]

    reports, unlisted = [], []
    for n in ordered:
        md = os.path.join(SRC, n + '.md')
        text = open(md, encoding='utf-8').read()
        title = text.split('\n', 1)[0].lstrip('# ').strip()

        # The first real paragraph, skipping the working-state blockquote and the
        # generated-by line. Used only as a fallback where ABOUT has no entry.
        lede = ''
        for para in re.split(r'\n\s*\n', text):
            p = para.strip()
            if (p.startswith('#') or p.startswith('>') or p.startswith('---')
                    or p.startswith('Analysis,') or not p):
                continue
            lede = re.sub(r'\s+', ' ', p)[:240]
            break
        if n not in ABOUT:
            unlisted.append(n)

        verifier = 'scripts/verify_%s.py' % n.replace('-', '_')
        has_verifier = os.path.exists(os.path.join(ROOT, verifier))
        pdf = os.path.join(PDF, n + '.pdf')

        charts = sorted(
            f for f in os.listdir(os.path.join(SRC, 'charts'))
            if f.startswith('fy26-') and n.endswith(
                'town' if '-town' in f else 'closeout')) \
            if os.path.isdir(os.path.join(SRC, 'charts')) and n.startswith('fy26') else []

        reports.append(dict(
            id=n, kind='document', title=title,
            # The document, rendered on the site in the same shell as every other report.
            # The .md stays the source of truth and stays published -- rule 12 -- and the
            # page renders it rather than transcribing it. See fy28/src/pages/Analysis.tsx.
            url=f'/analysis/{n}',
            about=ABOUT.get(n) or lede,
            words=len(text.split()),
            updated=git_date(md),
            markdown=dict(url=f'/docs/analyses/{n}.md',
                          bytes=os.path.getsize(md), sha256=sha256(md)),
            pdf=(dict(url=f'/docs/analyses/{n}.pdf', bytes=os.path.getsize(pdf))
                 if os.path.exists(pdf) else None),
            verifier=(dict(path=verifier,
                           command=f'python3 {verifier}') if has_verifier else None),
            charts=[f'/docs/analyses/charts/{c}' for c in charts],
        ))

    pages, undescribed = routed_reports()

    # --- group by subject, one entry per subject ------------------------------------
    by_id = {r['id']: r for r in list(reports) + list(pages)}
    groups, placed = [], set()
    for key, title, subs in CATEGORIES:
        out_subs = []
        for sub_title, ids in subs:
            rows = []
            for i in ids:
                if i in by_id:
                    rows.append(i)
                    placed.add(i)
            if rows:
                out_subs.append(dict(title=sub_title, ids=rows))
        if out_subs:
            groups.append(dict(key=key, title=title, sections=out_subs))

    # AND THE SECOND TAXONOMY MUST COVER THE SAME REPORTS. `/what-it-all-adds-up-to`
    # groups the same set by SUBJECT rather than by school/town, because special education
    # is four reports the index draws behind one door and athletics is two the index
    # separates -- see `conclusions.TOPICS`, which is the only declaration of it. Two
    # groupings over one set will drift unless something compares them, and a reader who
    # meets special education under one heading here and another there learns that neither
    # is meaningful. So this refuses to write if a routed report is in neither.
    import conclusions as _C
    astray = sorted(p['id'] for p in pages
                    if p['id'] not in _C.NOT_A_REPORT and not _C.topic_of(p['id']))
    if astray:
        raise SystemExit(
            'these routed reports are in no subject in conclusions.TOPICS, so '
            '/what-it-all-adds-up-to would not show them: %s\nAdd each to a topic there, '
            'or to NOT_A_REPORT if it is not a report.' % ', '.join(astray))

    # NOTHING MAY FALL OUT OF THE TAXONOMY SILENTLY. A report that is in neither a
    # category, nor superseded by one, nor deliberately uncategorised would simply stop
    # being listed -- the failure this index exists to prevent, arriving through the
    # feature meant to organise it. So it refuses to write.
    unplaced = sorted(set(by_id) - placed - set(SUPERSEDED) - UNCATEGORISED)
    if unplaced:
        raise SystemExit(
            'these reports are in no category:\n  ' + '\n  '.join(unplaced) +
            '\n\nAdd each to CATEGORIES in this script, or to SUPERSEDED if a page '
            'already covers the same subject, or to UNCATEGORISED if it genuinely '
            'belongs outside the grouping. Nothing written.')

    # And a supersession must point at something that exists, or the document it hides
    # would vanish while the page it points to was never built.
    missing = sorted(v for v in SUPERSEDED.values() if v not in by_id)
    if missing:
        raise SystemExit('SUPERSEDED points at reports that do not exist: %s. '
                         'Nothing written.' % missing)

    data = dict(
        generated=date.today().isoformat(),
        groups=groups,
        superseded={k: v for k, v in SUPERSEDED.items() if k in by_id},
        # The caveat leads. It is the first field for the same reason it is the first
        # thing on the page: these are not the town's documents and must never be
        # mistaken for them.
        caveat=dict(
            headline='Written by this project, not by the town or the district.',
            body=('Nothing on this page is an official document. These analyses are '
                  'written here, from documents the town and district published and from '
                  'records obtained by request. They have not been reviewed or endorsed '
                  'by the Town of Lunenburg, the Lunenburg School Committee, the Finance '
                  'Committee or Lunenburg Public Schools, and this project is not '
                  'affiliated with any of them.'),
            checkable=('Every figure in an analysis is recomputed from the underlying '
                       'data by a script, and the script is named on the row. The data '
                       'itself is published below — you do not have to take any of this '
                       'on trust, and you should not.'),
            corrections=('Where an earlier version of an analysis was wrong, the '
                         'correction stays in the text rather than being edited out. '
                         'Several of these documents describe their own earlier errors.'),
        ),
        reports=reports,
        # EVERY BOARD AND DEPARTMENT THAT OWNS MONEY, with the address of its
        # finances -- so this page is the door to the data and not only to the
        # write-ups. See finance_index().
        finance=finance_index(),
        # The reports that are React PAGES rather than documents. Same area, same shell,
        # same print stylesheet; what differs is that a page is computed from a published
        # payload on every build and a document is prose with a verifier beside it.
        pages=pages,
        data=dict(
            database=dict(
                url='/data/lunenburg.db',
                about='Every figure on this site in one SQLite file. The same database '
                      'the analyses are computed from.'),
            api=dict(url='/api/index',
                     about='A read-only JSON API. No key, no rate limit. /api/schema '
                           'states the grain of each table and the four ways to get a '
                           'confident wrong answer out of it.'),
            sources=dict(url='/sources',
                         about='Every source document, with its address, the publisher’s '
                               'own filename and a checksum.'),
            grossBudget=dict(
                url='/docs/data/gross-school-budget-fy2026.xlsx',
                about='The district’s budget in the district’s own shape, with what was '
                      'actually spent and what other money paid for it — and amber cells '
                      'wherever that money is not held.'),
        ),
    )

    fresh = json.dumps(data, separators=(',', ':'))

    # --check, and the reason it exists: this generator was NOT in check_generated.py, so
    # when two analyses were added the published index went on describing thirteen. The
    # site served a /reports page that was correct about everything it listed and silent
    # about what it did not -- an omission, which is the one defect shape nothing here
    # catches by re-reading. Found by somebody asking where the question list was.
    if '--check' in sys.argv:
        if not os.path.exists(OUT):
            raise SystemExit('%s does not exist. Run without --check.'
                             % os.path.relpath(OUT, ROOT))
        with open(OUT, encoding='utf-8') as fh:
            current = fh.read()

        # PDF byte counts are excluded from the comparison, and that is not a shortcut.
        # A PDF is not byte-reproducible -- re-rendering the same Markdown produces a
        # different size -- so including them would make this check fail every time the
        # PDFs are rebuilt, with nothing having changed. A check that cries wolf is worse
        # than no check, because it gets ignored on the day it is right.
        #
        # What that costs: a PDF whose CONTENT changed will not be caught here. That is
        # not what this check is for. It is for an analysis that exists on disk and is
        # missing from the index a reader browses -- the omission that let /reports
        # describe thirteen analyses while fifteen were published.
        def comparable(text):
            d = json.loads(text)
            for r in d.get('reports', []):
                if isinstance(r.get('pdf'), dict):
                    r['pdf'].pop('bytes', None)
            return json.dumps(d, separators=(',', ':'), sort_keys=True)

        if comparable(current) != comparable(fresh):
            now = json.loads(current)
            was = ({r['id'] for r in now.get('reports', [])}
                   | {r['id'] for r in now.get('pages', [])})
            has = ({r['id'] for r in data['reports']}
                   | {r['id'] for r in data['pages']})
            missing = sorted(has - was)
            extra = sorted(was - has)
            raise SystemExit(
                'STALE: %s no longer reproduces.%s%s\n  Run: python3 '
                'scripts/build_reports_index.py' % (
                    os.path.relpath(OUT, ROOT),
                    '\n  published index is MISSING: %s' % ', '.join(missing)
                    if missing else '',
                    '\n  published index lists what is gone: %s' % ', '.join(extra)
                    if extra else ''))
        print('ok: %s lists all %d documents and all %d routed reports'
              % (os.path.relpath(OUT, ROOT), len(data['reports']), len(data['pages'])))
        return

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write(fresh)
    print('wrote %s' % os.path.relpath(OUT, ROOT))
    print('  %d documents, %d with a verifier, %d with a PDF'
          % (len(reports), sum(1 for r in reports if r['verifier']),
             sum(1 for r in reports if r['pdf'])))
    print('  %d routed reports, %d with a published payload, %d with a named generator'
          % (len(pages), sum(1 for r in pages if r['data']),
             sum(1 for r in pages if r['generator'])))
    if undescribed:
        print('  NOT described in ABOUT_PAGES and carrying no `about` in their payload, '
              'showing their own title instead: %s' % ', '.join(undescribed))
    if unlisted:
        print('  NOT described in ABOUT, showing their own opening instead: %s'
              % ', '.join(unlisted))
    return 0


if __name__ == '__main__':
    sys.exit(main())
