# The town's staff directory

**Where it came from.** `https://www.lunenburgma.gov/m/directory`, the Town of Lunenburg's
own staff directory, fetched 22 September 2026. The landing page renders only the list of
DEPARTMENTS into its HTML; the people sit behind a tab that needs a click, so a headless
fetch of that address returns no names at all. Each department has its own address and
those render fully, so what is held here is one page per department:

    https://www.lunenburgma.gov/m/directory/department?did=<N>      28 pages

**The publisher's own name for it.** *Staff Directory*, under Departments on
lunenburgma.gov. Built on CivicEngage; the `did` is the town's own department identifier
and is what a later fetch should use to compare like with like.

**ONE FOLDER PER FETCH, AND NOTHING IS EVER OVERWRITTEN.** The town updates this page in
place. There is no FY2026 version of it anywhere, and the day somebody edits a page the
person who held that job before is gone from the internet — so the only history of who
worked for Lunenburg is the one kept here. Snapshots live under
`staff-directory/<fetch-date>/did-N.html`, the catalogue carries the date in every label,
and `extract_staff_directory.py` reads EVERY snapshot rather than the newest. A year
missing from the dataset is a year nobody fetched, and it will stay missing for ever.

**What we read out of it.** `sources/data/staff-directory.csv` — 147 people across 27
departments, each with the title the town prints beside their name, by
`scripts/extract_staff_directory.py`.

**WHAT IT IS AND IS NOT.** A contact list, not an organisational chart. It carries no rank
order, no reporting line and NO DATE — it is whoever the town is publishing today, which
makes it a snapshot rather than a series, and a later fetch will silently differ. Where it
disagrees with a department's own published chart the chart wins: the directory lists
Animal Control as its own entry, and the Police Department's FY27 budget presentation puts
`ACO Kathy Comeau` under the Chief.

**Why it was worth fetching.** Everything else this project knows about who works for the
town is read out of ANNUAL REPORTS, and a department that files none is invisible to both
of the other sources. Four departments appear here and in neither: Accounting, Human
Resources, Facilities/Grounds/Recreation, and Public Access Cable.
