# House Rules

Cross-ticker analysis rules. Read at the start of every research session and every driver-sheet build, on any ticker; apply without comment. Add a rule only after the owners (Thao, Duong) agree.

Format: `- [date] Rule. Origin: [TICKER], [one-line example]. App: [how the app enforces it, if it does].`

## Approved rules

- [2026-11-04] Registrations, permits and authorizations are not operating units; never count them as deployment. Origin: TSLA, Texas robotaxi registrations vs. cars actually driving. App: pick signals that count operating units; put permits on the Event ladder.
- [2026-11-04] A metric the company withholds on a natural disclosure occasion is a signal: no data for one cycle, red after it is skipped. Origin: TSLA, Optimus unit count missing on four calls. App: Scoring log "Withheld? = Y" scores RED; a value that is simply not available yet stays GREY. Disclosure expectations go on the Event ladder as kind "Disclosure".
- [2026-11-04] Social-media and tracker claims get the if-true / if-false analysis and a dated falsification test, but never move the rating on their own. Origin: TSLA, nextbigfuture fleet claim. App: such sources are Tier C; a driver with only Tier C signals shows "narrative-only".
- [2026-11-04] Footprint metrics (cities, units built, announcements) lag; validation metrics (failure rates, unit economics) lead. Find the one that gates scaling. Origin: TSLA, crash rate per mile vs. city count. App: mark that signal "Binding constraint = Y" (one per driver).
- [2026-11-04] When the company redefines a metric, break the series and say so rather than comparing across the change. Origin: TSLA, FSD subscriptions redefined in Q3 2026. App: Signals "Definition change" note plus a new Signal ID or base case version at the break.
