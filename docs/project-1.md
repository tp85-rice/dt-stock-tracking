# Project 1: AI stock driver tracker

Exported 2026-10-14. Working notes from the brainstorm, covering the idea, architecture, risks, scoring design, the 11-name universe, and the latest driver and data-availability re-check. Facts in the per-ticker sections come from web searches run on 2026-10-14; items I could not verify are flagged.

## 1. Idea

A web app where the user enters a ticker (for example TSLA) and gets:

1. A visualization of the key growth drivers that could rerate the stock over 1-5 years, based on deep assessment of the business, strategy, management presentations, earnings calls, and analyst views on what moves the needle.
2. A dashboard of key signals per driver, with alerts when momentum appears. Momentum can come from official and unofficial information.
3. Financial charts in the style of vizualstocks: segment revenue, profit contribution, margins over time, cost trends, and valuation trends (for example P/E over the last 5 years).

Hard product rules: no price targets, no buy/sell signals. The app only assesses the positivity and momentum of each signal.

## 2. Decisions made so far

| Topic | Decision |
|---|---|
| Build approach | Manual-first: hand-build the driver map and signals for 11 stocks before writing product code |
| Universe | TSLA, NVDA, GOOG, MRNA, GRAB, SE, KTOS, RKLB, AMZN, DUOL, COIN |
| Base case | Assumed: consensus-anchored, with the management case shown as a second reference line (user has not explicitly confirmed) |
| Scoring | Green / yellow / red per signal vs base case, plus separate momentum arrow, plus grey for missing or stale data |
| Roll-up | No single stock-level score. Colors per signal and at most per driver |
| Outputs | Positivity and momentum only. No targets, no buy/sell language |
| Forecasting | Qualitative driver state (accelerating, stalled, at risk) with ranges, not price targets. LLMs do not predict trends |

## 3. Proposed architecture

**Driver discovery (slow loop, quarterly or on major events).** Inputs: SEC EDGAR filings (10-K, 10-Q, 8-K; 20-F and 6-K for foreign filers like SE and GRAB), earnings call transcripts, investor decks. Sell-side reports are paywalled, so use a proxy: cluster the analyst questions in earnings call Q&A to see what the Street thinks matters. Pipeline: segment extraction, management KPI extraction, Q&A theme clustering, LLM synthesis into a structured Driver object (name, thesis, valuation mechanism, horizon, confidence, evidence citations, candidate leading indicators). Force JSON output against a schema and require every claim to cite a source chunk.

**Signal catalog (the real moat).** Each signal maps to a source adapter, unit, cadence, baseline, polarity, and reliability. Tiers:
- Tier A, hard/official: SEC filings, regulatory filings, DoD contract announcements, NHTSA, FCC, patents, on-chain data.
- Tier B, alt data: job postings, community trackers, app rankings, web traffic, shipping data, prediction-market odds.
- Tier C, soft: news, Reddit, X, forums, YouTube.

**Ingestion.** Scheduled jobs per source adapter, raw documents to object storage, parsed text plus embeddings in Postgres with pgvector. Dedup by URL hash plus semantic similarity so one story rewritten 200 times does not fake momentum. Tools: Firecrawl or Apify, Playwright, GDELT or a news API, Inngest/Trigger.dev/Temporal for orchestration.

**Event and momentum engine.** The LLM extracts structured events: `{driver, signal, event_type, value, unit, entity, date, source, confidence}`. Momentum is computed with plain statistics (z-score vs rolling baseline, EWMA, source-weighted mention velocity). The LLM explains alerts; the math decides whether one fires. Colors come from rules in config, not LLM judgment.

**Stack sketch.** Next.js on Vercel, Supabase Postgres (pgvector for text, partitioned tables or Timescale for `signal_observations`), Python worker service for crawling and LLM jobs, TradingView Lightweight Charts plus ECharts or Recharts, Polygon/Finnhub/FMP for market and fundamentals data.

