import type { FinancialRow } from "@/lib/types";

/** Quarterly charts from SEC filings. Hand-drawn SVG: one axis per chart, thin marks, legend for >= 2 series,
 *  hover tooltips (<title>) on every mark, and a table view for each chart. Colours: --series-1 / --series-2. */

const B = 1e9;
const W = 640, H = 240, L = 48, R = 16, T = 16, BOT = 34;

type Q = { end: string; label: string; values: Record<string, number> };

function byQuarter(rows: FinancialRow[], metrics: string[]): Q[] {
  const map = new Map<string, Q>();
  for (const r of rows) {
    if (!metrics.includes(r.metric)) continue;
    const q = map.get(r.period_end) ?? { end: r.period_end, label: r.fiscal_period ?? r.period_end, values: {} };
    q.values[r.metric] = r.value;
    map.set(r.period_end, q);
  }
  return [...map.values()].sort((a, b) => a.end.localeCompare(b.end));
}

function niceMax(v: number): number {
  const p = 10 ** Math.floor(Math.log10(v));
  return [1, 2, 2.5, 5, 10].map((m) => m * p).find((m) => m >= v) ?? v;
}

const usdB = (v: number) => `$${(v / B).toLocaleString("en-US", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}B`;

function Legend({ items }: { items: { label: string; color: string; line?: boolean }[] }) {
  return (
    <div className="legend small">
      {items.map((i) => (
        <span key={i.label}>
          <span aria-hidden="true" className={i.line ? "key-line" : "key-box"} style={{ background: i.color }} />
          {i.label}
        </span>
      ))}
    </div>
  );
}

