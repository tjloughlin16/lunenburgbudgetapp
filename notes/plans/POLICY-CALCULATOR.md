---
status: plan
---
# Policy calculator

TJ, 27 November 2026: *"lets build our first calculator since the creation of this project....
a 'Policy calculator' that the finance committee can use to adjust to show the outcomes towards
free cash, that shows todays settings, policy suggestions, etc"*.

## What it is built on

The unlisted financial policies report (commit `27dab70e0` and the ones after it):

- Pages: `/town-reserves/financial-policy-rules`, `/town-reserves/policies-in-practice`,
  `/town-reserves/retiree-health-liability`, `/town-reserves/financial-policy-debate`.
- `scripts/financial_policies_data.py`. `build()` returns every figure: the latest certified
  free cash and its date, the budget it is measured against, `split()` (the draft's shares),
  `BANDS` (target ranges), and the `DRAFT` / `TODAY` rule phrases. It also returns the series
  `stab_pct`, `fc_pct`, the OPEB schedule, capital and debt. Every rule is asserted verbatim on
  the DLS manual page or the Select Board policy section that prints it.
- `scripts/build_financial_policies.py` belongs to the report session. Do not edit it. Write a
  separate `scripts/build_policy_calculator.py` that imports `financial_policies_data`.

## What it does

**Presets:**

- **Today's rules** (Select Board policy 3.03, 3.04, 3.07):
  1. Top up general stabilization to five percent of the current budget, if it is below that.
  2. Then put at least 10% of free cash into the OPEB trust.
  3. Then deposit into the special purpose funds, an amount set in capital planning.
  4. The rest may go to one-time uses.
- **State draft** (DLS manual, pdf pp. 28-30):
  - keep back at least 20%;
  - at least 5% to general stabilization;
  - at least 10% to the special funds;
  - at least 10% to OPEB;
  - 20% to 30% to cash capital;
  - the lesser of 10% or $250,000 to other one-time costs;
  - a yearly stabilization deposit of 0.25% (summary table) or 0.3% (text) of the budget;
  - deposits into all stabilization funds capped at 10% of the previous year's total budget.
- **Custom:** a slider per share.

**Inputs** default to today's figures from the payload and are editable: the free cash amount,
the budget, and the current balances.

**Outputs:**

- dollars per use;
- what is left for Town Meeting to decide;
- general stabilization and the special funds as a share of the budget after deposits, against
  both rules' bands;
- the OPEB trust after the deposit;
- next year's starting free cash.

## The rules it is held to (CLAUDE.md)

- **Rule 8:** recommend neither direction. Use neutral colours, and never draw the draft in red.
- **Rule 2:** every default comes from a generated payload (`/data/policy-calculator.json`, with
  `--check`). No figure is typed into the component.
- **Rule 7:** label each number as published, our estimate, or the user's own input.
- Load the `building-a-page` skill first.

## Full renders are on hold

Read `notes/plans/NO-FULL-RENDERS.md` and `notes/process/AVOIDING-FULL-RENDERS.md`. A component
under `fy28/src` forces a full render. So build on a branch in a worktree, preview with the vite
dev server, and do not merge to main or deploy without TJ. Landing it needs a code deploy.

Keep it unlisted, like the report.
