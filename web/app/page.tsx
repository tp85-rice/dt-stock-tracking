import Link from "next/link";
import { redirect } from "next/navigation";
import { getViewer, listTickers } from "@/lib/data";
import { NotMember } from "@/components/NotMember";

export const dynamic = "force-dynamic";

async function goToTicker(formData: FormData) {
  "use server";
  const symbol = String(formData.get("symbol") ?? "").trim().toUpperCase().replace(/[^A-Z0-9.\-]/g, "");
  if (symbol) redirect(`/t/${symbol}`);
}

export default async function Home() {
  const viewer = await getViewer();
  if (!viewer.isMember) return <NotMember email={viewer.email} />;
  const tickers = await listTickers();
  return (
    <main className="shell">
      <h1 style={{ fontSize: 26 }}>Covered tickers</h1>
      <form action={goToTicker} className="search" role="search">
        <input type="text" name="symbol" placeholder="Ticker, e.g. NVDA" aria-label="Ticker" autoComplete="off" />
        <button className="primary" type="submit">Open</button>
      </form>
      {tickers.length === 0 ? (
        <p className="muted">No tickers yet. Import a driver sheet to add one.</p>
      ) : (
        <div className="ticker-list">
          {tickers.map((t) => (
            <Link key={t.symbol} href={`/t/${t.symbol}`} className="card ticker-link">
              <strong style={{ fontSize: 18 }}>{t.symbol}</strong>{" "}
              {t.is_test && <span className="tag warn">test</span>}
              <div className="small muted">{t.name ?? t.archetype ?? " "}</div>
            </Link>
          ))}
        </div>
      )}
    </main>
  );
}
