# KayfabeQuery Build Plan

Every phase ends with something you can run and see working.
Security is not an afterthought — it is built in from Phase 1.

---

## Phase 0: Fix the Database — COMPLETE
**Goal:** The database is complete and correct before any agent code is written.

### 0A: Fix match duration — DONE
- ~~Add a `duration_seconds` INTEGER column to the `matches` table~~
- ~~Write a migration script that converts "18:05" → 1085 for every row~~
- 32,280 matches converted. Question 7 is now answerable.
- Script: `scripts/migrate_duration.py`

### 0B: Build the factions tables — DONE
- ~~Two new tables: `factions` and `faction_members`~~
- 39 factions seeded from Attitude Era through 2026
- All member cagematch_ids verified against live match_participants data
- Script: `scripts/seed_factions.py`

**Verified:** `SELECT ring_name FROM factions JOIN faction_members ... WHERE name = 'The Shield'` returns Roman Reigns, Seth Rollins, Dean Ambrose.

---

## Phase 1: Prove the Pipeline Works — COMPLETE
**Goal:** The full 5-step pipeline works in a test script. No UI. No Astro. Just TypeScript you can run in the terminal and see a real answer come back.**
**This is where you learn what an AI agent actually does — by making it work yourself, step by step.**

### 1A: Set up the Astro project — DONE
- ~~`npm create astro@latest` with server mode~~
- ~~Install dependencies: `@google/generative-ai`, `better-sqlite3`, `@types/better-sqlite3`~~
- ~~Create the `lib/` folder structure~~
- ~~`.env` with Gemini API key, `.env.example` committed~~
- Note: `data/kayfabe.db` is at project root, referenced as `../data/kayfabe.db` from app/

### 1B: Name resolution (`lib/resolveNames.ts`) — DONE
- Takes a string ("Steve Austin", "The Usos", "The Shield")
- Checks factions table first, early return if matched
- Falls back to match_participants for individual wrestler lookup
- Returns: `{ ids: number[], displayNames: string[] }`
- User input never interpolated into SQL string

### 1C: SQL generation (`lib/generateSQL.ts`) — DONE
- Makes the first Gemini API call
- Sends: compressed schema + resolved IDs + user question
- Prompt rules: SELECT only, use IDs not names, always LIMIT, no_data fallback
- Returns: `{ sql: string, error: string }`
- try/catch on API call, never crashes pipeline

### 1D: SQL validation (`lib/validateSQL.ts`) — DONE
- Pure code. No AI involved.
- Blocks: INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, RENAME, ANALYZE, DETACH, PRAGMA, REPLACE, ATTACH
- Enforces: query must start with SELECT
- Enforces: must contain LIMIT
- Returns: `{ valid: boolean, sql: string, error: string }`

### 1E: Query execution (`lib/executeQuery.ts`) — DONE
- Opens SQLite with `{ readonly: true }`
- Runs the validated SQL
- Returns: `{ rows: object[], error: string }`
- try/catch returns clean error instead of crashing

### 1F: Result formatting (`lib/formatAnswer.ts`) — DONE
- Makes the second Gemini API call
- Sends: original question + SQL that ran + result rows
- Prompt: warm wrestling fan voice, honest about Jan 2026 data limit
- Rules: no outside knowledge, note small samples, end with record count
- Returns: `ReadableStream` — labeled envelopes: chunk, done, error
- streams word by word instead of waiting for the full response

### 1G: Test script (`app/scripts/testPipeline.ts`) — DONE
- 17/17 assertions passing across 3 sections: pure logic, DB only, full pipeline
- Tests question: "How many matches did Stone Cold Steve Austin win at WrestleMania?"
- Ground truth verified: Steve Austin has 6 WrestleMania wins in the DB
- Run with: `npm test` from inside `app/`

**Completed 2026-04-13:** 17/17 assertions passing. "Stone Cold Steve Austin won 6 matches at WrestleMania" — correct answer, verified against ground truth query. Pipeline is real.

