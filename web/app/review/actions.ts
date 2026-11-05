"use server";

import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { createClient } from "@/lib/supabase/server";
import { usingFixtures } from "@/lib/mode";

/** Server actions for the review queue. All decisions go through the database functions
 *  approve_proposal / reject_proposal, which check the caller's role and write the audit trail. */

function back(msg: string, kind: "ok" | "err" = "ok"): never {
  redirect(`/review?${kind}=${encodeURIComponent(msg)}`);
}

const str = (f: FormData, k: string) => String(f.get(k) ?? "").trim();

export async function approve(formData: FormData) {
  if (usingFixtures()) back("Preview mode: nothing is saved.", "err");
  const id = Number(formData.get("proposal_id"));
  const note = str(formData, "note");
  // Edits: only fields the reviewer actually changed are sent.
  const edits: Record<string, string | number | boolean | null> = {};
  for (const k of ["observed_on", "period", "base_case_version", "arrow", "source_code"]) {
    if (formData.has(`edit_${k}`) && str(formData, `edit_${k}`) !== str(formData, `orig_${k}`)) {
      edits[k] = str(formData, `edit_${k}`) || null;
    }
  }
  if (formData.has("edit_value") && str(formData, "edit_value") !== str(formData, "orig_value")) {
    const v = str(formData, "edit_value");
    if (v !== "" && Number.isNaN(Number(v))) back(`Proposal ${id}: the value must be a number.`, "err");
    edits.value = v === "" ? null : Number(v);
  }
  const supabase = await createClient();
  const { error } = await supabase.rpc("approve_proposal", { p_id: id, p_edits: edits, p_note: note || null });
  if (error) back(`Proposal ${id} not approved: ${error.message}`, "err");
  revalidatePath("/", "layout");
  back(`Proposal ${id} approved${Object.keys(edits).length ? " with your edits" : ""}.`);
}

export async function reject(formData: FormData) {
  if (usingFixtures()) back("Preview mode: nothing is saved.", "err");
  const id = Number(formData.get("proposal_id"));
  const note = str(formData, "note");
  if (!note) back(`Proposal ${id}: give a reason to reject it.`, "err");
  const supabase = await createClient();
  const { error } = await supabase.rpc("reject_proposal", { p_id: id, p_note: note });
  if (error) back(`Proposal ${id} not rejected: ${error.message}`, "err");
  revalidatePath("/review");
  back(`Proposal ${id} rejected.`);
}

export async function createManual(formData: FormData) {
  if (usingFixtures()) redirect("/review?err=" + encodeURIComponent("Preview mode: nothing is saved."));
  const [ticker, signal_code] = str(formData, "signal").split("|");
  const value = str(formData, "value");
  const withheld = formData.get("withheld") === "on";
  const fail = (m: string): never => redirect(`/review/new?err=${encodeURIComponent(m)}`);
  if (!ticker || !signal_code) fail("Choose a signal.");
  if (!withheld && (value === "" || Number.isNaN(Number(value)))) fail("Enter a number, or tick 'Withheld'.");
  for (const k of ["observed_on", "period", "base_case_version"]) if (!str(formData, k)) fail(`${k.replace(/_/g, " ")} is required.`);
  const payload: Record<string, string | number | boolean> = {
    observed_on: str(formData, "observed_on"),
    period: str(formData, "period"),
    base_case_version: str(formData, "base_case_version"),
    withheld,
  };
  if (!withheld) payload.value = Number(value);
  for (const k of ["arrow", "source_code", "notes"]) if (str(formData, k)) payload[k] = str(formData, k);
  const supabase = await createClient();
  const { error } = await supabase.from("proposals").insert({ kind: "observation", ticker, signal_code, payload, origin: "manual" });
  if (error) fail(`Not saved: ${error.message}`);
  revalidatePath("/review");
  redirect(`/review?ok=${encodeURIComponent(`Reading for ${ticker} ${signal_code} added to the queue.`)}`);
}