export function RevenueChart({ rows }: { rows: FinancialRow[] }) {
  const qs = byQuarter(rows, ["revenue", "rev_data_center"]).filter((q) => q.values.revenue !== undefined);
  if (qs.length < 2) return null;
  const max = niceMax(Math.max(...qs.map((q) => q.values.revenue)));
  const pw = W - L - R, ph = H - T - BOT;
  const step = pw / qs.length, bw = Math.min(44, step * 0.62);
  const y = (v: number) => T + ph - (v / max) * ph;
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => f * max);
  const last = qs[qs.length - 1];
  return (
    <figure className="chart">
      <figcaption>
        <strong>Quarterly revenue</strong>
        <span className="small muted"> · Data Center and the rest, $B, from SEC filings</span>
      </figcaption>
      <Legend items={[{ label: "Data Center", color: "var(--series-1)" }, { label: "Other", color: "var(--series-2)" }]} />
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Quarterly revenue, latest ${last.label} ${usdB(last.values.revenue)}`}>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={L} x2={W - R} y1={y(t)} y2={y(t)} className={t === 0 ? "axis" : "grid"} />
            <text x={L - 6} y={y(t) + 4} textAnchor="end" className="tick">{`$${Math.round(t / B)}B`}</text>
          </g>
        ))}
        {qs.map((q, i) => {
          const x = L + i * step + (step - bw) / 2;
          const total = q.values.revenue, dc = q.values.rev_data_center;
          const other = dc !== undefined ? total - dc : undefined;
          return (
            <g key={q.end}>
              {dc !== undefined && other !== undefined ? (
                <>
                  <rect x={x} y={y(dc)} width={bw} height={y(0) - y(dc)} fill="var(--series-1)">
                    <title>{`${q.label} Data Center: ${usdB(dc)}`}</title>
                  </rect>
                  {/* 2px surface gap between stacked segments; rounded data end on top */}
                  <path d={`M${x} ${y(total) + 4} q0 -4 4 -4 h${bw - 8} q4 0 4 4 V${y(dc) - 2} H${x} Z`} fill="var(--series-2)">
                    <title>{`${q.label} Other: ${usdB(other)} (total ${usdB(total)})`}</title>
                  </path>
                </>
              ) : (
                <rect x={x} y={y(total)} width={bw} height={y(0) - y(total)} rx={4} fill="var(--neutral)">
                  <title>{`${q.label} total: ${usdB(total)}`}</title>
                </rect>
              )}
              <text x={x + bw / 2} y={H - BOT + 16} textAnchor="middle" className="tick">{q.label.replace(" FY", " FY")}</text>
            </g>
          );
        })}
        <text x={L + (qs.length - 1) * step + step / 2} y={y(last.values.revenue) - 6} textAnchor="middle" className="value">
          {usdB(last.values.revenue)}
        </text>
      </svg>
      <TableView
        head={["Quarter", "Total", "Data Center", "Other"]}
        rows={qs.map((q) => [q.label, usdB(q.values.revenue),
          q.values.rev_data_center !== undefined ? usdB(q.values.rev_data_center) : "–",
          q.values.rev_data_center !== undefined ? usdB(q.values.revenue - q.values.rev_data_center) : "–"])}
      />
    </figure>
  );
}

export function MarginChart({ rows }: { rows: FinancialRow[] }) {
  const qs = byQuarter(rows, ["revenue", "gross_profit", "operating_income"])
    .filter((q) => q.values.revenue && q.values.gross_profit !== undefined && q.values.operating_income !== undefined);
  if (qs.length < 2) return null;
  const series = [
    { key: "gross_profit", label: "Gross margin", color: "var(--series-1)" },
    { key: "operating_income", label: "Operating margin", color: "var(--series-2)" },
  ].map((s) => ({ ...s, pts: qs.map((q) => (q.values[s.key] / q.values.revenue) * 100) }));
  const all = series.flatMap((s) => s.pts);
  const lo = Math.max(0, Math.floor((Math.min(...all) - 5) / 10) * 10), hi = Math.min(100, Math.ceil((Math.max(...all) + 2) / 10) * 10);
  const pw = W - L - R, ph = H - T - BOT;
  const x = (i: number) => L + (i + 0.5) * (pw / qs.length);
  const y = (v: number) => T + ph - ((v - lo) / (hi - lo)) * ph;
  const ticks = Array.from({ length: (hi - lo) / 10 + 1 }, (_, i) => lo + i * 10);
  return (
    <figure className="chart">
      <figcaption>
        <strong>Margins</strong>
        <span className="small muted"> · GAAP, % of revenue, from SEC filings</span>
      </figcaption>
      <Legend items={series.map((s) => ({ label: s.label, color: s.color, line: true }))} />
      <svg viewBox={`0 0 ${W} ${H}`} role="img"
        aria-label={`Margins, latest ${qs[qs.length - 1].label}: ${series.map((s) => `${s.label} ${s.pts[s.pts.length - 1].toFixed(1)}%`).join(", ")}`}>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={L} x2={W - R} y1={y(t)} y2={y(t)} className={t === lo ? "axis" : "grid"} />
            <text x={L - 6} y={y(t) + 4} textAnchor="end" className="tick">{`${t}%`}</text>
          </g>
        ))}
        {qs.map((q, i) => (
          <text key={q.end} x={x(i)} y={H - BOT + 16} textAnchor="middle" className="tick">{q.label.replace(" FY", " FY")}</text>
        ))}
        {series.map((s) => (
          <g key={s.key}>
            <path d={s.pts.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)} ${y(v).toFixed(1)}`).join(" ")}
              fill="none" stroke={s.color} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
            {s.pts.map((v, i) => (
              <circle key={i} cx={x(i)} cy={y(v)} r={i === s.pts.length - 1 ? 4.5 : 3.5} fill={s.color} stroke="var(--surface-1)" strokeWidth={2}>
                <title>{`${qs[i].label} ${s.label}: ${v.toFixed(1)}%`}</title>
              </circle>
            ))}
            <text x={x(s.pts.length - 1) - 8} y={y(s.pts[s.pts.length - 1]) - 9} textAnchor="end" className="value">
              {`${s.pts[s.pts.length - 1].toFixed(1)}%`}
            </text>
          </g>
        ))}
      </svg>
      <TableView head={["Quarter", ...series.map((s) => s.label)]}
        rows={qs.map((q, i) => [q.label, ...series.map((s) => `${s.pts[i].toFixed(1)}%`)])} />
    </figure>
  );
}

export function PlatformTable({ rows }: { rows: FinancialRow[] }) {
  const qs = byQuarter(rows, ["rev_hyperscale", "rev_acie", "rev_edge_computing"]);
  if (qs.length === 0) return null;
  return (
    <figure className="chart">
      <figcaption>
        <strong>Revenue by market platform</strong>
        <span className="small muted"> · $B, NVIDIA's presentation since Q1 FY27; earlier quarters as restated in the latest filing</span>
      </figcaption>
      <div style={{ overflowX: "auto" }}>
        <table className="sources num-table">
          <thead><tr><th>Quarter</th><th>Hyperscale</th><th>AI Clouds, Industrial &amp; Enterprise</th><th>Edge Computing</th></tr></thead>
          <tbody>
            {qs.map((q) => (
              <tr key={q.end}>
                <td>{q.label}</td>
                {["rev_hyperscale", "rev_acie", "rev_edge_computing"].map((m) => (
                  <td key={m} className="num">{q.values[m] !== undefined ? usdB(q.values[m]) : "–"}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </figure>
  );
}

function TableView({ head, rows }: { head: string[]; rows: string[][] }) {
  return (
    <details className="small">
      <summary>Show as table</summary>
      <table className="sources num-table">
        <thead><tr>{head.map((h) => <th key={h}>{h}</th>)}</tr></thead>
        <tbody>{rows.map((r) => <tr key={r[0]}>{r.map((c, i) => <td key={i} className={i ? "num" : ""}>{c}</td>)}</tr>)}</tbody>
      </table>
    </details>
  );
}
