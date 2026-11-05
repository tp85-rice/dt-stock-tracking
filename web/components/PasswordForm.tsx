"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";

/** Email + password sign-in, done in the browser so the session cookie is written before we navigate.
 *  Shows Supabase's own error message (e.g. "Invalid login credentials", "Email not confirmed"). */
export function PasswordForm({ defaultEmail }: { defaultEmail: string }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    const email = String(form.get("email") ?? "").trim().toLowerCase();
    const password = String(form.get("password") ?? "");
    setBusy(true);
    setError(null);
    try {
      const { error } = await createClient().auth.signInWithPassword({ email, password });
      if (error) {
        setError(error.message);
        setBusy(false);
        return;
      }
      // Full page load so the server and middleware read the new session cookie.
      window.location.assign("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-in failed. Try again.");
      setBusy(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="stack" style={{ margin: 0 }}>
      <input type="email" name="email" required placeholder="you@example.com" aria-label="Email"
        autoComplete="username" defaultValue={defaultEmail} />
      <input type="password" name="password" required placeholder="Password" aria-label="Password"
        autoComplete="current-password" />
      <button className="primary" type="submit" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
      {error && <p className="small" role="alert" style={{ margin: 0 }}>Sign-in failed: {error}</p>}
    </form>
  );
}
