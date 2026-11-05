import { cookies } from "next/headers";
import { createClient } from "@/lib/supabase/server";

export const dynamic = "force-dynamic";

/** Sign-in diagnostics for the owners. Shows cookie NAMES only (never values), who the site thinks you are,
 *  and whether you are in the members list. */
export default async function AuthStatus() {
  const cookieNames = (await cookies()).getAll().map((c) => c.name).filter((n) => n.startsWith("sb-"));
  const supabase = await createClient();
  const { data, error } = await supabase.auth.getUser();
  const user = data?.user ?? null;
  let role: string | null = null;
  let memberError: string | null = null;
  if (user) {
    const r = await supabase.from("members").select("role").eq("user_id", user.id).maybeSingle();
    role = r.data?.role ?? null;
    memberError = r.error?.message ?? null;
  }
  const rows: [string, string][] = [
    ["Supabase settings in this build", process.env.NEXT_PUBLIC_SUPABASE_URL ? "present" : "MISSING"],
    ["Sign-in cookies received", cookieNames.length ? cookieNames.join(", ") : "none"],
    ["Signed in as", user ? (user.email ?? user.id) : `not signed in${error ? ` (${error.message})` : ""}`],
    ["Email confirmed", user ? (user.email_confirmed_at ? "yes" : "NO") : "–"],
    ["Members list", user ? (role ? `yes, role ${role}` : `NOT a member${memberError ? ` (${memberError})` : ""}`) : "–"],
  ];
  return (
    <main className="shell" style={{ maxWidth: 640 }}>
      <div className="card stack">
        <h1 style={{ fontSize: 22 }}>Sign-in status</h1>
        <table className="sources">
          <tbody>
            {rows.map(([k, v]) => (
              <tr key={k}><td className="muted">{k}</td><td>{v}</td></tr>
            ))}
          </tbody>
        </table>
        <p className="small muted"><a href="/">Go to the dashboard</a> · <a href="/login">Sign-in page</a></p>
      </div>
    </main>
  );
}
