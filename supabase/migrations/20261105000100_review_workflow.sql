-- M3: review workflow.
--
-- 1. The colour rules move into one function, app.score(), used by v_scores and by the review queue's preview,
--    so a proposal shows exactly the colour it will get once approved. Same logic as before (golden test).
-- 2. v_proposal_queue: pending proposals with their signal, base case, current reading and preview colour.
-- 3. approve_proposal() / reject_proposal(): the only way a proposal becomes an observation. They check the
--    caller is a reviewer or owner, record who decided and when, and keep the original proposal unchanged.

-- ---------------------------------------------------------------- colour rules, once

create or replace function app.score(
  p_value numeric, p_withheld boolean, p_observed_on date, p_base numeric,
  p_polarity text, p_tolerance numeric, p_max_staleness_days int
) returns table (variance numeric, data_status text, colour text)
language sql stable
as $$
  with v as (
    select case when p_value is null or p_base is null or p_base = 0 then null
                else (p_value - p_base) / abs(p_base) end as variance
  ), st as (
    select case
             when p_value is null and coalesce(p_withheld, false) then 'Withheld'
             when p_value is null then 'Missing'
             when p_max_staleness_days is not null and p_observed_on is not null
                  and app.today() - p_observed_on > p_max_staleness_days then 'Stale'
             when p_base is null then 'No base case'
             else 'OK'
           end as data_status
  )
  select v.variance, st.data_status,
    case
      when st.data_status = 'Withheld' then 'RED'
      when st.data_status <> 'OK' then 'GREY'
      when v.variance is null then 'GREY'
      when p_polarity = 'Higher is better' then
        case when v.variance >= 0 then 'GREEN'
             when v.variance >= -coalesce(p_tolerance, 0) then 'YELLOW'
             else 'RED' end
      when p_polarity = 'Lower is better' then
        case when v.variance <= 0 then 'GREEN'
             when v.variance <= coalesce(p_tolerance, 0) then 'YELLOW'
             else 'RED' end
      else 'GREY'
    end
  from v, st
$$;

