import Link from "next/link";
import { getViewer, listSignalOptions, canReview } from "@/lib/data";
import { NotMember } from "@/components/NotMember";
import { createManual } from "../actions";

export const dynamic = "force-dynamic";

const field = { display: "flex", flexDirection: "column" as const, gap: 2 };

export default async function NewReading({ searchParams }: { searchParams: Promise<Record<string, string>> }) {
  const sp = await searchParams;
  const viewer = await getViewer();
  if (!viewer.isMember) return <NotMember email={viewer.email} />;
  if (!canReview(viewer)) return <main className="shell"><p className="muted">Only reviewers and owners can add readings.</p></main>;
  const signals = await listSignalOptions();
  const tickers = [...new Set(signals.map((s) => s.ticker))];
  const today = new Date().toISOString().slice(0, 10);

  return (
    <main className="shell" style={{ maxWidth: 640 }}>
      <div className="card stack">
        <h1 style={{ fontSize: 22 }}>Add a reading by hand</h1>
        <p className="small muted">It goes to the review queue first, like any other proposed reading.</p>
        {sp.err && <p className="small" role="alert">{sp.err}</p>}
        <form action={createManual} className="stack">
          <label className="small" style={field}>Signal
            <select name="signal" required defaultValue="" style={{ font: "inherit", padding: 8, borderRadius: 8 }}>
              <option value="" disabled>Choose…</option>
              {tickers.map((t) => (
                <optgroup key={t} label={t}>
                  {signals.filter((s) => s.ticker === t).map((s) => (
                    <option key={s.code} value={`${s.ticker}|${s.code}`}>{s.code} · {s.name}</option>
                  ))}
                </optgroup>
              ))}
            </select>
          </label>
          <label className="small" style={field}>Value (in the signal's unit)
            <input type="text" name="value" inputMode="decimal" placeholder="e.g. 201.9" />
          </label>
          <label className="small"><input type="checkbox" name="withheld" /> Withheld: the company skipped a natural chance to disclose it (shows RED)</label>
          <label className="small" style={field}>Period (exactly as in the base case, e.g. Q3 FY27)
            <input type="text" name="period" required />
          </label>
          <label className="small" style={field}>Date observed (when the number became public)
            <input type="text" name="observed_on" required defaultValue={today} pattern="\d{4}-\d{2}-\d{2}" />
          </label>
          <label className="small" style={field}>Base case version
            <input type="text" name="base_case_version" required defaultValue="v1" />
          </label>
          <label className="small" style={field}>Source ID (from the ticker's source log, e.g. R1)
            <input type="text" name="source_code" />
          </label>
          <label className="small" style={field}>Arrow
            <select name="arrow" defaultValue="" style={{ font: "inherit", padding: 8, borderRadius: 8 }}>
              <option value="">–</option><option>Accelerating</option><option>Flat</option><option>Decelerating</option><option>n/a</option>
            </select>
          </label>
          <label className="small" style={field}>Notes
            <input type="text" name="notes" />
          </label>
          <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
            <button className="primary" type="submit">Add to review queue</button>
            <Link href="/review" className="small">Cancel</Link>
          </div>
        </form>
      </div>
    </main>
  );
}
