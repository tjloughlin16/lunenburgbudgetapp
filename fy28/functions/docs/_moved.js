// Where a document used to live.
//
// On 4 September 2026 `sources/` was reorganised by provenance: format folders dissolved,
// acquisition-dated folders renamed for what they hold, and the meeting archive moved from
// `minutes/` to `meetings/`. llms.txt publishes 302 documents at `/docs/<path>` and tells
// agents to CITE those URLs, so a reader or an assistant may hold any of the old ones. This
// maps them, permanently.
//
// WHY A FUNCTION AND NOT `_redirects`
//
// Because `_redirects` does not work here and never has. Its own header records that
// Cloudflare Pages parsed zero valid rules from it -- invalid status codes and a loop -- so
// a redirect written there would look correct and do nothing.
//
// WHY 301 AND NOT A SILENT REWRITE
//
// A moved document should tell the caller it moved. An agent that fetched
// `/docs/minutes/text/...` and got content back with no signal would keep citing an address
// that only works because of this file. 301 puts the new URL in the caller's hands.
//
// PREFIXES FIRST, THEN EXCEPTIONS. Seven prefix rules cover 1,748 of the 1,849 moves --
// almost all of them the meeting archive -- and the exceptions are the documents that
// changed name as well as folder, plus the fifteen duplicates that were deleted in favour
// of the publisher's own copy.

const PREFIX = [
  ["xlsx/", "budget-workbooks/"],
  ["district-budget-page/", "district-budget/"],
  ["dls-free-cash/", "dls/"],
  ["business/", "data/business/"],
  ["town-site/", "town-budget/"],
]

