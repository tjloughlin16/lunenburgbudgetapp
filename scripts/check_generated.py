#!/usr/bin/env python3
"""Is every generated file still what its generator would produce?

    python3 scripts/check_generated.py

THE ROOT CAUSE THIS EXISTS FOR

Nearly every defect found in this project on 5 September 2026 was one shape:
**something derived was written down, the thing it derived from moved, and nothing
connected the two.** Thirteen instances in a day.

  * a word index moved folders and llms.txt kept citing the old URL
  * a provenance join hardcoded `town-budget/index.csv` and resolved 0 of 225 rows
  * eight scripts globbed `town-budget/docs` for reports that had left it
  * 43 document rows named files that no longer existed, and were still being cited as
    the place to check a figure
  * a caveat quoted a series -- 0, 5, 4, 4, 0 -- typed from a field that the same commit
    had already fixed, so it repeated the undercount it existed to explain

Three sub-causes, and each has a countermeasure:

  1. **A LOCATION WAS HARDCODED where location is not identity.** This archive is keyed on
     provenance and re-files documents on purpose; a literal folder path in a script is a
     latent break with a date on it. Read the manifest or glob every `sources/*/index.csv`.
  2. **A FIGURE OR A NAME WAS TYPED into prose.** Rule 2 was stated for the projection and
     never applied to llms.txt, the READMEs, the caveats, the worked examples or the check
     fixtures -- all of which are prose that ships.
  3. **A JOIN THAT MATCHES NOTHING LOOKS EXACTLY LIKE DATA THAT IS ABSENT.** Four of the
     thirteen were silent zeros. A join whose result is used must assert that it matched.

This runs the `--check` mode of every generator, which is the mechanical half of the
answer: if an input moved, the output no longer reproduces, and this says so. It does not
catch a figure typed into a sentence that nothing regenerates -- for that the only defence
is deriving it, which is why the caveats and examples now are.
"""
import os
import argparse
import concurrent.futures as cf
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Every generator that can check itself. Ordered cheapest first, so a fast failure comes
# back fast. `sync_d1` is last because it is the only one that touches the network.
CHECKS = [
    ('build_readme.py', ['--check']),
    # The printable decisions/questions sheet is EXTRACTED from the notes rather
    # than typed, so this fails the moment a decision is taken and struck from
    # notes/findings/DRILL-IN-PAGES.md without the sheet being rebuilt -- which is
    # the failure that matters, because the sheet is what gets printed and reviewed.
    ('build_decisions_doc.py', ['--check']),
    # Every DESE source with its address, so next year's refresh does not require
    # rediscovering where any of it came from. Fails if a registered file is absent:
    # a registry pointing at nothing reads as coverage, which is worse than none.
    ('build_dese_registry.py', ['--check']),
    # Every money parser against every printed shape of a negative. A dropped sign
    # does not zero a figure, it reflects it -- the paraprofessional line came out
    # $315,772 wrong, twice the line, and that line feeds a published projection.
    ('check_money_parsers.py', []),
    # Added 6 Sept 2026, after it had already drifted: two analyses were published
    # and /reports went on listing thirteen. Nothing caught it because this file is
    # the thing that catches it, and this generator was not in it.
    ('build_reports_index.py', ['--check']),
    # ONE REPORT OVER ALL OF THEM. It reads every report's payload and writes none of its
    # own claims, so this entry fails exactly when it should: a report changed a
    # conclusion, or stopped publishing one, and the synthesis still says the old thing.
    # It is also the only check that can catch a report going SILENT -- the generator
    # names every routed report with no conclusions rather than dropping it, so a report
    # that loses its conclusions changes this output rather than vanishing from it.
    ('build_master_report.py', ['--check']),
    # And the conclusions themselves, against the reports they came from: rule 2 re-run on
    # the published payloads rather than on the generators' own copies, every figure
    # counted as quoted or computed, and the synthesis asserted to be byte-identical to
    # its sources. It is here rather than only in a verifier because a conclusion is prose
    # that ships, and prose that ships is what nothing was checking.
    ('verify_conclusions.py', []),
    ('build_money_flow.py', ['--check']),
    ('build_money_nodes.py', ['--check']),
    ('build_ledger_structure.py', ['--check']),
    ('build_who_decides.py', ['--check']),
    ('build_town_flow.py', ['--check']),
    # The schema inventory. It RUNS its worked queries against the live database, so this
    # entry also catches a query that has stopped answering -- not only a stale file.
    ('build_schema_page.py', ['--check']),
    # The reference pages, published into fy28/public/reference/ as byte-identical copies.
    # This entry is the whole reason that is safe: the originals are regenerated by the
    # scripts around it, so without a check the published copy is a snapshot of whatever
    # the page said on the day somebody ran the copier -- the exact shape of defect this
    # file exists for, with the added twist that a stale copy of a generated page is
    # indistinguishable from a current one. It also fails if a reference document appears
    # that is neither published nor deliberately excluded, which is the omission half.
    ('build_reference_pages.py', ['--check']),
    # Added 7 Sept 2026 after it had been CRASHING for an unknown length of time. It reads
    # a row's label as `label`; this schedule builds rows with `fund`, so every run raised
    # KeyError and the committed CSV could not be regenerated. It was not in this list,
    # which is the file whose whole job is catching that.
    ('extract_special_revenue.py', ['--check']),
    # The read-from-the-page version, checked against the report's own printed GRAND TOTAL
    # and against the identity the table states. Two independent checks; a year that does
    # not pass both is not in the dataset.
    ('verify_special_revenue_read.py', []),
    # The combined balance sheet, read from the page. Its cross-check is the strongest in
    # the archive: special revenue + enterprise fund equity must equal the special revenue
    # schedule's own carried-forward total — two documents, different pages, and the
    # second was verified to the penny by an entirely separate pass.
    ('verify_balance_sheet.py', []),
    # The ENTERPRISE-funds combining balance sheet, FY2024-FY2025, read from the page.
    # Five checks: column footing, the identity the sheet states, the sheet's OWN printed
    # Proof row, the memorandum column cross-footed against the four fund columns, and --
    # free, because the town gave it to us -- FY2024's two printings of the same sheet on
    # pages 21 and 28, transcribed independently and asserted to agree.
    ('verify_enterprise_balance_sheet.py', []),
    # PEG Access / Public Access Cable, FY2015-FY2025, read from the page. Seven checks:
    # the expense lines foot to the report's own printed TOTAL; the printed percent column
    # foots to its printed 100.00% and every percent recomputes; the identities each
    # statement states about ITSELF hold; every printed row is reached by one of them --
    # which is what caught FY2020's orphan `Subtotal`; the two pages of each report agree
    # on total expenses; and what the prose says the revenue was matches what the table
    # prints. Five printed defects are pinned to the penny rather than smoothed.
    ('verify_peg_access.py', []),
    # What the reports contain that we have not read, or have read without checking.
    # Generated because a count nobody maintains is the only kind that stays true.
    ('build_extraction_gaps.py', ['--check']),
    # The budget-versus-actual page's series. It reconciles every function group against
    # `variance_by_group` before it will write, so this entry catches two different things
    # going stale: the published file, and the agreement between the database route and
    # the CSV route to the same figure.
    ('build_variance_charts.py', ['--check']),
    # The school-staffing page's series. It reconciles two independent routes to the
    # paraprofessional dollars -- summing five line keys out of `budget_figure`, and
    # `sped_para_history`'s own total column -- and REFUSES to write if they share no year,
    # because a comparison that compares nothing passes trivially. It also refuses if the
    # roster fails to join to its classification, since a name with no category looks
    # exactly like a name with no role.
    ('build_staffing_charts.py', ['--check']),
    # The health-insurance page's series. Three things go stale independently here and this
    # catches all three: the published file against the ledger; the annual-report extract,
    # which refuses to write unless the insurance block of each year sums to the `Total
    # Insurance` that same page prints; and the gap-register rows the page quotes BY KEY,
    # since a limit whose reason has been renamed out from under it renders as an empty box.
    # It also refuses if a dept-914 account appears that this project has not described --
    # an undescribed account would otherwise be drawn as a bar with no meaning on it.
    ('build_insurance_charts.py', ['--check']),
    # The athletics page's series. Athletics is the one programme where both sides of the
    # money are visible, so this generator is also the place four assertions live that
    # nothing else in the project can make: the district workbook's cost columns summing
    # to its own printed total, the fund's cash chaining to the opening balance the town
    # printed for the next year, and -- the one that has actually gone wrong here -- a
    # REVENUE row reaching a spending total. An appropriation, a fund's spending and a
    # fund's receipts are three quantities, and "$335,856 through the revolving fund" was
    # once the second plus the third.
    ('build_athletics_charts.py', ['--check']),
    # The state-aid page's series. This one reaches outside the database for three of its
    # five quantities, so it is the entry that catches the most kinds of drift: the DESE
    # Chapter 70 workbook (whose column headings and Lunenburg row it asserts against
    # `model/taxbase.CH70` — two routes to the same eight figures), `model/finance.py`'s
    # state aid growth rate and FY27 revenue base, and five MEETING MINUTES, each quote
    # checked to still be present verbatim in the file it is attributed to. A quote that
    # has drifted from its source is rule 13's exact shape and nothing else here would see
    # it. It also refuses on a 45xx revenue object this project has not classified, since
    # `object LIKE '45%'` is neither all state aid nor only state aid — two of those
    # accounts are local option taxes the state merely collects.
    ('build_state_aid.py', ['--check']),
    # The school-choice scenario page. It reaches five documents and reconciles three of
    # them against each other, so this entry catches the drift nothing else would: the
    # FY2025 annual town report's enrollment table, whose COLUMN HEADINGS are read off the
    # printed page because `column_meaning` is empty for that dataset and `v1` is an
    # ordinal -- get that wrong and 433 stops being a count of resident students; the same
    # table checked against `report_enrollment_mcas`, two routes to one row; the DESE
    # Chapter 70 workbook against `model/taxbase.CH70`; thirteen years of the School Choice
    # revolving fund, every one of them `check failed` at the PAGE level, so this generator
    # supplies the row-level checks instead and refuses on either -- forward + receipts -
    # disbursements = carried, and the carried balance opening the next annual town report;
    # and five meeting quotes, each asserted verbatim in the file it is attributed to. It
    # also refuses if Lunenburg's Chapter 70 aid stops being above foundation minus
    # required contribution, which is the measurement the page's central correction rests
    # on -- that one is meant to be rebuilt rather than reworded.
    ('build_if_students_leave.py', ['--check']),
    # What a HOUSEHOLD pays, priced for one to four children. It catches four kinds of
    # drift that nothing else here would, and every one of them is about a unit rather
    # than a figure: a family cap acquiring or losing a stated period in its own source;
    # the FY2027 rate ladder ceasing to be the FY2026 sibling discount compounding, which
    # is what lets an unpublished fourth-child rate be called INFERRED rather than
    # unknown; five children at one sport each reaching the cap in a single season, which
    # would end the page's lead inference and require it rewritten rather than
    # re-rendered; and the LHS Athletics FAQ losing the sentence "Only one sport per
    # season is allowed", which is the whole of what makes a season fee also a per-sport
    # fee. It also refuses if `rate_register` stops carrying unpublished fees, because the
    # open band above every total on that page rests on there being some.
    ('build_what_families_pay.py', ['--check']),
    # And the register the household table reads. `rate-register.csv` is GENERATED, which
    # makes it the data-entry point for a fee whose amount arrives later: fill the value in
    # here and the table prices a row that was rendering as "not published". The --check is
    # the guard on that -- it re-derives every rate from the athletic fee schedule, the
    # contracts file and the Superintendent's own emails, and asserts each household charge
    # quote is still verbatim in the document it is attributed to (rule 13).
    ('build_rate_register.py', []),
    # Every figure the household table publishes, recomputed from the register and the fee
    # schedule rather than from the payload's own arithmetic. It asserts three STRUCTURES
    # as well as the numbers, because each is a sentence the page rests on that no single
    # figure would catch: a total that is not the sum of the rows under it; an unpriced row
    # that has acquired an amount without changing band, which would be a guess published
    # as a measurement; and a charge with no records request written for it, which rule 7c
    # calls a grievance rather than a gap.
    ('verify_what_families_pay.py', []),
    # The BUDGET-to-BUDGET state aid series, FY2005-FY2027 -- the like-for-like
    # counterpart to the receipts series above, and the evidence behind decision D10 in
    # notes/findings/STATE-AID-RATE.md. It catches four kinds of drift nothing else here
    # would: a heading moving inside the FY19 budget handout workbook (whose year labels
    # sit on TWO rows, and three of whose twenty columns are a projection, an ACTUAL and a
    # duplicate override column that must never enter a budget series); five later
    # worksheets RESTATING the same fiscal year with different figures; the FY2027 Town
    # Meeting booklet's cherry sheet components no longer summing to its own printed
    # `Total Receipts`; and the definitional bridge -- the booklet counts School Choice
    # Receiving in the total and every earlier worksheet does not, so the series is only
    # publishable while 10,776,998.00 - 94,912.00 still equals the 10,682,086.00 the 2024
    # Annual Town Meeting booklet prints for the same year. It also refuses if
    # model/finance.py's FY27 state aid base stops being the figure this series ends on.
    ('build_state_aid_series.py', ['--check']),
    # The free-cash page's series. It is the only generator here that reads FOUR
    # independent things and reconciles them against each other, so it catches the most
    # kinds of drift at once: the Division of Local Services' free cash proof (whose
    # eleven component rows must sum, to the cent, to the workbook's own `Identified Free
    # Cash July 1,` in all 45 town-years, and whose certified figure must chain year to
    # year); the WORKBOOK ITSELF, re-opened so every cited cell is asserted to hold the
    # cited amount — `source_ref` names the LABEL cell in column A and the amount is in
    # the year's own column, which is rule 13's exact shape; the TOWN's own undesignated
    # fund balance roll-forward out of two annual reports, cross-footed against both
    # totals each page prints and chained across the two documents, read from two
    # different instruments (OCR for FY2024, the PDF's text layer for FY2025); and five
    # figures `model/freecash.py` carries as TYPED constants, recomputed from the proof
    # they were copied out of. It also refuses on a `money_gaps` row it quotes by key
    # having been renamed, on a gap row whose stated figures have drifted from the data,
    # and on any of six meeting quotes no longer being present verbatim in the file it
    # is attributed to.
    ('build_free_cash_charts.py', ['--check']),
    # The special-revenue page's series. It re-derives the two checks that make the
    # dataset publishable rather than trusting the provenance note: every fund row's
    # forward + receipts − disbursements = carried, and every year's four columns
    # summed against the GRAND TOTAL the town printed. It refuses to write if either
    # fails or if the reconciliation join matches nothing, so this entry catches the
    # published file going stale AND a rebuild that silently emptied the table.
    ('build_special_revenue.py', ['--check']),
    # The what-stopped-being-funded page's series. It is the only generator here whose
    # subject is an ABSENCE, which is the shape rule 6 warns about: a line that goes to
    # zero and reappears renamed produces a −100% rate that looks like a finding. So this
    # entry catches five separate things going wrong. The stage name — the rows were
    # called `actual` until 7 September 2026 and read as the accounting system, so the
    # generator refuses to run if that name comes back. The two AGGREGATE pseudo-lines a
    # printed GRAND TOTAL produced, excluded by name, so a rename would leave the
    # exclusion either wrong or silently matching nothing. The rename pass, which must
    # match something: a detector that finds no renames in a book that demonstrably
    # renames lines is broken, not clean. The spelling-candidate pass, likewise. And the
    # four `money_gaps` rows the page quotes BY KEY, since a limit whose wording has been
    # edited out from under it renders as an empty box.
    ('build_stopped_funding.py', ['--check']),
    # The cut register, in two halves. The EXTRACTOR first: every `printed` and
    # `consequence` string on /cut-register is read out of a district document at a named
    # page, and this re-reads all of them on every run — a register whose quotations have
    # drifted from the pages they cite is rule 13's exact failure, and slide decks extract
    # differently when an extractor improves. It also asserts a row count for every one of
    # the twelve blocks it parses, because a parser that matches nothing and a document
    # with no cuts in it produce the same output.
    ('extract_stated_cuts.py', ['--check']),
    # Then the ANALYSIS. This entry catches six things a stale-file check would not,
    # because the generator asserts the structure each conclusion rests on: that the
    # FY2020 March list still names eight positions at a school and that the three the
    # April list dropped are still absent from it; that the middle school foreign language
    # FTE still falls and the high school's still does not, which is what makes the
    # withdrawal case a case; that the district's restated `P.S. Librarian` line is still
    # first funded in FY2020; that the FY2025 override statement still reconciles to its
    # own sentence — 19 full-time posts cut, 10 retained, nine left — and that all nine
    # still pair to the ESSER list; that the FY2026 world language cut is still visible
    # and at least one FY2026 row still goes the other way, since the page publishes both
    # on purpose. Plus the five meeting quotes, re-read verbatim, and the three
    # money_gaps rows it cites BY KEY.
    ('build_cut_register.py', ['--check']),
    # The grant-unwinding page's series -- DESE's split of every district dollar into the
    # general fund and grants/revolving. Four things fail here that nothing else would
    # catch. The year-on-year join, which must match functions: a join that matches
    # nothing looks exactly like a district that never moved money between funds. The
    # length of the district-total series, since a truncated one would publish a shorter
    # record as though it were the whole one. The five meeting quotes, re-read out of the
    # extracted minutes on every run -- a quote is a claim about a document and the
    # extractor can change what a document renders to. And the document's own sha256,
    # read from the archive manifest rather than typed, so a citation cannot lose its
    # hash silently.
    ('build_grant_unwinding.py', ['--check']),
    # Chapter 70's aid components, term by term, on /why-we-only-get-minimum-aid. This
    # entry catches more than staleness, because the generator asserts the identities the
    # page's prose rests on rather than just recomputing them: that the year's whole aid
    # increase still equals the minimum aid increment to the cent, that DESE's own
    # foundation-aid rule still reproduces the printed increment, that the target local
    # contribution still equals the combined effort yield in every year, that the town's
    # requirement still splits between its districts by foundation budget share, and that
    # Lunenburg still lands on a per-pupil rate several other districts share. Any one of
    # those ceasing to hold makes a sentence on the page wrong while every figure in it is
    # still a faithful copy of the workbook. It also re-reads the eight meeting quotes and
    # refuses to write if the five money_gaps rows it CITES have been renamed.
    ('build_minimum_aid.py', ['--check']),
    # What every OTHER district spends, on /what-other-districts-spend. This entry catches
    # far more than a stale file, because the generator asserts the structure the page's
    # sentences rest on and refuses to write if one has stopped holding: that the four
    # LEVELS in the finance table are still separable and the STATE row is still outside
    # the district set (a sum across them is an order of magnitude wrong); that
    # (1+spending) / (1+pupils) still equals (1+per pupil) for every district, which is the
    # page's central claim and is arithmetic rather than an argument; that the eleven
    # category gaps still SUM to the in-district gap, which is why the decomposition is
    # against one named district rather than a category-by-category median; that DESE's
    # per-pupil column still reproduces from its own dollar totals over TOTAL FTE on the
    # district row and IN-DISTRICT FTE on every other one -- two denominators under one
    # heading, and our own derived label is wrong about it; that DESE's average teacher
    # salary is still the Teachers function's spend per teacher FTE, so the page's
    # "salary times ratio" line stays labelled a definition rather than a discovery; and
    # that the net school spending measure still carries more than one STAGE, since rule 1
    # forbids differencing across it and the page splits on it. It also re-reads the seven
    # meeting quotes out of the extracted minutes and refuses to write if the four
    # money_gaps rows it CITES have been renamed.
    ('build_peer_spending.py', ['--check']),
    # The FOUR special education reports. One generator, four payloads, and this entry
    # catches far more than a stale file, because the generator asserts the structural
    # claims each page's prose rests on and refuses to write if one has stopped holding:
    # that DESE's own in-district and out-of-district counts still sum to the total it
    # prints beside them (the reconciliation that turned an unexplained disagreement in
    # `money_gaps` into a measured one); that the paraprofessional staffing rate still
    # reproduces from its own printed FTE and count in every year, which is the sole
    # reason that row is published while three others in the same table are not; that the
    # district's restated out-of-district budget line still ties to DESE's GENERAL FUND
    # column rather than to its all-funds column, which is the whole of the rule 11
    # finding; that the two starting placements in the trajectory are both still there,
    # since one of them is half a comparison; and that a quote attributed to a meeting is
    # still in the extracted minutes. Any one of those going quiet would leave every
    # figure on the pages a faithful copy of the source and a sentence beside it wrong.
    ('build_special_education.py', ['--check']),
    # The Monty Tech assessment. This entry catches far more than a stale file: the
    # generator refuses to write unless the DERIVATION the whole page rests on -- the
    # town's required local contribution minus its own school district's -- still equals
    # what DESE's own apportionment sheet PRINTS for FY2026, field for field, as the
    # district reprinted it in its FY2027 budget book; unless the town's total required
    # contribution is still bound by wealth rather than by the 82.5%-of-foundation cap,
    # which is the one sentence that makes "a child changing school does not change the
    # town's obligation" true; unless the four assessment parts still sum to the total
    # the district prints, in every year it prints them; unless the town's ledger and the
    # district's own book still agree on FY2026 to the cent; unless five figures stated
    # at three different public meetings still match the derived series to the dollar;
    # unless `report_monty_tech` is still the unusable table the page says it is; and
    # unless every figure read off a printed budget book is still on the line of the
    # extracted text this page cites. Any one of those going quiet leaves every number on
    # the page a faithful copy and a sentence beside it wrong.
    ('build_monty_tech.py', ['--check']),

    # The generator agrees with its own output by construction. This recomputes every
    # figure /where-students-go-instead renders by a SECOND route -- SQL against the raw
    # DESE table -- and asserts rule 2 structurally against the page's prose. A rival
    # generator for the same page got the in-district definition wrong and only a second
    # route found it.
    ('verify_where_students_go.py', []),
    # How far the money can be followed — the six rungs on /what-we-cannot-answer. It
    # quotes each rung's reason out of `money_gaps` and `money_edges` BY KEY and exits if
    # a key is not there, so this entry catches two things: the published file going
    # stale against the ledger, and a gap-register row being renamed out from under a
    # rung that would otherwise render with no reason on it.
    ('build_traceability_ladder.py', ['--check']),
    ('build_sitemap.py', ['--check']),
    ('check_github_mirror.py', []),
    ('classify_roster_roles.py', ['--check']),
    # What each of the 4,671 PEG-channel videos IS. The most derived thing in this
    # archive -- a language model's reading of a title -- so this entry catches four kinds
    # of drift nothing else would. A title stem with no decision recorded, which becomes
    # `undetermined` rather than a guess and is printed by name. A board named in the
    # classification that is not in the board registry, or a registry row naming a
    # sources/meetings/ folder that does not exist -- a registry pointing at nothing reads
    # as coverage. A run where the join to the decisions matches nothing, which looks
    # exactly like a channel with no meetings on it. And the overrides file, which is READ
    # and never written: without it every improvement to the classification would silently
    # discard every human correction, and nothing would report that it happened.
    ('build_youtube_classification.py', ['--check']),
    ('build_views.py', ['--check']),
    ('build_archive_guide.py', ['--check']),
    ('build_show_your_work.py', ['--check']),
    ('build_data_model_grids.py', ['--check']),
    # How much of the meeting archive can actually be SEARCHED, per board and year --
    # which is not how much of it has a text file beside it. A .txt exists for every scan
    # the extractor opened, holding only the `===PAGE n===` markers the extractor itself
    # wrote, and `search_minutes.py` counted every one of those as searched. A quarter of
    # the archive was reported as covered while contributing nothing a grep could match,
    # which defeats the single thing that coverage line exists to prevent. This entry also
    # catches the reverse: an OCR run that recovers documents and is never reflected in
    # what the tool tells a reader it searched. It refuses to write unless every count
    # foots against the town's own listing.
    ('build_minutes_searchable.py', ['--check']),
    ('build_meeting_register.py', ['--check']),
    # The meeting watch, added 8 September 2026. Three entries because there are three
    # different ways this can be wrong and only one of them is staleness.
    #
    #   * the state file can stop holding together -- a duplicate key, an event naming a
    #     document the state does not hold, a seeded row carrying a first_seen date it
    #     cannot know;
    #   * the detector can stop being DETERMINISTIC, which is TJ's requirement and the
    #     one failure a --check cannot see: a feed that announces the same meeting twice
    #     reproduces its output perfectly. It needs a test that runs the thing twice;
    #   * the published feed can go stale against the state behind it.
    #
    # None touches the network. The crawl is scripts/watch_meetings.py, run on its own.
    ('watch_meetings.py', ['--check']),
    ('check_meeting_watch_idempotent.py', []),
    ('build_meeting_feed.py', ['--check']),
    ('build_spending_vs_required.py', ['--check']),
    # The generator agrees with its own output by construction. This recomputes every
    # figure /what-the-state-requires-us-to-spend renders by a SECOND route -- both
    # DESE tables read whole and partitioned in Python rather than filtered in SQL --
    # and asserts the six values the PAGE derives at render time, which no generator
    # produces and nothing else would notice going wrong. It also asserts rule 1
    # mechanically: that the actual and budgeted stages are two disjoint collections
    # and that no chart names a dataKey capable of drawing one line through both.
    ('verify_spending_vs_required.py', []),
    ('split_large_text.py', ['--check']),
    ('build_question_bank.py', ['--check']),
    # DESE's three district-finance datasets: the registry of how to get them again, and
    # every stored sha256. The registry is the only place the portal page, the API
    # endpoint, the Socrata dataset id and the publisher's own filename are written down,
    # so a refresh that has to rediscover them is a refresh that will pick the wrong file.
    ('fetch_dese_finance.py', ['--check']),
    # The function-code extract. It refuses to write unless the hierarchy it asserts still
    # holds in all 5,479 district-years -- the ten in-district categories summing to their
    # own detail and then to IIII, TUIT detail plus ODTR summing to OODD, and IIII plus
    # OODD to TTPP -- and unless its two cross-checks against the RADAR workbook already
    # in the archive match SOMETHING. A rollup summed with its own detail produces a
    # plausible number four times too large, which is the exact shape this project has
    # shipped before.
    ('extract_dese_finance.py', ['--check']),
    # The Chapter 70 formula and the circuit breaker. It ties DESE's FY2026 Chapter 70
    # aid to what the TOWN'S OWN MUNIS revenue ledger records receiving -- two sources,
    # neither derived from the other -- and refuses to write if they part company. It
    # also splits two pairs of identically named columns that hold different numbers,
    # and carries whether each year's net school spending is actual or BUDGETED.
    ('extract_dese_state_aid.py', ['--check']),
    # The student datasets. Six DESE files, five tables: the sending and receiving
    # enrollment files hold the identical rows and are loaded once, and the extract
    # compares them row by row on every run so that a divergence stops the build rather
    # than quietly becoming two sources for one measurement.
    ('extract_dese_students.py', ['--check']),
    # The staffing datasets. SLOW -- it reads a 133 MB workbook of 1.77M rows, which is
    # about four minutes, and it is here rather than omitted because the alternative is
    # a rollup summed with its own detail going unnoticed. `dese_xlsx.py` is why it is
    # four minutes and not forty.
    ('extract_dese_staffing.py', ['--check']),
    ('build_db.py', ['--check']),
    ('check_archive_layout.py', []),
    ('check_moved_docs.py', []),
    ('build_source_index.py', []),
    ('sync_d1.py', ['--check']),
]


