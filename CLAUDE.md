# Notes for Claude sessions in this repo

## Project status doc (standing instruction from the owners, updated 2026-11-05)

Update the status doc **only when an owner says a step is done and asks for it**. Do not publish new versions
on your own. The organization does not allow the Google Docs connector, so each update is a new numbered copy:

1. Edit the source of truth, `docs/STATUS.html`: bump "Version", "Last updated", the milestone table, the
   per-ticker "at a glance" section(s), "Decisions waiting for you", "Coming up", "Your to-dos", and add one dated
   line `(v-N)` at the top of the Change log. Commit it with the session's other changes.
2. Find the current highest version: Google Drive search in folder `11RrJZHSRBhU6ha8x1-pLYYnghZyeCPy5`
   (`dt-dashboard`) for titles containing `dt-dashboard — Project Status v-`. Next version = highest N + 1.
   Versions so far: v-0 to v-7 (2026-11-05).
3. Upload `docs/STATUS.html` with the Google Drive connector `create_file` (contentMimeType `text/html`,
   parentId = that folder) titled `dt-dashboard — Project Status v-<N>`, then read it back to check it converted.
4. Never delete, trash or rename older versions; the owners delete them by hand. Tell the owners the new version's link.
5. Facts only, no advice: no ratings, price targets or buy/sell wording (same rule as the app).