---

## Phase 2: The Secure API Route - COMPLETE
**Goal:** The pipeline moves into an Astro server endpoint. It is rate-limited, secure, and ready for a frontend to call.**
**This is where the security you built in Phase 1 gets wrapped in production-grade protections.**

### Phase 2 Prep Notes (start here next session) - DONE
- Phase 1 pipeline is committed and pushed to GitHub
- All 5 lib functions are in `app/src/lib/`
- `gemini.ts` is the single entry point for the AI client — update model name there if needed
- Current model: `gemini-2.5-flash` (paid tier, Kayfabe Query project)
- SCHEMA constant lives in `app/scripts/testPipeline.ts` — needs to be moved to `app/src/lib/schema.ts` before Phase 2 so both the test script and the API endpoint share it
- `npm test` from inside `app/` runs the full 17-assertion test suite
- First task in Phase 2: create `src/pages/api/query.ts` and wire the pipeline into it

### 2A: The endpoint (`src/pages/api/query.ts`) - DONE
- Accepts: `POST` with `{ question: string }`
- Rejects: missing question, question over 500 characters, non-POST methods
- Runs the full Phase 1 pipeline
- Returns: `{ answer: string, sql: string, rowCount: number, dataWindow: string }`
  - `rowCount` powers the provenance strip ("Based on 847 matches")
  - `dataWindow` is always "WWE 1971 through January 2026"
- All Gemini API keys are server-side only — never sent to the browser

### 2B: Rate limiting - DONE
- IP-based: 10 requests per minute per IP address
- In-memory store (simple Map, resets on server restart)
- Returns HTTP 429 with a clear message if exceeded
- **Why this matters:** Gemini Flash is free tier. Without rate limiting, one bad actor drains your daily token budget in minutes.

### 2C: Streaming - DONE
- Convert the endpoint to stream the formatted answer back word by word
- The SQL generation and execution steps still complete fully before streaming starts
- Only the final human-readable answer streams
- Uses the Web Streams API built into Astro

**Done when:** You can `curl` the endpoint with a wrestling question and see a streaming answer come back. The database is still safe — test by trying to send `DROP TABLE wrestlers` in a question and confirming it gets blocked.

### Phase 2C: COMPLETE — 2026-04-21
19/19 assertions passing. Streaming verified. Labeled envelope format confirmed working.

---

## Phase 3: The Supervisor Harness (Harness Engineering)
**Goal:** Transform the pipeline from an unpredictable "Black Box" into a deterministic "Harness." You lead the execution. I provide the logic maps.

---

### 3A: Standardized Envelopes (Principle 8)
**Status:** In Progress

#### The Problem
Currently, our `lib/` functions return raw data. If a function returns an empty set or an error, the rest of the pipeline is "flying blind." It doesn't know *why* the failure happened (e.g., was it a DB error or just no matches?).

#### The Solution: `HarnessResult<T>`
We wrap every result in a standard "Metal" envelope. This ensures the system is **Observable**. We don't guess; we read the `success` flag and the `trace` log.

#### Implementation Checklist
1. [ ] **Update `lib/schema.ts`**: Define the `HarnessResult<T>` interface.
2. [ ] **Refactor `lib/resolveNames.ts`**:
   - Change return type to `HarnessResult`.
   - Add `trace` logging for faction and wrestler scanning steps.
   - Wrap in `try/catch` for deterministic error reporting.

---

### 3B: Whitelist Validator (Principle 4 & 9)
**Status:** Pending

#### The Problem
The current `validateSQL.ts` uses a "Blacklist" (blocking `DROP`, `DELETE`). Blacklists are inherently leaky—there is always a clever way to bypass them (e.g., `ATTACH DATABASE`).

#### The Solution: Whitelist Enforcement
We move from "Magic" (trying to catch bad words) to "Metal" (only allowing good words). If a keyword isn't on the approved list (e.g., `SELECT`, `JOIN`, `LIMIT`), the query is physically blocked.

