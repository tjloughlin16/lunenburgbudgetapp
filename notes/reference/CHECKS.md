# Running the checks

The full catalogue of checks and generators, one line each. Moved out of `CLAUDE.md`
on 27 October 2026 because the instruction files had passed Claude Code's 150,000-character
load limit; `CLAUDE.md` keeps a pointer here and the handful every session needs.

    python3 scripts/check_generated.py      # EVERY generator still reproduces its output
    python3 scripts/build_sitemap.py        # the sitemap, generated — pages AND endpoints
    python3 scripts/check_prerender.py      # is dist/ WHOLLY prerendered, or wholly not — a mixture is a killed
                                            #   build, and it looks exactly like a finished one
    bash scripts/check_phone_width.sh       # every route at a TRUE 400px viewport; fails if any page scrolls sideways
    (cd fy28 && npm run check:crumbs)       # every Menu page's breadcrumb sits where the Menu files it; runs in npm run build
    bash scripts/deploy_site.sh             # THE way to deploy (rule 10: only when asked): waits for any build, refuses a
                                            #   half-built dist (check_dist_complete.py + check_prerender.py), then deploys
    python3 scripts/check_dist_complete.py  # is every sitemap page in fy28/dist? A build caught halfway passes check_prerender
    bash scripts/tail_backlog.sh            # follow the minutes run -- whichever process-meeting*.log was written last
    python3 scripts/check_github_mirror.py  # the fallback for agents that cannot reach the site
    python3 scripts/check_sitemap.py        # the live sitemap, and every URL in it, answers
    python3 scripts/check_sitemap.py --submit    # ...and tell the IndexNow engines it changed
    python3 scripts/check_indexing.py       # ...and ask Google and Bing whether they DID index it
    python3 scripts/audit_provenance.py     # no projection reads actuals; model.json is fresh
    python3 scripts/backtest_rates.py       # assumptions against the district's own later budgets
    python3 scripts/build_source_index.py   # every source catalogued, every catalogued file present
    python3 scripts/check_source_links.py   # does the publisher's own copy still open
    python3 scripts/verify_source_copies.py # ...and if it opens, is it still the same bytes
    python3 scripts/source_cadence.py       # every source, its cadence, last look, next due -- and what changed
    python3 scripts/check_socrata_sources.py # have DESE's portal datasets changed since our copy
    python3 scripts/verify_workbook_twins.py # the untraced FY27 workbook against the traced one
    python3 model/export.py                 # regenerate model.json after any model/ change
    python3 scripts/classify_document_basis.py   # what produced each document's figures
    python3 scripts/extract_athletics_history.py # athletics, both sides, checked against its source
    python3 scripts/verify_athletics.py          # every figure in the athletics analysis
    python3 scripts/build_big_picture.py         # the one big report: the hole by year, overrides, drivers, building, the facts
    python3 scripts/build_big_picture.py --check # ...and fail if it is stale
    python3 scripts/build_one_big_report.py      # the story page, from sources/data/one-big-report-story.csv (TJ's sheet)
    python3 scripts/build_one_big_report.py --check
    python3 scripts/build_property_owners.py     # who owns the homes, for how long, and what the bill has done
    python3 scripts/build_property_owners.py --check
    python3 scripts/build_enrollment.py          # who is in the schools: DESE's headcount, FY1994 to today
    python3 scripts/verify_enrollment.py         # ...every figure in its conclusions, recomputed
    python3 scripts/build_homes_and_students.py  # homes and students: single-family parcels beside enrolment, FY1994 to today
    python3 scripts/build_board_posting.py       # the boards, compared: measure 1, which meetings got minutes, by board and fiscal year, on the town's own site
    python3 scripts/build_youth_sports.py        # youth sports and the town: what the leagues pay for the fields, the funds it lands in, what was said
    python3 scripts/build_circuit_breaker.py     # the circuit breaker, FY2006 to today
    python3 scripts/verify_circuit_breaker.py    # ...every figure in its conclusions, recomputed
    python3 scripts/build_ap.py                  # AP exams at the high school, SY2007 to today
    python3 scripts/verify_ap.py                 # ...every figure in its conclusions, recomputed
    python3 scripts/verify_if_students_leave.py   # the both-directions record on /if-students-leave,
                                                 #   recomputed from the database against a payload
                                                 #   built from DESE's workbooks
    python3 scripts/verify_free_cash_capital.py  # the capital section of the free cash analysis
    python3 scripts/build_show_your_work.py       # regenerate the method document
    python3 scripts/build_show_your_work.py --check   # fail if it is stale (audit_provenance runs this)
    python3 scripts/extract_munis_report.py --check   # every MUNIS glytdbud report, tied to its own GRAND TOTAL
    python3 scripts/extract_munis_school_ytd.py --check  # the school dept's MUNIS YTD reports (FY23-FY26 P13) and
                                                 #   the fund 1300 trial balance, from the PUBLISHED xlsx only --
                                                 #   never the private PDFs; tied to every total the sheet prints
    python3 scripts/check_function_crosswalk.py  # the Town's function coding against the district's book
    python3 scripts/build_db.py --check          # rebuild the analysis database; fail if a reconciliation drifts
    python3 scripts/export_ledger.py             # regenerate the ledger page's data from the database
    python3 scripts/fetch_dese_radar.py          # DESE's all-funds figures, fetched and catalogued
    python3 scripts/extract_dese_radar.py        # ...checked against DESE's own printed totals
    python3 scripts/verify_fy26_closeout.py      # every figure in the FY26 closeout analysis
                                                 #   ...and that the persona review in notes/process/PERSONAS.md was run
    python3 scripts/verify_fy26_closeout_town.py # ...and in its town-side companion
    python3 scripts/build_closeout_charts.py     # the charts that head both closeout analyses
    python3 scripts/build_school_surplus.py --all --check   # the school surplus by year (FY25, FY26), from the period-13 ledger -- UNLISTED;
                                                 #   one generator, --fy YEAR; build_fy25_school_surplus.py is a wrapper
    python3 scripts/verify_school_surplus.py --all # every figure in them, recomputed with Decimal off the CSV (and FY26's period 12
                                                 #   off lunenburg.db), a different route than the generator's
    python3 scripts/build_reports_index.py       # the /reports index, generated from what is on disk
    python3 scripts/build_reports_index.py --check    # ...and fail if an analysis is missing from it
    python3 scripts/build_reading_time.py        # how long every page takes to read, from the build; longest first
    python3 scripts/build_reading_time.py --check     # ...and that no short version grew past its 1,150-word budget, five minutes (a ratchet)
    python3 scripts/build_reading_time.py --strict    # ...and fail every page that declares no short version, once coverage is done
    python3 scripts/build_short_versions.py      # every page and the points its short version asks a reader to leave with (.md table + .csv)
    python3 scripts/build_short_versions.py --check
    CF_ANALYTICS_TOKEN=... python3 scripts/report_site_events.py   # the funnel: where people land, which door, was the fold opened, what search found nothing
    python3 scripts/build_blog.py                # the blog: ONLY the posts named in PUBLISHED
    python3 scripts/build_blog.py --check        # ...and that no unpublished one is anywhere on the site
    python3 scripts/verify_blog.py               # every sentence on a post, verbatim from the copy
    python3 scripts/build_blog.py --all          # ...all of them, locally, for review (gitignored)
    python3 scripts/build_blog.py --pdf          # ...and as PDFs, for somebody who cannot open the site
    python3 scripts/build_blog.py --measure      # does each 1200x630 share card fit, measured not eyeballed
    python3 scripts/build_analysis_pdf.py --all  # render the analyses to PDF for reading on paper
    python3 scripts/build_request_doc.py         # regenerate what is still outstanding from the Town
    python3 scripts/build_gross_budget_xlsx.py   # the gross budget spreadsheet, in the district's own shape
    python3 scripts/build_code_reconciliation_xlsx.py  # FY26 budget vs ledger, per line, summed by function code
    python3 scripts/build_discrepancy_review.py   # the categories of discrepancy, for review by the Town
    python3 scripts/minutes_decisions.py         # ...and every quote in it, checked against the minutes
    python3 scripts/check_sent_documents.py      # has anything we sent the Town drifted from what we hold
    python3 scripts/build_town_flow.py           # the whole town in the school model — in, out, held
    python3 scripts/build_who_decides.py         # every dollar in, where it lands, who decides
    python3 scripts/build_ledger_structure.py    # how the town's ledger is built and named
    python3 scripts/build_money_nodes.py         # every node in the school money graph, in/out
    python3 scripts/build_money_flow.py          # the money-flow diagram, drawn from the ledger
    python3 scripts/build_money_flow.py --check  # ...and fail if it is stale
    python3 scripts/build_data_model_grids.py    # the completeness grids in notes/reference/data-model/*.html
    python3 scripts/build_data_model_grids.py --check   # ...and fail if either has gone stale
    python3 scripts/build_views.py               # the browsable views of the archive, by year and by group
    python3 scripts/build_views.py --check       # ...and every symlink in them still resolves
    python3 scripts/check_archive_layout.py      # is every document where the layout says, under the right name
    python3 scripts/check_moved_docs.py          # every address published before the reorg still resolves
    python3 scripts/annual_report_progress.py   # WHICH ANNUAL-REPORT YEARS ARE DONE, and which is next.
                                             #   A year is done when EVERY financial page is `proven`;
                                             #   row-level status is a different question. --next gives
                                             #   the bare year; --check refuses off a stale page map
    python3 scripts/extract_tables.py <dataset>  # the annual reports, one table family at a time
    python3 scripts/verify_report_tables.py      # every reconciliation those extracts state, recomputed
    python3 scripts/build_report_tables_provenance.py  # what the generic extracts are, generated from them
    python3 scripts/build_archive_guide.py       # the annual-report entry point and the backup manifest
    python3 scripts/build_archive_guide.py --check    # ...and fail if either has gone stale
    python3 scripts/build_dataset_provenance.py  # every dataset row joined to the document it came from
    python3 scripts/build_api.py                 # publish the database and the read-only JSON API
    python3 scripts/build_agent_endpoints.py     # regenerate llms.txt and the published data endpoints
    python3 scripts/extract_department_rosters.py  # Police and Fire by name and RANK, off the column pages
    python3 scripts/extract_board_chairs.py     # who chaired each board, from the body's own report
    python3 scripts/build_org_charts.py         # every department, board and school as an org chart, by year
    python3 scripts/build_tenure.py             # how long people stay and how many leave, by body — counted in
                                                #   the years each body PUBLISHED, with both edges of the archive
                                                #   marked as censored rather than short
    python3 scripts/build_tenure.py --check
    python3 scripts/fetch_staff_directory.py --if-changed   # the TOWN's directory; a snapshot only when it moved
    python3 scripts/extract_staff_directory.py  # who works for the town TODAY, off its own staff directory —
                                                #   the only people source here not read out of an annual report
    python3 scripts/fetch_school_staff_directory.py --if-changed  # the DISTRICT's six sheets, discovered off its
                                                #   own directory page; both fetchers run WEEKLY from refresh.py,
                                                #   because both publishers overwrite in place and the archive's
                                                #   snapshots are the only history of either that will exist
    python3 scripts/fetch_school_staff_directory.py --check
    python3 scripts/extract_school_staff_directory.py   # the district's people as each listing prints them, and
                                                #   who is printed TWICE — never merged, which is the point
    python3 scripts/extract_school_staff_directory.py --check
    python3 scripts/build_body_crosswalk.py      # one body, two pages: the org chart joined to the money page, so
                                                #   /org-charts and /departments link both ways. The name join
                                                #   lives HERE and both payloads read it
    python3 scripts/build_body_crosswalk.py --check   # ...and fails if the join matches fewer bodies than it did
    python3 scripts/build_report_filing.py      # which bodies file an annual report, which say `No Report
                                                #   Submitted`, and which the town never asked
    python3 scripts/build_data_problems.py      # EVERY KNOWN PROBLEM WITH THE DATA in one place: a defective
                                                #   document, a thin reading of ours, a question nobody answered
    python3 scripts/build_roster_completeness.py # how many of a body's people the chart HOLDS against a count
                                                #   the town itself published — the only way to KNOW a chart is short
    python3 scripts/build_personnel_discrepancies.py  # ...and where the three people records cannot be
                                                #   reconciled — INTERNAL, notes/generated/
    node fy28/../scripts/check_org_html.mjs     # ...and every unit RENDERED and read back out of the HTML, from
                                                #   fy28/, as a citizen sees it: heads first, nobody above their chief
    python3 scripts/check_org_charts.py         # ...and the SHAPE of every body asserted: headless, many-heads,
                                                #   doubled, a heading read as a person, a grouping with one value
    python3 scripts/classify_roster_roles.py    # what job each printed roster title is
    python3 scripts/classify_roster_roles.py --check   # ...and fail if it is stale
    python3 scripts/sync_d1.py                  # push the database to D1 — INCREMENTAL: only
                                                #   tables whose DIGEST differs are sent, at most
                                                #   --limit rows a run (default 40,000), and what
                                                #   does not fit is named and waits. A TABLE BIGGER
                                                #   THAN THE LIMIT IS LOADED IN SLICES under a
                                                #   staging name and swapped in whole when complete
                                                #   (d1_incremental.plan_staged). THE DAILY REFRESH
                                                #   RUNS THIS (step 9, since 24 October 2026); by
                                                #   hand only to publish before tomorrow. --plan
                                                #   says what is owed without sending anything
    python3 scripts/sync_d1.py --check          # ...and fail if the two copies disagree;
                                                #   SKIPPED while tables are still deferred,
                                                #   because counting a table D1 does not hold
                                                #   yet errors rather than returning zero
    python3 scripts/build_search_index.py       # one FTS index over pages, posts, documents, minutes, transcripts
    python3 scripts/build_search_index.py --check    # ...and fail if any input has changed since
    python3 scripts/sync_search_d1.py           # push it to D1, INCREMENTALLY, inside the shared
                                                #   100,000-writes-a-day budget; never the same day
                                                #   as a full sync_d1.py
    python3 scripts/sync_search_d1.py --check   # ...and fail if the two copies disagree
    python3 scripts/write_recording_minutes.py <board> <date>   # OUR minutes of one recording, via claude -p
    python3 scripts/write_recording_minutes.py --check    # every minutes file parses, links, and matches its transcript
    python3 scripts/reconcile_minutes.py                  # ours against the town's minutes: caption errors resolved, differences flagged
    python3 scripts/extract_official_votes.py --board X   # the votes in the TOWN'S minutes, each with its verbatim quote (claude -p, haiku); joined with ours by build_boards
    python3 scripts/extract_official_votes.py --check     # every quote verbatim in the minutes it came from
    python3 scripts/ocr_scanned_minutes.py --limit 40     # scanned minutes read by macOS Vision, newest first; local, free; marked ===OCR=== and never re-extracted over
    python3 scripts/ocr_scanned_minutes.py --check
    python3 scripts/process_meeting.py --status          # THE BACKLOG: how many meetings still need our minutes, the
                                                         #   town's minutes read structured, or a reconcile
    python3 scripts/process_meeting.py --next 10 --dry-run   # the next 10, NEWEST FIRST: which steps, the estimate, the ceiling
    python3 scripts/process_meeting.py --next 10         # ...do them. THE ONLY WAY TO WORK THIS BACKLOG, and only when TJ
                                                         #   asks, with the number he gives. Serial, locked, ceiling 2x the
                                                         #   estimate; stops on a limit, no progress on disk, 3 failures, or
                                                         #   build/STOP-METERED. sweep_backlog.py is superseded and refuses
    python3 scripts/read_order.py --summary              # transcripts FIRST: which meetings write ours before the town's are read
    python3 scripts/build_agentic_backlog.py              # every machine-reading stream: done and to do, last two years vs older -- notes/generated/AGENTIC-BACKLOG.md
    python3 scripts/extract_document_timestamps.py        # when each agenda and set of minutes was MADE, from the document's own metadata — a LOWER bound on posting
    python3 scripts/build_meeting_register.py             # THE MEETING RECORD: one row per board and date, every artifact's address, the two legal timestamps
    python3 scripts/build_meeting_register.py --unnoticed --since 2025-01-01   # ...meetings the AgendaCenter does not list, to CHECK
    python3 scripts/build_recording_minutes.py            # the /what-was-said payload, from the files
    python3 scripts/build_recording_minutes.py --check    # ...and fail if it is stale
    python3 scripts/build_fund_owners.py --seed           # the ACCOUNT REGISTRY: every measure a held report prints, with an owner
    python3 scripts/build_fund_owners.py --check          # ...and fail if a report prints one the registry lacks, or an owner is nobody
    python3 scripts/build_finance.py                      # every measure by owner, FY26 figures beside the annual-report history: /accounts, /departments, /boards/<slug>/finance
    python3 scripts/build_finance.py --check
    python3 scripts/extract_parks_myrec.py --check         # the Parks registration system's FY2025 sales, tied to the printed totals
    python3 scripts/build_parks.py                        # Parks & Recreation: the department, its fund since FY2011, its sales, its grounds bid
    python3 scripts/build_parks.py --check
    python3 scripts/build_monty_tech_topics.py --check   # the Monty Tech hub (/monty-tech) and Monty Tech per pupil; the long
                                                #   report is /analysis/monty-tech. Reads per_pupil_measures.py, which reads DESE's
                                                #   by-function workbook (~90s cold, cached in build/cache by sha256) and the
                                                #   Census Bureau's FY2024 school finance table, asserting both files' identities
    python3 scripts/build_suggested_reports.py --check   # reports a meeting suggests, merged across meetings -> the backlog
    python3 scripts/build_agenda_threads.py --check      # agenda items matched to threads by the threads' own patterns (no model)
    python3 scripts/build_boards.py                       # one page per board: upcoming, recent, every vote, time, budget calendar
    python3 scripts/build_boards.py --check
    python3 scripts/build_budget_feed.py                  # everything budget-related across every board, on one page
    python3 scripts/build_budget_feed.py --check
    python3 scripts/build_feeds.py                        # Atom feeds under /feeds/: one per board, the budget feed, and all -- what a resident subscribes to
    python3 scripts/build_feeds.py --check
    python3 scripts/write_budget_state.py --since DATE     # the deficit, the cuts, the proposals as put on the record, per meeting (claude -p)
    python3 scripts/write_budget_state.py --check
    python3 scripts/extract_scenario_lines.py            # every line the FY27 scenarios differ on -- the full cut list, footed to the documents
    python3 scripts/extract_scenario_lines.py --check
    python3 scripts/build_budget_season.py fy27             # the season as a status board, from sources/data/budget-seasons/fy27.csv; every citation resolved
    python3 scripts/build_budget_season.py fy27 --check
    python3 scripts/build_budget_season.py fy28                  # the LIVE season: warnings straight from the record, figures proposed into fy28.proposed.csv
    python3 scripts/build_budget_feed.py --as-of 2026-05-16 --out fy28/public/data/budget-feed-fy27.json   # a season replayed
    python3 scripts/fetch_board_pages.py                  # every board's town page: charter text, members, meetings, Facebook
    python3 scripts/fetch_dls_tax_bills.py                # DLS average single-family tax bill, eleven towns, by script
    python3 scripts/fetch_dls_property.py                 # DLS assessed value by class, certified new growth (eleven towns) and HEALTH INSURANCE spending (all 351), by script
    python3 scripts/build_health_options.py               # what c.32B lets a town do about health insurance, each option linked to its section, beside every town's spending
    python3 scripts/build_health_options.py --check
    python3 scripts/build_commercial_base.py             # the commercial base as the state certifies it: size, share, and what was BUILT, with conclusions
    python3 scripts/extract_dls_overrides.py            # every Proposition 2.5 question the state records, 351 towns
    python3 scripts/extract_dls_overrides.py --check    # ...tied to the identity the workbook states about itself
    python3 scripts/build_town_comparison.py            # HOW LUNENBURG COMPARES: the six towns it borders (computed from
                                                        #   boundary polygons), the peers this project chose, the towns the
                                                        #   MATH picks out of all 351 -- matched twice, on what a town IS and
                                                        #   on what it DOES -- and where its children are actually schooled
    python3 scripts/build_town_comparison.py --check
    python3 scripts/verify_towns_like_us.py            # ...every headline figure recomputed by a different route, and
                                                        #   every sentence it QUOTES still verbatim in the minute it cites
    python3 scripts/build_app_metrics.py                  # what the project holds, counted, for sharing
    python3 scripts/build_no_captions_report.py           # which meeting recordings have captions disabled, with links
    python3 scripts/build_app_metrics.py --check          # ...and fail if it has drifted
    python3 scripts/textract_pages.py FILE --pages N-M --dry-run   # AMAZON TEXTRACT: page tables with row/col, BILLED IN
                                                #   DOLLARS through a meter with a latching cut-off; drop --dry-run to send
    python3 scripts/textract_spend.py --status  # ...its spend: 24 hours, month vs the $50 cap, AWS's own figure, the latch.
    python3 scripts/searchable_pdfs.py --status  # SEARCHABLE COPIES of PDFs with picture pages: surveyed, waiting, built
    python3 scripts/searchable_pdfs.py --quote   # ...what reading every waiting page with Textract would cost
    python3 scripts/searchable_pdfs.py --new     # ...the refresh step: survey, Textract (metered), build, verify, push
    python3 scripts/searchable_pdfs.py --check   # ...every built copy rebuilds byte for byte AND the bucket holds it
                                                #   Setup, and redoing it on another machine: notes/process/TEXTRACT-SETUP.md
    python3 scripts/generate_report.py --status # AUTO-GENERATION TRIALS: every suggested report an agent drafted, its
                                                #   status, cost and verdict. Started by the dashboard's Generate button;
                                                #   the process and what would let it run alone: notes/process/AUTO-GENERATING-REPORTS.md
    bash scripts/status.sh                      # THE INGESTION DASHBOARD: what is running, what is queued,
                                                #   what is left, and where today's refresh looked. Local,
                                                #   gitignored, refreshes itself every 20s. --once to just write it
    python3 scripts/build_ingest_status.py --watch   # ...keep it fresh without opening it
    python3 scripts/refresh.py                  # THE DAILY RUN: watch the town and the channel, fetch what is new,
                                                #   write minutes inside the policy, rebuild, push the search index
    python3 scripts/refresh.py --deploy         # ...and build and deploy the site (rule 10: only when asked)
    python3 scripts/refresh.py --dry-run        # ...watch only, write nothing
    python3 scripts/watch_youtube.py            # the channel's RSS feed; record what is NEW
    python3 scripts/watch_youtube.py --check    # ...and that its state holds together
    python3 scripts/build_question_bank.py      # 107 questions, each run against the database
    python3 scripts/build_question_bank.py --check   # ...and fail if one stops answering
    python3 scripts/watch_meetings.py --seed     # adopt what we hold, announcing nothing
    python3 scripts/watch_meetings.py            # crawl the town; report only what is NEW
    python3 scripts/watch_meetings.py --check    # ...and that the watch state holds together
    python3 scripts/check_meeting_watch_idempotent.py  # run it twice; one result, not two
    python3 scripts/build_meeting_feed.py        # what is coming, and what minutes just appeared
    python3 scripts/build_meeting_feed.py --check     # ...and fail if the feed is stale
    python3 scripts/split_large_text.py         # long documents, in parts a caller can read
    python3 scripts/split_large_text.py --check  # ...and fail if a long one has no parts
    python3 scripts/build_readme.py             # the repository's front door, counts derived
    python3 scripts/build_readme.py --check      # ...and every path it promises is in git
    python3 scripts/check_archive_backed_up.py   # THE GATE: is every document this tree holds in the
                                                #   bucket, read back and compared? Nothing destructive may
                                                #   run while one is not. Offline, under a second
    python3 scripts/check_archive_backed_up.py --push   # ...and back up whatever is not
    python3 scripts/takedown.py --status        # documents registered for REMOVAL: served 410? still in the bucket?
    python3 scripts/takedown.py --dry-run       # ...exactly what --delete would do, and what it refuses
    python3 scripts/ingest.py --status          # documents in flight: staged, not yet in the bucket
    python3 scripts/ingest.py --secure          # ...finish them (push, read back, file, catalogue)
    python3 scripts/check_manifest_history.py   # has any document LEFT the index? A dropped row does not
                                                #   delete an object, it ORPHANS it — the bucket cannot be
                                                #   listed, so the manifest is the only thing that names it
    python3 scripts/check_manifest_history.py --record   # ...register an orphan that cannot be undone
    python3 scripts/sync_archive.py --manifest   # hash every file in sources/; APPEND-ONLY for documents
    python3 scripts/sync_archive.py --push       # upload what is new, read it back, compare sha256
    python3 scripts/sync_archive.py --pull       # a fresh clone gets the documents themselves
    python3 scripts/check_archive_storage.py     # manifest vs bucket, reconciled both ways
    python3 scripts/check_archive_urls.py --base URL  # every /docs/ address, hashed against the manifest


## Scripted `claude -p` calls

**Every scripted `claude` call goes through `scripts/claude_lean.py`** (`claude_lean.run(argv, add_dirs=[...], **subprocess_kwargs)`). It adds `--setting-sources ""`, `--strict-mcp-config` and `--no-session-persistence`, one `--add-dir` per directory the call must read, and runs in an empty directory under `build/`, so CLAUDE.md, memory, settings and MCP servers do not ride along in the first turn. Not `--bare`: it refuses OAuth, and this is a Max login. Settings no longer load, so pass permissions as flags (`--tools`, `--allowedTools`) and use absolute paths in prompts.

Measured 29 October 2026, haiku, one-word prompt, `--tools Read`, cache-creation tokens:

    from the repo, no other flags                          82,615 tokens   $0.0165
    + --setting-sources "" --strict-mcp-config              5,134 tokens   $0.0010
    + cwd = an empty directory                             ~1,700 tokens   $0.00014

Not converted, because they need the repo's own context: `generate_report.py` (sandboxed, edits a worktree) and `triage_refresh.py` (`acceptEdits` on the repo).
