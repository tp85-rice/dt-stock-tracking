/** "$201.9B", "54.6%", "60 days", "1,234 units". */
export function formatValue(v: number | null, unit: string | null): string {
  if (v === null) return "–";
  const n = (d: number) => v.toLocaleString("en-US", { maximumFractionDigits: d });
  switch ((unit ?? "").trim()) {
    case "$B": return `$${v.toLocaleString("en-US", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}B`;
    case "$M": return `$${n(0)}M`;
    case "%": return `${n(1)}%`;
    case "": return n(2);
    default: return `${n(2)} ${unit}`;
  }
}
