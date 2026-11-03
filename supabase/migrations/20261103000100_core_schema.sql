-- Core schema for the stock driver tracker.
--
-- The first seven tables mirror the tabs of templates/stock_driver_template.xlsx.
-- The rest support the review workflow (proposals, runs, audit log, members).
-- Codes (D1, S1, R1) are unique per ticker, so the same code can be reused
-- across tickers. Every table carries a ticker so new tickers need no schema change.

create schema if not exists app;

-- ---------------------------------------------------------------- helpers

-- "Today" for staleness and event-ladder colours. Tests pin it with
--   set app.today = '2026-11-03';
-- In production the setting is absent and current_date is used.
create or replace function app.today() returns date
language sql stable
as $$
  select coalesce(nullif(current_setting('app.today', true), '')::date, current_date)
$$;

-- ---------------------------------------------------------------- people

create table public.members (
  user_id    uuid primary key references auth.users (id) on delete cascade,
  email      text not null,
  role       text not null check (role in ('owner', 'reviewer', 'viewer')),
  created_at timestamptz not null default now()
);
comment on table public.members is
  'People allowed into the app. owner = edit everything; reviewer = approve proposals; viewer = read only.';

-- ---------------------------------------------------------------- spreadsheet tables

create table public.tickers (
  symbol      text primary key check (symbol ~ '^[A-Z0-9][A-Z0-9.\-]{0,11}$'),
  name        text,
  archetype   text,
  owner_note  text,
  is_test     boolean not null default false,
  created_at  timestamptz not null default now()
);
comment on column public.tickers.is_test is
  'Test tickers (e.g. TEST) are hidden from viewers and safe to delete.';

create table public.sources (
  id               bigint generated always as identity primary key,
  ticker           text not null references public.tickers (symbol) on delete cascade,
  code             text not null check (code ~ '^[A-Z0-9_\-]+$'),
  accessed_on      date,
  name             text,
  url              text,
  tier             text check (tier in ('A', 'B', 'C')),
  access_method    text check (access_method in ('API', 'Download', 'Scrape', 'Manual', 'Vendor')),
  cost             text check (cost in ('Free', 'Paid', 'Unknown')),
  tos_note         text,
  redistribute     text check (redistribute in ('Yes', 'No', 'Unknown')),
  used_for         text,
  reliability_note text,
  unique (ticker, code)
);

create table public.drivers (
  id                  bigint generated always as identity primary key,
  ticker              text not null references public.tickers (symbol) on delete cascade,
  code                text not null check (code ~ '^[A-Z0-9_\-]+$'),
  name                text not null,
  thesis              text,
  valuation_mechanism text,
  horizon_years       int check (horizon_years between 1 and 5),
  impact              text check (impact in ('H', 'M', 'L')),
  direction           text check (direction in ('Upside', 'Downside', 'Both')),
  evidence            text,
  confidence          text check (confidence in ('High', 'Medium', 'Low')),
  notes               text,
  unique (ticker, code)
);

create table public.signals (
  id                 bigint generated always as identity primary key,
  ticker             text not null references public.tickers (symbol) on delete cascade,
  code               text not null check (code ~ '^[A-Z0-9_\-]+$'),
  driver_code        text not null,
  name               text not null,
  source_text        text,
  tier               text check (tier in ('A', 'B', 'C')),
  cadence            text check (cadence in ('Daily', 'Weekly', 'Monthly', 'Quarterly', 'Event')),
  unit               text,
  polarity           text check (polarity in ('Higher is better', 'Lower is better', 'Event ladder')),
  tolerance          numeric check (tolerance >= 0),
  max_staleness_days int check (max_staleness_days >= 0),
  reliability        int check (reliability between 1 and 5),
  definition_change  text,
  notes              text,
  -- Which adapter feeds this signal (e.g. 'edgar', 'agent_web') and its settings.
  -- Filled from M4 on; null = manual only.
  adapter            text,
  adapter_params     jsonb not null default '{}'::jsonb,
  active             boolean not null default true,
  unique (ticker, code),
  foreign key (ticker, driver_code) references public.drivers (ticker, code) on update cascade
);
comment on column public.signals.tolerance is 'Fraction, e.g. 0.10 = 10%. Blank counts as 0.';

create table public.base_case (
  id            bigint generated always as identity primary key,
  ticker        text not null references public.tickers (symbol) on delete cascade,
  version       text not null,
  snapshot_date date,
  case_type     text not null check (case_type in ('Consensus', 'Management')),
  signal_code   text not null,
  period        text not null,
  value         numeric not null,
  unit          text,
  source_code   text,
  notes         text,
  created_at    timestamptz not null default now(),
  foreign key (ticker, signal_code) references public.signals (ticker, code) on update cascade,
  foreign key (ticker, source_code) references public.sources (ticker, code) on update cascade
);
-- Matching is case-insensitive, like Excel's COUNTIFS.
create unique index base_case_natural_key
  on public.base_case (ticker, lower(version), case_type, signal_code, lower(period));
comment on table public.base_case is
  'Never edited. After each earnings call add a new version (v2, v3, ...).';

create table public.event_ladder (
  id          bigint generated always as identity primary key,
  ticker      text not null references public.tickers (symbol) on delete cascade,
  signal_code text not null,
  step_no     int not null check (step_no >= 0),
  milestone   text not null,
  target_date date,
  status      text check (status in ('Pending', 'Occurred', 'Slipped', 'Failed')),
  actual_date date,
  source_code text,
  notes       text,
  unique (ticker, signal_code, step_no),
  foreign key (ticker, signal_code) references public.signals (ticker, code) on update cascade,
  foreign key (ticker, source_code) references public.sources (ticker, code) on update cascade
);

