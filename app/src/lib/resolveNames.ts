/**
 * src/lib/resolveNames.ts
 *
 * Goal: Convert plain text (e.g. "Steve Austin") into database IDs.
 * Why: The DB only understands numbers (cagematch_ids).
 *
 * Note: Factions like "Degeneration X" aren't in match data; we have to
 * find the faction, then find all its members.
 *
 * @param question - The user's full question string
 * @returns HarnessResult - A "Pizza Box" containing IDs + a "Trace" of how we found them.
 *
 * Security: User input is never pasted directly into a SQL string.
 */

import Database from "better-sqlite3";
import type { HarnessResult } from "./schema";

const db = new Database("../data/kayfabe.db", { readonly: true });

export function resolveNames(
  question: string,
): HarnessResult<{ ids: number[]; displayNames: string[] }> {
  const trace: string[] = [];
  const lower = question.toLowerCase();

  try {
    trace.push("Step 1: Scanning for group/faction names...");

    // Check if the question mentions a faction first
    const factionsList = db.prepare("SELECT id, name FROM factions").all() as {
      id: number;
      name: string;
    }[];
    const matchedFaction = factionsList.find((f) => lower.includes(f.name.toLowerCase()));

    if (matchedFaction) {
      trace.push(`Found faction match: "${matchedFaction.name}". Pulling members...`);

      const members = db
        .prepare("SELECT cagematch_id, ring_name FROM faction_members WHERE faction_id = ?")
        .all(matchedFaction.id) as { cagematch_id: number; ring_name: string }[];

      trace.push(`Resolved ${members.length} members for "${matchedFaction.name}".`);

      return {
        success: true,
        data: {
          ids: members.map((m) => m.cagematch_id),
          displayNames: members.map((m) => m.ring_name),
        },
        trace,
      };
    }

    trace.push("Step 2: No factions found. Looking for individual names...");

    // If no faction, look for individual names (e.g. "Stone Cold")
    const wrestlers = db
      .prepare(
        `SELECT DISTINCT cagematch_id, ring_name
         FROM match_participants
         WHERE LOWER(?) LIKE '%' || LOWER(ring_name) || '%'
         AND LENGTH(ring_name) > 4
         LIMIT 10`,
      )
      .all(lower) as { cagematch_id: number; ring_name: string }[];

    if (wrestlers.length > 0) {
      trace.push(`Resolved ${wrestlers.length} individual wrestler(s).`);
      return {
        success: true,
        data: {
          ids: wrestlers.map((w) => w.cagematch_id),
          displayNames: wrestlers.map((w) => w.ring_name),
        },
        trace,
      };
    }

    trace.push("Step 3: No names or factions found in our database.");
    return {
      success: true,
      data: { ids: [], displayNames: [] },
      trace,
    };
  } catch (err: any) {
    // Catch-all for database or code crashes
    return {
      success: false,
      data: null,
      error: "NAME_RESOLUTION_FAILED",
      trace: [...trace, `Critical Error: ${err.message}`],
    };
  }
}