const EXACT = {
  "pdf/assessors-agenda-11-19-2025.pdf": "town-supplementary/docs/assessors-agenda-11-19-2025.pdf",
  "pdf/health-insurance-rates-2025.pdf": "town-supplementary/docs/health-insurance-rates-2025.pdf",
  "pdf/lhs-athletics-faq.pdf": "district-budget/docs/lhs-athletics-faq.pdf",
  "pdf/tax-classification-fy23.pdf": "town-budget/docs/tax-classification-fy23.pdf",
  "pdf/town-2026-election-unofficial-results.pdf": "town-supplementary/docs/town-2026-election-unofficial-results.pdf",
  "q3-fy26/ef-peg-access-expenditures-fy26-q3.pdf": "munis-ledgers/expenses/glytdbud-expense-fy2026-p09-ef-peg-access.pdf",
  "q3-fy26/ef-peg-access-expenditures-fy26-q3.txt": "munis-ledgers/expenses/glytdbud-expense-fy2026-p09-ef-peg-access.txt",
  "q3-fy26/ef-peg-access-revenue-fy26-q3.pdf": "munis-ledgers/revenue/glytdbud-revenue-fy2026-p09-ef-peg-access.pdf",
  "q3-fy26/ef-peg-access-revenue-fy26-q3.txt": "munis-ledgers/revenue/glytdbud-revenue-fy2026-p09-ef-peg-access.txt",
  "q3-fy26/ef-sewer-expenditures-fy26-q3.pdf": "munis-ledgers/expenses/glytdbud-expense-fy2026-p09-ef-sewer.pdf",
  "q3-fy26/ef-sewer-expenditures-fy26-q3.txt": "munis-ledgers/expenses/glytdbud-expense-fy2026-p09-ef-sewer.txt",
  "q3-fy26/ef-sewer-revenue-fy26-q3.pdf": "munis-ledgers/revenue/glytdbud-revenue-fy2026-p09-ef-sewer.pdf",
  "q3-fy26/ef-sewer-revenue-fy26-q3.txt": "munis-ledgers/revenue/glytdbud-revenue-fy2026-p09-ef-sewer.txt",
  "q3-fy26/ef-solid-waste-expenditures-fy26-q3.pdf": "munis-ledgers/expenses/glytdbud-expense-fy2026-p09-ef-solid-waste.pdf",
  "q3-fy26/ef-solid-waste-expenditures-fy26-q3.txt": "munis-ledgers/expenses/glytdbud-expense-fy2026-p09-ef-solid-waste.txt",
  "q3-fy26/ef-solid-waste-revenue-fy26-q3.pdf": "munis-ledgers/revenue/glytdbud-revenue-fy2026-p09-ef-solid-waste.pdf",
  "q3-fy26/ef-solid-waste-revenue-fy26-q3.txt": "munis-ledgers/revenue/glytdbud-revenue-fy2026-p09-ef-solid-waste.txt",
  "q3-fy26/ef-water-expenditures-fy26-q3.pdf": "munis-ledgers/expenses/glytdbud-expense-fy2026-p09-ef-water.pdf",
  "q3-fy26/ef-water-expenditures-fy26-q3.txt": "munis-ledgers/expenses/glytdbud-expense-fy2026-p09-ef-water.txt",
  "q3-fy26/ef-water-revenue-fy26-q3.pdf": "munis-ledgers/revenue/glytdbud-revenue-fy2026-p09-ef-water.pdf",
  "q3-fy26/ef-water-revenue-fy26-q3.txt": "munis-ledgers/revenue/glytdbud-revenue-fy2026-p09-ef-water.txt",
  "q3-fy26/fincom-deck-fy26-q3.pptx": "town-budget/docs/fincom-deck-fy26-q3.pptx",
  "q3-fy26/fincom-deck-fy26-q3.txt": "town-budget/docs/fincom-deck-fy26-q3.txt",
  "q3-fy26/fincom-memo-fy26-q3.docx": "town-budget/docs/fincom-memo-fy26-q3.docx",
  "q3-fy26/fincom-memo-fy26-q3.txt": "town-budget/docs/fincom-memo-fy26-q3.txt",
  "q3-fy26/town-general-fund-expenditures-fy26-q3.pdf": "munis-ledgers/expenses/glytdbud-expense-fy2026-p09-gf-all.pdf",
  "q3-fy26/town-general-fund-expenditures-fy26-q3.txt": "munis-ledgers/expenses/glytdbud-expense-fy2026-p09-gf-all.txt",
  "q3-fy26/town-general-fund-revenue-fy26-q3.pdf": "munis-ledgers/revenue/glytdbud-revenue-fy2026-p09-gf-all.pdf",
  "q3-fy26/town-general-fund-revenue-fy26-q3.txt": "munis-ledgers/revenue/glytdbud-revenue-fy2026-p09-gf-all.txt",
  "q3-fy26/town-special-revenue-fy26-q3.xlsx": "munis-ledgers/fund-balances/special-revenue-fy2026-p09.xlsx",
  "q3-fy26/town-trust-agency-fy26-q3.xlsx": "munis-ledgers/fund-balances/trust-agency-fy2026-p09.xlsx",
  "records-request-2026-06/PROVENANCE.md": "munis-ledgers/account-details/PROVENANCE-fund1301.md",
  "records-request-2026-06/athletic-fee-counts-2025-2026.docx": "munis-ledgers/account-details/athletic-fee-counts-fy2026.docx",
  "records-request-2026-06/athletics-by-sport-fy24-fy26.xlsx": "munis-ledgers/account-details/athletics-by-sport-fy2024-fy2026.xlsx",
  "records-request-2026-06/fund-1301-journal-detail-fy24.xlsx": "munis-ledgers/account-details/account-details-fy2024-fund1301.xlsx",
  "records-request-2026-06/fund-1301-journal-detail-fy25.xlsx": "munis-ledgers/account-details/account-details-fy2025-fund1301.xlsx",
  "records-request-2026-06/fund-1301-journal-detail-fy26.xlsx": "munis-ledgers/account-details/account-details-fy2026-fund1301.xlsx",
  "records-request-2026-09/PROVENANCE.md": "munis-ledgers/expenses/PROVENANCE-fy2026-p12.md",
  "records-request-2026-09/town-general-fund-expenditures-fy26-p12.pdf": "munis-ledgers/expenses/glytdbud-expense-fy2026-p12-gf-all.pdf",
  "records-request-2026-09/town-general-fund-expenditures-fy26-p12.txt": "munis-ledgers/expenses/glytdbud-expense-fy2026-p12-gf-all.txt",
  "records-request-2026-09/town-general-fund-expenditures-fy26-p12.xlsx": "munis-ledgers/expenses/glytdbud-expense-fy2026-p12-gf-all.xlsx",
  "town-site/docs/1352-fy25-snow-and-ice-vendor-agreement.pdf": "town-supplementary/docs/1352-fy25-snow-and-ice-vendor-agreement.pdf",
  "town-site/docs/1416-senior-tax-work-off-record-hours.pdf": "town-supplementary/docs/1416-senior-tax-work-off-record-hours.pdf",
  "town-site/docs/182-w-4-federal-tax-form-pdf.pdf": "town-supplementary/docs/182-w-4-federal-tax-form-pdf.pdf",
  "town-site/docs/187-conflict-of-interest-financial-disclosure-pdf.pdf": "town-supplementary/docs/187-conflict-of-interest-financial-disclosure-pdf.pdf",
  "town-site/docs/1982-3-25-2024-presentation-how-can-we-help-you-property-tax-exemptions-amp-assistanc.pptx": "town-supplementary/docs/1982-3-25-2024-presentation-how-can-we-help-you-property-tax-exemptions-amp-assistanc.pptx",
  "town-site/docs/2086-4-14-sex-offender-audits-pdf.pdf": "town-supplementary/docs/2086-4-14-sex-offender-audits-pdf.pdf",
  "town-site/docs/2499-fy25-governor-awards-lunenburg-fd-state-firefighter-safety-grant-pdf.pdf": "town-supplementary/docs/2499-fy25-governor-awards-lunenburg-fd-state-firefighter-safety-grant-pdf.pdf",
  "town-site/docs/2504-2-3-25-assessor-conference-presentation-pdf.pdf": "town-supplementary/docs/2504-2-3-25-assessor-conference-presentation-pdf.pdf",
  "town-site/docs/3358-lunenburg-senior-citizen-property-tax-work-off-program-application-2025-pdf.pdf": "town-supplementary/docs/3358-lunenburg-senior-citizen-property-tax-work-off-program-application-2025-pdf.pdf",
  "town-site/docs/344-bencor-financial-wellness-pdf.pdf": "town-supplementary/docs/344-bencor-financial-wellness-pdf.pdf",
  "town-site/docs/3463-bridge-assessment-and-ranking-prepared-for-the-town-of-lunenburg-by-bsc-group-ma.pdf": "town-supplementary/docs/3463-bridge-assessment-and-ranking-prepared-for-the-town-of-lunenburg-by-bsc-group-ma.pdf",
  "town-site/docs/3541-board-of-assessors-code-of-conduct-pdf.pdf": "town-supplementary/docs/3541-board-of-assessors-code-of-conduct-pdf.pdf",
  "town-site/docs/3547-role-of-the-assessing-department.pdf": "town-supplementary/docs/3547-role-of-the-assessing-department.pdf",
  "town-site/docs/394-1-40-school-resource-officer-pdf.pdf": "town-supplementary/docs/394-1-40-school-resource-officer-pdf.pdf",
  "town-site/docs/4283-fy27-senior-means-tested-application.pdf": "town-supplementary/docs/4283-fy27-senior-means-tested-application.pdf",
  "town-site/docs/4284-fy27-real-estate-exemption-flyer.pdf": "town-supplementary/docs/4284-fy27-real-estate-exemption-flyer.pdf",
  "town-site/docs/4285-fy27-senior-means-tested-brochure.pdf": "town-supplementary/docs/4285-fy27-senior-means-tested-brochure.pdf",
  "town-site/docs/4306-notice-of-tax-taking-lists.pdf": "town-supplementary/docs/4306-notice-of-tax-taking-lists.pdf",
  "town-site/docs/4365-september-3-2026-special-town-meeting-legal-notice.pdf": "town-budget/docs/4365-september-3-2026-special-town-meeting-legal-notice.pdf",
  "town-site/docs/442-4-38-reserve-officer-hiring-process-pdf.pdf": "town-supplementary/docs/442-4-38-reserve-officer-hiring-process-pdf.pdf",
  "town-site/docs/443-4-39-reserve-officer-program-pdf.pdf": "town-supplementary/docs/443-4-39-reserve-officer-program-pdf.pdf",
  "town-site/docs/493-senior-citizen-property-tax-work-off-program-application-form-pdf.pdf": "town-supplementary/docs/493-senior-citizen-property-tax-work-off-program-application-form-pdf.pdf",
  "town-site/docs/494-senior-tax-work-off-program-brochure-pdf.pdf": "town-supplementary/docs/494-senior-tax-work-off-program-brochure-pdf.pdf",
  "town-site/docs/783-real-estate-personal-property-tax-actual-billing-pdf.pdf": "town-supplementary/docs/783-real-estate-personal-property-tax-actual-billing-pdf.pdf",
  "town-site/docs/784-real-estate-tax-preliminary-billing-pfd.pdf": "town-supplementary/docs/784-real-estate-tax-preliminary-billing-pfd.pdf",
  "town-site/docs/785-motor-vehicle-excise-tax-pdf.pdf": "town-supplementary/docs/785-motor-vehicle-excise-tax-pdf.pdf",
  "town-site/docs/786-tax-lien-sale-auction-notice-pdf.pdf": "town-supplementary/docs/786-tax-lien-sale-auction-notice-pdf.pdf",
  "town-site/docs/787-march-17-2022-tax-lien-sale-auction-registration-form-pdf.pdf": "town-supplementary/docs/787-march-17-2022-tax-lien-sale-auction-registration-form-pdf.pdf",
  "town-site/text/1352-fy25-snow-and-ice-vendor-agreement.txt": "town-supplementary/text/1352-fy25-snow-and-ice-vendor-agreement.txt",
  "town-site/text/1416-senior-tax-work-off-record-hours.txt": "town-supplementary/text/1416-senior-tax-work-off-record-hours.txt",
  "town-site/text/182-w-4-federal-tax-form-pdf.txt": "town-supplementary/text/182-w-4-federal-tax-form-pdf.txt",
  "town-site/text/187-conflict-of-interest-financial-disclosure-pdf.txt": "town-supplementary/text/187-conflict-of-interest-financial-disclosure-pdf.txt",
  "town-site/text/1982-3-25-2024-presentation-how-can-we-help-you-property-tax-exemptions-amp-assistanc.txt": "town-supplementary/text/1982-3-25-2024-presentation-how-can-we-help-you-property-tax-exemptions-amp-assistanc.txt",
  "town-site/text/2086-4-14-sex-offender-audits-pdf.txt": "town-supplementary/text/2086-4-14-sex-offender-audits-pdf.txt",
  "town-site/text/2499-fy25-governor-awards-lunenburg-fd-state-firefighter-safety-grant-pdf.txt": "town-supplementary/text/2499-fy25-governor-awards-lunenburg-fd-state-firefighter-safety-grant-pdf.txt",
  "town-site/text/2504-2-3-25-assessor-conference-presentation-pdf.txt": "town-supplementary/text/2504-2-3-25-assessor-conference-presentation-pdf.txt",
  "town-site/text/3358-lunenburg-senior-citizen-property-tax-work-off-program-application-2025-pdf.txt": "town-supplementary/text/3358-lunenburg-senior-citizen-property-tax-work-off-program-application-2025-pdf.txt",
  "town-site/text/344-bencor-financial-wellness-pdf.txt": "town-supplementary/text/344-bencor-financial-wellness-pdf.txt",
  "town-site/text/3463-bridge-assessment-and-ranking-prepared-for-the-town-of-lunenburg-by-bsc-group-ma.txt": "town-supplementary/text/3463-bridge-assessment-and-ranking-prepared-for-the-town-of-lunenburg-by-bsc-group-ma.txt",
  "town-site/text/3541-board-of-assessors-code-of-conduct-pdf.txt": "town-supplementary/text/3541-board-of-assessors-code-of-conduct-pdf.txt",
  "town-site/text/3547-role-of-the-assessing-department.txt": "town-supplementary/text/3547-role-of-the-assessing-department.txt",
  "town-site/text/394-1-40-school-resource-officer-pdf.txt": "town-supplementary/text/394-1-40-school-resource-officer-pdf.txt",
  "town-site/text/4283-fy27-senior-means-tested-application.txt": "town-supplementary/text/4283-fy27-senior-means-tested-application.txt",
  "town-site/text/4284-fy27-real-estate-exemption-flyer.txt": "town-supplementary/text/4284-fy27-real-estate-exemption-flyer.txt",
  "town-site/text/4285-fy27-senior-means-tested-brochure.txt": "town-supplementary/text/4285-fy27-senior-means-tested-brochure.txt",
  "town-site/text/4306-notice-of-tax-taking-lists.txt": "town-supplementary/text/4306-notice-of-tax-taking-lists.txt",
  "town-site/text/442-4-38-reserve-officer-hiring-process-pdf.txt": "town-supplementary/text/442-4-38-reserve-officer-hiring-process-pdf.txt",
  "town-site/text/443-4-39-reserve-officer-program-pdf.txt": "town-supplementary/text/443-4-39-reserve-officer-program-pdf.txt",
  "town-site/text/493-senior-citizen-property-tax-work-off-program-application-form-pdf.txt": "town-supplementary/text/493-senior-citizen-property-tax-work-off-program-application-form-pdf.txt",
  "town-site/text/494-senior-tax-work-off-program-brochure-pdf.txt": "town-supplementary/text/494-senior-tax-work-off-program-brochure-pdf.txt",
  "town-site/text/783-real-estate-personal-property-tax-actual-billing-pdf.txt": "town-supplementary/text/783-real-estate-personal-property-tax-actual-billing-pdf.txt",
  "town-site/text/784-real-estate-tax-preliminary-billing-pfd.txt": "town-supplementary/text/784-real-estate-tax-preliminary-billing-pfd.txt",
  "town-site/text/785-motor-vehicle-excise-tax-pdf.txt": "town-supplementary/text/785-motor-vehicle-excise-tax-pdf.txt",
  "town-site/text/786-tax-lien-sale-auction-notice-pdf.txt": "town-supplementary/text/786-tax-lien-sale-auction-notice-pdf.txt",
  "town-site/text/787-march-17-2022-tax-lien-sale-auction-registration-form-pdf.txt": "town-supplementary/text/787-march-17-2022-tax-lien-sale-auction-registration-form-pdf.txt",
  "txt/assessors-agenda-11-19-2025.txt": "town-supplementary/text/assessors-agenda-11-19-2025.txt",
  "txt/health-insurance-rates-2025.txt": "town-supplementary/text/health-insurance-rates-2025.txt",
  "txt/lhs-athletics-faq.txt": "district-budget/text/lhs-athletics-faq.txt",
  "txt/tax-classification-fy23.txt": "town-budget/text/tax-classification-fy23.txt",
  "txt/town-2026-election-unofficial-results.txt": "town-supplementary/text/town-2026-election-unofficial-results.txt",
}

