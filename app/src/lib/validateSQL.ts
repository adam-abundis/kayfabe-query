/**
 * src/lib/validateSQL.ts
 *
 * validates the SQL string from generatedSQL
 * Goes through multiple checks to ensure it is a proper SELECT statement.
 * No AI involved.
 *
 * @param sql - SQL sttring from generateSQL
 * @returns { valid: boolean, sql: string, error: string }
 */

export function validateSQL(sql: string) {
  // Step 1: make sure it starts with SELECT
  //   if not, return errror
  const upper = sql.trim().toUpperCase();
  if (!upper.startsWith("SELECT")) {
    return { valid: false, sql: "", error: "Query must start with SELECT" };
  }

  // Step 2: check for dangerous keywords
  //   block: INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, RENAME, ANALYZE, DETACH, PRAGMA, REPLACE, ATTACH
  //   if found, return error
  const blockedWords = [
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "CREATE",
    "TRUNCATE",
    "RENAME",
    "ANALYZE",
    "DETACH",
    "PRAGMA",
    "REPLACE",
    "ATTACH",
  ];
  for (const keyword of blockedWords) {
    if (upper.includes(keyword)) {
      return { valid: false, sql: "", error: `Blocked keyword: ${keyword}` };
    }
  }

  // Step 3: make sure it has a LIMIT clause
  //   if not, return error
  if (!upper.includes("LIMIT")) {
    return { valid: false, sql: "", error: "Query must include LIMIT" };
  }
  //Step 4: all checks passed
  //   return SQL as safe
  return { valid: true, sql: sql.trim(), error: "" };
}
