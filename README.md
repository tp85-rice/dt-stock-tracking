# dt-stock-tracking

A private, invite-only dashboard: open a stock ticker and see whether each of its growth drivers is running ahead of or behind a base case. AI agents gather evidence; a person approves every update before it shows.

**No price targets and no buy/sell wording, anywhere.** Green means "ahead of the base case", not "the stock will go up".

The full plan (decisions, architecture, milestones, who does what) is the shared game plan doc. This README covers the code.

## How it fits together

```
Web app (Next.js on Vercel, from M2) ──┐
                                       ├──  Supabase Postgres  (tables, colour rules, access rules)
Worker (Python, GitHub Actions) ───────┘
```

The parts never call each other; they only share database tables. Colours are calculated in one place: the SQL views in `supabase/migrations/`.

## Repository layout

| Path | What it is |
| --- | --- |
| `supabase/migrations/` | Database structure, colour rules (`v_scores`, `v_event_ladder`, `v_driver_status`, `v_signal_latest`) and access rules. Applied automatically when merged to `main` |
| `worker/driver_sheet.py` | Reads and checks a filled driver spreadsheet (no database needed) |
| `worker/import_xlsx.py` | Imports a checked spreadsheet into the database |
| `worker/tests/` | Tests, including the golden test that compares the spreadsheet's own formulas with the database |
| `templates/` | `stock_driver_template.xlsx`, `llm_eval_scorecard.xlsx`, and `build_templates.py` that regenerates them |
| `inputs/` | Filled driver sheets, one per ticker |
| `docs/` | Setup guide and background research |
| `.github/workflows/` | `tests` (every pull request), `migrate database` (on merge), `weekly database backup` |
| `web/` | The Next.js app (arrives in M2) |

## Common tasks

Install once (Python 3.12+):

```bash
pip install -r worker/requirements-dev.txt
```

Check a sheet without touching the database:

```bash
python -m worker.import_xlsx inputs/NVDA_driver_sheet.xlsx --dry-run
```

Import a sheet (needs `DATABASE_URL` in `.env`, see `docs/SETUP.md`):

```bash
python -m worker.import_xlsx inputs/NVDA_driver_sheet.xlsx
```

Try a sheet as a hidden test ticker first:

```bash
python -m worker.import_xlsx inputs/NVDA_driver_sheet.xlsx --ticker TEST --test
```

Run the tests (needs a local Postgres, never the Supabase project; LibreOffice for the golden test):

```bash
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres python -m pytest worker/tests -q
```

## Rules for changes

- Every change goes through a pull request; `tests` must be green before merging. `main` is production.
- Database changes are new files in `supabase/migrations/` named `YYYYMMDDHHMMSS_what.sql`. Never edit a migration that has already been merged; add a new one. Never change tables by hand in the Supabase dashboard.
- Colour rules live only in the SQL views. If you change one, update `worker/tests/test_scoring.py` and keep `test_golden_excel.py` passing (or change the template formulas to match).
- Base cases are never edited or deleted (the database refuses). Add a new version after each earnings call.
- Secrets live in `.env` (git-ignored), GitHub secrets and Vercel settings only. Run `git status` before every commit.
