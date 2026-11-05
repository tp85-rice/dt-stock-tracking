import { redirect } from "next/navigation";
import type { EmailOtpType } from "@supabase/supabase-js";
import { createClient } from "@/lib/supabase/server";

export const dynamic = "force-dynamic";

const TYPES: EmailOtpType[] = ["email", "magiclink", "invite", "recovery", "signup", "email_change"];

/** Email link target: /auth/confirm?token_hash=...&type=email
 *  Signing in needs a button press (a POST). Mail-security scanners open links but do not press buttons,
 *  so they can no longer use up the one-time link. Works in any browser (no PKCE cookie needed). */
async function confirm(formData: FormData) {
  "use server";
  const token_hash = String(formData.get("token_hash") ?? "");
  const type = String(formData.get("type") ?? "email") as EmailOtpType;
  if (!token_hash || !TYPES.includes(type)) redirect("/login?e=link");
  const supabase = await createClient();
  const { error } = await supabase.auth.verifyOtp({ token_hash, type });
  if (error) redirect(`/login?e=link&reason=${encodeURIComponent(error.code ?? error.message)}`);
  redirect("/");
}

export default async function Confirm({ searchParams }: { searchParams: Promise<Record<string, string>> }) {
  const sp = await searchParams;
  return (
    <main className="shell" style={{ maxWidth: 460 }}>
      <div className="card stack">
        <h1 style={{ fontSize: 22 }}>Continue signing in</h1>
        {sp.token_hash ? (
          <form action={confirm}>
            <input type="hidden" name="token_hash" value={sp.token_hash} />
            <input type="hidden" name="type" value={sp.type ?? "email"} />
            <button className="primary" type="submit">Continue</button>
          </form>
        ) : (
          <p className="muted">This link is incomplete. <a href="/login">Request a new sign-in code</a>.</p>
        )}
      </div>
    </main>
  );
}
