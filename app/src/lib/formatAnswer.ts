/**
 * src/lib/formatAnswer.ts
 *
 * Second Gemini API Call.
 * Takes the raw database rows and turns them int oa plain English answer wit ha warm conversational tone.
 *
 * @param question - the user's original question
 * @param sql - the SQL that ran
 * @param rows - the rows returned from  executeQuery
 * @returns { answer: string, error: string }
 */

import { getModel } from "./gemini";

export async function formatAnswer(question: string, sql: string, rows: object[]) {
  // Step 1: build the prompt
  const prompt = `
  You are a direct, knowledgeable analyst answering questions about WWE history. Give clear, accurate answers in plain English. No filler phrases, no excessive enthusiasm.
  The data covers WWE from 1971 to January 2026. Be honest if something may be more recent than that.
  If the results are empty, explain why — do not just say "no results found."
  Keep the tone warm and conversational, not robotic.

  Rules:
  - Only use the data in the results below. Do not use outside knowledge to fill gaps.
  - If results contain fewer than 3 rows, note that the sample is small.
  - End every answer with one sentence stating how many records this is based on.
  - If results are empty, say the data may not cover this or it may be after January 2026.

  Question: ${question}

  SQL that ran: ${sql}

  Results: ${JSON.stringify(rows, null, 2)}

  Answer the question in plain English based only on the results above.
  `;
  try {
    // Step 2: send prompt to Gemini
    const model = getModel();
    const result = await model.generateContent(prompt);
    // Step 3: return the answer
    return { answer: result.response.text().trim(), error: "" };
  } catch (err) {
    // Step 4: return error if prompt fails.
    return { answer: "", error: err instanceof Error ? err.message : "Gemini API call failed" };
  }
}