**Core tables.** `companies`, `drivers`, `signals`, `signal_observations`, `documents`, `events`, `evidence_links`, `alerts`, `user_watchlists`, plus `base_cases` (versioned, dated) and a `definition_changes` flag per time series.

## 4. Scoring design

- Color = position vs base case. Arrow = direction of momentum. Grey = no data or stale. Do not let yellow mean both "unchanged" and "broken scraper".
- Thresholds are rules in config: polarity (higher is better or worse), expected path, tolerance band (for example green at or above base, yellow within 10% below, red beyond).
- Polarity is defined per driver, not per metric. Customer capex is good for NVDA and a free-cash-flow headwind for AMZN and GOOG.
- Base case is a quantified path with a snapshot date and version, rebased after each earnings call with history kept, so "green versus which base case?" is always answerable.
- Event-ladder signals (milestones that occurred, slipped, or failed) are needed alongside numeric bands, for MRNA, RKLB, KTOS, COIN, and GRAB's GoTo situation.
- Each driver needs at least one Tier A or B signal. A driver with only Tier C signals is labeled "narrative-only" in the UI. Cap at 5 signals per driver.
- UI explainer: green means ahead of base case, not "stock goes up". If consensus is already optimistic, in-line is already priced in.

## 5. Financial charts: data reality

| Chart | Catch |
|---|---|
| Segment revenue and profit | XBRL segment tagging is inconsistent and restated on reorganizations. Many companies do not disclose segment profit (Tesla does not for FSD or Robotaxi). Use a vendor plus manual cleanup |
| Margins and cost trends | Gross and operating margin are easy. Cost breakdowns beyond opex lines live in filing text, so expect LLM extraction plus human verification |
| Valuation history | Needs point-in-time price and trailing EPS adjusted for splits. Pick GAAP or non-GAAP and label it. P/E is meaningless with negative earnings, so fall back to EV/Sales or EV/EBITDA. Forward P/E history needs historical consensus, usually paid |

## 6. Risks, ranked

1. **Regulatory.** Alerts plus forecasts can start to look advisory. Keep content impersonal, no targets, no buy/sell language, and talk to securities counsel before public launch. Set a policy against ingesting possible MNPI (leaks, employee posts).
2. **Signal validity.** Nobody has shown most candidate signals lead price or fundamentals. Backtest with point-in-time data and watch for lookahead bias, survivorship bias, data-snooping, and LLM training contamination on historical "as of" tests.
3. **"Any ticker" scalability.** Signal catalogs are bespoke per company. Build templates by archetype and hand-curate the first 20-50 tickers.
4. **Hallucination and false alerts.** Require citations, cross-source confirmation for Tier C, and confidence scores. Alert fatigue kills retention.
5. **Prompt injection and manipulation.** Crawled text is untrusted input. Treat it as data, sandbox agent tools, no write access for crawlers. Bot farms can fake momentum.
6. **Time-horizon mismatch.** Daily signals mostly speak to 1-4 quarters, the thesis is 1-5 years. Split the UI into thesis tracking and momentum alerts.
7. **Edge decay and competition.** AlphaSense, Koyfin, Stocktwits, Perplexity Finance. The defensible angle is the driver-to-signal mapping with transparent provenance.
8. **Cost.** Tiered refresh, cached embeddings, cheap-model triage before expensive-model calls.
9. **Validation bias.** TSLA is a good demo but a poor rigor test because sentiment dominates. Validate on hard-signal names too.

## 7. The 11 names: status as of 2026-10-14

Rating key. Impact: H/M/L on the 1-5 year rerating thesis. Data: A = free and official, B = free but unofficial or biased, C = paid, X = not obtainable.

Templates needed: roughly 8, since TSLA/NVDA/GOOG/AMZN share a skeleton and SE/GRAB share one. MRNA, COIN, KTOS, and DUOL each need their own.

### TSLA

