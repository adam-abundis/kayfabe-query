# 60-30-10 Architecture: KayfabeQuery

This document outlines the architectural balance of KayfabeQuery. The goal is a production-grade AI tool built on a $0 budget by prioritizing engineering logic over expensive AI services.

## The Ratio
*   **60% Traditional Code:** Database migrations, Astro API routing, streaming response handling, and read-only SQLite connections.
*   **30% Smart Logic:** Deterministic name resolution, safety validators, local-first throttling, and context-aware error handling.
*   **10% AI Processing:** Targeted translation of natural language to SQL and raw data to human narrative.

---

## Zero-Cost Optimization Strategy

### 1. Deterministic Name Resolution (The "Referee's Review")
*   **Logic (30%):** Prioritize exact SQL `LIKE` matches in `resolveNames.ts` for speed and cost-efficiency.
*   **AI Fallback (10%):** If SQL returns zero matches, use a lightweight LLM call to compare the user's input against a list of top 20 stars. 
*   **Outcome:** Handles user typos without failing the pipeline or requiring expensive fuzzy-search libraries.

### 2. Client-Side Throttling (The "Local Lock")
*   **Platform (60%):** Utilize the browser's `localStorage` to persist state across sessions.
*   **Logic (30%):** Store a timestamp of the last successful query. If a new query is attempted within 10 seconds, disable the UI and show a countdown.
*   **Outcome:** Protects Gemini API quotas from accidental or malicious spam without the cost of a centralized Redis instance.

### 3. Embedded Knowledge (The "Bio Search")
*   **Platform (60%):** Utilize the built-in SQLite `FTS5` (Full-Text Search) engine.
*   **Logic (30%):** Store wrestler bios in a dedicated SQLite table. Query this table for keyword matches to inject context into the final `formatAnswer` prompt.
*   **Outcome:** Provides Retrieval-Augmented Generation (RAG) capabilities for biographical questions with zero infrastructure cost.

### 4. Branded Error States (The "Promo Engine")
*   **Logic (30%):** Map standard HTTP status codes to wrestling-themed "Promos" to maintain immersion.
    *   **429 (Rate Limit):** "The crowd is too loud! Give the ring 10 seconds to clear."
    *   **500 (Server Error):** "Bah Gawd! The server just went through a Spanish Announce Table!"
    *   **Empty Results:** "This match ended in a double count-out. No data found for that period."
*   **Outcome:** Turns technical failures into a deliberate part of the "Industrial" UX.

---

## Senior Architectural Rationales
When presenting this architecture, use these technical justifications:

1.  **"Edge Throttling":** Implementing rate limiting at the client layer to minimize server-side compute and protect API quotas.
2.  **"Layered Resolution":** A tiered strategy that prioritizes deterministic database lookups before falling back to probabilistic LLM resolution.
3.  **"Native Retrieval":** Leveraging embedded SQLite Full-Text Search for context injection, eliminating the latency and cost of external vector stores.
