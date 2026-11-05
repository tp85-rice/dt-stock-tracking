import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import type { TickerPage, Ticker, QueueItem, SignalOption } from "./types";

import { usingFixtures } from "./mode";

export { usingFixtures };

const FIXTURES = join(process.cwd(), "fixtures");

function fixture(symbol: string): TickerPage | null {
  try {
    return JSON.parse(readFileSync(join(FIXTURES, `${symbol}.json`), "utf8")) as TickerPage;
  } catch {
    return null;
  }
}

export type Viewer = { email: string | null; isMember: boolean; role: string | null };

export async function getViewer(): Promise<Viewer> {
  if (usingFixtures()) return { email: "preview@localhost", isMember: true, role: "owner" };
  const { createClient } = await import("./supabase/server");
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return { email: null, isMember: false, role: null };
  const { data } = await supabase.from("members").select("role").eq("user_id", user.id).maybeSingle();
  return { email: user.email ?? null, isMember: !!data, role: data?.role ?? null };
}

export async function listTickers(): Promise<Ticker[]> {
  if (usingFixtures()) {
    return readdirSync(FIXTURES)
      .filter((f) => f.endsWith(".json"))
      .map((f) => fixture(f.replace(/\.json$/, ""))!.ticker)
      .sort((a, b) => a.symbol.localeCompare(b.symbol));
  }
  const { createClient } = await import("./supabase/server");
  const supabase = await createClient();
  const { data, error } = await supabase
    .from("tickers")
    .select("symbol, name, archetype, is_test")
    .order("symbol");
  if (error) throw new Error(`Could not load tickers: ${error.message}`);
  return data ?? [];
}

export async function getTickerPage(symbol: string): Promise<TickerPage | null> {
  symbol = symbol.toUpperCase();
  if (usingFixtures()) return fixture(symbol);

  const { createClient } = await import("./supabase/server");
  const supabase = await createClient();
  const { data: ticker } = await supabase
    .from("tickers")
    .select("symbol, name, archetype, is_test")
    .eq("symbol", symbol)
    .maybeSingle();
  if (!ticker) return null;

  const [drivers, signals, history, events, sources, baseCase] = await Promise.all([
    supabase.from("v_driver_status").select("*").eq("ticker", symbol).order("code"),
    supabase.from("v_signal_latest").select("*").eq("ticker", symbol).order("signal_code"),
    supabase
      .from("v_scores")
      .select("observation_id, signal_code, observed_on, observed_value, period, colour, data_status")
      .eq("ticker", symbol)
      .order("observed_on", { ascending: true })
      .order("observation_id", { ascending: true }),
    supabase.from("v_event_ladder").select("*").eq("ticker", symbol).order("signal_code").order("step_no"),
    supabase.from("sources").select("code, name, url, tier, accessed_on").eq("ticker", symbol).order("id"),
    supabase
      .from("base_case")
      .select("version, snapshot_date")
      .eq("ticker", symbol)
      .eq("case_type", "Consensus")
      .order("snapshot_date", { ascending: false })
      .limit(1),
  ]);
  for (const r of [drivers, signals, history, events, sources, baseCase]) {
    if (r.error) throw new Error(`Could not load ${symbol}: ${r.error.message}`);
  }
  return {
    ticker,
    baseCase: baseCase.data?.[0] ?? null,
    drivers: drivers.data ?? [],
    signals: signals.data ?? [],
    history: history.data ?? [],
    events: events.data ?? [],
    sources: sources.data ?? [],
  };
}

// ---------------------------------------------------------------- review queue (M3)


export function canReview(v: Viewer): boolean {
  return v.role === "owner" || v.role === "reviewer";
}

export async function listQueue(status: "pending" | "decided", ticker?: string): Promise<QueueItem[]> {
  if (usingFixtures()) {
    try {
      const all = JSON.parse(readFileSync(join(FIXTURES, "review", "queue.json"), "utf8")) as QueueItem[];
      return all.filter((q) => (status === "pending" ? q.status === "pending" : q.status !== "pending"))
        .filter((q) => !ticker || q.ticker === ticker);
    } catch {
      return [];
    }
  }
  const { createClient } = await import("./supabase/server");
  const supabase = await createClient();
  let q = supabase.from("v_proposal_queue").select("*");
  q = status === "pending" ? q.eq("status", "pending") : q.neq("status", "pending");
  if (ticker) q = q.eq("ticker", ticker);
  q = status === "pending" ? q.order("created_at", { ascending: false }) : q.order("reviewed_at", { ascending: false }).limit(30);
  const { data, error } = await q;
  if (error) throw new Error(`Could not load the review queue: ${error.message}`);
  return (data ?? []) as QueueItem[];
}

export async function countPending(): Promise<number> {
  if (usingFixtures()) return (await listQueue("pending")).length;
  const { createClient } = await import("./supabase/server");
  const supabase = await createClient();
  const { count } = await supabase.from("proposals").select("id", { count: "exact", head: true }).eq("status", "pending");
  return count ?? 0;
}

export async function listSignalOptions(): Promise<SignalOption[]> {
  if (usingFixtures()) {
    return readdirSync(FIXTURES).filter((f) => f.endsWith(".json")).flatMap((f) => {
      const page = fixture(f.replace(/\.json$/, ""))!;
      return page.signals.map((s) => ({ ticker: page.ticker.symbol, code: s.signal_code, name: s.signal_name, unit: s.unit }));
    });
  }
  const { createClient } = await import("./supabase/server");
  const supabase = await createClient();
  const { data, error } = await supabase.from("signals").select("ticker, code, name, unit").eq("active", true)
    .neq("polarity", "Event ladder").order("ticker").order("code");
  if (error) throw new Error(`Could not load signals: ${error.message}`);
  return data ?? [];
}
