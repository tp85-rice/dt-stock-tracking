# NVDA research notes

Built 2026-11-04 by the driver-sheet-builder skill. Status: **structure only, no numbers in the sheet.**

The build environment's network allowlist blocked every primary source (www.sec.gov, nvidianews.nvidia.com, investor.nvidia.com, pr.tsmc.com, Yahoo Finance), so no page could be opened. Under the skill's rules a number that was not read from an opened page is not entered. Everything below is a **lead from web-search summaries: UNVERIFIED, do not import as is**. Each lead names where to check it.

## Leads to verify (unverified)

| Item | Lead | Period | Where to verify | Signal |
|---|---|---|---|---|
| Earnings release date for Q2 FY27 | 2026-08-26 | Q2 FY27 (qtr ended Jul 26 2026) | R2 | — |
| Total revenue | about $96.2B, +106% YoY | Q2 FY27 | R2 | — |
| Data Center revenue | about $89.0B, +117% YoY | Q2 FY27 | R2 | context for S4 |
| Gross margin | 75.0% (GAAP or non-GAAP unclear) vs 72.4% a year earlier | Q2 FY27 | R1, R2 | S5 |
| Inventory provisions | $985M, partly offset by a $177M release | Q2 FY27 | R1 | S7 context |
| Supply commitments | $279B vs $119B prior quarter, mostly memory | Q2 FY27 | R1 | S9 |
| China | Hopper DC shipments to China under 1% of Data Center revenue; Q3 guide assumes no China DC compute revenue | Q2 FY27 / Q3 guide | R2 | S6 |
| Q3 FY27 outlook | revenue about $108.0B ±2%; gross margin about 74% ±50 bp (GAAP vs non-GAAP labelled inconsistently) | Q3 FY27 | R2 | S5 Management row |
| Margin trough | call remarks reportedly say margin bottoms at 71–72% in Q4 FY27 | Q4 FY27 | call transcript / R2 | S5 anchor |
| Possible definition change | an "Edge Computing" line of about $7.2B, +27% YoY | Q2 FY27 | R2 | new market platform? |
| Q3 FY27 earnings date | Tue 2026-11-17 (announced Oct 28); some calendars show Nov 18 | Q3 FY27 | investor.nvidia.com | Disclosure steps' target date |
| Consensus Q3 FY27 revenue | "closer to $104B" (no source or date) | Q3 FY27 | R8 | — |
| Amazon capex | purchases of P&E about $54.2B (Q2 CY26), about $77.3B (Q3 CY26); 2026 guide about $220B | Q2/Q3 CY26 | R3 | S1 |
| Alphabet capex | 2026 guide $195–205B, unchanged on the Oct 28 call; quarterly figures not found | 2026 | R4 | S1 |
| Microsoft capex | $45.2B incl. finance leases (FY27 Q1); a second source says about $170B for CY2026 | FY27 Q1 | R5 | S1 |
| Meta capex | 2026 guide $130–145B; quarterly not found | 2026 | R6 | S1 |
| TSMC Sep 2026 revenue | NT$511.86B, +54.6% YoY, −0.6% MoM; Q3 NT$1,494.24B | Sep 2026 | R7 | S2 |
| Export controls | Jan 13 2026: case-by-case H200 licensing with a 25% fee; Jul 2026: H200 shipping "in very small quantities" | 2026 | R9 | S6 |

## Gaps (not found even as leads)

- Inventory, accounts receivable and DSO for Q2 FY27 and Q1 FY27 (S7, S8)
- Whether NVIDIA states Rubin's share of Data Center revenue (S3)
- Any customer-type split of Data Center revenue (S4)
- Consensus with a named source: Q3 FY27 revenue, EPS, gross margin; the pre-report Q2 FY27 consensus
- Alphabet and Meta quarterly capex; a verified Microsoft quarterly figure
- TSMC Aug 2026 (and Oct 2026, due around Nov 10)
- Export-licence news Aug–Nov 2026

## Conflicts

- Q3 FY27 gross margin guide: GAAP vs non-GAAP labelling differs between secondary sources.
- Microsoft capex: $45.2B (quarter) vs about $170B (calendar year), not compared like for like.
- Q3 FY27 earnings date: Nov 17 (company) vs Nov 18 (third-party estimate).

## Decisions for the owners

1. Consensus source (R8): which one, given its terms (figures not republished raw)?
2. Signals with no consensus (S2, S7, S8, S9): use a Thesis row only (GREY until a Consensus row exists) or treat our estimate as the scored base case?
3. S4: keep only if NVIDIA discloses a customer-type split; otherwise delete it and D3 shows narrative-only.
4. Share of price for each driver: needs a thesis session (valuation work), left blank.

## To finish the sheet

Either allow the hosts below in the environment's network settings and re-run the skill ("Refresh NVDA driver sheet"), or fill the numbers by hand from the sources: www.sec.gov, nvidianews.nvidia.com, investor.nvidia.com, investor.tsmc.com, pr.tsmc.com, ir.aboutamazon.com, abc.xyz, microsoft.com, investor.atmeta.com, reuters.com.
