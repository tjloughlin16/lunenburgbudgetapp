# The paraprofessional correction and the Dee Bus contract — records request, 9 October 2026

Covers eight documents under `contracts/pdf/` and `contracts/docx/`, and one email held
privately whose transcription is `correspondence/2026-09-16-para-wages-superintendent-counsel-payroll.txt`.
The decision on each file, and why, is in `sources/data/redactions.csv`, keyed by its sha256.

## How it reached us

**Public records request by TJ Loughlin to the Superintendent, 9 October 2026; response
forwarded to him on 9 October 2026.** Two requests were sent that day, both to Dr. Jodi
Fortuna, Superintendent, and both are rows in `notes/reference/records-requests.csv`:

- `2026-10-09-revised-para-salary-schedule` — the revised paraprofessional salary schedule
  approved by the School Committee on 7 October 2026, the agreement as re-ratified with it,
  and any memorandum describing the corrections;
- `2026-10-09-dee-bus-contract` — the current transportation contract with Dee Bus Service,
  its rate schedule, amendments and extensions, and the contract it replaced.

The response arrived as one zip. There is no URL: none of these documents is posted on the
district's site, so this note is the address in rule 12's sense.

| | |
|---|---|
| file | `fwexternalrecordsrequest.zip`, as received |
| bytes | 11,018,572 |
| sha256 | `6aab4c710a5a1e8d5f7972cb109ac8645c8d9edd1d2a181a1b9155f8bbdb6dd5` |
| members | 9 files, 13,384,910 bytes unpacked |

The zip is kept unchanged, outside the archive, at
`build/inbox/2026-10-09-records-request-para-and-dee-bus/fwexternalrecordsrequest.zip`.

## Every member, as delivered and as filed

The publisher's filename is the name to ask the district for if this copy is ever lost.

| delivered as | filed as | sha256 | bytes | `pdf_kind` | decision |
|---|---|---|---:|---|---|
| `Para Contract Signature Page with Corrected Salary Schedule Approved by SC 10-7-26.pdf` | `contracts/pdf/paraprofessional-salary-fy26-fy28-corrected-2026-10-07.pdf` | `f70d37dc4ca9eb335b0933a8f4239932abdf1258cd09efd5c6fa69e9a3e04700` | 2,522,982 | scan, 3 pages | publish |
| `MOA Para 2025-2028.pdf` | `contracts/pdf/paraprofessional-moa-fy26-fy28.pdf` | `f0a55557bf531c07dedef40545c69104bf3f83358d62a3083084e30e559f882f` | 1,046,171 | scan, 2 pages | publish |
| `Draft Union Agreement - Para Wages.docx` | `contracts/docx/paraprofessional-wages-draft-union-agreement-2026-09.docx` | `b66ca4b1489d77f1e3b4bffde14ff32af55272aa229f93649d51be1bfd9e10cf` | 24,630 | (Word) | publish |
| `Draft Individual Waiver - Para Wages.docx` | `contracts/docx/paraprofessional-wages-draft-individual-waiver-2026-09.docx` | `43111a96e031bb9b717d37753df9d151d3cee4c2fc6626a81caf47f3648f51f2` | 24,747 | (Word) | publish |
| `Lunenburg Schools - Dee Bus - Transportation Contract - 05.23.2025 smv.pdf` | `contracts/pdf/dee-bus-transportation-agreement-fy26-fy28.pdf` | `67e4279cb4029279d202c1d9defb424b97cf50bd701f62a123c6b116f405a2c3` | 1,087,006 | scan, 3 pages | publish |
| `Daily Transportation Rates 25-28.pdf` | `contracts/pdf/dee-bus-bid-proposal-rates-fy26-fy30.pdf` | `2a05b91924d7a680339c75b199e233876ef3ba4acc33a2d6ba838233aa624599` | 4,356,894 | scan, 6 pages | publish |
| `First Amendment to Specimen Agreement.pdf` | `contracts/pdf/dee-bus-first-amendment-2025.pdf` | `d4b6bf07e55b0fd054a2aede74e7b22a4fd9a40c269e25bb4a230dad8860a354` | 1,289,945 | scan, 2 pages | publish |
| `Performance Bond 2026-2027.pdf` | `contracts/pdf/dee-bus-performance-and-payment-bond-fy27.pdf` | `f5c1d9517e1d93d4eabc08aa9e9190d5dc4d1d1a7f681a6755f44eadd5a7232c` | 2,903,717 | scan, 3 pages | publish |
| ``Fwd_ [External] RE_ [External] RE_ [External] RE_ Paras`.eml`` | held privately as `raw/correspondence/2026-09-16-para-wages-superintendent-counsel-payroll.eml`; published as our transcription, `correspondence/2026-09-16-para-wages-superintendent-counsel-payroll.txt` | `db1e04d40dac3886935d564956971cbd7335f400685b1c4a9b77789791d403ab` | 128,818 | (email) | withhold; transcription published |

Every PDF is a scan at 300 dpi (`pdf_kind`: every page an image, no text layer). The text
beside each in `contracts/txt/` is OCR (macOS Vision), labelled as such, and is a finding
aid: the figures in `notes/findings/PARA-SALARY-CORRECTION.md` and
`notes/findings/DEE-BUS-CONTRACT.md` were read off the rendered pages, not off the OCR.

## What the delivery is, and what it is not

- **The email is not the district's cover letter to the requester.** It is an internal
  chain of 11-16 September 2026 between the Superintendent and the district's counsel, then
  forwarded within the payroll office, carrying the two draft wage documents as attachments.
  The district released it as part of the response.
- **Page 2 of `First Amendment to Specimen Agreement.pdf` belongs to another document.** It
  is the last page of a consultant services agreement about E-Rate filings (it names
  "Form 471" and a "Funding Commitment Decision Letter"), signed for the district on
  3 December 2024. Nothing on it concerns Dee Bus. It is kept as delivered.
- **The Dee Bus agreement is pages 31-33 of the Invitation for Bids**, and the rates are
  pages 24-29 of the same document (Exhibit E, the bid proposal). The rest of the Invitation
  for Bids — the specifications the agreement incorporates, including the insurance amounts
  and the bus and route requirements — was **not** in the delivery.
- **The contract the Dee Bus agreement replaced was not in the delivery**, though the
  request asked for it.

## The 13e review

Every page and both Word files were read in full by eye. The salary scale is by column and
step, with no employee named; the signatures are School Committee members, union officers,
the Superintendent and company officers, all signing in role. The bid form carries the
contractor's federal employer identification number, a company identifier. The two draft
wage documents are blank: the waiver's employee line is an empty blank and no amount or date
is filled in. The email was held whole because an `.eml` has no redactor in `redact.py` and
its headers and signatures carry staff and counsel email addresses, telephone numbers and
mail-routing data; the transcription keeps every word of every message and removes only
those. No personal email address of the requester, or of anybody, appears in any file.
