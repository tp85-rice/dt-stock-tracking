// Shapes of the database views the app reads (see supabase/migrations/).
// The app never calculates colours: they come from the views.

export type Colour = "GREEN" | "YELLOW" | "RED" | "GREY" | "PENDING";

export interface Ticker {
  symbol: string;
  name: string | null;
  archetype: string | null;
  is_test: boolean;
}

export interface Driver {
  code: string;
  name: string;
  thesis: string | null;
  valuation_mechanism: string | null;
  horizon_years: number | null;
  impact: string | null;
  direction: string | null;
  confidence: string | null;
  driver_type: string | null;
  depends_on: string | null;
  n_signals: number;
  n_tier_ab: number;
  driver_status: string; // OK | narrative-only | no signals | over cap (5)
}

export interface SignalLatest {
  signal_code: string;
  driver_code: string;
  signal_name: string;
  tier: string | null;
  cadence: string | null;
  unit: string | null;
  polarity: string | null;
  tolerance: number | null;
  binding_constraint: boolean;
  kill_switch: boolean;
  observed_on: string | null;
  observed_value: number | null;
  base_value: number | null;
  variance: number | null;
  data_status: string;
  colour: Colour;
  arrow: string | null;
  source_code: string | null;
  age_days: number | null;
}

export interface Observation {
  observation_id: number;
  signal_code: string;
  observed_on: string | null;
  observed_value: number | null;
  period: string | null;
  colour: Colour;
  data_status: string;
}

export interface EventStep {
  signal_code: string;
  step_no: number;
  milestone: string;
  kind: string | null;
  target_date: string | null;
  status: string | null;
  actual_date: string | null;
  days_late: number | null;
  colour: Colour;
}

export interface Source {
  code: string;
  name: string | null;
  url: string | null;
  tier: string | null;
  accessed_on: string | null;
}

export interface BaseCaseInfo {
  version: string;
  snapshot_date: string | null;
}

export interface TickerPage {
  ticker: Ticker;
  baseCase: BaseCaseInfo | null;
  drivers: Driver[];
  signals: SignalLatest[];
  history: Observation[];
  events: EventStep[];
  sources: Source[];
}

export interface QueueItem {
  proposal_id: number;
  kind: string;
  status: string;
  ticker: string;
  signal_code: string | null;
  signal_name: string | null;
  driver_name: string | null;
  unit: string | null;
  polarity: string | null;
  origin: string;
  confidence: number | null;
  model: string | null;
  prompt_version: string | null;
  citations: { url?: string; quote?: string; title?: string }[] | null;
  check_result: Record<string, unknown> | null;
  created_at: string;
  reviewer_note: string | null;
  reviewed_at: string | null;
  observed_on: string | null;
  value: number | null;
  period: string | null;
  base_case_version: string | null;
  arrow: string | null;
  source_code: string | null;
  notes: string | null;
  withheld: boolean;
  base_value: number | null;
  preview_variance: number | null;
  preview_status: string;
  preview_colour: Colour;
  current_value: number | null;
  current_observed_on: string | null;
  current_colour: Colour | null;
  current_status: string | null;
}

export interface SignalOption {
  ticker: string;
  code: string;
  name: string;
  unit: string | null;
}
