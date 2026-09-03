# Producing this export without the confidential parts

*A one-page procedure for whoever runs the MUNIS export. Written so the person doing it does
not have to make judgement calls about what is confidential.*

---

## The problem in one sentence

The MUNIS **Journal Detail Export** carries 25 columns, and **two of them can contain a
person's name**. The other 23 cannot. So this is a field-selection question, not a
document-review question — nobody has to read the rows and decide.

| column | | |
|---|---|---|
| **X** | `VDR NAME/ITEM DESC` | **Omit.** On a special education line this is often a parent being reimbursed, not a company. |
| **Y** | `COMMENTS` | **Omit.** Free text, so nothing constrains what it can contain. |
| A–W | `ORG` `OBJECT` `PROJECT` `ACCOUNT` `DESCRIPTION` `YEAR` `PER` `JOURNAL` `EFF DATE` `POST DATE` `SRC` `T` `REF1` `PROJECT STRING` `PO/REF2` `REF3` `REFERENCE` `AMOUNT` `P` `CHECK NO` `WARRANT` `VOUCHER` `CARRY FORWARD` | **Send.** No person is named in any of these. |

---

## Best: change the export, once

If the Journal Detail Export field list can be edited and saved as a named layout, **remove
columns X and Y from the layout and save it**. Every future export is then correct by
construction — no per-file step, and nothing to remember or forget in a year's time.

This is worth ten minutes once. Everything below is a workaround for not having done it.

## If the layout cannot be changed: delete in Excel, save as CSV

1. Open the export in Excel.
2. Select columns **X** and **Y**. Right-click → **Delete**.
3. **File → Save As → CSV UTF-8 (Comma delimited).**

**Delete the columns; do not hide them.** A hidden column is still in the file and opens
with one click. And **save as CSV, not .xlsx** — an .xlsx keeps hidden columns, hidden rows,
hidden sheets, cached values and document properties, none of which are visible in the window
you are looking at. A CSV is only what you can see.

*This is not a hypothetical caution.* A workbook already in this archive hides nine columns,
including a whole fiscal year, and nothing on screen said so.

## If it can only come out as PDF, say so first

Do not draw boxes over the names. A black rectangle in a PDF sits on top of text that is
still in the file and comes straight back out with any text extractor. If PDF is the only
option, we will take aggregate figures instead.

---

## Better still: send the vendor **number** instead of the name

If MUNIS can put the vendor number in place of the vendor name, please do. It answers every
question this project actually asks — how many distinct payees, is this the same payee as
last year, is this a placement or a transport contract — and it names nobody.

One caveat, stated so it is not a surprise: a vendor number is a **stable pseudonym, not
anonymity**. If any single payment's payee is learned some other way, every row sharing that
number is identified with it. It is a large improvement over a name and it is not the same
as the name being absent.

---

## Please send one month first

Send a **single month** before the full range. If the field list is wrong, the mistake is one
month of data instead of several years, and it is found in a day.

We check the file's **column headers only** on arrival — a script reads the header row and
reports which columns are present. It does not read the rows.

---

## If something confidential arrives anyway

Agreed in advance, so that it is a procedure and not an accusation:

1. We stop, and do not open, copy, process or forward the file.
2. We tell you the same day, naming the file and the column.
3. We delete our copy and confirm the deletion in writing.
4. We ask for a re-export. Nothing from the original is used.

Nothing confidential is ever committed to our repository or published on the site. Our
pipeline refuses to record a file carrying these columns, before the point where anything
becomes public.

---

## One thing we would rather you check than us

Column **U** (`WARRANT`) and column **T** (`CHECK NO`) name nobody by themselves. But if the
town publishes warrants that list payees, those two columns are a **join key** back to a
name — the confidential field would be removed from our copy and still be recoverable from a
public document.

We do not know whether Lunenburg's published warrants carry payee names, and you do. If they
do, tell us and we will ask for those two columns to be dropped as well. We would rather lose
the ability to trace a payment than have removed a name in a way that does not hold.
