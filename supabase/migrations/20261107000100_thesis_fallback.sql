-- Owner decisions 2026-11-07 (research/OPEN_DECISIONS.md, decisions 1-3). Each can be reversed; see the notes.
--
-- Decision 2: a signal with no Consensus row for a version and period is scored against the Thesis row
--   (our own estimate) for the same version and period, and the app labels it "vs our estimate".
--   Consensus always wins when both exist. Management rows stay reference only.
--   Base case rows are only written by an owner's sheet import, so a Thesis row is owner-approved by definition.
--   To reverse: make app.scoring_base() return app.consensus_base() again (and the sheet formula, see
--   templates/build_templates.py, Scoring log column F).
--
-- Decision 3: NVDA S5 (gross margin) tolerance 2% -> 0.7% of base, so YELLOW = inside NVIDIA's guided
--   band of +/-0.5 points and RED = below it. Tolerances are data (signals.tolerance), so this is a one-row update;
--   it also changes the colour of past S5 readings, as any tolerance change does. To reverse: set it back to 0.02.
--
-- Decision 1 (where consensus comes from) needs no schema change: Consensus rows are typed in from news coverage
--   with the article as the source (Redistribute = No). The app shows colour and variance, never the consensus
--   number itself; base_value is only shown to reviewers on /review.

-- ---------------------------------------------------------------- which base case a reading is scored against

-- 'Consensus' if a Consensus row exists for the signal, version and period, else 'Thesis' if a Thesis row does,
-- else null (the reading shows GREY, "No base case").
create or replace function app.scoring_base_type(p_ticker text, p_signal text, p_version text, p_period text)
returns text
language sql stable
as $$
  select bc.case_type from public.base_case bc
  where bc.ticker = p_ticker and bc.signal_code = p_signal and bc.case_type in ('Consensus', 'Thesis')
    and lower(bc.version) = lower(p_version) and lower(bc.period) = lower(p_period)
  order by case bc.case_type when 'Consensus' then 0 else 1 end
  limit 1
$$;

create or replace function app.scoring_base(p_ticker text, p_signal text, p_version text, p_period text)
returns numeric
language sql stable
as $$
  select bc.value from public.base_case bc
  where bc.ticker = p_ticker and bc.signal_code = p_signal and bc.case_type in ('Consensus', 'Thesis')
    and lower(bc.version) = lower(p_version) and lower(bc.period) = lower(p_period)
  order by case bc.case_type when 'Consensus' then 0 else 1 end
  limit 1
$$;

comment on function app.scoring_base(text, text, text, text) is
  'Base value a reading is scored against: the Consensus row, or the Thesis row when no Consensus row exists '
  '(owner decision 2026-11-07). Same matching as Excel COUNTIFS: case-insensitive version and period.';

-- ---------------------------------------------------------------- views (same columns, plus base_type at the end)

create or replace view public.v_scores with (security_invoker = true) as
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
  s.kill_switch,
  b.base_type
from public.observations o
left join public.signals s on s.ticker = o.ticker and s.code = o.signal_code
cross join lateral (
  select app.scoring_base(o.ticker, o.signal_code, o.base_case_version, o.period) as base_value,
         app.scoring_base_type(o.ticker, o.signal_code, o.base_case_version, o.period) as base_type
) b
cross join lateral app.score(o.value, o.withheld, o.observed_on, b.base_value,
                             s.polarity, s.tolerance, s.max_staleness_days) sc;

comment on view public.v_scores is
  'One row per observation with variance, data status and colour (GREEN/YELLOW/RED/GREY). Rules: app.score(). '
  'base_type says what it was scored against: Consensus, or Thesis (shown as "vs our estimate").';

create or replace view public.v_signal_latest with (security_invoker = true) as
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
  case when l.observed_on is not null then app.today() - l.observed_on end as age_days,
  l.base_type
from public.signals s
left join lateral (
  select sc.*
  from public.v_scores sc
  where sc.ticker = s.ticker and sc.signal_code = s.code
  order by sc.observed_on desc nulls last, sc.observation_id desc
  limit 1
) l on true;

create or replace view public.v_proposal_queue with (security_invoker = true) as
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
  cur.data_status                        as current_status,
  b.base_type
from public.proposals p
left join public.signals s on s.ticker = p.ticker and s.code = p.signal_code
left join public.drivers d on d.ticker = s.ticker and d.code = s.driver_code
cross join lateral (
  select app.scoring_base(p.ticker, p.signal_code, p.payload ->> 'base_case_version', p.payload ->> 'period') as base_value,
         app.scoring_base_type(p.ticker, p.signal_code, p.payload ->> 'base_case_version', p.payload ->> 'period') as base_type
) b
cross join lateral app.score((p.payload ->> 'value')::numeric,
                             coalesce((p.payload ->> 'withheld')::boolean, false),
                             (p.payload ->> 'observed_on')::date, b.base_value,
                             s.polarity, s.tolerance, s.max_staleness_days) pv
left join public.v_signal_latest cur on cur.ticker = p.ticker and cur.signal_code = p.signal_code;

-- ---------------------------------------------------------------- decision 3: NVDA S5 tolerance

-- Only changes the value the owners approved (2%), so a later hand edit is never overwritten.
update public.signals set tolerance = 0.007
where ticker = 'NVDA' and code = 'S5' and tolerance = 0.02;
