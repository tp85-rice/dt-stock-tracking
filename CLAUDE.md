# Notes for Claude sessions in this repo

## Project status doc (standing instruction from the owners, 2026-11-05)

The owners' organization does not allow the Google Docs connector, so the status doc cannot be edited in place.
Instead, publish **numbered versions**. At the end of every work session that changes anything (code, research,
decisions, dates):

1. Edit the source of truth, `docs/STATUS.html`: bump "Version", "Last updated", the milestone table, the
   per-ticker "at a glance" section(s), "Decisions waiting for you", "Coming up", "Your to-dos", and add one dated
   line `(v-N)` at the top of the Change log. Commit it with the session's other changes.
2. Find the current highest version: Google Drive search in folder `11RrJZHSRBhU6ha8x1-pLYYnghZyeCPy5`
   (`dt-dashboard`) for titles containing `dt-dashboard — Project Status v-`. Next version = highest N + 1.
   Versions so far: v-0 to v-5 (2026-11-05).
3. Upload `docs/STATUS.html` with the Google Drive connector `create_file` (contentMimeType `text/html`,
   parentId = that folder) titled `dt-dashboard — Project Status v-<N>`, then read it back to check it converted.
4. Never delete, trash or rename older versions; the owners delete them by hand. Tell the owners the new version's link.
5. Facts only, no advice: no ratings, price targets or buy/sell wording (same rule as the app).

## Other rules

- Owners: Thao (tp85@rice.edu) and Duong (collaborator). Decisions waiting on them live in `research/OPEN_DECISIONS.md`.
- Build driver sheets with the `driver-sheet-builder` skill. Never put a number in a sheet that was not read from an
  opened source page.
- Never read or use the personal sections of `thesis-research-bundle/reference/Equity_Research_Master_Instructions.md`.
- SEC requests identify the client as `dt-stock-tracking tp85@rice.edu`.
- Tests: `TEST_DATABASE_URL=<local postgres> python -m pytest worker/tests -q`. Never point it at Supabase.