// Deleted as byte-identical duplicates; these point at the copy that survived.
const REPLACED = {
  "pdf/athletic-program-costs-by-sport.pdf": "district-budget/docs/athletic-program-costs-by-sport.pdf",
  "pdf/fy27-balanced-slides-3-23-26.pdf": "district-budget/docs/balanced-budget-slides-3-23-26.pdf",
  "pdf/fy27-final-budget-doc.pdf": "district-budget/docs/final-budget-document.pdf",
  "pdf/fy27-multi-scenario-addendum.pdf": "district-budget/docs/budget-addendum-multi-scenario-financial-analysis.pdf",
  "pdf/fy27-projections-3-16-26.pdf": "district-budget/docs/fy27-budget-projections-as-of-3-16-26-with-restorations.pdf",
  "pdf/fy27-projections-3-23-26.pdf": "district-budget/docs/fy27-budget-projections-as-of-3-23-26.pdf",
  "pdf/fy27-sc-slidedeck-3-23-26.pdf": "district-budget/docs/slide-deck-from-the-sc-meeting-3-23-26.pdf",
  "pdf/town-2026-election-warrant.pdf": "town-budget/docs/4161-2026-annual-town-election-warrant.pdf",
  "pdf/town-additional-revenue-plan.pdf": "district-budget/docs/additional-town-revenue-spending-plan.pdf",
  "pdf/town-article13-fy27-capital-plan.pdf": "town-budget/docs/4111-article-13-fy-2027-capital-plan.pdf",
  "pdf/town-atm-2026-booklet-warrant.pdf": "town-budget/docs/3765-town-meeting-booklet-including-warrant.pdf",
  "pdf/town-fy27-budget-press-release.pdf": "town-budget/docs/4090-click-here-for-a-release-on-quot-understanding-lunenburg-apos-s-fy27-budget-how-.pdf",
  "pdf/town-fy27-detailed-budget.pdf": "town-budget/docs/4082-fy-2027-detailed-budget.pdf",
  "pdf/town-fy27-operating-budgets-balanced-tier1-tier2.pdf": "town-budget/docs/3769-fy-2027-operating-budgets-balanced-tier-1-tier2.pdf",
  "pdf/town-revenue-prop25-presentation.pdf": "town-budget/docs/1591-town-revenue-amp-proposition-2-5-presentation.pdf",
  "txt/athletic-program-costs-by-sport.txt": "district-budget/text/athletic-program-costs-by-sport.txt",
  "txt/fy27-balanced-slides-3-23-26.txt": "district-budget/text/balanced-budget-slides-3-23-26.txt",
  "txt/fy27-final-budget-doc.txt": "district-budget/text/final-budget-document.txt",
  "txt/fy27-multi-scenario-addendum.txt": "district-budget/text/budget-addendum-multi-scenario-financial-analysis.txt",
  "txt/fy27-projections-3-16-26.txt": "district-budget/text/fy27-budget-projections-as-of-3-16-26-with-restorations.txt",
  "txt/fy27-projections-3-23-26.txt": "district-budget/text/fy27-budget-projections-as-of-3-23-26.txt",
  "txt/fy27-sc-slidedeck-3-23-26.txt": "district-budget/text/slide-deck-from-the-sc-meeting-3-23-26.txt",
  "txt/town-2026-election-warrant.txt": "town-budget/text/4161-2026-annual-town-election-warrant.txt",
  "txt/town-additional-revenue-plan.txt": "district-budget/text/additional-town-revenue-spending-plan.txt",
  "txt/town-article13-fy27-capital-plan.txt": "town-budget/text/4111-article-13-fy-2027-capital-plan.txt",
  "txt/town-atm-2026-booklet-warrant.txt": "town-budget/text/3765-town-meeting-booklet-including-warrant.txt",
  "txt/town-fy27-budget-press-release.txt": "town-budget/text/4090-click-here-for-a-release-on-quot-understanding-lunenburg-apos-s-fy27-budget-how-.txt",
  "txt/town-fy27-detailed-budget.txt": "town-budget/text/4082-fy-2027-detailed-budget.txt",
  "txt/town-fy27-operating-budgets-balanced-tier1-tier2.txt": "town-budget/text/3769-fy-2027-operating-budgets-balanced-tier-1-tier2.txt",
  "txt/town-revenue-prop25-presentation.txt": "town-budget/text/1591-town-revenue-amp-proposition-2-5-presentation.txt",
}

/** The current path for a path that used to exist, or null. */
export function movedTo(path) {
  if (EXACT[path]) return EXACT[path]
  if (REPLACED[path]) return REPLACED[path]
  for (const [from, to] of PREFIX) {
    if (path.startsWith(from)) return to + path.slice(from.length)
  }
  return null
}
