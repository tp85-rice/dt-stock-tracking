// Fails the build if advice wording appears in the app's own text (house rule: no price targets, no buy/sell).
// Run: npm run check:wording
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, extname } from "node:path";

const ROOTS = ["app", "components", "lib"];
const BANNED = [
  /\bbuy\b/i, /\bsell\b/i, /\bhold rating\b/i, /\bprice target/i, /\btarget price/i,
  /\bstrong buy\b/i, /\boutperform\b/i, /\bunderperform\b/i, /\boverweight\b/i, /\bunderweight\b/i,
  /\byou should (buy|sell|own)\b/i,
];
const bad = [];
function walk(dir) {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) walk(p);
    else if ([".ts", ".tsx", ".css", ".md"].includes(extname(p))) {
      readFileSync(p, "utf8").split("\n").forEach((line, i) => {
        if (/check-wording: allow/.test(line)) return;
        for (const re of BANNED) if (re.test(line)) bad.push(`${p}:${i + 1}: "${line.trim()}" matches ${re}`);
      });
    }
  }
}
ROOTS.forEach((r) => walk(r));
if (bad.length) {
  console.error("Advice wording found (house rule: no price targets, no buy/sell):\n" + bad.join("\n"));
  process.exit(1);
}
console.log(`check-wording: OK (${ROOTS.join(", ")})`);
