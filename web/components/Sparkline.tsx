import type { Observation } from "@/lib/types";
import { formatValue } from "@/lib/format";

const DOT: Record<string, string> = {
  GREEN: "var(--good)",
  YELLOW: "var(--warning)",
  RED: "var(--critical)",
  GREY: "var(--neutral)",
  PENDING: "var(--neutral)",
};

/** Small history line for one signal. Single series, so no legend; every point has a hover tooltip
 *  (period, value, colour). Points without a value are skipped. */
export function Sparkline({ points, unit }: { points: Observation[]; unit: string | null }) {
  const pts = points.filter((p) => p.observed_value !== null);
  if (pts.length < 2) return <span className="small muted">{pts.length === 1 ? "1 reading" : "–"}</span>;
  const W = 120, H = 32, PAD = 5;
  const vals = pts.map((p) => p.observed_value as number);
  const lo = Math.min(...vals), hi = Math.max(...vals);
  const span = hi - lo || 1;
  const x = (i: number) => PAD + (i * (W - 2 * PAD)) / (pts.length - 1);
  const y = (v: number) => H - PAD - ((v - lo) / span) * (H - 2 * PAD);
  const d = pts.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)} ${y(p.observed_value as number).toFixed(1)}`).join(" ");
  const fmt = (v: number) => formatValue(v, unit);
  return (
    <svg className="spark" width={W} height={H} viewBox={`0 0 ${W} ${H}`} role="img"
      aria-label={`History: ${pts.map((p) => `${p.period ?? p.observed_on} ${fmt(p.observed_value as number)}`).join(", ")}`}>
      <line className="base" x1={PAD} x2={W - PAD} y1={H - PAD} y2={H - PAD} />
      <path className="line" d={d} />
      {pts.map((p, i) => (
        <g key={i}>
          <circle cx={x(i)} cy={y(p.observed_value as number)} r={i === pts.length - 1 ? 4.5 : 3.5} fill={DOT[p.colour]} />
          {/* larger invisible hit target for the tooltip */}
          <circle cx={x(i)} cy={y(p.observed_value as number)} r={9} fill="transparent">
            <title>{`${p.period ?? p.observed_on}: ${fmt(p.observed_value as number)} (${p.data_status === "OK" ? p.colour : p.data_status})`}</title>
          </circle>
        </g>
      ))}
    </svg>
  );
}