#### Implementation Checklist
1. [ ] **Define Whitelist**: Create a strict constant of allowed SQLite keywords.
2. [ ] **Refactor `lib/validateSQL.ts`**:
   - Strip all non-whitelisted characters/words.
   - Enforce the "SELECT only" rule at the parser level.

---

### 3C: Trajectory Controller (Principle 2)
**Status:** Pending

#### The Problem
If the AI generates a slightly wrong SQL syntax, the whole pipeline crashes. This is "False Infeasibility"—the task is possible, but the local strategy failed.

#### The Solution: The Orchestrator
We build a "Conductor" (`lib/orchestrator.ts`) that manages the pipeline flow. It can detect a syntax error, send it back for a "Lite" AI correction, and retry **once** before stopping.

#### Implementation Checklist
1. [ ] **Create `lib/orchestrator.ts`**: A central state machine to call each `lib` function.
2. [ ] **Implement Retry Logic**: Add one-shot correction for SQL syntax errors.
3. [ ] **Add `EXPLAIN QUERY PLAN`**: Use deterministic DB checks before running any query.

---

### 3D: Full Observability (Principle 5)
**Status:** Pending

#### The Problem
When the AI gives a weird answer, we have to guess what happened. We lack an "Audit Trail."

#### The Solution: Session Logging
Every interaction creates a `LOG-[TIMESTAMP].json` file. This is the "Receipt." It contains the raw input, the AI's first attempt, the validator's feedback, and the final result.

#### Implementation Checklist
1. [ ] **Build `lib/logger.ts`**: A utility to write JSON logs to a `logs/` directory.
2. [ ] **Integrate with Orchestrator**: Capture the `trace` from every `HarnessResult` into the final log.

---

### 3E: Integrity Test Suite (Validation)
**Status:** Pending

#### The Problem
We shouldn't trust that the harness works just because we wrote it.

#### The Solution: The Red Team Test
We write tests that intentionally try to break the system (e.g., passing a malicious question) to verify the Whitelist and Orchestrator catch it.

#### Implementation Checklist
1. [ ] **Create `tests/harness.test.ts`**: Dedicated suite for "Systems Integrity."
2. [ ] **Assert Failure**: Prove that `DROP TABLE` results in a clean `HarnessResult` error, not a DB crash.

---

## Phase 4: The Frontend
**Goal:** A real UI that makes the pipeline feel like a conversation.

### 4A: Page layout (`src/pages/index.astro`)
- Clean, centered layout
- Header with KayfabeQuery name and tagline
- Data disclaimer: "Covers WWE 1971 through January 2026"
- Chat area in the middle, input at the bottom
- Houses the streaming reader: `fetch` POST `/api/query`, `ReadableStream` reader,
  dispatches envelope types to component state
- **Note:** Frontend uses `fetch` with a streaming reader, not `EventSource` — the endpoint is POST

### 4B: Example questions (`src/components/ExampleQuestions.astro`)
Five questions decided before the component is written. Each one showcases a different
capability of the schema and produces a list, not a single number.

**The five questions (final):**
1. "What are the highest rated matches in WrestleMania history?" — ratings + show_series filtering
2. "Who has won the most matches at WrestleMania?" — match_participants leaderboard, fans will argue with it
3. "What are the five longest title reigns in WWE history?" — title_reigns, Bruno's ~2,800-day reign will surprise people
4. "Which wrestlers have the most submission victories?" — win_type column, Bret/Angle/Benoit will surface
5. "How has average match quality changed by year?" — rating_num by year, literally shows the Attitude Era and the modern renaissance

Component behaviour: clickable chips that pre-fill the input. Disappear after the user submits their first question — they've found their footing, the training wheels come off.

### 4C: Chat messages (`src/components/ChatMessage.astro`)
- User question right, agent answer left
- SQL drawer collapsed below every answer by default, expandable ("How I found this")
  - SQL renders in a `<pre>` block, copyable
  - Proves the answer is real, not hallucinated
  - Shows any technical interviewer exactly what the agent generated

