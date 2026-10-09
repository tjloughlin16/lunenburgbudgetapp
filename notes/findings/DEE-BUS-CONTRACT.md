# The Dee Bus contract: what the district pays per bus, and what the 7.6% was

9 October 2026. Four documents received by records request on 9 October 2026 (see
`sources/contracts/PROVENANCE-records-request-2026-10-09.md`), all scans, every figure below
read off the page images:

| short name | file | what it is |
|---|---|---|
| AGREEMENT | `sources/contracts/pdf/dee-bus-transportation-agreement-fy26-fy28.pdf` | the *Specimen Agreement*, pages 31-33 of the Invitation for Bids, executed |
| BID | `sources/contracts/pdf/dee-bus-bid-proposal-rates-fy26-fy30.pdf` | *Exhibit E: Bid Proposal*, pages 24-29 of the Invitation for Bids, filled in by hand; delivered as *Daily Transportation Rates 25-28.pdf* |
| AMENDMENT | `sources/contracts/pdf/dee-bus-first-amendment-2025.pdf` | *First Amendment to Specimen Agreement*, page 1 (page 2 is a stray page of another agreement) |
| BOND | `sources/contracts/pdf/dee-bus-performance-and-payment-bond-fy27.pdf` | performance bond, payment bond, surety's power of attorney |

Page numbers below are the PDF page, then the Invitation for Bids page printed at its foot.

---

## 1. What the documents establish

- **The district pays a price per bus per day, by bus size, fixed in advance for every year.**
  FY2026: **$485** for a 77-passenger bus and **$515** for an 83-passenger bus. FY2027:
  **$523** and **$556**. FY2028: **$565** and **$588.50**. There is no escalator, index or
  reopener: the bid form's instruction is *"All unit prices must remain constant for the
  entire contract"* and each year's prices were bid in December 2024 (BID p1/24).
- **Eleven regular-route buses for 180 days, priced: eight 77-passenger and three
  83-passenger.** That agrees with the owner's figure of 11 regular-education buses. The form
  printed *seven* 77-passenger buses plus a half-bus line; the 7 is overwritten by hand to 8
  in every year and the half-bus line is marked `N/A` (BID p1/24, p2/25, p3/26, p5/28, p6/29).
- **The FY2026 regular-route price is exactly the 7.6%.** 8 x $485 x 180 + 3 x $515 x 180 =
  **$976,500**. The FY2025 budget for general education transportation was **$907,200**. The
  difference is **$69,300**, which is **7.64%**: the district's own FY2026 overview prints
  *"Dee Bus 7.6% line increase = $69,300"*. So the 7.6% is the contract's first-year price
  over the previous year's budget line. It is not a rate increase, and the rates alone cannot
  produce it, because the FY2025 rates are not in what the district sent (section 4).
- **The FY2027 budget line is the contract's second-year price to the dollar.** 8 x $523 x 180
  + 3 x $556 x 180 = **$1,053,360**, and `General Education Transportation` in the FY2027
  budget (balanced) is **$1,053,360** (`sources/data/lps-budget-lines.csv`, row 167).
- **The regular-route price rises 7.87% into FY2027 and 7.41% into FY2028**, at a constant
  eleven buses and 180 days.

## 2. The contract: term, parties, procurement

