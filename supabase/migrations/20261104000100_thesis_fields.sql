-- Template v2: fields from the thesis research bundle (thesis-driver-dashboard skill).
--
-- * drivers: type (Core / Option / Mechanism / Event), share of today's price, dependencies.
-- * signals: binding constraint, kill switch, threshold anchor.
-- * base_case: new case type 'Thesis' = our own base case from the thesis work.
--   Reference line only; colours are still scored against Consensus.
-- * event_ladder: kind of step (Milestone, Catalyst, Falsification test,
--   Thesis breaker, Disclosure).
-- * observations: withheld = the company skipped a natural chance to disclose
--   the metric. A withheld observation with no value scores RED (House Rule:
--   "a metric the company withholds on a natural disclosure occasion is a signal").
--   A value that is simply missing still scores GREY.

alter table public.drivers
  add column driver_type    text check (driver_type in ('Core', 'Option', 'Mechanism', 'Event')),
  add column share_of_price numeric check (share_of_price between 0 and 1),
  add column depends_on     text;
comment on column public.drivers.depends_on is
  'Comma-separated Driver IDs this driver depends on, e.g. "D4". A red Mechanism caps its dependants.';

alter table public.signals
  add column binding_constraint boolean not null default false,
  add column kill_switch        boolean not null default false,
  add column threshold_anchor   text;

alter table public.base_case drop constraint base_case_case_type_check;
alter table public.base_case
  add constraint base_case_case_type_check check (case_type in ('Consensus', 'Management', 'Thesis'));

alter table public.event_ladder
  add column kind text check (kind in ('Milestone', 'Catalyst', 'Falsification test', 'Thesis breaker', 'Disclosure'));

alter table public.observations
  add column withheld boolean not null default false;

-- ---------------------------------------------------------------- views
-- Recreated so they include the new columns and the Withheld rule.
-- Same logic as templates/stock_driver_template.xlsx (template v2).

drop view public.v_signal_latest;
drop view public.v_scores;
drop view public.v_event_ladder;
drop view public.v_driver_status;

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
  b.value               as base_value,
  v.variance,
  s.polarity,
  s.tolerance,
  s.max_staleness_days,
  st.data_status,
  case
    when st.data_status = 'Withheld' then 'RED'
    when st.data_status <> 'OK' then 'GREY'
    when v.variance is null then 'GREY'                       -- base case of zero
    when s.polarity = 'Higher is better' then
      case when v.variance >= 0 then 'GREEN'
           when v.variance >= -coalesce(s.tolerance, 0) then 'YELLOW'
           else 'RED' end
    when s.polarity = 'Lower is better' then
      case when v.variance <= 0 then 'GREEN'
           when v.variance <= coalesce(s.tolerance, 0) then 'YELLOW'
           else 'RED' end
    else 'GREY'                                               -- no polarity / event ladder
  end                   as colour,
  o.arrow,
  o.source_code,
  o.notes,
  o.origin,
  o.proposal_id,
  o.withheld,
  s.binding_constraint,
  s.kill_switch
from public.observations o
left join public.signals s
  on s.ticker = o.ticker and s.code = o.signal_code
left join lateral (
  -- Scored against the Consensus row only; Management and Thesis rows are reference lines.
  select bc.value
  from public.base_case bc
  where bc.ticker = o.ticker
    and bc.signal_code = o.signal_code
    and bc.case_type = 'Consensus'
    and lower(bc.version) = lower(o.base_case_version)
    and lower(bc.period) = lower(o.period)
  limit 1
) b on true
cross join lateral (
  select case
           when o.value is null or b.value is null or b.value = 0 then null
           else (o.value - b.value) / abs(b.value)
         end as variance
) v
cross join lateral (
  select case
           when o.value is null and o.withheld then 'Withheld'
           when o.value is null then 'Missing'
           when s.max_staleness_days is not null and o.observed_on is not null
                and app.today() - o.observed_on > s.max_staleness_days then 'Stale'
           when b.value is null then 'No base case'
           else 'OK'
         end as data_status
) st;

comment on view public.v_scores is
  'One row per observation with variance, data status and colour (GREEN/YELLOW/RED/GREY).';

create view public.v_event_ladder with (security_invoker = true) as
select
  e.*,
  case when e.actual_date is not null and e.target_date is not null
       then e.actual_date - e.target_date end as days_late,
  case
    when e.status in ('Failed', 'Slipped') then 'RED'
    when e.status = 'Occurred' then
      case when coalesce(e.actual_date - e.target_date, 0) <= 0 then 'GREEN' else 'YELLOW' end
    when e.target_date is not null and app.today() > e.target_date then 'YELLOW'
    else 'PENDING'
  end as colour
from public.event_ladder e;

create view public.v_driver_status with (security_invoker = true) as
select
  d.*,
  coalesce(c.n_signals, 0) as n_signals,
  coalesce(c.n_tier_ab, 0) as n_tier_ab,
  case
    when coalesce(c.n_signals, 0) = 0 then 'no signals'
    when coalesce(c.n_tier_ab, 0) = 0 then 'narrative-only'
    when c.n_signals > 5 then 'over cap (5)'
    else 'OK'
  end as driver_status
from public.drivers d
left join (
  select ticker, driver_code,
         count(*)                                   as n_signals,
         count(*) filter (where tier in ('A', 'B')) as n_tier_ab
  from public.signals
  group by ticker, driver_code
) c on c.ticker = d.ticker and c.driver_code = d.code;

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

-- Views are recreated, so re-apply "the public (anon) key gets nothing".
revoke all on public.v_scores, public.v_event_ladder, public.v_driver_status, public.v_signal_latest from anon;
