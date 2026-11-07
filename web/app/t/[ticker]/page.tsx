import Link from "next/link";
import { getTickerPage, getViewer } from "@/lib/data";
import type { Driver, EventStep, Observation, SignalLatest, Source } from "@/lib/types";
import { StatusChip, EventChip, Arrow } from "@/components/Status";
import { formatValue } from "@/lib/format";
import { Sparkline } from "@/components/Sparkline";
import { NotMember } from "@/components/NotMember";
import { RevenueChart, MarginChart, PlatformTable } from "@/components/Charts";

export const dynamic = "force-dynamic";

const fmt = formatValue;
const pct = (v: number | null) => (v === null ? "–" : `${v >= 0 ? "+" : ""}${(v * 100).toFixed(1)}%`);
const age = (d: number | null) => (d === null ? "–" : d === 0 ? "today" : d === 1 ? "1 day" : `${d} days`);

export default async function TickerPageView({ params }: { params: Promise<{ ticker: string }> }) {
  const { ticker: raw } = await params;
  const viewer = await getViewer();
  if (!viewer.isMember) return <NotMember email={viewer.email} />;
  const page = await getTickerPage(raw);

  if (!page) {
    return (
      <main className="shell">
        <h1 style={{ fontSize: 26 }}>{raw.toUpperCase()}</h1>
        <p className="muted">No driver map yet for this ticker. <Link href="/">Back to covered tickers</Link></p>
      </main>
    );
  }

  const { ticker, baseCase, drivers, signals, history, events, sources, financials = [] } = page;
  const bySignal = (code: string) => history.filter((h) => h.signal_code === code);

  return (
    <main className="shell">
      <div className="ticker-head">
        <h1>{ticker.symbol}</h1>
        {ticker.is_test && <span className="tag warn">test ticker</span>}
        <span className="muted">{ticker.name ?? ticker.archetype}</span>
      </div>
      <div className="small muted">
        Base case:{" "}
        {baseCase ? `${baseCase.version}, set ${baseCase.snapshot_date ?? "date unknown"}` : "no consensus base case yet, so readings show grey"}
      </div>
      <p className="explainer">
        Green means a signal is at or ahead of the consensus base case, not that the stock goes up.
        Grey means no reading, stale data or no base case to compare with; it never means "in line".
        Where there is no consensus for a signal, it is compared with our own estimate instead, marked "vs our estimate".
      </p>

      <div className="drivers">
        {drivers.map((d) => (
          <DriverCard key={d.code} driver={d} signals={signals.filter((s) => s.driver_code === d.code)} history={bySignal} />
        ))}
      </div>

      {events.length > 0 && <EventLadder events={events} signals={signals} />}
      {financials.length > 0 && (
        <>
          <h2 className="section-title">Financials</h2>
          <div className="charts">
            <RevenueChart rows={financials} />
            <MarginChart rows={financials} />
          </div>
          <PlatformTable rows={financials} />
        </>
      )}
      <SourceLog sources={sources} />
    </main>
  );
}

function DriverCard({ driver, signals, history }: {
  driver: Driver; signals: SignalLatest[]; history: (code: string) => Observation[];
}) {
  return (
    <section className="card" aria-labelledby={`d-${driver.code}`}>
      <div className="driver-head">
        <h2 id={`d-${driver.code}`}>{driver.name}</h2>
        {driver.driver_type && <span className="tag">{driver.driver_type}</span>}
        {driver.impact && <span className="tag">Impact {driver.impact}</span>}
        {driver.driver_status !== "OK" && <span className="tag warn">{driver.driver_status}</span>}
        {driver.depends_on && <span className="small muted">depends on {driver.depends_on}</span>}
      </div>
      {driver.thesis && <p className="driver-thesis">{driver.thesis}</p>}
      {signals.length === 0 ? (
        <p className="small muted">No signals defined.</p>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table className="signals">
            <colgroup>
              <col className="c-name" /><col className="c-status" /><col className="c-latest" /><col className="c-var" />
              <col className="c-arrow" /><col className="c-hist" /><col className="c-age" />
            </colgroup>
            <thead>
              <tr>
                <th>Signal</th>
                <th>Status</th>
                <th className="num">Latest</th>
                <th className="num hide-sm">vs base</th>
                <th className="hide-sm">Momentum</th>
                <th className="hide-sm">History</th>
                <th className="num">Age</th>
              </tr>
            </thead>
            <tbody>
              {signals.map((s) => (
                <tr key={s.signal_code}>
                  <td className="sig-name">
                    {s.binding_constraint && <span className="star" title="Binding constraint: the signal that gates this driver">★</span>}
                    {s.signal_name}
                    <div className="small muted">
                      {s.signal_code} · Tier {s.tier ?? "?"} · {s.cadence ?? "–"}
                      {s.kill_switch && " · kill switch"}
                      {s.source_code && ` · source ${s.source_code}`}
                    </div>
                  </td>
                  <td data-label="Status"><StatusChip colour={s.colour} detail={s.data_status} /></td>
                  <td className="num" data-label="Latest">{s.polarity === "Event ladder" ? <span className="small muted">see milestones</span> : fmt(s.observed_value, s.unit)}</td>
                  <td className="num hide-sm">
                    {pct(s.variance)}
                    {s.base_type === "Thesis" && s.variance !== null && <div className="small muted">vs our estimate</div>}
                  </td>
                  <td className="hide-sm"><Arrow value={s.arrow} /></td>
                  <td className="hide-sm"><Sparkline points={history(s.signal_code)} unit={s.unit} /></td>
                  <td className="num" data-label="Age">{age(s.age_days)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function EventLadder({ events, signals }: { events: EventStep[]; signals: SignalLatest[] }) {
  const name = (code: string) => signals.find((s) => s.signal_code === code)?.signal_name ?? code;
  return (
    <>
      <h2 className="section-title">Milestones and checks</h2>
      <div className="card">
        <ul className="ladder">
          {events.map((e) => (
            <li key={`${e.signal_code}-${e.step_no}`}>
              <span className="small muted when">
                {e.actual_date ? `done ${e.actual_date}` : e.target_date ? `due ${e.target_date}` : "no date"}
              </span>
              <span>
                {e.milestone}
                <div className="small muted">{e.kind ?? "Milestone"} · {name(e.signal_code)}</div>
              </span>
              <EventChip colour={e.colour} status={e.status} />
            </li>
          ))}
        </ul>
      </div>
    </>
  );
}

function SourceLog({ sources }: { sources: Source[] }) {
  if (sources.length === 0) return null;
  return (
    <details className="card" style={{ marginTop: 32 }}>
      <summary>Sources ({sources.length})</summary>
      <table className="sources">
        <tbody>
          {sources.map((s) => (
            <tr key={s.code}>
              <td className="muted">{s.code}</td>
              <td>{s.url ? <a href={s.url} target="_blank" rel="noreferrer">{s.name ?? s.url}</a> : (s.name ?? "–")}</td>
              <td className="muted small">{s.tier ? `Tier ${s.tier}` : ""}</td>
              <td className="muted small hide-sm">{s.accessed_on ? `accessed ${s.accessed_on}` : ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </details>
  );
}