| | | where |
|---|---|---|
| parties | *"the Town of Lunenburg acting by and through its School Committee"* and **Dee Bus Service, Inc.** (handwritten in the blank), 33 Great Road, Shirley, MA 01464 | AGREEMENT p1/31, p2/32 |
| term | *"commence work under this Contract on July 1, 2025, and shall complete the work ... by June 30, 2028"*; *"at the sole discretion of the Lunenburg Public Schools"* one-year extensions for 2028/2029 and 2029/2030 | AGREEMENT p1/31, Art. 2 |
| funding | beyond the first year *"subject to appropriation"*; if funds are not appropriated the Town shall cancel *"pursuant to G.L. c.30B, §12(d)"* | AGREEMENT p1/31, Art. 2; Art. 7 |
| payment | *"in accordance with the prices specified on the Contractor's Bid Form"*, monthly over the ten months of the school year | AGREEMENT p1/31, Art. 3 |
| contract documents | the Agreement; amendments and change orders; the *Invitation for Bids for School Bus Transportation*; the Contractor's response *"including a completed Bid Form"*. Conflicts resolve *"most favorable to the Town"* | AGREEMENT p1/31, Art. 4 |
| amendments | in writing, approved by the Town Accountant first, *"in accordance with M.G.L. c.30B, §13"* | AGREEMENT p2/32, Art. 10 |
| bonds | performance and payment bonds *"in an amount equal to 100% of the contract price"* | AGREEMENT p2/32, Art. 12 |
| award basis | *"One contract for all regular route, activity, field and athletic trip buses will be awarded to the responsive and responsible bidder with the lowest grand total price"*; *"Award of the contract will be made to the bidder submitting the lowest Grand Total price for a three (3) year contract"* | BID p1/24; p4/27 |
| bid signed | 12-27-24, by the company | BID p4/27 |
| executed | for the School Committee by the Director of Administration and Finance; *"Approved as to availability of Funds"*, Town Accountant, 5/23/2025; *"Approved as to Form"*, Town Counsel, 05-23-2025 | AGREEMENT p3/33 |

**Procurement basis:** an Invitation for Bids under G.L. c.30B, awarded on the lowest
three-year grand total. The School Committee minutes of 8 January 2025 record the step
before: *"Dr. Gilson supplied the bid with Dee Bus, it is a 3 year contract with tentative
increases over the 3 years ... Mr. Beardmore makes a motion to authorized Dr. Gilson to
negotiate and finalize this contract"* (`sources/meetings/text/school-committee/2025-01-08-minutes-6948.txt`,
line 119). How many bids were received, and the rest of the Invitation for Bids, are not in
the delivery.

## 3. Every rate, every year

**Regular-route buses**, price per bus per day, 180 days, from BID p1/24 (FY2026), p2/25
(FY2027), p3/26 (FY2028), p5/28 and p6/29 (the two optional years):

| year | 77-passenger | x buses | 83-passenger | x buses | regular-route subtotal (i)+(iii) | rise |
|---|---:|---:|---:|---:|---:|---:|
| FY2026 (Year One) | $485.00 | 8 | $515.00 | 3 | $976,500.00 | |
| FY2027 (Year Two) | $523.00 | 8 | $556.00 | 3 | $1,053,360.00 | +7.87% |
| FY2028 (Year Three) | $565.00 | 8 | $588.50 | 3 | $1,131,390.00 | +7.41% |
| FY2029 (optional) | $590.00 | 8 | $630.00 | 3 | $1,189,800.00 | +5.16% |
| FY2030 (optional) | $637.20 | 8 | $680.40 | 3 | $1,284,984.00 | +8.00% |

By bus size, year on year: 77-passenger **+7.84%, +8.03%**, then +4.42% and +8.00% in the
optional years; 83-passenger **+7.96%, +5.85%**, then +7.05% and +8.00%.

**Field trips, athletic events, band buses.** The form's estimate is *"Buses for 100 field
trips, athletic events, or band event trips. These trips will require 6,500 miles of travel as
well as approximately four (4) hours of 'waiting time' per trip"*. One rate is bid for every
bus size each year, entered against lines of the form `count x $rate x miles`:

| year | rate (all sizes: 83, 77, 65, 45-passenger, 16-passenger van) | wait time, per hour |
|---|---:|---:|
| FY2026 | $6.50 | $130.00 |
| FY2027 | $6.65 | $140.00 |
| FY2028 | $6.90 | $150.00 |
| FY2029 (optional) | $7.00 | $175.00 |
| FY2030 (optional) | $7.25 | $190.00 |

