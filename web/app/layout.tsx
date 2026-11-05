import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import { getViewer, canReview, countPending } from "@/lib/data";

export const metadata: Metadata = {
  title: "Driver Tracker",
  description: "Growth drivers and their signals, measured against a base case.",
  robots: { index: false, follow: false },
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const viewer = await getViewer();
  const pending = viewer.isMember && canReview(viewer) ? await countPending().catch(() => 0) : null;
  return (
    <html lang="en">
      <body>
        <header className="topbar">
          <div className="shell">
            <Link href="/" className="brand">Driver Tracker</Link>
            {viewer.email && (
              <div className="who">
                {pending !== null && <Link href="/review">Review{pending ? ` (${pending})` : ""}</Link>}
                <span className="hide-sm">{viewer.email}</span>
                <form action="/auth/signout" method="post">
                  <button className="linkbtn" type="submit">Sign out</button>
                </form>
              </div>
            )}
          </div>
        </header>
        {children}
        <footer className="disclaimer" role="contentinfo">
          This app measures signals against a base case. It is not investment advice.
        </footer>
      </body>
    </html>
  );
}
