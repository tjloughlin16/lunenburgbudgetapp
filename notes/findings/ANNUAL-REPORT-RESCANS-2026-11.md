# The town replaced the 1997 and 1999 annual reports on 3 November 2026

Found 10 November 2026, by comparing the town's Annual Town Reports shelf
(`https://www.lunenburgma.gov/838/Annual-Town-Reports`) with
`sources/town-annual-reports/index.csv`. 66 of the 68 shelf links matched an address we hold;
these two did not.

| year | our copy | town's current copy |
|---|---|---|
| 1997 | `DocumentCenter/View/4523`, `4523-1997-annual-town-report.pdf`, 100 pages, PDF CreationDate 2026-10-24, sha256 `ddef7192c885...`. **Upstream now 404** | `DocumentCenter/View/4615`, publisher filename `1997 Annual Town Report_1.pdf`, 104 pages, CreationDate 2026-11-03, 4,997,301 bytes, sha256 `827458585b8e27de6b73c6262b7e0368fc7ac556adf57904414378da2366b2ef` |
| 1999 | `DocumentCenter/View/4525`, `4525-1999-annual-town-report.pdf`, 110 pages, CreationDate 2026-10-25, sha256 `912bc582b45e...`. **Upstream now 404** | `DocumentCenter/View/4616`, publisher filename `1999 Annual Town Report_1.pdf`, 112 pages, CreationDate 2026-11-03, 5,689,038 bytes, sha256 `ebccc6b28366520d05bd0949acbabcdd02eab9208fe34785d749580ad902d059` |

Both are image-only scans (no text layer), Creator `RICOH IM C3000`.

## What changed: pages were added, none removed

Every page was rendered to a 24x32 grey thumbnail and the two editions were aligned with an
edit-distance alignment (match cost = mean pixel difference, insert/delete cost 25). Every
old page matched a new one (median difference 1.9 for 1997, 0.9 for 1999). Pages present
only in the NEW edition, in the new edition's numbering:

- **1997: pp 97, 99, 100, 101.** The town employees' *Report of Wages Paid*: the list's
  first page (`TOWN OF LUNENBURG / TOWN EMPLOYEES / REPORT OF WAGES PAID`, ATIO ... GENDRON),
  a G-O page, a page that looked blank at thumbnail size (check it), and the P-Z page ending
  `TOTAL TOWN EMPLOYEES 155   TOTAL TOWN GROSS WAGES $2,103,949` (read off the render at the time; extracted since, see *Outcome*). Our first 1997 text
  contained no `TOTAL TOWN EMPLOYEES`.
- **1999: pp 108, 109.** The school staff wage list, printed page numbers 105 and 106
  (Okerman, Papadopoulos, Stafford, Xerras... none of whom appear in our 1999 text).

So the first scans the town posted (late October) dropped pages, and the rescans restore
them. Every page reference in `sources/data/report-tables/1997/` and `/1999/` after the first
insertion is now off by the number of pages inserted before it.

## What would not have caught it

- `verify_source_copies.py` follows only the recorded address. It would have seen a 404 around
  2 December and recorded `unreachable`, which reads as a host problem, not a replacement.
- The quarterly `watch_documents.py --annual-reports` would have filed 4615/4616 as NEW,
  unrelated documents: two "1997 Annual Town Report"s with nothing linking them, and nothing
  re-reading the added pages.
- Separately, the 15 FY2011-FY2025 reports have never been compared at all:
  their `upstream` holds two space-joined URLs and `verify_source_copies.py` passes the whole
  string to curl (`code 000`, `unreachable`, in `copy-status.csv`).

## Outcome (commit `dff3cb6f6`, 10 November 2026)

Both rescans were landed under new keys and re-read; the old keys stay in the bucket,
registered in `archive-orphans.csv`. The commit message carries the per-year results: the
1997 town wage list now foots to its printed total, the 1999 school list's restored pages
close its shortfall, and 1997 p55 and 1999 p65 moved from blocked to proven. The detection
gap above is still open.