Robotaxi is live but thin: an independent tracker lists unsupervised operation in Miami, Houston, and Dallas, Austin ramping, and the Bay Area with a safety driver. Orlando and Tampa followed in July for seven cities across three states. Fleet size per city is not disclosed. Tesla targeted about a dozen states by year end and unmonitored FSD on customer cars in Q4. Optimus is the downgrade: the July shareholder deck replaced "late July or August" production timing with "later this year", and no production report has carried an Optimus line item. Tesla publishes a company-compiled analyst consensus: Q3 deliveries of 486,532 beat the 461,974 consensus, while storage of 13.7 GWh missed the 15.9 GWh consensus by 14%.

| Driver | Impact | Best signal | Data |
|---|---|---|---|
| Robotaxi scale | H | Cities unsupervised, geofence area, fleet per city | Cities A, fleet B |
| Unsupervised FSD on customer cars | H | Release event vs Q4 target | A (event) |
| Optimus | H (narrative) | First unit count in quarterly P&D report | A, binary, currently zero |
| Energy storage | M | GWh vs company-compiled consensus | A quarterly |
| Core auto | M | Deliveries vs consensus, auto gross margin | A |

Freeze the base case after the October 21 earnings call.

### NVDA

Q2 FY27 revenue was $96.2B vs $92.07B consensus. October-quarter guide is $108B with no China data center compute revenue assumed. Management put FY2028 growth at about 70% vs 44% modeled by analysts. Vera Rubin should be about 20% of data center revenue. China is pure optionality (base case zero). New risk driver: inventory rose to $32B and days sales outstanding to 60, and Nvidia is increasingly financing whole data center projects.

| Driver | Impact | Best signal | Data |
|---|---|---|---|
| Hyperscaler capex | H | Capex lines in AMZN/GOOG/MSFT/META 10-Qs | A quarterly |
| Rubin ramp | H | Rubin share of DC revenue vs guide | A quarterly |
| Non-hyperscale demand | H | New non-hyperscale DC sub-segment | A, new series |
| Gross margin | M | GM vs guided trough (Q4 guided 71-72%) | A |
| China | M (upside only) | BIS rules, license grants | A event |
| Balance sheet quality | M (risk) | Inventory, DSO, lease commitments | A quarterly |

TSMC monthly revenue is the best monthly proxy (A, free).

### GOOG

Cloud is now driver #1, ahead of search resilience. Search grew 17%, Google Cloud grew 82% to $24.8B, backlog reached $514B. Q2 capex was about $44.9B (doubling YoY), pushing free cash flow negative. Waymo surpassed 500,000 fully autonomous rides per week. Data trap: Alphabet changed its backlog definition in Q1 2026 to include contracts of one year or less, so the backlog series has a structural break.

| Driver | Impact | Best signal | Data |
|---|---|---|---|
| Cloud growth and backlog conversion | H | Backlog, Cloud growth, Cloud op margin | A quarterly (series break) |
| Search resilience | H | Search revenue growth vs consensus | A quarterly |
| Capex and FCF | H (negative) | Capex, FCF | A |
| Waymo | M | Weekly rides, cities | B, sporadic; CPUC data CA only |
| Gemini monetization | M | MAU, paid subs | Sporadic management disclosure |

### AMZN

AWS grew 37% to $42.2B (fastest in 18 quarters). Backlog $496B, up from $364B in March. 2026 cash capex now about $220B, and management still expects capacity to fall short of demand in 2026 and into 2027. Ads $19.8B (+26%). Free cash flow turned negative. Trainium capacity reported sold out through 2027. Kuiper is now Amazon Leo, with commercial service guided for Q3. Zoox is immaterial for now.

| Driver | Impact | Best signal | Data |
|---|---|---|---|
| AWS growth vs capacity | H | AWS growth, backlog, power capacity adds | A quarterly; capacity sporadic |
| Capex and FCF | H (negative) | Capex, FCF | A |
| Ads | M | Ad revenue growth | A |
| Trainium | M | Chip run-rate, customer commitments | Sporadic |
| Amazon Leo | M | Satellites launched, commercial customers | A (FCC, launch manifests) |
| Retail margin | M | NA and International op margin | A |

