import { headers } from "next/headers";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";

export const dynamic = "force-dynamic";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

async function sendCode(formData: FormData) {
  "use server";
  const email = String(formData.get("email") ?? "").trim().toLowerCase();
  if (!EMAIL_RE.test(email)) redirect("/login?e=missing");
  const h = await headers();
  const origin = h.get("origin") ?? `https://${h.get("host")}`;
  const supabase = await createClient();
  const { error } = await supabase.auth.signInWithOtp({
    email,
    // Invite-only: never create an account from the login form.
    options: { shouldCreateUser: false, emailRedirectTo: `${origin}/auth/callback` },
  });
  if (error && error.status === 429) redirect(`/login?e=rate&email=${encodeURIComponent(email)}`);
  // Same next step whether or not the address is invited, so the form does not reveal who is.
  redirect(`/login?sent=1&email=${encodeURIComponent(email)}`);
}

async function verifyCode(formData: FormData) {
  "use server";
  const email = String(formData.get("email") ?? "").trim().toLowerCase();
  const token = String(formData.get("code") ?? "").replace(/\s+/g, "");
  if (!EMAIL_RE.test(email) || !/^\d{6,10}$/.test(token)) {
    redirect(`/login?sent=1&e=code&email=${encodeURIComponent(email)}`);
  }
  const supabase = await createClient();
  const { error } = await supabase.auth.verifyOtp({ email, token, type: "email" });
  if (error) redirect(`/login?sent=1&e=code&email=${encodeURIComponent(email)}`);
  redirect("/");
}

export default async function Login({ searchParams }: { searchParams: Promise<Record<string, string>> }) {
  const sp = await searchParams;
  const email = sp.email ?? "";
  return (
    <main className="shell" style={{ maxWidth: 460 }}>
      <div className="card stack">
        <h1 style={{ fontSize: 22 }}>Sign in</h1>
        {sp.sent ? (
          <>
            <p>
              If <strong>{email || "this address"}</strong> is invited, an email is on its way with a sign-in code.
              Type the code here:
            </p>
            <form action={verifyCode} className="search" style={{ margin: 0 }}>
              <input type="hidden" name="email" value={email} />
              <input type="text" name="code" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9 ]{6,12}"
                required placeholder="6-digit code" aria-label="Sign-in code" />
              <button className="primary" type="submit">Sign in</button>
            </form>
            <p className="small muted">
              The email also has a link: open it and press Continue. Wrong address? <a href="/login">Start again</a>.
            </p>
          </>
        ) : (
          <>
            <p className="muted small">Invite only. Enter your email and we'll send you a sign-in code.</p>
            <form action={sendCode} className="search" style={{ margin: 0 }}>
              <input type="email" name="email" required placeholder="you@example.com" aria-label="Email" defaultValue={email} />
              <button className="primary" type="submit">Send code</button>
            </form>
          </>
        )}
        {sp.e === "code" && <p className="small" role="alert">That code didn't work. Check it, or request a new one.</p>}
        {sp.e === "rate" && <p className="small" role="alert">Too many emails were sent just now. Wait a minute, then try again.</p>}
        {sp.e === "missing" && <p className="small" role="alert">Enter a valid email address.</p>}
        {sp.e === "link" && (
          <p className="small" role="alert">
            That sign-in link has expired or was already used{sp.reason ? ` (${sp.reason})` : ""}. Request a new one
            and use the code from the email instead.
          </p>
        )}
      </div>
    </main>
  );
}