### 4D: Chat input (`src/components/ChatInput.astro`)
- Single text input + send button
- Disabled while streaming (re-enabled on `done` or `error` envelope)
- Clears after submission
- Keyboard accessible: Enter submits, Escape clears

### 4E: Data provenance strip (`src/components/DataProvenance.astro`)
- Renders as soon as the `metadata` envelope arrives — before the answer text starts streaming
- `rowCount` and `dataWindow` come from that first envelope, not the end
- Shows: "Based on 847 matches" + "WWE 1971 through January 2026"
- Empty result variant: "No matches found — this may be more recent than our data covers"
- **Why this matters:** Showing the row count proves the answer came from real data. No other portfolio SQL agent will have this. It's the difference between a demo and a tool people can trust.

### 4F: "What can I ask?" helper (`src/components/WhatCanIAsk.astro`)
- Decide format before building: modal, slide-out panel, or inline collapse
- Content: time range (1971–Jan 2026), promotions covered, question categories
  (match history, title reigns, ratings, win types, factions, head-to-head)
- Honest about limits: no post-January 2026, no AEW/NJPW, gender covers ~1,450 of 4,135 wrestlers
- Respects the user's time — they know what to ask and what not to expect before they type anything

### 4G: Two-phase loading state
- Phase A ("Thinking..."): from submission until the `metadata` envelope arrives
- Phase B: answer streams in word by word, from `metadata` until `done`
- `metadata` envelope is the transition trigger: SQL drawer and provenance strip render immediately,
  answer text starts appending with the first `chunk` envelope
- `done` envelope: re-enables input, clears loading state
- No blank white screen at any point

**Done when:** You open the browser, click an example question, watch the SQL drawer and provenance strip appear before the answer starts, read the answer stream in word by word, and can expand the SQL to see exactly how it was found. It feels like a conversation with someone who shows their work.

---

## Phase 5: Polish
**Goal:** The thing you show people. GSAP, accessibility, edge cases.**

### 5A: GSAP entrance animations
- Chat messages animate in smoothly
- Example questions stagger in on load
- Nothing jarring, everything purposeful

### 5B: Accessibility (WCAG AA)
- All interactive elements keyboard accessible
- Screen reader announcements for streaming answers
- Color contrast verified
- Focus management when messages appear

### 5C: Edge cases
- Question returns no results → warm explanation, not an empty screen
- Gemini API is down → clear message, not a stack trace
- Rate limit hit → friendly message with a wait time
- Question is not about wrestling → "I only know about WWE wrestling. Try asking about..."

---

## Security Summary

| Threat | Defense | Where |
|---|---|---|
| User deletes data via SQL | Read-only SQLite connection | `executeQuery.ts` |
| LLM generates destructive SQL | Keyword validator + SELECT check | `validateSQL.ts` |
| SQL injection from user input | Parameterized queries in name resolution | `resolveNames.ts` |
| API key exposure | Server-side only, never in browser | Astro server endpoints |
| Free tier abuse / DoS | IP rate limiting | `query.ts` |
| Off-topic questions | System prompt guardrails + no matching tables | `generateSQL.ts` |

---

## The Order That Matters

```
Phase 0A → 0B → 1A → 1B → 1C → 1D → 1E → 1F → 1G
                ↓
           Does the pipeline produce correct answers?
           If yes → Phase 2
           If no → fix before moving on
                ↓
           Phase 2A → 2B → 2C
                ↓
           Is the pipeline secure and streaming?
           If yes → Phase 3
                ↓
           Phase 3A → 3B → 3C → 3D → 3E
                ↓
           Is the Harness observing and correcting?
           If yes → Phase 4
                ↓
           Phase 4A → 4B → 4C → 4D → 4E
                ↓
           Does it feel like a real product?
           If yes → Phase 5
```

Never skip a phase. The test script in Phase 1G is not optional.
If the pipeline doesn't work in the terminal, it won't work in the browser.
