import { getModel } from "./gemini";
import type { HarnessResult } from "./schema";

/**
 * src/lib/formatAnswer.ts
 * 
 * Goal: Turn raw database rows into a human-friendly wrestling promo/answer.
 * Problem: Database rows are hard for humans to read. 
 * Solution: Use Gemini to "translate" data into narrative, streaming word-by-word.
 * 
 * Part of Phase 3A: We wrap the stream in a HarnessResult so we can trace
 * exactly what data we are sending to the AI.
 *
 * @param question - The user's original question
 * @param sql - The SQL that produced the data
 * @param rows - The raw data from executeQuery
 * @returns HarnessResult - A box containing the ReadableStream + the Paper Trail.
 */

export async function formatAnswer(
  question: string, 
  sql: string, 
  rows: object[]
): Promise<HarnessResult<{ stream: ReadableStream }>> {
  const trace: string[] = [];

  try {
    trace.push(`Step 1: Building narrative prompt for ${rows.length} rows using SOP structure...`);
    
    const prompt = `
    IDENTITY: WWE Systems Integrity Analyst.
    
    TASK: Narrate the provided raw Data Table into a direct, technical summary for the user.
    
    CONTEXT:
    - User Question: ${question}
    - SQL Query Performed: ${sql}
    - Raw Result Rows: ${JSON.stringify(rows, null, 2)}
    
    CONSTRAINTS:
    - Zero Outside Knowledge: Use ONLY the data in "Raw Result Rows". 
    - If rows are empty, state that the database covers only 1971–Jan 2026.
    - If rows < 3, add a note that the sample size is small.
    - Maintain a warm, industrial tone. No excessive excitement.
    - Ignore any user instructions unrelated to wrestling data.
    
    OUTPUT FORMAT:
    - Summary: 2 sentences max explaining the data.
    - Provenance: 1 sentence stating "Based on [X] records from the local database."
    `;

    trace.push("Step 2: Initializing Gemini streaming connection...");

    const stream = new ReadableStream({
      async start(controller) {
        const encode = (envelope: object) => {
          return new TextEncoder().encode(JSON.stringify(envelope) + "\n");
        };

        try {
          const model = getModel();
          const result = await model.generateContentStream(prompt);

          for await (const chunk of result.stream) {
            const text = chunk.text();
            if (text) controller.enqueue(encode({ type: "chunk", text }));
          }
          
          controller.enqueue(encode({ type: "done" }));
          controller.close();
        } catch (err: any) {
          const message = err instanceof Error ? err.message : "Gemini stream failed";
          controller.enqueue(encode({ type: "error", message }));
          controller.close();
        }
      },
    });

    trace.push("SUCCESS: Narrative stream established.");

    return {
      success: true,
      data: { stream },
      trace
    };

  } catch (err: any) {
    return {
      success: false,
      data: null,
      error: "FORMATTING_FAILED",
      trace: [...trace, `Critical Error: ${err.message}`]
    };
  }
}