-- Consensus base value for a signal, version and period (case-insensitive, like Excel's COUNTIFS).
create or replace function app.consensus_base(p_ticker text, p_signal text, p_version text, p_period text)
returns numeric
language sql stable
as $$
  select bc.value from public.base_case bc
  where bc.ticker = p_ticker and bc.signal_code = p_signal and bc.case_type = 'Consensus'
    and lower(bc.version) = lower(p_version) and lower(bc.period) = lower(p_period)
  limit 1
$$;

drop view public.v_signal_latest;
drop view public.v_scores;

create view public.v_scores with (security_invoker = true) as
select
  o.id                  as observation_id,
  o.ticker,
  o.signal_code,
  s.driver_code,
  s.name                as signal_name,
  o.observed_on,
  o.value               as observed_value,
  o.base_case_version,
  o.period,
  b.base_value,
  sc.variance,
  s.polarity,
  s.tolerance,
  s.max_staleness_days,
  sc.data_status,
  sc.colour,
  o.arrow,
  o.source_code,
  o.notes,
  o.origin,
  o.proposal_id,
  o.withheld,
  s.binding_constraint,
  s.kill_switch
from public.observations o
left join public.signals s on s.ticker = o.ticker and s.code = o.signal_code
cross join lateral (select app.consensus_base(o.ticker, o.signal_code, o.base_case_version, o.period) as base_value) b
cross join lateral app.score(o.value, o.withheld, o.observed_on, b.base_value,
                             s.polarity, s.tolerance, s.max_staleness_days) sc;

comment on view public.v_scores is
  'One row per observation with variance, data status and colour (GREEN/YELLOW/RED/GREY). Rules: app.score().';

create view public.v_signal_latest with (security_invoker = true) as
select
  s.ticker,
  s.code          as signal_code,
  s.driver_code,
  s.name          as signal_name,
  s.tier,
  s.cadence,
  s.unit,
  s.polarity,
  s.tolerance,
  s.max_staleness_days,
  s.binding_constraint,
  s.kill_switch,
  s.threshold_anchor,
  l.observation_id,
  l.observed_on,
  l.observed_value,
  l.base_value,
  l.variance,
  coalesce(l.data_status, 'No data') as data_status,
  coalesce(l.colour, 'GREY')         as colour,
  l.arrow,
  l.source_code,
  case when l.observed_on is not null then app.today() - l.observed_on end as age_days
from public.signals s
left join lateral (
  select sc.*
  from public.v_scores sc
  where sc.ticker = s.ticker and sc.signal_code = s.code
  order by sc.observed_on desc nulls last, sc.observation_id desc
  limit 1
) l on true;

-- ---------------------------------------------------------------- proposals: who and what was approved

alter table public.proposals alter column created_by set default auth.uid();
alter table public.proposals add column approved_payload jsonb;
comment on column public.proposals.approved_payload is
  'What was actually written as an observation: the proposal payload with any reviewer edits applied.';

-- ---------------------------------------------------------------- the review queue

create view public.v_proposal_queue with (security_invoker = true) as
select
  p.id                                   as proposal_id,
  p.kind,
  p.status,
  p.ticker,
  p.signal_code,
  s.name                                 as signal_name,
  s.driver_code,
  d.name                                 as driver_name,
  s.unit,
  s.polarity,
  s.tolerance,
  p.origin,
  p.confidence,
  p.prompt_version,
  p.model,
  p.check_result,
  p.citations,
  p.created_at,
  p.created_by,
  p.reviewer_note,
  p.reviewed_at,
  p.payload,
  (p.payload ->> 'observed_on')::date    as observed_on,
  (p.payload ->> 'value')::numeric       as value,
  p.payload ->> 'period'                 as period,
  p.payload ->> 'base_case_version'      as base_case_version,
  p.payload ->> 'arrow'                  as arrow,
  p.payload ->> 'source_code'            as source_code,
  p.payload ->> 'notes'                  as notes,
  coalesce((p.payload ->> 'withheld')::boolean, false) as withheld,
  b.base_value,
  pv.variance                            as preview_variance,
  pv.data_status                         as preview_status,
  pv.colour                              as preview_colour,
  cur.observed_value                     as current_value,
  cur.observed_on                        as current_observed_on,
  cur.colour                             as current_colour,
  cur.data_status                        as current_status
from public.proposals p
left join public.signals s on s.ticker = p.ticker and s.code = p.signal_code
left join public.drivers d on d.ticker = s.ticker and d.code = s.driver_code
cross join lateral (
  select app.consensus_base(p.ticker, p.signal_code, p.payload ->> 'base_case_version', p.payload ->> 'period') as base_value
) b
cross join lateral app.score((p.payload ->> 'value')::numeric,
                             coalesce((p.payload ->> 'withheld')::boolean, false),
                             (p.payload ->> 'observed_on')::date, b.base_value,
                             s.polarity, s.tolerance, s.max_staleness_days) pv
left join public.v_signal_latest cur on cur.ticker = p.ticker and cur.signal_code = p.signal_code;

-- ---------------------------------------------------------------- decisions

-- Payload keys a proposal of kind 'observation' may carry (reviewer edits use the same keys).
create or replace function app.observation_payload_ok(p jsonb) returns boolean
language sql immutable
as $$
  select p ?& array['observed_on', 'period', 'base_case_version']
     and not exists (
       select 1 from jsonb_object_keys(p) k
       where k not in ('observed_on', 'value', 'period', 'base_case_version', 'arrow', 'source_code', 'notes', 'withheld'))
$$;

create or replace function public.approve_proposal(p_id bigint, p_edits jsonb default '{}'::jsonb, p_note text default null)
returns bigint
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  prop public.proposals%rowtype;
  final jsonb;
  obs_id bigint;
begin
  if not app.can_review() then
    raise exception 'only reviewers and owners can approve proposals' using errcode = '42501';
  end if;
  select * into prop from public.proposals where id = p_id for update;
  if not found then
    raise exception 'proposal % not found', p_id;
  end if;
  if prop.status <> 'pending' then
    raise exception 'proposal % is already %', p_id, prop.status;
  end if;
  if prop.kind <> 'observation' then
    raise exception 'approving % proposals is not supported yet', prop.kind;
  end if;
  final := prop.payload || coalesce(p_edits, '{}'::jsonb);
  if not app.observation_payload_ok(final) then
    raise exception 'proposal % needs observed_on, period and base_case_version, and only known fields', p_id;
  end if;
  if (final ->> 'value') is null and not coalesce((final ->> 'withheld')::boolean, false) then
    raise exception 'proposal % has no value (mark it withheld if the company skipped disclosing it)', p_id;
  end if;

  perform set_config('app.actor', 'review:' || coalesce(auth.uid()::text, current_user), true);

  insert into public.observations
    (ticker, signal_code, observed_on, value, base_case_version, period, arrow, source_code, notes,
     withheld, origin, proposal_id, created_by)
  values
    (prop.ticker, prop.signal_code, (final ->> 'observed_on')::date, (final ->> 'value')::numeric,
     final ->> 'base_case_version', final ->> 'period', nullif(final ->> 'arrow', ''),
     nullif(final ->> 'source_code', ''), nullif(final ->> 'notes', ''),
     (final ->> 'value') is null and coalesce((final ->> 'withheld')::boolean, false),
     'proposal', prop.id, auth.uid())
  returning id into obs_id;

  update public.proposals
     set status = 'approved', approved_payload = final, reviewed_by = auth.uid(), reviewed_at = now(),
         reviewer_note = nullif(trim(coalesce(p_note, '')), '')
   where id = p_id;
  return obs_id;
end
$$;

create or replace function public.reject_proposal(p_id bigint, p_note text)
returns void
language plpgsql
security definer
set search_path = public, pg_temp
as $$
begin
  if not app.can_review() then
    raise exception 'only reviewers and owners can reject proposals' using errcode = '42501';
  end if;
  if nullif(trim(coalesce(p_note, '')), '') is null then
    raise exception 'a reason is required to reject a proposal';
  end if;
  perform set_config('app.actor', 'review:' || coalesce(auth.uid()::text, current_user), true);
  update public.proposals
     set status = 'rejected', reviewed_by = auth.uid(), reviewed_at = now(), reviewer_note = trim(p_note)
   where id = p_id and status = 'pending';
  if not found then
    raise exception 'proposal % is not pending', p_id;
  end if;
end
$$;

revoke all on function public.approve_proposal(bigint, jsonb, text) from public, anon;
revoke all on function public.reject_proposal(bigint, text) from public, anon;
grant execute on function public.approve_proposal(bigint, jsonb, text) to authenticated;
grant execute on function public.reject_proposal(bigint, text) to authenticated;
grant execute on all functions in schema app to authenticated;

-- Reviewers may type a proposal in by hand, but only a well-formed observation for a real signal.
drop policy proposals_review_insert on public.proposals;
create policy proposals_review_insert on public.proposals for insert to authenticated
  with check (app.can_review() and origin = 'manual' and status = 'pending'
              and kind = 'observation' and app.observation_payload_ok(payload));

-- Decisions go through approve_proposal / reject_proposal only.
drop policy proposals_review_update on public.proposals;

revoke all on public.v_scores, public.v_signal_latest, public.v_proposal_queue from anon;