### MRNA

Base case moved positively: the FDA approved mFLUSIVA (first US mRNA flu vaccine) for adults 50+, the flu/COVID combo got EU authorization, cash was $6.9B at June 30 with year-end guide of $4.7-5.2B, and cash breakeven is targeted for 2028. Approval is not uptake: ACIP cannot revoke an FDA approval but decides usage recommendations. Intismeran melanoma Phase 3 readout still expected in H2 2026 (management guidance only). This name breaks percentage-band scoring: use event-type signals (occurred, delayed, failed) and treat cash runway as a first-class driver. Keep policy polarity neutral and sourced to official actions.

| Driver | Impact | Best signal | Data |
|---|---|---|---|
| Intismeran Phase 3 | H (binary) | Readout outcome and timing | A event |
| Seasonal franchise uptake | H | ACIP recs, script and uptake data | ACIP A; uptake mostly C |
| Cash runway to 2028 breakeven | H | Cash vs YE guide, opex | A quarterly |
| US vaccine policy | H | ACIP/CDC/FDA actions | A event, politically loaded |
| Ex-US approvals | M | EMA, Health Canada, TGA decisions | A event |

### COIN

Base case reset. The Senate voted 49-50 against cloture on the CLARITY Act on Sept 15, and Polymarket priced 2026 enactment at 6.5% afterward. The bill stays on the calendar but January 2027 brings a legislative reset, so regulation moves to 2027+ optionality. Structural driver is stablecoins: Q1 stablecoin revenue was $305M (about 52% of subscription and services revenue), and the Senate text proposed banning rewards on idle stablecoin balances. Split signals into market-driven (exogenous to crypto prices) and company-specific (share of volume, stablecoin share, product adoption) and flag that in the UI. Use adjusted EBITDA or revenue multiples for valuation, not GAAP P/E, because of mark-to-market swings.

| Driver | Impact | Best signal | Data |
|---|---|---|---|
| Stablecoin economics | H | USDC supply (on-chain), USDC held on platform | Supply A daily; on-platform quarterly |
| Derivatives (Deribit) | H | Volume, open interest | B/C |
| Spot volume and share | H (exogenous) | CEX volume, COIN share | B/C |
| Market structure regulation | H | Bill status, SEC/CFTC rulemaking | A event; prediction odds B |
| Revenue mix | M | S&S share of revenue | A quarterly |

### GRAB

A major driver I had missed: Indonesia reportedly issued Presidential Regulation 27/2026 capping platform commissions at 8% (from 20%), and Grab's guidance assumes the current Indonesia ojol commission structure stays. This rests on one source, verify scope and timing before scoring. Operations are strong: Q2 revenue +22% to $997M, adjusted EBITDA +54% to $168M, MTU 54M, guidance raised (partly from consolidating Superbank and acquiring Stash). Commercial AV fares in Singapore's Punggol planned for Q4. GoTo: last firm facts found are repeated denials of talks; current status unconfirmed.

| Driver | Impact | Best signal | Data |
|---|---|---|---|
| Indonesia ride-hailing regulation | H (downside) | Commission cap enforcement, ojol take rate | A, Bahasa-language sources |
| GoTo consolidation | H (binary) | IDX/SGX disclosures, KPPU review | A event; rumors C-tier |
| Fintech (loan book, Superbank) | M-H | Loan book, fintech EBITDA breakeven | A quarterly |
| On-demand GMV and margin | M | GMV, MTU, mobility margin | A quarterly |
| Autonomous vehicles | L near-term | Punggol commercial launch | A event |

### SE

Strongest name for data. Shopee GMV +28% to $38.3B, ad revenue up over 70%, ad take rate up over 90 bps (roughly 2.9%), overall GAAP take rate 14.6%. Monee loan book +62% to $11.1B with 1.0% NPL90. Shopee expected to reach $1B adjusted EBITDA for the year. Watch Brazil: fastest-growing market, described as higher-rate and higher-risk, so Monee credit quality in Brazil deserves its own signal. Management said the pace of fixed commission increases is likely to slow.

