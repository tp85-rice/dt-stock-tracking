// Builds web/fixtures/<TICKER>.json from a local test database, for previews without Supabase.
// Usage: FIXTURE_DB_URL=postgresql://... node scripts/export-fixtures.mjs TEST NVDA   (source ticker, name in fixture)
// Never point it at the real Supabase project.
import { execFileSync } from "node:child_process";
import { writeFileSync } from "node:fs";

const [src = "TEST", as = src] = process.argv.slice(2);
const url = process.env.FIXTURE_DB_URL;
if (!url || url.includes("supabase")) throw new Error("Set FIXTURE_DB_URL to a local test database (not Supabase).");
const q = (sql) => JSON.parse(execFileSync("psql", [url, "-At", "-c", `select coalesce(json_agg(t), '[]') from (${sql}) t`]).toString() || "[]");
const t = `'${src.replace(/'/g, "")}'`;
const ticker = q(`select '${as}' as symbol, name, archetype, false as is_test from tickers where symbol = ${t}`)[0];
const page = {
  ticker,
  baseCase: q(`select version, snapshot_date from base_case where ticker = ${t} and case_type = 'Consensus' order by snapshot_date desc limit 1`)[0] ?? null,
  drivers: q(`select * from v_driver_status where ticker = ${t} order by code`),
  signals: q(`select * from v_signal_latest where ticker = ${t} order by signal_code`),
  history: q(`select observation_id, signal_code, observed_on, observed_value, period, colour, data_status from v_scores where ticker = ${t} order by observed_on, observation_id`),
  events: q(`select * from v_event_ladder where ticker = ${t} order by signal_code, step_no`),
  sources: q(`select code, name, url, tier, accessed_on from sources where ticker = ${t} order by id`),
  financials: q(`select metric, period_end, fiscal_period, value::float8 as value from financials where ticker = ${t} order by period_end`),
};
writeFileSync(`fixtures/${as}.json`, JSON.stringify(page, null, 2) + "\n");
console.log(`Wrote fixtures/${as}.json`);
