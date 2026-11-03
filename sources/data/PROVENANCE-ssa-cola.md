# Social Security cost-of-living adjustments, 1975-2026 (`ssa-cola.csv`)

**Publisher:** Social Security Administration, Office of the Chief Actuary.
**Address:** https://www.ssa.gov/oact/cola/colaseries.html — page title *Social Security
Cost-Of-Living Adjustments*.

**How it reached us:** TJ copied the table from that page and pasted it into a session on
2 November 2026. Our automated fetch of the page was refused (HTTP 403 to WebFetch; a 402-byte
response to curl), so no copy of the page itself is held. The CSV is a transcription of the
pasted table, year for year; nothing is computed.

**What a row means:** the COLA percentage SSA prints for that year. SSA's year is the year the
adjustment was **determined**, effective for December and first **paid the following January**
— so the 2025 row (2.8%) is in January 2026 payments, and the 2026 row (3.6%) in January 2027.

**Known gap:** the table prints a footnote marker `a` against 1999; the footnote's text was not
in the pasted copy. Read it on the page before quoting the 1999 figure.

**Check:** 52 years, 1975-2026 consecutive. To verify against the publisher, open the address
above and compare row by row.
