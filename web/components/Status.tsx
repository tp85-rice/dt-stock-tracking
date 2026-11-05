import type { Colour } from "@/lib/types";

const LABEL: Record<Colour, string> = {
  GREEN: "Ahead",
  YELLOW: "Slightly behind",
  RED: "Behind",
  GREY: "No reading",
  PENDING: "Pending",
};

/** Colour chip. Always shows a text label next to the colour, so meaning never relies on colour alone. */
export function StatusChip({ colour, detail }: { colour: Colour; detail?: string | null }) {
  let label = LABEL[colour] ?? colour;
  if (colour === "GREY" && detail && detail !== "OK") label = detail; // Missing / Stale / No base case / No data
  if (colour === "RED" && detail === "Withheld") label = "Withheld";
  return (
    <span className="chip" title={detail ?? undefined}>
      <span className={`dot ${colour}`} aria-hidden="true" />
      {label}
    </span>
  );
}

/** Event-ladder chip: describes what happened to the milestone, not a comparison with a base case. */
export function EventChip({ colour, status }: { colour: Colour; status: string | null }) {
  const label =
    colour === "GREEN" ? "Done on time" :
    colour === "YELLOW" ? (status === "Occurred" ? "Done late" : "Overdue") :
    colour === "RED" ? (status ?? "Missed") :
    "Pending";
  return (
    <span className="chip">
      <span className={`dot ${colour}`} aria-hidden="true" />
      {label}
    </span>
  );
}

const ARROW: Record<string, string> = { Accelerating: "↗", Flat: "→", Decelerating: "↘" };

export function Arrow({ value }: { value: string | null }) {
  if (!value || value === "n/a") return <span className="muted">–</span>;
  return (
    <span title={`Momentum: ${value}`}>
      {ARROW[value] ?? ""} <span className="small muted">{value}</span>
    </span>
  );
}
