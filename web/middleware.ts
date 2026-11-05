import { NextResponse, type NextRequest } from "next/server";
import { updateSession } from "@/lib/supabase/middleware";
import { usingFixtures } from "@/lib/mode";

export async function middleware(request: NextRequest) {
  // Fixture mode is for local previews only: no login, sample data from web/fixtures/.
  if (usingFixtures()) return NextResponse.next();

  // NEXT_PUBLIC_* values are baked in at build time. If they were missing when Vercel built the site,
  // say so plainly instead of crashing with MIDDLEWARE_INVOCATION_FAILED.
  // Each variable is referenced by its literal name: Next.js only inlines process.env.NEXT_PUBLIC_<NAME> written out.
  const missing: string[] = [];
  if (!process.env.NEXT_PUBLIC_SUPABASE_URL) missing.push("NEXT_PUBLIC_SUPABASE_URL");
  if (!process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY) missing.push("NEXT_PUBLIC_SUPABASE_ANON_KEY");
  if (missing.length) {
    return new NextResponse(
      `Site not configured: ${missing.join(" and ")} ${missing.length > 1 ? "are" : "is"} missing.\n\n` +
        "Add them in Vercel > Settings > Environment Variables for this environment " +
        "(Production and Preview), then redeploy. See docs/SETUP.md section 6.\n",
      { status: 503, headers: { "content-type": "text/plain; charset=utf-8" } },
    );
  }
  return updateSession(request);
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)"],
};
