import Database from "better-sqlite3";
import type { HarnessResult } from "./schema";

/**
 * src/lib/executeQuery.ts
 * 
 * Goal: Run the safe SQL against our SQLite database.
 * Problem: Database files can lock or crash. We need to catch those errors.
 * Solution: A protected "Read-Only" execution zone.
 * 
 * @param sql - The validated SQL string
 * @returns HarnessResult - A box containing the raw data rows + the paper trail.
 */

// We open the DB once outside the function for performance.
const db = new Database("../data/kayfabe.db", { readonly: true });

export function executeQuery(sql: string): HarnessResult<{ rows: any[] }> {
  const trace: string[] = [];

  try {
    trace.push("Step 1: Preparing to execute SQL query...");
    
    // We use .all() to get all matching rows as an array.
    const rows = db.prepare(sql).all();
    
    trace.push(`Step 2: Successfully retrieved ${rows.length} rows from the database.`);

    return {
      success: true,
      data: { rows },
      trace
    };

  } catch (err: any) {
    // If the SQL is bad or the DB is locked, we catch the error here.
    return {
      success: false,
      data: null,
      error: "DATABASE_EXECUTION_FAILED",
      trace: [...trace, `Critical DB Error: ${err.message}`]
    };
  }
}