The rate's unit is not printed on its line; the result column is headed *"(Estimated) Mileage
Charge"*, so it reads as a price per mile. The form multiplies a trip count by the rate by a
mileage figure for each size (35, 35, 10, 10, 10 trips; 1,750, 1,750, 500, 500, 500). The
counts sum to the estimate's 100 trips; the mileage figures sum to 5,000, not its 6,500.
The subtotal they produce (FY2026: $893,750) is a quantity for comparing bids, not a
forecast of spending: *"In any given year during the contract term, the number of miles may
increase or decrease and the number of hours waiting may increase or decrease. Any increase or
decrease will be at the unit prices specified on this bid form. LPS reserves the right to hire
any contractor for class trips and/or field trips or transport students ourselves."*

**Every printed total foots.** (i) through (ix) sum to the printed year totals: $1,922,250
(FY2026), $2,023,735 (FY2027), $2,140,140 (FY2028), $2,222,300 and $2,357,859 (optional
years); the three base years sum to the printed **Grand Total $6,086,125.00** (BID p4/27).

**Late buses, extra buses, summer.** No late-bus or activity-bus rate appears. The form
allows the regular-route fleet to move by **"a maximum of two buses"** a year, and *"Summer
transportation and any increase/decrease will be at the unit prices specified on this bid
form"* (BID p4/27). The number of **routes** is not stated anywhere in the delivery; the form
counts buses.

## 4. Testing the 7.6%

**What it is.** The Finance Committee minutes of 6 March 2025 list among the FY2026 increases
*"7.6% increase in Dee Bus services"* (`sources/meetings/text/finance-committee/2025-03-06-minutes-7008.txt`,
line 63). The district's FY2026 budget overview states it in full: *"Dee Bus 7.6% line
increase = $69,300"* (`sources/district-budget/text/school-department-fy26-budget-overview.txt`,
line 97). It is a **line** increase.

**The arithmetic, budget to budget (rule 1).** FY2025 general education transportation,
original budget: **$907,200** (`lps-budget-lines.csv` row 167, `fy25_budget`; the FY2025
period 13 ledger prints the same original appropriation, `munis-school-ytd.csv`). The
contract's FY2026 regular-route price: **$976,500**. $976,500 − $907,200 = **$69,300**;
$69,300 / $907,200 = **7.64%**.

**The FY2026 budget then carried $11,000 less than that.** The FY2026 final budget prints
**$965,500** for the line (`lps-budget-lines.csv`, `fy26_final`), and the FY2026 period 13
ledger shows the same original appropriation with **+$11,000** of transfers, revised to
**$976,500** (`munis-school-ytd.csv`, FY2026, account `535025`). So the line was voted at
6.43% over FY2025 and moved during the year to the contract price.

**Can the rates alone produce 7.6%? Not from these documents.** The 7.6% compares the new
contract's first year with the last year of the contract it replaced, and **the replaced
contract was asked for and not delivered**. What the line is made of:

    line = price per bus per day x buses x days (+ anything else charged to it)

The FY2026 side is known in full: 11 buses, 180 days, $976,500. The FY2025 side is one number,
$907,200, which is $5,040 a day over 180 days. That one number fits more than one fleet:

- *Hypothesis A: the same eleven buses.* Then FY2025 averaged **$458.18** a bus a day against
  FY2026's **$493.18**, and the whole 7.64% is price.
- *Hypothesis B: ten buses.* Then FY2025 averaged **$504.00** a bus a day, more than FY2026's
  77-passenger price, and the increase would be the eleventh bus with the price per bus
  falling.

