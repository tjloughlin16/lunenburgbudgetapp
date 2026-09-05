# The sanitiser — design

A tool the Town runs on its own machine that turns a MUNIS export into two files: one safe
to send out, and one crosswalk naming only the vendors the Town has decided may be named.

**It decides nothing.** Every approval is a human click. There is no model in it, no
heuristic that guesses whether a name is a person, and no network. It is a tool for making a
decision quickly and recording it, not a tool that makes the decision.

Status: design for discussion. Not built.

---

## 1. What it is, and why that shape

A **single self-contained HTML file**. Saved to disk, opened by double-click, runs offline in
the browser already on the machine.

That shape is chosen for the review, not for convenience:

| property | why it matters to whoever approves this |
|---|---|
| No install | Nothing added to a managed machine. |
| No server, no account | No vendor relationship, so no contract to review and no procurement question. |
| No network calls at all | Provable in ten seconds: disconnect, and it still works. |
| **No build step** | The file they run *is* the source. "Review the code" means "open the file" — no minification, no bundle, no trust in a toolchain. |
| Published, not donated | The Town adopts nothing. It opens a public file, or does not. |

The last two are the ones to lead with. Most software asks a reviewer to trust a process;
this asks them to read a file and unplug a cable.

---

## 2. The problem it solves, restated exactly

The MUNIS **Journal Detail Export** has 25 columns. Two can name a person: **X
`VDR NAME/ITEM DESC`** and **Y `COMMENTS`**. The Town has been asked to omit them at export
time, which is better than any tool. This exists for when that cannot be done — the layout is
fixed, or the report is canned — and for producing the crosswalk, which no export can produce
because it is a list of decisions.

**There is no vendor ID column in that export.** So the tool must create one. That is the
part of the design that needs the most care, because an ID that changes between runs makes
"the same payee across years" unanswerable, which is most of what the ID was for.

---

## 3. The three files, and which never leaves

```
  MUNIS export (CSV)  ──▶  [ the tool ]  ──┬──▶  sanitised-<name>.csv      SEND
                               ▲           ├──▶  vendor-crosswalk.csv      SEND
                               │           ├──▶  sanitisation-manifest.txt SEND
                     vendor-register.json ─┘
                        NEVER LEAVES
```

**`vendor-register.json` is the sensitive file and the whole design turns on it.** It maps
every vendor ID to every vendor name — approved, withheld and undecided alike — and it is
what makes IDs stable across runs. It stays on the Town's machine forever. The UI says so on
every screen that touches it, and the file itself carries a header line saying it.

The register is also the reason the tool has no database and no memory: **the register file
is the state.** Drag it in at the start, save it at the end. Nothing persists in the browser
— no localStorage, no cookies, no IndexedDB — so closing the tab leaves nothing behind on a
shared machine.

- **`sanitised-<name>.csv`** — the export minus the hazardous columns, plus a `VENDOR_ID`
  column. This is what gets sent.
- **`vendor-crosswalk.csv`** — approved vendors only, in the schema
  `vendor_id,vendor_name,vendor_type,approved_by,approved_date,basis`.
- **`sanitisation-manifest.txt`** — what was removed and how much: columns dropped, rows
  total, distinct vendors, how many approved / withheld / undecided, and the amount carried
  by each group. It names nobody. It exists so the recipient can see the *shape* of what they
  did not get, rather than reading absence as absence of the thing.

---

## 4. Vendor identity — the hard part

Requirements in tension: stable across runs and across years; not reversible by a recipient;
and no state beyond a file a clerk can misplace.

**Chosen: opaque IDs assigned once and recorded in the register.** An ID is drawn from a
random pool on first sight of a vendor and written to the register. Later runs read the
register and reuse it.

Rejected, with reasons, because both look attractive:

- **Hash of the name.** Stateless and stable — and reversible. A recipient who guesses a name
  can confirm it by hashing. A salt fixes that and reintroduces exactly the state the hash
  was meant to avoid, with the added failure that losing the salt silently breaks every
  historical ID.
- **Sequential numbering.** Leaks order of first appearance, which is information about the
  data nobody intended to send.