| Driver | Impact | Best signal | Data |
|---|---|---|---|
| Shopee ad monetization | H | Ad take rate, GAAP take rate | A quarterly |
| Shopee profitability | H | Shopee adj EBITDA vs $1B target | A |
| Monee growth vs credit quality | H | Loan book, NPL90, provisions, Brazil credit macro | A (6-K plus Brazil central bank data) |
| Competition (TikTok Shop) | M | App rank, share estimates | B/C |
| Garena | L-M | Bookings, game rankings | A/B |

### KTOS

Northrop and Kratos won the USMC MUX TACAIR CCA contract with Valkyrie as the aircraft, first prototype due summer 2026. About 165 jet drones produced per year, Oklahoma City expansion under way, about $1.2B equity raise at $84 in February. Catalysts: jet engine LRIP in H2 2026, possible Taiwan Mighty Hornet production decision in Q4 2026. Data trap: Northrop is the prime, so Valkyrie dollars often appear under Northrop in DoD announcements, so match on program name, not just company. Sources conflict on when Valkyrie reaches 40 units per year (end of 2027 vs end of 2028), so use the company's latest statement.

| Driver | Impact | Best signal | Data |
|---|---|---|---|
| Valkyrie/CCA production | H | Production contracts, ramp vs 40/yr target | A, with subcontract trap |
| Space and missile defense | M | Space Force and SDA awards | A (DoD, SAM.gov) |
| Jet engines | M | LRIP start | A event |
| International (Taiwan) | M | DSCA arms sale notifications | A |
| Defense budget | M | FY27 appropriations | A |

### RKLB

Base case reset. On the August 2026 call, Rocket Lab said Neutron should reach the pad in Q4 2026 but launch within that quarter is not guaranteed because static fire testing comes first. Base case should now be first launch in 2027. Score Neutron as a milestone ladder (pad arrival, static fire, FAA license, launch) so users see progress or slippage between earnings calls. One slip turns many signals red at once.

| Driver | Impact | Best signal | Data |
|---|---|---|---|
| Neutron first launch | H | Milestone ladder, FAA license | A events; prediction markets B |
| Electron cadence | M | Launches per quarter vs plan | A |
| Space systems backlog | M-H | Backlog | A quarterly |
| Government awards | M | SDA and NASA contracts | A |

### DUOL

Tension between users and monetization. DAU +23% to 58.7M, paid subscribers +17% to 12.7M, goal of 100M DAU by 2028. But bookings grew only 8%, and shares fell 11% on cautious bookings guidance (about 11% full-year). The call raised the possibility of discontinuing the Max plan. Keep DAU and bookings as separate drivers with separate polarity, otherwise the dashboard shows green on users while the market reacts to red on revenue. Best leading indicators (DAU, engagement) are mostly paid third-party data.

| Driver | Impact | Best signal | Data |
|---|---|---|---|
| DAU growth | H | DAU YoY vs guide | A quarterly; monthly only via paid app data |
| Monetization | H | Bookings vs ~11% guide, paid sub conversion | A quarterly |
| Gross margin and AI cost | M | GM vs guide | A |
| Product tiering (Max) | M | Tier changes | A event |

## 8. Data source reality (verified 2026-10-14 unless noted)

| Source | Status |
|---|---|
| SEC EDGAR | Free, reliable. Start here |
| Earnings call transcripts | Paid vendor needed; scraping is a licensing problem |
| X API | Pay-per-use is the default since Feb 6, 2026, free tier gone for new developers. About $0.005 per post read, 7-day search only on pay-per-use, read cap reported as 2M or 3M per month (sources disagree, check the official page). Self-serve is aimed at prototyping and limited apps, commercial use expected via Enterprise at $42,000+ per month. Third-party providers exist for history |
| Reddit | Effectively out for the MVP. Access requires explicit approval before any data access, commercial use needs written approval and a separate agreement, no published commercial rate card, ML or AI training use restricted. Aggregator APIs inherit the ToS problem |
| Forums (Tesla Motors Club etc.) | ToS restrictions, fragile scrapers, blocking risk |
| Paywalled news | Analyze headlines and snippets, do not store or republish full text |
| Real-time quotes | Exchange display licensing matters. Use delayed data or a vendor with redistribution license |

