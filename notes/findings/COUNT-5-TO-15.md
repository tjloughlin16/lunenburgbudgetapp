# Why "5 pages left" became "15 pages left"

27 September 2026. Nothing broke, nothing was lost, and no work was undone. A number that
had been wrong for four days became right. This is the whole of it, in the shortest form
it can be told.

---

## The one-sentence version

**We read 11 new pages, and at the same time found out that 10 pages we thought were
finished had been emptied that morning.** 16 − 11 = 5 was the arithmetic everybody could
see. The 10 was invisible, and it had been invisible since about 11 a.m.

## Why the 10 were invisible

The counter answers one question: *how many financial pages of the annual reports have
been read?* It decides a page is "read" by asking whether any dataset mentions that page.
It looks in **two** places and accepts either:

    1. the CSV files in sources/data/          <- the actual data
    2. lunenburg.db                            <- a COPY of those CSV files

The database is a copy, rebuilt from the CSVs from scratch whenever anybody runs
`build_db.py`. That is a good design and it is not the problem. The problem is that the
counter treats the copy as an independent witness.

## The timeline

| when | what happened | CSV says | database says | counter reports |
|---|---|---|---|---|
| 23 Sep | `receivables.csv` holds 523 rows, covering 10 pages. Database built from it. | 10 pages have rows | 10 pages have rows | read |
| **27 Sep, morning** | `extract_receivables.py` was tightened to write **only rows that prove against the totals the pages themselves print**. 342 rows failed and were deleted. `receivables.csv` drops to 181 rows and those 10 pages lose every row they had. **Nobody rebuilt the database.** | 10 pages have NO rows | 10 pages have rows *(stale)* | **still read — wrong** |
| 27 Sep, afternoon | 11 more pages genuinely read. | | | 469 read, 5 left |
| 27 Sep, evening | `build_db.py` run as part of a cleanup. The copy catches up. | 10 pages have NO rows | 10 pages have NO rows | **459 read, 15 left — right** |

The counter was asking two witnesses and believing whichever said yes. One of them was
four days out of date, so it kept saying yes about rows that no longer existed anywhere.

## What the numbers actually were

|  | read | left |
|---|---:|---:|
| before today, as reported | 458 | 16 |
| before today, **the truth** | 448 | 26 |
| after 11 pages, as reported | 469 | 5 |
| after 11 pages, **the truth** | 459 | 15 |

The 11 pages are real and in every row of that table. The only thing that changed at the
end of the day is that 10 credits the count had no right to were withdrawn.

## The part that is easy to miss, and is the good news

Those 10 pages were emptied **on purpose**, that morning, by somebody making the archive
stricter. The old rows did not add up to the totals printed on the pages they came from.
Publishing them would have meant publishing figures that the source document contradicts.
Deleting them was right.

So the sequence is: the archive got more honest in the morning, and the *counter* caught up
with it twelve hours later.

## Why no check caught it

Every check here asks "does this output still reproduce from its inputs?" The database
reproduced perfectly — from the inputs **as they were on 23 September**. Nothing anywhere
compared the database to the CSVs as they are *now*. The staleness was not a broken thing;
it was an old thing, and nothing was looking at its age.

It was found because a person read the dashboard, saw a number move the wrong way, and
asked why. That is the fourth time this year that the finder was a person rather than a
check.

## What was changed so it cannot happen again

1. **`build_db.py` now records what it was built from.** Every CSV it reads is hashed into
   a `build_inputs` table, with the build time in `build_meta`. 116 files on the first run.

2. **`scripts/db_freshness.py` is the single place that asks "is this database still
   true?"** It compares those hashes against the files on disk now. Offline, milliseconds.
   It compares **content hashes, not timestamps** — a timestamp moves every time any
   generator rewrites a file byte-for-byte, so a time-based check would cry stale hourly
   and be ignored inside a day.

3. **The counter refuses to publish rather than publish something stale.** Any figure taken
   partly from the database is now gated:

       python3 scripts/db_freshness.py          # ok, or names the files and the remedy

   Proven able to fail: altering one byte of `receivables.csv` makes both the checker and
   `map_annual_report_pages.py` exit 1 and refuse to write.

4. **"Unread" was carrying two different facts, and now says which.** A page nobody has
   opened needs somebody to read it. A page an extractor read and then **refused** needs
   the extractor fixed — the page is legible and the reader exists. All 10 of these were
   the second kind and the queue called them the first, which describes a job nobody has
   started and is the opposite of true. There is now a third state, `refused`, and:

       459 of 474 pages READ
        15 of 474 pages READ AND REFUSED -- the rows would not prove
         0 of 474 pages NOT YET READ

   **Every page in the archive has been looked at.** None is waiting for a first reading.

5. **`receivables-refused.csv` exists**, because the refusals were printed to a terminal
   and lost. Seven other extractors already followed that convention; this one did not.

6. **Every count on the backlog page carries its unit**, and the headline no longer adds
   13,222 rows to 2,880 sets of minutes to 15 pages and calls the result 18,001.

## What to take from it

The failure is the one this repository's own rules open with: **something derived was
quoted as evidence, after the thing it derived from moved.** The derived thing was a
database, which is the last place anybody looks for that mistake, because a database feels
like a source. It is not. It is a copy with a date on it, and it had been the wrong date
since breakfast.