-- ---------------------------------------------------------------- workflow tables

create table public.runs (
  id            bigint generated always as identity primary key,
  job           text not null,
  ticker        text references public.tickers (symbol) on delete set null,
  started_at    timestamptz not null default now(),
  finished_at   timestamptz,
  status        text not null default 'running' check (status in ('running', 'succeeded', 'failed')),
  n_proposals   int not null default 0,
  input_tokens  bigint not null default 0,
  output_tokens bigint not null default 0,
  cost_usd      numeric(12, 4) not null default 0,
  error         text,
  meta          jsonb not null default '{}'::jsonb
);

create table public.proposals (
  id             bigint generated always as identity primary key,
  kind           text not null check (kind in ('observation', 'event_status', 'base_case', 'source')),
  ticker         text not null references public.tickers (symbol) on delete cascade,
  signal_code    text,
  payload        jsonb not null,
  citations      jsonb not null default '[]'::jsonb,
  status         text not null default 'pending'
                   check (status in ('pending', 'rejected_by_check', 'approved', 'rejected')),
  origin         text not null,          -- adapter name, 'agent_web', or 'manual'
  run_id         bigint references public.runs (id) on delete set null,
  prompt_version text,
  model          text,
  confidence     numeric check (confidence between 0 and 1),
  check_result   jsonb,
  reviewer_note  text,
  created_by     uuid,
  reviewed_by    uuid,
  reviewed_at    timestamptz,
  created_at     timestamptz not null default now(),
  foreign key (ticker, signal_code) references public.signals (ticker, code) on update cascade
);
create index proposals_queue on public.proposals (status, created_at desc);

create table public.observations (
  id                bigint generated always as identity primary key,
  ticker            text not null references public.tickers (symbol) on delete cascade,
  signal_code       text not null,
  observed_on       date,
  value             numeric,              -- null = Missing (shows GREY)
  base_case_version text,
  period            text,
  arrow             text check (arrow in ('Accelerating', 'Flat', 'Decelerating', 'n/a')),
  source_code       text,
  notes             text,
  origin            text not null default 'manual',  -- 'import', 'manual', or 'proposal'
  proposal_id       bigint references public.proposals (id) on delete set null,
  created_by        uuid,
  created_at        timestamptz not null default now(),
  foreign key (ticker, signal_code) references public.signals (ticker, code) on update cascade,
  foreign key (ticker, source_code) references public.sources (ticker, code) on update cascade
);
create index observations_signal on public.observations (ticker, signal_code, observed_on desc);

create table public.financials (
  id            bigint generated always as identity primary key,
  ticker        text not null references public.tickers (symbol) on delete cascade,
  metric        text not null,
  period_end    date not null,
  fiscal_period text,
  value         numeric not null,
  unit          text,
  source        text not null,          -- 'edgar', 'fred', 'manual'
  source_ref    text,                   -- e.g. XBRL tag or accession number
  fetched_at    timestamptz not null default now(),
  unique (ticker, metric, period_end, source)
);

create table public.audit_log (
  id         bigint generated always as identity primary key,
  at         timestamptz not null default now(),
  actor      uuid,
  actor_label text,
  action     text not null,
  table_name text not null,
  row_pk     text,
  before     jsonb,
  after      jsonb
);
create index audit_log_row on public.audit_log (table_name, row_pk, at desc);

-- ---------------------------------------------------------------- guards

-- Base cases are append-only. Deleting is allowed only for test tickers.
create or replace function app.base_case_guard() returns trigger
language plpgsql
as $$
begin
  if tg_op = 'UPDATE' then
    raise exception 'base_case rows cannot be changed; add a new version instead (row %)', old.id;
  end if;
  if tg_op = 'DELETE' and not exists (
       select 1 from public.tickers t where t.symbol = old.ticker and t.is_test) then
    raise exception 'base_case rows cannot be deleted (row %)', old.id;
  end if;
  return coalesce(new, old);
end
$$;

create trigger base_case_guard
  before update or delete on public.base_case
  for each row execute function app.base_case_guard();

-- Allow cascading deletes of whole test tickers by letting the trigger see the
-- ticker row: cascades fire after the parent row is gone, so the check above
-- would fail. Deleting a test ticker therefore deletes its base cases first.
create or replace function app.delete_test_ticker(p_symbol text) returns void
language plpgsql
as $$
begin
  if not exists (select 1 from public.tickers where symbol = p_symbol and is_test) then
    raise exception '% is not a test ticker', p_symbol;
  end if;
  delete from public.base_case where ticker = p_symbol;
  delete from public.tickers where symbol = p_symbol;
end
$$;

-- ---------------------------------------------------------------- audit trail

create or replace function app.audit_row() returns trigger
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  rec jsonb := to_jsonb(coalesce(new, old));
begin
  insert into public.audit_log (actor, actor_label, action, table_name, row_pk, before, after)
  values (
    auth.uid(),
    coalesce(nullif(current_setting('app.actor', true), ''), current_user),
    lower(tg_op),
    tg_table_name,
    coalesce(rec ->> 'id', rec ->> 'symbol', rec ->> 'user_id'),
    case when tg_op in ('UPDATE', 'DELETE') then to_jsonb(old) end,
    case when tg_op in ('INSERT', 'UPDATE') then to_jsonb(new) end
  );
  return coalesce(new, old);
end
$$;

do $$
declare t text;
begin
  foreach t in array array['members', 'tickers', 'sources', 'drivers', 'signals', 'base_case',
                           'event_ladder', 'observations', 'proposals']
  loop
    execute format(
      'create trigger audit_%1$s after insert or update or delete on public.%1$I
         for each row execute function app.audit_row()', t);
  end loop;
end
$$;
