/**
 * src/pages/api/query.ts
 *
 * The single entry point between the browser and the pipeline.
 * A plain English question comes in, all 5 steps run in order,
 * a real answer backed by real data comes out.
 *
 * @param request - POST body containing { question: string }
 * @returns { answer: string, sql: string, rowCount: number, dataWindow: string }
 *
 * A failed step returns { error: string, detail: string } and stops the pipeline.
 * The browser uses the HTTP status code to know which shape it received.
 */

import type { APIRoute } from "astro";
import { resolveNames } from "../../lib/resolveNames";
import { generateSQL } from "../../lib/generateSQL";
import { validateSQL } from "../../lib/validateSQL";
import { executeQuery } from "../../lib/executeQuery";
import { formatAnswer } from "../../lib/formatAnswer";
import { SCHEMA } from "../../lib/schema";

export const POST: APIRoute = async ({ request }) => {
  // ------Input Guard---------------------
  // Parse and validate before we run the pipeline

  let question: string;

  try {
    const body = await request.json();
    question = body?.question?.trim() ?? "";
  } catch (err) {
    return new Response(JSON.stringify({ error: "Invalid JSON body" }), {
      status: 400,
      headers: { "content-type": "application/json" },
    });
  }

  if (!question) {
    return new Response(JSON.stringify({ error: "Question is required" }), {
      status: 400,
      headers: { "content-type": "application/json" },
    });
  }

  // 500 character limit protects the prompt from oversized input
  if (question.length > 500) {
    return new Response(JSON.stringify({ error: "question must be 500 characters or fewer" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  // ------Pipeline-------------------------
  // STEP 1: Resolve resolveNames
  // Scans the full question for known wrestler and faction names
  const wrestlerIds = resolveNames(question);

  // STEP 2: Generate SQL
  // First Gemini API call. Question + ids + schema -> a single SQL SELECT statement
  const rawSQL = await generateSQL(question, wrestlerIds.ids, SCHEMA);
  if (rawSQL.error) {
    return new Response(JSON.stringify({ error: "Failed to generate SQL", detail: rawSQL.error }), {
      status: 502,
      headers: { "Content-Type": "application/json" },
    });
  }

  // STEP 3: Validate SQL
  // Blocks anything that isn't a SELECT with a LIMIT. No data manipulation.
  const validatedSQL = validateSQL(rawSQL.sql);
  if (!validatedSQL.valid) {
    return new Response(
      JSON.stringify({ error: "Failed to validate SQL", detail: validatedSQL.error }),
      {
        status: 422,
        headers: { "Content-Type": "application/json" },
      },
    );
  }

  // STEP 4: Execute Query
  // creats a read-only SQLite connection and runs the validated SQL
  const rows = executeQuery(validatedSQL.sql);
  if (rows.error) {
    return new Response(JSON.stringify({ error: "Failed to execute query", detail: rows.error }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }

  // STEP 5: Format Answer
  // Second Gemini call. Raw rows → plain English answer.
  const formattedAnswer = await formatAnswer(question, validatedSQL.sql, rows.rows as object[]);
  if (formattedAnswer.error) {
    return new Response(
      JSON.stringify({ error: "Failed to format answer", detail: formattedAnswer.error }),
      { status: 502, headers: { "Content-Type": "application/json" } },
    );
  }

  // ------Response---------------------------
  // Return the answer, SQL, row count, and data window
  return new Response(
    JSON.stringify({
      answer: formattedAnswer.answer,
      sql: validatedSQL.sql,
      rowCount: rows.rows.length,
      dataWindow: "WWE 1971 through January 2026",
    }),
    { status: 200, headers: { "Content-Type": "application/json" } },
  );
};
