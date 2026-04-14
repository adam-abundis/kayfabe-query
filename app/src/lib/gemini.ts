/**
 * src/lib/gemini.ts
 *
 * Single point of entry for Gemini API client.
 *
 * To swap models: update the model name string below.
 * To swap AI providers: replace GoogleGnerativeAI
 */

import { GoogleGenerativeAI } from "@google/generative-ai";

export function getModel() {
  // Step 1: verify API key.Gemini
  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey) {
    throw new Error("GEMINI_API_KEY is not set. Check your .env file. ");
  }
  // Step 2: initialize Gemini client with API key.
  const genAI = new GoogleGenerativeAI(apiKey);
  // Step 3: Return model instance.
  return genAI.getGenerativeModel({ model: "gemini-2.5-flash" });
}