**The record leans to A, and it is evidence of a statement, not a count.** A district
School Committee presentation filed under 2024-2025, *Transportation: Bus Fee Proposal*, says
*"LPS uses 11 buses; (8) 77-Passenger Buses and (3) 88-Passenger Buses"* and *"Increase is
above 7 % each year for the next three years"*
(`sources/district-budget/text/sc-meetings/2024-2025-transportation-fee-proposal.txt`, page 4).
In January 2024 the district had asked Dee Bus to meet ridership *"with 10 buses"*
(`sources/district-budget/text/sc-meetings/2024-01-24-revised-superintendent-s-fy25-proposed-budget-1-24-24.txt`,
line 69) — that is evidence of what it meant to do, not of what ran. Our machine captions of
meetings in February and March 2024 locate statements that the bus company insisted on
eleven; they are a finding aid and are not quoted here as fact. The presentation's
*"88-Passenger"* does not match the contract's 83-passenger buses; which is right for FY2025
is not established.

**What would settle it:** the FY2023-FY2025 Dee Bus contract and its bid form (the daily
rate per bus and the number of buses), or the FY2025 invoices. Registered in `money-gaps.csv`.

**Days.** Both years are 180 days in the contract; nothing in the delivery suggests the FY2025
line paid for a different number, and nothing rules it out.

## 5. The First Amendment and the bond

**AMENDMENT p1** changes one thing: the bonds. Article 12 required bonds of *"100% of the
contract price"*. The amendment substitutes bonds *"totaling 100% of the contract price for one
year, for the faithful performance of the Agreement in that year, at the start of each year of
the Agreement"*, posted *"before July 1 of each year"*, by a surety *"licensed by the
Massachusetts Division of Insurance and acceptable to the Town Counsel"*. Everything else
*"shall remain unchanged"*. Signed for the School Committee by the Director of Administration
and Finance 5/5/25 and for the contractor by its President 5/15/25. **AMENDMENT p2 is not
part of it**: it is the last page of a consultant agreement about E-Rate filings (*"Form 471"*,
*"Funding Commitment Decision Letter"*), signed for the district 12/3/24.

**BOND** (bond no. UCSX2X6021, United Casualty and Surety Insurance Company, Boston; signed and
sealed 8 July 2026):

- **Performance bond, p1:** **$2,019,685.00**, for *"Student Transportation Services for the
  period of July 1, 2026 through June 30, 2027 only"*, term 07/01/2026 to 06/30/2027. On
  default the surety is liable *"only for the loss to the Obligee due to actual excess costs
  for performance of the contract"* up to the end of the term, and the amount reduces as work
  is completed. Claims must be brought within six months of completion.
- **Payment bond, p2:** the same sum and term, for persons who furnished labour and material
  directly to the contractor, each with a right of direct action; the time limits for a claim
  are its condition 3.
- **Power of attorney, p3:** the surety's appointment of its attorneys-in-fact, notarised
  18 March 2026, certified 8 July 2026.

**The bond is $4,050 less than the bid's FY2027 total** ($2,023,735.00, BID p2/25). The
documents do not say how $2,019,685.00 was arrived at. It was signed on 8 July 2026, after the
1 July date the amendment sets for posting it.

## 6. What none of this establishes

- **What the district actually paid Dee Bus in any year.** The bid prices a fleet; the
  ledger shows FY2026 general education transportation spent at the revised budget,
  $976,500 (`munis-school-ytd.csv`), which is an actual and is not used in any calculation
  above.
- **Field-trip and athletic spending under this contract.** Those are charged at the unit
  rates to other lines (athletic transportation, band transportation) and the form's subtotal
  is not a forecast.
- **The FY2025 rates and fleet** (section 4). The request asked for the contract it replaced,
  the Invitation for Bids and the bids received; none came.
- **Whether special education transportation is in this contract.** The form covers regular
  route and trip buses; the Superintendent's 17 August 2026 email says the route list *"does
  not include Van Pool Special Education bussing"* (`sources/correspondence/2026-08-17-bus-routes-and-fees-superintendent.txt`).
- **How the bus fees relate to the line.** Rule 11: a line can be net. Here the FY2026
  revised and FY2027 balanced figures equal the contract's gross regular-route price to the
  dollar, so whatever the fees fund, they are not netted out of those two figures; where fee
  receipts are booked is already a registered gap (`money-gaps.csv`, *Where bus fee receipts
  are booked*).
