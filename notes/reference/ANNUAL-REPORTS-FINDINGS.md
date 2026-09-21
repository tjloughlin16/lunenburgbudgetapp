# FY2023 trust and stabilization: what was established, 21 September 2026

Batch 1 of the ingestion plan. FY2023 still proves **0** stabilization rows. This is what
is now known, so the next session starts from evidence rather than rediscovering it.

## FY2023 prints TWO different tables, and `LAYOUTS` is keyed by YEAR

That is the first thing that has to change. One year, two tables, two headers:

| page | table | figure columns |
|---|---|---|
| 50 | `TRUST FUNDS / FISCAL YEAR 2023 SUMMARY` (Bartholomew, "Page 3 of 9") | **14** |
| 49 | `TRUST AND STABILIZATION FUNDS HELD BY OTHER BANKS` ("Page 2 of 9") | 8 in the header, **6 ever used** |

The stabilization funds are on **page 49**, not 50. Page 50 is cemetery and conservation
trusts. `LAYOUTS[2023]` can only name one of them, so whichever is recorded is wrong for
the other page.

## The FY2023 fourteen-column header, read off page 50 and written down

Committed as `FOURTEEN` in `read_trust_table.py`. It binds correctly — 14 named columns,
42 rows with cells. Left to right by heading x:

    ACCOUNT NUMBER (.08) | FUND NAME (.16) | BEGINNING MARKET VALUE (.25) |
    BEGINNING PRINCIPAL (.31) | BEGINNING EARNINGS (.36) | NET INCOME (.40) |
    REALIZED GAIN/LOSS (.44) | NET EARNINGS (.49) | TRANSFERS OF PRINCIPAL (.53) |
    TRANSFERS OF EARNINGS (.58) | ENDING PRINCIPAL (.63) | ENDING EARNINGS (.68) |
    ENDING CASH VALUE (.72) | CHANGE IN UNREALIZED GAIN/LOSS (.77) |
    UNREALIZED GAIN/LOSS (.82) | ENDING MARKET VALUE (.87)

`NET INCOME` + `REALIZED GAIN/LOSS` are the components of `NET EARNINGS`, and
`ENDING PRINCIPAL` + `ENDING EARNINGS` are the components of `ENDING CASH VALUE`. None of
the four may enter `verify()`'s inflow sum or the money is counted twice and nothing
closes.

## The page 49 header, read and NOT yet usable

    ACCOUNT NUMBER (.12) | FUND NAME (.22) | BEGINNING PRINCIPAL (.39) |
    NET EARNINGS (.45) | TRANSFERS OF PRINCIPAL (.50) | EXPENDITURES (.56) |
    ENDING CASH VALUE (.64) | CHANGE IN UNREALIZED (.70) | UNREALIZED GAIN/LOSS (.76) |
    ENDING MARKET VALUE (.83)

Eight figure columns printed; the two unrealised ones hold **no figure anywhere on the
page**, exactly as FY2025 does — so the usable shape is six and `BANKS_6` is the right
family.

## Why it still does not close, and it is NOT the layout

Clustering the right edges of **every** figure on page 49 finds six columns —
`0.436 0.494 0.548 0.629 0.685 0.871` — and all six candidate layouts produce identical
results, which is the tell: the layout is not what is wrong.

**Figures are being dropped from rows.** Both stabilization rows come back with three
values where the arithmetic needs at least four:

    ZONING INCENTIVE STABILIZATION      231,007.68 → ending cash 235,681.11
                                        the missing earnings figure is 4,673.43
    VEHICLE/EQUIPMENT STABILIZATION     450,000.00 → ending cash 1,936,143.89
                                        450,000 looks like a TRANSFER IN, and the
                                        beginning balance 1,486,143.89 is absent

Both differences are exact, so the figures exist on the page and are not reaching
`place()`. Next step is `place()`'s right-edge tolerance (`abs(c['x'] - right) > 0.05`)
measured against this page's own column pitch, not the dropped-figure symptom.

## What this does not establish

Whether the same defect explains FY2011, FY2012 and FY2013, which also prove nothing.
They have not been opened.