def _run(job):
    """One generator's --check, as a subprocess. Returns (label, rc, output)."""
    script, args = job
    path = os.path.join(ROOT, 'scripts', script)
    label = script + (' ' + ' '.join(args) if args else '')
    r = subprocess.run([sys.executable, path, *args], cwd=ROOT,
                       capture_output=True, text=True)
    return label, r.returncode, (r.stdout or r.stderr).strip()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('-j', '--jobs', type=int, default=min(8, (os.cpu_count() or 4)),
                    help='how many checks to run at once (default: CPU count, max 8)')
    ap.add_argument('--serial', action='store_true',
                    help='one at a time, for debugging a check that misbehaves')
    args_ns = ap.parse_args()

    jobs = [(s, a) for s, a in CHECKS
            if os.path.exists(os.path.join(ROOT, 'scripts', s))]

    # RUN THEM AT ONCE. This was a serial loop and it grew to 63 generators, which is
    # roughly half an hour -- long enough that it stops being run before a commit, which
    # is the only moment it earns anything.
    #
    # They are independent BY CONSTRUCTION: in --check mode every one reads its sources,
    # compares against its own output, and writes nothing. Nothing here shares state, so
    # nothing here needs ordering. The one thing concurrency costs is interleaved output,
    # which is why results are collected and printed in the order CHECKS declares them
    # rather than in the order they happen to finish -- a run whose output reshuffles
    # between invocations is hard to diff, and diffing runs is how a new failure is spotted.
    results = {}
    if args_ns.serial or args_ns.jobs <= 1:
        for job in jobs:
            label, rc, out = _run(job)
            results[label] = (rc, out)
    else:
        with cf.ThreadPoolExecutor(max_workers=args_ns.jobs) as pool:
            for label, rc, out in pool.map(_run, jobs):
                results[label] = (rc, out)

    failed = []
    for script, a in jobs:
        label = script + (' ' + ' '.join(a) if a else '')
        rc, out = results[label]
        mark = ' ok ' if rc == 0 else 'FAIL'
        tail = out.splitlines()
        print(f'  {mark}  {label:42s} {tail[-1][:60] if tail else ""}')
        if rc != 0:
            failed.append((label, out))

    print()
    if failed:
        print(f'{len(failed)} generator(s) no longer reproduce their output:\n')
        for label, out in failed:
            print(f'--- {label}')
            print('\n'.join(out.splitlines()[-6:]))
            print()
        print('Something a generated file depends on has moved or changed. That is the '
              'shape\nof nearly every defect in this project: a derived thing written '
              'down, and the\nthing it derived from moved underneath it.')
        return 1
    print(f'ok: all {len(CHECKS)} generators still reproduce what is committed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
