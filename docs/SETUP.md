# Setup guide

Step-by-step instructions for the owner and the collaborator. Do the steps in order. Nothing here needs coding.

Current state (2026-11-03): **one** Supabase project, `dt-dashboard-prd` (`https://loyiamqdycxljgcrmfbh.supabase.co`). The free plan allows two projects and both slots are used, so there is no separate dev database yet. The rules that keep this safe are listed in section 5.

## 1. Give GitHub the database connection (owner, once)

The `migrate database` and `weekly database backup` workflows need to reach the database.

1. In Supabase, open project **dt-dashboard-prd** and click **Connect** (top of the page).
2. Choose **Session pooler**. Copy the connection string. It looks like
   `postgresql://postgres.loyiamqdycxljgcrmfbh:[YOUR-PASSWORD]@aws-0-<region>.pooler.supabase.com:5432/postgres`
   - Use the Session pooler, not "Direct connection": the direct one only works over IPv6, which GitHub Actions and many home networks don't have.
   - Replace `[YOUR-PASSWORD]` with the database password chosen when the project was created. Forgot it? **Project Settings > Database > Reset database password**.
3. In GitHub, open the repo **tp85-rice/dt-stock-tracking > Settings > Secrets and variables > Actions > New repository secret**.
   - Name: `SUPABASE_DB_URL`
   - Value: the connection string from step 2.
4. Never paste this string into chat, docs, issues or code.

## 2. Create the tables (owner, once)

The tables are created by the `migrate database` workflow, which runs automatically when a pull request that changes `supabase/migrations/` is merged into `main`.

1. Merge the M1 pull request (after `tests` is green).
2. Open **Actions > migrate database** and check the run is green. If the secret from step 1 was added after merging, click **Run workflow** to run it by hand.
3. Check in Supabase: **Table Editor** should list `tickers`, `drivers`, `signals`, `base_case`, `event_ladder`, `sources`, `observations`, `financials`, `proposals`, `runs`, `audit_log`, `members`.

## 3. Make yourself the owner (owner, once)

Access rules let in only people listed in the `members` table.

1. Supabase > **Authentication > Users > Add user > Send invitation**, using your own email. Accept the invite from your inbox.
2. Supabase > **SQL Editor**, run (with your email):
   ```sql
   insert into public.members (user_id, email, role)
   select id, email, 'owner' from auth.users where email = 'tp85@rice.edu';
   ```
3. Repeat for the collaborator with role `'reviewer'` (or `'owner'` if they should edit drivers too).

Later, invited viewers get role `'viewer'`. From M2 this is done in the app.

## 4. Import a driver sheet (owner or collaborator)

On your laptop, once:

1. Install Python 3.12 or newer.
2. Clone the repo and, inside it, run:
   ```bash
   pip install -r worker/requirements-dev.txt
   ```
3. Copy `.env.example` to `.env` and fill in `DATABASE_URL` (the same Session pooler string as step 1). `.env` is git-ignored.

Each time:

1. Copy `templates/stock_driver_template.xlsx` to `inputs/<TICKER>_driver_sheet.xlsx` and fill it in (see the game plan, section 8).
2. Check it:
   ```bash
   python -m worker.import_xlsx inputs/NVDA_driver_sheet.xlsx --dry-run
   ```
   Fix every `[ERROR]`. Read the `[WARNING]`s: they don't block the import but usually point at a gap (a driver with no Tier A/B signal, a scoring row with no base case).
3. First time only, import it as a hidden test ticker and look at the result in Supabase (**Table Editor > v_scores** is not a table; use **SQL Editor**: `select * from v_scores where ticker = 'TEST';`):
   ```bash
   python -m worker.import_xlsx inputs/NVDA_driver_sheet.xlsx --ticker TEST --test
   ```
   Remove it afterwards in the SQL Editor: `select app.delete_test_ticker('TEST');`
4. Import it for real:
   ```bash
   python -m worker.import_xlsx inputs/NVDA_driver_sheet.xlsx
   ```
5. Compare a few colours with the spreadsheet's Scoring log (open the file in Excel so the formulas calculate). They must match.

