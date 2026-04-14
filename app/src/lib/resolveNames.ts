/**
 * src/lib/resolveNames.ts
 *
 * Translate plain text intput into cagematch_ids the database can actually understand.
 * "Degeneration X" does not exist int he match data.
 * Only individual members do.
 *
 * @param input - String to be checked against the database
 * @returns { ids: number[], displayNames: string[] }
 *
 * The user input never gets pasted directly into a SQL string
 */

import Database from "better-sqlite3";

const db = new Database("../data/kayfabe.db", { readonly: true });

export function resolveNames(input: string) {
  // Step 1: check if input matches a faction name
  const faction = db.prepare("SELECT id FROM factions WHERE name LIKE ?").get(input) as
    | { id: number }
    | undefined;

  if (faction) {
    const members = db
      .prepare("SELECT cagematch_id, ring_name FROM faction_members WHERE faction_id = ?")
      .all(faction.id) as { cagematch_id: number; ring_name: string }[];
    return {
      ids: members.map((m) => m.cagematch_id),
      displayNames: members.map((m) => m.ring_name),
    };
  }

  // Step 2: check if input matches a wrestler name
  const wrestlers = db
    .prepare(
      "SELECT DISTINCT cagematch_id, ring_name FROM match_participants WHERE ring_name LIKE ?",
    )
    .all(`%${input}%`) as { cagematch_id: number; ring_name: string }[];

  if (wrestlers.length > 0) {
    return {
      ids: wrestlers.map((w) => w.cagematch_id),
      displayNames: wrestlers.map((w) => w.ring_name),
    };
  }

  // Step 3: if nothing found, return empty object
  return { ids: [], displayNames: [] };
}
