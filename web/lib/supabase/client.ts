import { createBrowserClient } from "@supabase/ssr";

/** Supabase client for the browser. Writes the session cookie directly, so the next page load is signed in. */
export function createClient() {
  return createBrowserClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!);
}
