-- Who can see and change what (Row Level Security).
--
-- * Not logged in (anon): nothing.
-- * Logged in but not in public.members: nothing.
-- * viewer:   read everything except test tickers.
-- * reviewer: read everything, create and decide proposals.
-- * owner:    read and write everything, manage members.
--
-- The worker connects with the database password or service-role key,
-- which bypasses these rules. It never runs in the browser.

-- ---------------------------------------------------------------- role helpers
-- security definer so they can read members without recursive policy checks.

create or replace function app.member_role() returns text
language sql stable security definer
set search_path = public, pg_temp
as $$
  select role from public.members where user_id = auth.uid()
$$;

create or replace function app.is_member() returns boolean
language sql stable
as $$ select app.member_role() is not null $$;

create or replace function app.is_owner() returns boolean
language sql stable
as $$ select coalesce(app.member_role() = 'owner', false) $$;

create or replace function app.can_review() returns boolean
language sql stable
as $$ select coalesce(app.member_role() in ('owner', 'reviewer'), false) $$;

create or replace function app.can_see_ticker(p_ticker text) returns boolean
language sql stable security definer
set search_path = public, pg_temp
as $$
  select app.is_member()
     and (app.can_review()
          or not coalesce((select is_test from public.tickers where symbol = p_ticker), false))
$$;

grant usage on schema app to authenticated;
grant execute on all functions in schema app to authenticated;

-- Defence in depth: the public (anon) key gets no table access at all.
revoke all on all tables in schema public from anon;
revoke all on all sequences in schema public from anon;

-- ---------------------------------------------------------------- enable RLS everywhere

do $$
declare t text;
begin
  foreach t in array array['members', 'tickers', 'sources', 'drivers', 'signals', 'base_case',
                           'event_ladder', 'observations', 'financials', 'proposals', 'runs',
                           'audit_log']
  loop
    execute format('alter table public.%I enable row level security', t);
  end loop;
end
$$;

-- ---------------------------------------------------------------- read rules

create policy members_read on public.members for select to authenticated
  using (user_id = auth.uid() or app.is_owner());

create policy tickers_read on public.tickers for select to authenticated
  using (app.is_member() and (not is_test or app.can_review()));

do $$
declare t text;
begin
  foreach t in array array['sources', 'drivers', 'signals', 'base_case', 'event_ladder',
                           'observations', 'financials', 'proposals']
  loop
    execute format(
      'create policy %1$s_read on public.%1$I for select to authenticated
         using (app.can_see_ticker(ticker))', t);
  end loop;
end
$$;

create policy runs_read on public.runs for select to authenticated
  using (app.can_review());

create policy audit_log_read on public.audit_log for select to authenticated
  using (app.can_review());

-- ---------------------------------------------------------------- write rules

create policy members_owner_write on public.members for all to authenticated
  using (app.is_owner()) with check (app.is_owner());

do $$
declare t text;
begin
  -- Spreadsheet tables: owners only (later edited through in-app forms).
  foreach t in array array['tickers', 'sources', 'drivers', 'signals', 'event_ladder',
                           'observations', 'financials']
  loop
    execute format(
      'create policy %1$s_owner_write on public.%1$I for all to authenticated
         using (app.is_owner()) with check (app.is_owner())', t);
  end loop;
end
$$;

-- Base cases: insert only (the guard trigger blocks updates and deletes anyway).
create policy base_case_owner_insert on public.base_case for insert to authenticated
  with check (app.is_owner());

-- Proposals: reviewers can type one in and decide on it.
create policy proposals_review_insert on public.proposals for insert to authenticated
  with check (app.can_review() and origin = 'manual');
create policy proposals_review_update on public.proposals for update to authenticated
  using (app.can_review()) with check (app.can_review());
