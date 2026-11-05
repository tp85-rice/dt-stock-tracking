import { headers } from "next/headers";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";

export const dynamic = "force-dynamic";

async function sendLink(formData: FormData) {
  "use server";
  const email = String(formData.get("email") ?? "").trim().toLowerCase();
  if (!email) redirect("/login?e=missing");
  const h = await headers();
  const origin = h.get("origin") ?? `https://${h.get("host")}`;
  const supabase = await createClient();
  const { error } = await supabase.auth.signInWithOtp({
    email,
    // Invite-only: never create an account from the login form.
    options: { shouldCreateUser: false, emailRedirectTo: `${origin}/auth/callback` },
  });
  // Same message whether or not the address is known, so the form does not reveal who is invited.
  redirect(error && error.status !== 400 && error.status !== 422 ? "/login?e=send" : "/login?sent=1");
}

export default async function Login({ searchParams }: { searchParams: Promise<Record<string, string>> }) {
  const sp = await searchParams;
  return (
    <main className="shell" style={{ maxWidth: 440 }}>
      <div className="card stack">
        <h1 style={{ fontSize: 22 }}>Sign in</h1>
        {sp.sent ? (
          <p>If this address is invited, a sign-in link is on its way. Open it on this device.</p>
        ) : (
          <>
            <p className="muted small">Invite only. Enter your email and we'll send you a sign-in link.</p>
            <form action={sendLink} className="search" style={{ margin: 0 }}>
              <input type="email" name="email" required placeholder="you@example.com" aria-label="Email" />
              <button className="primary" type="submit">Send link</button>
            </form>
          </>
        )}
        {sp.e === "send" && <p className="small" role="alert">Could not send the link. Try again in a minute.</p>}
        {sp.e === "link" && <p className="small" role="alert">That sign-in link has expired or was already used. Request a new one.</p>}
      </div>
    </main>
  );
}
