# Notes for Claude sessions in this repo

## Project status doc (standing instruction from the owners, 2026-11-05)

At the end of every work session that changes anything (code, research, decisions, dates), update the Google Doc
**"dt-dashboard — Project Status"** in the owners' Drive folder `dt-dashboard`:

- Doc ID: `1zxUk3FWp2L6kxCLImTAaYOCg_E5JoUqc61KYzpn5MhM`
- Folder ID: `11RrJZHSRBhU6ha8x1-pLYYnghZyeCPy5`

How:
- Edit the doc **in place** with the Google Docs connector (same file, same link). Update "Last updated", the
  milestone table, "NVDA at a glance" (or one section per covered ticker), "Decisions waiting for you",
  "Coming up", "Your to-dos", and add one dated line to the top of the Change log.
- Keep the owners' comments; never delete the doc or create a replacement.
- If the Google Docs connector is not available, do not create a second doc: tell the owners in one line that the
  status doc could not be updated and what changed, so they can turn the connector on.
- Facts only, no advice: no ratings, price targets or buy/sell wording (same rule as the app).

## Other rules

- Owners: Thao (tp85@rice.edu) and Duong (collaborator). Decisions waiting on them live in `research/OPEN_DECISIONS.md`.
- Build driver sheets with the `driver-sheet-builder` skill. Never put a number in a sheet that was not read from an
  opened source page.
- Never read or use the personal sections of `thesis-research-bundle/reference/Equity_Research_Master_Instructions.md`.
- SEC requests identify the client as `dt-stock-tracking tp85@rice.edu`.
- Tests: `TEST_DATABASE_URL=<local postgres> python -m pytest worker/tests -q`. Never point it at Supabase.