New free sources worth adding: company-compiled consensus (Tesla publishes one, check whether others do) and prediction-market odds for binary events (check their terms before displaying commercially).

## 9. Cross-cutting framework changes

- Hyperscaler capex is the most important shared signal. Build once, attach with per-company polarity.
- Every time series needs a "definition change" flag. Examples: Alphabet's backlog redefinition, Coinbase's stablecoin revenue reclassification, Nvidia's new data center sub-segments. Without it, charts and momentum math produce false signals.
- Add an event-ladder base case type alongside numeric bands.
- Most hard signals are quarterly filings. Between earnings, momentum relies on a small set of monthly or event signals: TSMC monthly revenue, on-chain USDC, DoD announcements, launch events, regulatory actions, prediction-market odds.
- Shared adapters cut the work to about 6 or 7 source families: hyperscaler capex (NVDA, GOOG, AMZN), USAspending/SAM.gov/DoD (KTOS, RKLB), app rankings and web traffic (SE, GRAB, DUOL), SEA regional regulation (SE, GRAB), CPUC/NHTSA (TSLA, GOOG, AMZN), on-chain data (COIN).

## 10. Manual build process per stock

One spreadsheet per ticker with five tabs:

1. Drivers: name, thesis, valuation mechanism, horizon, source citations.
2. Base case: quantified path with date and version, consensus-anchored with management case as reference line.
3. Signals: source, cadence, polarity, thresholds, reliability, tier.
4. Source log: URL, access method, ToS note.
5. Scoring log: observed value, color, arrow, date.

Budget half a day to a day per stock the first time. Pilot three names that stress different things (NVDA for clean hard signals, TSLA for soft signals, COIN or MRNA for template-breaking), fix the template, then batch the other eight. Most names report between late October and mid-November, so build templates and signal catalogs now and freeze each base case right after that company's print. Snapshot the pre-earnings state as version 1. Decide the manual update cadence up front so a stale scoring log is not mistaken for a broken scraper.

## 11. Unverified items

- Indonesia's 8% commission cap rests on one source.
- GRAB-GoTo current status is unclear past repeated denials.
- Kratos Valkyrie ramp date conflicts across sources.
- Intismeran readout timing is management guidance only.
- X read cap differs between sources (2M vs 3M).
- All driver lists should be re-checked against the Q3 calls as they land (TSLA reports October 21).
- Legal posture (advisory-adjacent risk) not yet reviewed by counsel.

## 12. Open questions

1. Who is the user: retail, analysts, or funds? This sets legal posture, pricing, and rigor expectations.
2. Confirm the base case definition (consensus-anchored with management reference line is assumed).
3. Budget for licensed data (transcripts, alt data, app intelligence for DUOL)?
4. Real-time or daily refresh?
5. Qualitative driver direction only, or numeric forecasts for some signals?
6. Any ticker or curated universe at launch?
7. Which vizualstocks chart types to replicate exactly (pages were not opened)?

## 13. Next steps

1. Build the five-tab spreadsheet template (xlsx or Google Sheets), pre-filled with NVDA and TSLA from this document.
2. Run the data availability check on the pilot three before finalizing signals.
3. Re-freeze base cases after each company's Q3 print.
4. Add the definition-change flag and event-ladder type to the template from day one.

## 14. Sources

Tesla and robotaxi
- https://www.basenor.com/pages/tesla-robotaxi-tracker
- https://www.basenor.com/blogs/news/tesla-robotaxi-launches-in-orlando-and-tampa-just-18-days-after-miami
- https://teskas.net/t/fsd-4/17477?tl=en
- https://ai2.work/blog/tesla-s-optimus-line-is-open-at-fremont-output-is-still-zero
- https://driveteslacanada.ca/?p=124427

