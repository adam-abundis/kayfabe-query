/**
 * src/lib/executeQuery.ts
 *
 * Runs validated SQL against the database in read-only mode.
 *
 * @param sql - SQL string from validateSQL
 * @returns { rows: object[], error: string }
 */

import Database from "better-sqlite3";

export function executeQuery(sql: string) {
  // Step 1: open database in read-only mode
  const db = new Database("../data/kayfabe.db", { readonly: true });

  try {
    // Step 2: run the SQL query
    //   return rows as an array of objects
    const rows = db.prepare(sql).all();
    return { rows: rows, error: "" };
  } catch (err) {
    // Step 3: if the query errors
    //   return a clean error object
    return { rows: [], error: err instanceof Error ? err.message : "Query failed" };
  }
}
