/** DATA_SOURCE=fixtures reads web/fixtures/*.json instead of Supabase (local previews and screenshots only).
 *  Refused on Vercel production so it can never bypass the login. Kept free of Node APIs: the middleware imports it. */
export function usingFixtures(): boolean {
  return process.env.DATA_SOURCE === "fixtures" && process.env.VERCEL_ENV !== "production";
}
