import Link from "next/link";
import { getViewer, listQueue, canReview } from "@/lib/data";
import type { QueueItem } from "@/lib/types";
import { formatValue } from "@/lib/format";
import { StatusChip } from "@/components/Status";
import { NotMember } from "@/components/NotMember";
import { approve, reject } from "./actions";

export const dynamic = "force-dynamic";

const pct = (v: number | null) => (v === null ? "–" : `${v >= 0 ? "+" : ""}${(v * 100).toFixed(1)}%`);
const day = (iso: string | null) => (iso ? iso.slice(0, 10) : "–");

export default async function Review({ searchParams }: { searchParams: Promise<Record<string, string>> }) {
  const sp = await searchParams;
  const viewer = await getViewer();
  if (!viewer.isMember) return <NotMember email={viewer.email} />;
  if (!canReview(viewer)) {
    return (
      <main className="shell"><div className="card"><h1 style={{ fontSize: 22 }}>Review queue</h1>
        <p className="muted">Only reviewers and owners can review proposed readings.</p></div></main>
    );
  }
  const [pending, decided] = await Promise.all([listQueue("pending", sp.ticker), listQueue("decided", sp.ticker)]);

  return (
    <main className="shell">
      <div className="ticker-head">
        <h1>Review queue</h1>
        <span className="muted">{pending.length} waiting</span>
        <Link href="/review/new" className="small">+ Add a reading by hand</Link>
      </div>
      <p className="explainer">
        Nothing appears on the dashboard until it is approved here. Check the quoted source, then approve,
        edit and approve, or reject with a reason. Every decision is recorded with your name and time.
      </p>
      {sp.ok && <p className="card small" role="status">{sp.ok}</p>}
      {sp.err && <p className="card small" role="alert" style={{ borderColor: "var(--critical)" }}>{sp.err}</p>}

      {pending.length === 0 ? (
        <div className="card muted">Nothing waiting for review.</div>
      ) : (
        <div className="drivers">{pending.map((q) => <ReviewCard key={q.proposal_id} q={q} />)}</div>
      )}

      {decided.length > 0 && (
        <>
          <h2 className="section-title">Recent decisions</h2>
          <div className="card">
            <table className="sources" style={{ width: "100%" }}>
              <tbody>
                {decided.map((q) => (
                  <tr key={q.proposal_id}>
                    <td className="muted small">{day(q.reviewed_at)}</td>
                    <td>{q.ticker} · {q.signal_name ?? q.signal_code}</td>
                    <td className="small">{q.status === "approved" ? "Approved" : "Rejected"}</td>
                    <td className="small muted">{q.reviewer_note ?? ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </main>
  );
}

function ReviewCard({ q }: { q: QueueItem }) {
  const proposed = q.withheld && q.value === null ? "Withheld (not disclosed)" : formatValue(q.value, q.unit);
  return (
    <section className="card" aria-labelledby={`p-${q.proposal_id}`}>
      <div className="driver-head">
        <h2 id={`p-${q.proposal_id}`} style={{ fontSize: 17 }}>{q.ticker} · {q.signal_name ?? q.signal_code}</h2>
        <span className="tag">{q.origin === "manual" ? "typed in" : q.origin.startsWith("agent") ? "AI agent" : q.origin}</span>
        {q.confidence !== null && <span className="tag">confidence {Math.round(q.confidence * 100)}%</span>}
        <span className="small muted">#{q.proposal_id} · {day(q.created_at)}{q.driver_name ? ` · ${q.driver_name}` : ""}</span>
      </div>

      <table className="sources" style={{ marginTop: 10 }}>
        <tbody>
          <tr><td className="muted">Proposed</td><td><strong>{proposed}</strong> for {q.period ?? "?"}, observed {q.observed_on ?? "?"}</td></tr>
          <tr><td className="muted">Base case</td><td>{q.base_value === null ? `none for ${q.base_case_version ?? "?"} ${q.period ?? ""}` : `${formatValue(q.base_value, q.unit)} (${q.base_case_version})`}</td></tr>
          <tr><td className="muted">Would show as</td><td><StatusChip colour={q.preview_colour} detail={q.preview_status} /> <span className="small muted">{pct(q.preview_variance)} vs base</span></td></tr>
          <tr><td className="muted">Currently shown</td><td>{q.current_colour ? <><StatusChip colour={q.current_colour} detail={q.current_status} /> {formatValue(q.current_value, q.unit)} <span className="small muted">({q.current_observed_on ?? "no date"})</span></> : "–"}</td></tr>
          {q.source_code && <tr><td className="muted">Source</td><td>{q.source_code}</td></tr>}
          {q.notes && <tr><td className="muted">Notes</td><td className="small">{q.notes}</td></tr>}
        </tbody>
      </table>

      {q.citations && q.citations.length > 0 && (
        <div className="small" style={{ marginTop: 8 }}>
          {q.citations.map((c, i) => (
            <blockquote key={i} style={{ margin: "6px 0", paddingLeft: 10, borderLeft: "3px solid var(--hairline)" }}>
              {c.quote && <>“{c.quote}”<br /></>}
              {c.url && <a href={c.url} target="_blank" rel="noreferrer">{c.title ?? c.url}</a>}
            </blockquote>
          ))}
        </div>
      )}

      <form action={approve} className="stack" style={{ marginTop: 12 }}>
        <input type="hidden" name="proposal_id" value={q.proposal_id} />
        <details>
          <summary className="small">Edit before approving</summary>
          <div className="search" style={{ flexWrap: "wrap" }}>
            {([
              ["value", q.value === null ? "" : String(q.value), "Value"],
              ["period", q.period ?? "", "Period"],
              ["observed_on", q.observed_on ?? "", "Date observed (YYYY-MM-DD)"],
              ["base_case_version", q.base_case_version ?? "", "Base case version"],
              ["source_code", q.source_code ?? "", "Source ID"],
              ["arrow", q.arrow ?? "", "Arrow"],
            ] as const).map(([k, v, label]) => (
              <label key={k} className="small" style={{ display: "flex", flexDirection: "column", gap: 2, minWidth: 140 }}>
                {label}
                <input type="hidden" name={`orig_${k}`} value={v} />
                <input type="text" name={`edit_${k}`} defaultValue={v} />
              </label>
            ))}
          </div>
        </details>
        <input type="text" name="note" placeholder="Note (optional for approval, required to reject)" aria-label="Review note" />
        <div style={{ display: "flex", gap: 16, flexWrap: "wrap", alignItems: "center" }}>
          <button className="primary" type="submit">Approve</button>
          <button className="linkbtn" type="submit" formAction={reject} style={{ color: "var(--critical)" }}>Reject</button>
        </div>
      </form>
    </section>
  );
}