**Say what this is.** A stable ID is a **pseudonym, not anonymity**: if one row's payee is
ever learned, every row sharing that ID is identified with it, retrospectively and
permanently. That is a good trade and it is not the same as the name being absent, and the
manifest says so in those words so that nobody downstream assumes more.

---

## 5. Screens

**1 — Load.** Drop the export. Drop the register if one exists; otherwise start a new one.
CSV only, by choice: it matches the "Save As CSV" step the Town is already asked to do, and
that step independently strips hidden columns, hidden sheets and document properties that an
`.xlsx` carries invisibly. Supporting `.xlsx` would mean inlining a spreadsheet parser and
accepting the hidden-data problem the CSV step exists to remove.

**2 — Columns.** All columns listed, with the hazardous ones flagged by the same rule as
`scripts/check_intake_headers.py` — one list of hazard words, so the tool and the check
cannot disagree about what is dangerous. Default for a flagged column is **drop**. Keeping
one requires a typed reason, which goes in the manifest.

**3 — Vendors.** The work. One row per distinct value in the vendor column, with occurrence
count, total amount, and the accounts it appears under. Two actions: **Approve** (an
institution, may be named) or **Withhold** (a person, or unsure). Default is Withhold and
nothing is approved by inaction. An approval requires `vendor_type` and initials; `basis` is
optional free text. Keyboard-driven, because a first run may have hundreds of rows and a
tool that is tedious gets abandoned for a bulk select-all.

Already-decided vendors from the register are shown collapsed and are not re-asked. **This is
the payoff and it should be visible: after the first run, this screen is nearly empty.**

**4 — Review and export.** Counts, amounts by group, and the three files to save.

A warning here, not a block: **how many withheld vendors appear in only one or two rows.** A
single family with an unusual reimbursement is identifiable from amount, date and account by
anyone local, whatever the vendor column says — removing a name does not anonymise a
population of one. The tool cannot fix that; it can refuse to let it pass unnoticed.

---

## 6. What it must never do

- **No automatic classification.** No name detection, no pattern that guesses person versus
  company. Such a rule would be wrong sometimes and silently, and would train the operator to
  click through. Every approval is a human decision, or there is no approval.
- **No network.** No `fetch`, no `XMLHttpRequest`, no WebSocket, no external stylesheet,
  script, font or image. Everything inlined. This is stated as a test, not an intention: the
  published file's source contains none of those tokens, and that is checkable by search.
- **No persistence.** Nothing in localStorage, sessionStorage, IndexedDB or cookies.
- **No bulk approve.** No "approve all", no "approve all matching". The one shortcut worth
  having is the register, which is a record of decisions already made.

---

## 7. Publishing it

On this site, at a stable address, with:

- **a sha256 of the file**, so a reviewer can confirm what they downloaded;
- **"save this file and run it offline"** as the primary instruction, not an afterthought —
  running it from the web works identically but is harder for a reviewer to believe;
- a **plain-language page for whoever reviews it**: what it does, what it never does, and the
  disconnect-the-network test;
- an **open licence**, and a plain statement of no warranty and that the operator is
  responsible for reviewing the output before sending it.

Published, not offered. The Town is not asked to accept anything.

---

## 8. Requirements still to decide

1. **Does the Town's export really lack a vendor ID?** §2 assumes so from the 25 columns we
   hold. If MUNIS can emit a vendor number, §4 mostly disappears and the tool gets simpler.
   Worth one question before building.
2. **`.xlsx` input** — excluded in §5 for good reasons, at the cost of a manual Save As. If
   the operator is likely to skip that step, the trade changes.
3. **Who is `approved_by`?** Initials, a role, or a name. A name is a person in a published
   file, which is fine for a public official acting officially and should still be a choice
   somebody makes deliberately.
4. **The small-cell threshold** in §5 — warn only, or refuse to export? And at what n? DESE
   publishes its own suppression rule for this population, and matching it is more defensible
   than choosing a number here.
5. **Warrant and check numbers.** If the Town publishes warrants naming payees, columns T and
   U are a join key back to the name. If so they belong in the hazardous list, and the tool
   should flag them by default.
