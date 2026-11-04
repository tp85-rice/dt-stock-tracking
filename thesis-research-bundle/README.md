# Thesis Research Bundle — setup guide

Everything another AI tool or account needs to run the stock discussion process: establish a base case for a stock through an interactive discussion, save the view to a per-ticker state file, and build a monitoring dashboard from it. Position-neutral: no holdings, cost basis, entries, exits or options are used or stored.

Exported 2026-11-04.

## What's in the bundle

| Path | What it is | Required? |
|---|---|---|
| `skills/thesis-discussion-loop/SKILL.md` | The main skill: runs the discussion, captures your judgment, writes the state file | Yes |
| `skills/thesis-driver-dashboard/SKILL.md` | Companion skill: turns the state file into drivers, indicators, thresholds and color roll-ups | Yes, if you want dashboards |
| `reference/Equity_Research_Master_Instructions.md` | Your research framework. The discussion skill uses Master Prompt 1 Sections 1–6 and 8 for thesis content | Yes |
| `reference/information_extraction_guide.md` | Used only to bootstrap a state file from an existing long thread | Only for existing threads |
| `templates/House_Rules.md` | Starter file for cross-ticker rules, with five candidate rules from the TSLA thread for you to approve or delete | Recommended |

## How the pieces connect

```
Master Instructions (what a thesis contains)
        │
        ▼
thesis-discussion-loop ──writes──► [TICKER]_Thesis_State.md ◄──reads/writes colors── thesis-driver-dashboard ──writes──► [TICKER]_Dashboard.md
        ▲                                   ▲
        └────────── House_Rules.md ─────────┘   (read every session, any ticker)
```

## Setup: another Claude account

1. Upload each skill as a custom skill (Settings → Capabilities → Skills, or your org's equivalent). Ready-to-upload zips are in `skills/` (`thesis-discussion-loop.zip`, `thesis-driver-dashboard.zip`); upload each one.
2. Create a Project and add `Equity_Research_Master_Instructions.md` and `information_extraction_guide.md` as project files. Set the project instructions to: "Refer to the Equity Research Master Instructions in Files."
3. Add `House_Rules.md` to the project as `claude/House_Rules.md` once you've kept or deleted the candidate rules.
4. Start with "Thesis on [TICKER]". The skill creates `claude/[TICKER]_Thesis_State.md` in the project.

The skills call `project_read` and `project_write` to load and save files in a Claude Project. They work as written in any Claude session attached to a Project.

## Setup: a different AI tool (not Claude)

Most tools don't load SKILL.md files natively. Put the content in as instructions instead:

1. **System prompt / custom instructions:** paste the paste-ready block below, then the full text of `thesis-discussion-loop/SKILL.md`.
2. **Knowledge files / attachments:** upload the Master Instructions, the dashboard skill, the extraction guide and House_Rules.md.
3. **File storage:** the tool needs somewhere to keep the state file between sessions (knowledge files, a connected drive, a repo). If it has no writable storage, have it output the full state file at the end of each session and paste it back in at the start of the next.
4. **Web search** must be on. Both skills look up current prices and news every session.

Tool-name mapping for the other tool:

| The skills say | Means |
|---|---|
| `project_read <path>` | Open and read that file from your storage |
| `project_write <path>` | Save the full file to storage, replacing the old version (there is no partial edit) |
| `claude/[TICKER]_Thesis_State.md` | Any consistent location, e.g. `state/TSLA_Thesis_State.md` |
| "send the file to the user" | Output it as a downloadable file or full code block |
| "offer a biweekly calendar reminder" | Use the tool's scheduler, or skip |

### Paste-ready system prompt block

```
You are my equity research analyst. Follow these documents, in this order of authority:
1. thesis-discussion-loop (process: how every session starts, what to save, how to treat my judgment)
2. Equity Research Master Instructions (content: what a thesis contains; use Master Prompt 1 Sections 1–6 and 8, skip Section 7 and entry tickets)
3. thesis-driver-dashboard (when I ask for a dashboard or a refresh)
4. House_Rules.md (cross-ticker rules; apply silently every session)

Position-neutral: never use or store my holdings, cost basis, entries, exits, sizing or options. Rate the stock as if I held none.

At the start of every session on a ticker: read [TICKER]_Thesis_State.md if it exists, then search for the current price and news since its as_of date.
At the end of every session where anything changed: print the State delta block and save the full updated state file.
Wherever the documents say project_read / project_write, read from and save to my file storage.
```

## Automating it (unattended runs)

- A scheduled job can run "Refresh [TICKER] dashboard" every two weeks for each ticker that has a state file.
- Unattended runs may update price, indicator readings, colors and the evidence log. They may not change rating, conviction, probabilities or the judgment log; they write proposals to the state file's "Pending review" section and set `review_status: draft-unreviewed`.
- A new ticker with no discussion yet gets a cold-start draft labeled "No owner judgment yet" until you run a discussion session on it.
- The YAML header of the state file and section 9 of the dashboard are the machine-readable contract for a webpage. Keep the field names stable.

## Notes

- **Personal details:** the Master Instructions are your original document, so they still describe your portfolio size and options strategy (About Me, Section 7, Master Prompt 3). The skills ignore those parts. Edit them out before uploading if you don't want them in the other tool.
- **Not included:** the TSLA dashboard and GRAB export. Both predate the position-neutral format and still hold position details, so they're poor examples. The first state file you build with the new skill becomes the reference example.