Nvidia
- https://rivkin.com.au/?p=37534
- https://transcripts.platformaeronaut.com/summaries/NVDA-2Q27-AI-Summary
- https://www.xtb.com/sca-en/market-analysis/news-and-research/nvidia-shares-react-to-solid-earnings-report-and-stonger-guidance-what-s-next-for-the-ai-giant

Alphabet and Amazon
- https://www.sec.gov/Archives/edgar/data/0001652044/000165204426000071/goog-20260630.htm
- https://www.nasdaq.com/articles/alphabet-q2-earnings-call-highlights
- https://247wallst.com/investing/2026/07/27/alphabet-capex-concerns-are-bogus-but-theres-an-internal-hedge-against-them-regardless/
- https://letsdatascience.com/news/aws-revenue-growth-outruns-available-ai-capacity-b0361d90
- https://pro.thestreet.com/portfolio/were-boosting-our-amazon-price-target
- https://vectorshift.ai/research/companies/amazon-com/earnings/2026-q1-summary

Moderna and Coinbase
- https://www.beckershospitalreview.com/pharmacy/fda-approves-modernas-mrna-flu-vaccine/
- https://www.newswire.com/news/moderna-reports-second-quarter-2026-financial-results-and-provides-business
- https://medcitynews.com/2026/08/moderna-flu-vaccine-fda-approval-mflusiva-acip-cdc-mrna/
- https://thedefiant.io/news/regulation/senate-blocks-clarity-act-49-50-with-no-democratic-votes-to-proceed
- https://news.bitcoin.com/regulation-and-legal/clarity-act-isnt-dead-but-washington-is-running-out-of-calendar/
- https://stockti.com/coinbase-s-post-clarity-act-rally-fades-as-q2-loss-forecast-looms

Grab and Sea
- https://www.sec.gov/Archives/edgar/data/0001855612/000185561226000123/a2026q2-earningspressrelea.htm
- https://www.marketbeat.com/instant-alerts/grab-q2-earnings-call-highlights-2026-08-03/
- https://transcripts.platformaeronaut.com/summaries/GRAB-2Q26-AI-Summary
- https://dailysocial.id/p/goto-finds-profit-ojol-gets-a-floor
- https://media.dealstreetasia.com/stories/grab-goto-deal-445154
- https://www.marketbeat.com/instant-alerts/sea-q2-earnings-call-highlights-2026-08-11/
- https://www.roic.ai/quote/SE:US/transcripts

Kratos and Rocket Lab
- https://ir.kratosdefense.com/node/33006
- https://www.barchart.com/story/news/3140125/kratos-expands-oklahoma-city-manufacturing-facility-to-accelerate-production-of-valkyrie-firejet-and-other-jet-drone-systems
- https://fintool.com/app/research/companies/KTOS/earnings/Q4%202025
- https://www.robotics.press/news/kratos-defense-447m-space-force-valkyrie-production/
- https://spacecenter.gov.ua/novyny/pershij-zapusk-neutron-mozhe-buti-vidkladenij-do-2027-roku.html?lang=en

Duolingo
- https://www.sec.gov/Archives/edgar/data/0001562088/000162828026053299/q2fy26duolingo6-30x26share.htm
- https://quartr.com/events/duolingo-inc-duol-q2-2026_3P0xhIR9
- https://www.allinvestview.com/earnings/DUOL/q2-2026/
- https://longportapp.cn/news/295028818

X and Reddit data access
- https://opentweet.io/how-to/x-api-pay-per-use-explained
- https://www.xpoz.ai/blog/guides/understanding-twitter-api-pricing-tiers-and-alternatives/
- https://opentermsarchive.org/en/memos/x-replaces-its-dollar200-entry-level-api-plan-with-a-pay-per-use-model/
- https://apiserpent.com/blog/best-reddit-api-providers-2026
