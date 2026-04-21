/**
 * src/lib/resolveNames.ts
 *
 * Translate plain text intput into cagematch_ids the database can actually understand.
 * "Degeneration X" does not exist int he match data.
 * Only individual members do.
 *
 * @param question - The user's full question string
 * @returns { ids: number[], displayNames: string[] }
 *
 * The user input never gets pasted directly into a SQL string
 */

import Database from "better-sqlite3";
const db = new Database("../data/kayfabe.db", { readonly: true });

export function resolveNames(question: string) {
  const lower = question.toLowerCase();

  // Step 1: scan question for faction names
  const factions = db
    .prepare("SELECT id, name FROM factions WHERE LOWER(name) = LOWER(?)")
    .all(question) as { id: number; name: string }[];
  // Try each faction name against the question
  const matchedFaction = (
    db.prepare("SELECT id, name FROM factions").all() as { id: number; name: string }[]
  ).find((f) => lower.includes(f.name.toLowerCase()));

  if (matchedFaction) {
    const members = db
      .prepare("SELECT cagematch_id, ring_name FROM faction_members WHERE faction_id = ?")
      .all(matchedFaction.id) as { cagematch_id: number; ring_name: string }[];
    return {
      ids: members.map((m) => m.cagematch_id),
      displayNames: members.map((m) => m.ring_name),
    };
  }

  // Step 2: check if input matches a wrestler name
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
    return {
      ids: wrestlers.map((w) => w.cagematch_id),
      displayNames: wrestlers.map((w) => w.ring_name),
    };
  }

  // Step 3: if nothing found, return empty object
  return { ids: [], displayNames: [] };
}