Re-importing the same file is safe. Base cases are never overwritten: if you change a base case value, the import stops and asks you to add a new version (v2) instead.

## 5. Rules while there is only one database

- Database changes only through reviewed, merged pull requests (the `migrate database` workflow). Never edit tables by hand in the dashboard.
- Experiments use a test ticker (`--test`). Test tickers are hidden from viewers and can be deleted with `app.delete_test_ticker`.
- The `weekly database backup` workflow saves a copy every Monday (Actions > a run > Artifacts). Run it by hand before any risky change.
- Never point `TEST_DATABASE_URL` (automated tests) at Supabase. The tests refuse to run if you try.
- Add a dev project before inviting viewers (M6), or as soon as a Supabase slot frees up or we upgrade. Only settings change.

## 6. Put the web app online (owner, once, for M2)

The web app lives in `web/`. Vercel needs four settings; Supabase needs to know the web address.

**In Vercel** (your project, connected to `tp85-rice/dt-stock-tracking`):

1. **Settings > Build and Deployment > Root Directory**: `web`. Framework Preset: Next.js (detected automatically).
2. **Settings > Environment Variables**, for both Production and Preview:
   - `NEXT_PUBLIC_SUPABASE_URL` = `https://loyiamqdycxljgcrmfbh.supabase.co`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY` = Supabase > **Project Settings > API Keys**, the **anon / publishable** key.
     It is safe in the browser because every table has row level security. Never put the service-role key in Vercel.
3. **Deployments**: redeploy the latest `main` after saving the variables. Note the production address, e.g. `https://dt-stock-tracking.vercel.app`.

**In Supabase** (project dt-dashboard-prd):

4. **Authentication > URL Configuration**:
   - Site URL: the production address from step 3.
   - Redirect URLs: add `https://<production address>/auth/callback` and, for preview deployments,
     `https://*-<your-vercel-team>.vercel.app/auth/callback`.
5. **Authentication > Sign In / Providers > Email**: Email enabled. Turn **off** "Allow new users to sign up"
   (invite only; the login form never creates accounts either).
6. **Sign-in method.** The site signs people in with **email + password**; no email is sent, so no SMTP is needed.
   - An owner creates each account in Supabase: **Authentication > Users > Add user > Create new user**, with a
     password and **Auto Confirm User** ticked. Send the password to the person privately.
   - To change a password: **Authentication > Users >** the user **> Reset password** (needs SMTP), or delete and
     re-create the user, then re-add them to `members`.
   - Optional, later (before inviting viewers): set up SMTP so the "Email me a sign-in code" option works.
     Supabase's built-in sender cannot use custom templates. **Project Settings > Authentication > SMTP Settings**:
     e.g. a Gmail account with 2-step verification and an App Password (host `smtp.gmail.com`, port `465`, user =
     the Gmail address, password = the 16-character app password). Then **Authentication > Emails > Magic Link**,
     replace the body with:
     ```html
     <h2>Sign in to Driver Tracker</h2>
     <p>Your sign-in code: <strong>{{ .Token }}</strong></p>
     <p>Type it on the sign-in page, or <a href="{{ .SiteURL }}/auth/confirm?token_hash={{ .TokenHash }}&type=email">open this link</a> and press Continue.</p>
     ```
     (A code instead of a plain link, because university mail scanners open links and use them up.)
7. Make sure you and Duong are in `members` (section 3). Only members see any data.

**Check it:** open the production address, sign in with your email and the password you set in Supabase. You should
see the ticker list. A ticker only appears after its sheet is imported (section 4).

Notes:
- Local preview without Supabase: `cd web && npm install && npm run build && DATA_SOURCE=fixtures npx next start`,
  then open http://localhost:3000/t/NVDA. Fixture mode is refused on Vercel production.

## 7. Anthropic API key (needed from M5)

The Anthropic account doesn't have to be under the owner's email, but:

- whoever owns it controls billing and can revoke the key, so both of us should know who that is;
- set a monthly spending limit in the Anthropic console;
- the key goes only into GitHub secrets (`ANTHROPIC_API_KEY`) and `.env`, never into Vercel or the repo.
