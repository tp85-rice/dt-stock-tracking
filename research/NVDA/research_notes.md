# NVDA research notes

Refreshed 2026-11-05 by the driver-sheet-builder skill. Every figure below was read from a page opened on www.sec.gov or nvidianews.nvidia.com (inline XBRL facts or the filing text). Source IDs match the sheet's Source log.

Still blocked from the build environment: data.sec.gov, reuters.com, Yahoo Finance (proxy), and investor.nvidia.com, pr.tsmc.com, ir.aboutamazon.com, abc.xyz, investor.atmeta.com (the sites refuse automated requests). So **no analyst consensus yet**.

## Verified facts

### NVIDIA (fiscal Q2 FY27 = Apr 27 to Jul 26 2026)

| Item | Q1 FY27 | Q2 FY27 | Q2 FY26 | Source |
|---|---|---|---|---|
| Revenue, $B | 81.615 | 96.221 | 46.743 | R11, R1 |
| Gross profit, $B | 61.157 | 72.142 | 33.853 | R11, R1 |
| GAAP gross margin | 74.9% | 75.0% (74.98%) | 72.4% | computed; R2 states 75.0% |
| Data Center revenue, $B | 75.246 | 89.023 | 41.096 | R1 |
| Hyperscale, $B | 43.050 (recast; 37.869 as first reported) | 48.710 | 24.168 | R1, R10 |
| AI Clouds, Industrial & Enterprise (ACIE), $B | 32.196 (recast; 37.377 as first reported) | 40.313 | 16.928 | R1, R10 |
| Edge Computing, $B | 6.369 | 7.198 | 5.647 | R1 |
| Inventory, $B | 25.797 | 31.575 | | R11, R1 |
| Accounts receivable, $B | 40.710 | 63.059 | | R11, R1 |
| DSO, days (company-stated) | 45 | 60 | | R10 |
| Supply and capacity commitments, $B | 119 | 279 | | R1 |
| Provisions for inventory and excess purchase obligations | | $985M (net GM impact −0.8 pt) | | R1 |
| China | | Hopper Data Center shipments to China "less than 1% of Data Center revenue" | | R10 |

**Q3 FY27 outlook (R2, R10):** revenue $108.0B ±2%; "NVIDIA is not assuming any Data Center compute revenue from China in its outlook"; GAAP and non-GAAP gross margin 74.0% ±50 bp (the earlier GAAP vs non-GAAP conflict is resolved: both are 74.0%).

**Rubin (R2, R10):** "Vera Rubin platform is ramping into full production"; inventory rose "as we prepare for the introduction of Vera Rubin in the third quarter". No Rubin revenue share disclosed.

**Definition changes (R1):** Q1 FY27 new revenue-by-market-platform presentation (Hyperscale / ACIE / Edge Computing), prior periods recast. Q2 FY27: one company moved from ACIE to Hyperscale "due to a change in their business model", prior periods recast.

**Q3 FY27 results call (R20):** Tuesday 2026-11-17, 2 p.m. PT; quarter ended 2026-10-25; CFO commentary published in writing before the call.

### Hyperscaler capex (cash purchases of property and equipment, $B; excludes finance leases)

| Company | Q1 CY26 | Q2 CY26 | Q3 CY26 | Q3 CY25 | Sources |
|---|---|---|---|---|---|
| Amazon (purchases of property and equipment, gross) | 44.203 | 54.208 | 77.259 | 35.095 | R12, R3 |
| Alphabet | 35.674 | 44.924 | 51.355 | 23.953 | R14, R13, R4 |
| Microsoft (FY ends June) | 30.876 | 35.802 | 39.367 | 19.394 | R16, R15, R5 |
| Meta | 18.997 | 30.116 | 33.942 | 18.829 | R18, R17, R6 |
| **Total** | **129.750** | **165.050** | **201.923** | **97.271** | |

Quarters are year-to-date minus prior year-to-date where the filing reports only YTD. Q3 CY26 total: +107.6% YoY, +22.3% QoQ. Finance-lease principal payments are excluded (Q3 CY26: Amazon 0.433, Alphabet 1.110, Microsoft 1.000; Meta reports YTD only).

### TSMC monthly revenue (R19, R7)

| Month | NT$B | YoY | MoM |
|---|---|---|---|
| Aug 2026 | 514.81 | +53.3% | +10.1% |
| Sep 2026 | 511.86 | +54.6% | −0.6% |

October 2026 is due around 2026-11-10.

## Earlier leads: outcome

| Lead (from search summaries, 2026-11-04) | Outcome |
|---|---|
| Q2 FY27 revenue ~$96.2B, DC ~$89.0B | Confirmed: 96.221 / 89.023 |
| Gross margin 75.0%, GAAP or non-GAAP unclear | Confirmed GAAP 75.0% |
| Supply commitments $279B vs $119B | Confirmed |
| Q3 guide $108B ±2%, GM 74% ±50 bp, label unclear | Confirmed; GAAP and non-GAAP both 74.0% |
| Edge Computing ~$7.2B possibly new | Confirmed: new market platform since Q1 FY27 |
| Amazon capex 54.2 / 77.3 | Confirmed: 54.208 / 77.259 |
| Microsoft $45.2B incl. finance leases | Not used: our definition excludes finance leases (39.367 cash capex) |
| TSMC Sep NT$511.86B +54.6% | Confirmed |
| Earnings date Nov 17 vs Nov 18 | Nov 17 confirmed by the company (R20) |
| Margin trough 71–72% in Q4 FY27 (call remarks) | Not found in the press release or CFO commentary; the Q3 guide is 74.0%. Dropped |
| Capex guidance (Amazon ~$220B, Alphabet $195–205B, Meta $130–145B) | Not verified (earnings-call material, sites blocked). Not used |
| Consensus "closer to $104B" | Not verified. Not used |

## Gaps

- Analyst consensus for Q3 FY27 (revenue, gross margin) and pre-report consensus for Q2 FY27: blocked sources.
- 2026 capex guidance per hyperscaler (earnings calls, not in 10-Qs).
- US export-control notices (R9): bis.gov not tried.
