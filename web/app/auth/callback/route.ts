import { NextResponse, type NextRequest } from "next/server";
import { createClient } from "@/lib/supabase/server";

/** Default Supabase email link target (?code=...). Kept for the standard email template; the
 *  recommended template uses /auth/confirm instead (see docs/SETUP.md section 6). */
export async function GET(request: NextRequest) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");
  let reason = searchParams.get("error_code") ?? searchParams.get("error") ?? "";
  if (code) {
    const supabase = await createClient();
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) return NextResponse.redirect(`${origin}/`);
    reason = error.code ?? error.message;
  }
  const q = reason ? `&reason=${encodeURIComponent(reason)}` : "";
  return NextResponse.redirect(`${origin}/login?e=link${q}`);
}
