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

## Phase 1: Prove the Pipeline Works
**Goal:** The full 5-step pipeline works in a test script. No UI. No Astro. Just TypeScript you can run in the terminal and see a real answer come back.**
**This is where you learn what an AI agent actually does — by making it work yourself, step by step.**

### 1A: Set up the Astro project
- `npm create astro@latest` with server mode
- Install dependencies: `@google/generative-ai`, `better-sqlite3`, `@types/better-sqlite3`
- Copy `data/kayfabe.db` into the project
- Create the `lib/` folder structure

### 1B: Name resolution (`lib/resolveNames.ts`)
- Takes a string ("Steve Austin", "The Usos", "The Shield")
- Searches `match_participants` for matching ring names → returns cagematch_ids
- Searches `factions` table for team names → returns member cagematch_ids
- Returns: `{ ids: number[], displayNames: string[] }`
- **Security note:** This is read-only SQL. The user's text is parameterized, never interpolated into the query string. This prevents SQL injection.

### 1C: SQL generation (`lib/generateSQL.ts`)
- Makes the first Gemini API call
- Sends: compressed schema + resolved IDs + 4 few-shot examples + user question
- Returns: a SQL string
- The LLM's only job here is writing one SELECT statement

### 1D: SQL validation (`lib/validateSQL.ts`)
- Pure code. No AI involved.
- Blocks: INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, ATTACH
- Enforces: query must start with SELECT
- Enforces: must contain LIMIT
- Validates: only known table names are referenced
- **This is your primary security layer.** The read-only database connection is the backup.

### 1E: Query execution (`lib/executeQuery.ts`)
- Opens SQLite in read-only mode: `file:kayfabe.db?mode=ro`
- Runs the validated SQL
- Returns rows as JSON
- If the query errors, catches it and returns a clean error object

### 1F: Result formatting (`lib/formatAnswer.ts`)
- Makes the second Gemini API call
- Sends: original question + SQL that ran + result rows
- Instructs the LLM: warm, conversational, knowledgeable fan voice
- Instructs: data ends January 2026 — be honest if something may be more recent
- Instructs: if results are empty, explain why, don't just say "no results"
- Returns: a plain English answer string

### 1G: Test script (`scripts/testPipeline.ts`)
- Runs all 5 steps for 3 real questions
- Prints each step's output so you can see exactly what the LLM received and returned
- Run with: `npx tsx scripts/testPipeline.ts`

**Done when:** You run the test script, ask "How many matches did Stone Cold Steve Austin win at WrestleMania?" and get a real, accurate, conversational answer printed in your terminal.

---

## Phase 2: The Secure API Route
**Goal:** The pipeline moves into an Astro server endpoint. It is rate-limited, secure, and ready for a frontend to call.**
**This is where the security you built in Phase 1 gets wrapped in production-grade protections.**

### 2A: The endpoint (`src/pages/api/query.ts`)
- Accepts: `POST` with `{ question: string }`
- Rejects: missing question, question over 500 characters, non-POST methods
- Runs the full Phase 1 pipeline
- Returns: `{ answer: string, sql: string, rowCount: number, dataWindow: string }`
  - `rowCount` powers the provenance strip ("Based on 847 matches")
  - `dataWindow` is always "WWE 1971 through January 2026"
- All Gemini API keys are server-side only — never sent to the browser

### 2B: Rate limiting
- IP-based: 10 requests per minute per IP address
- In-memory store (simple Map, resets on server restart)
- Returns HTTP 429 with a clear message if exceeded
- **Why this matters:** Gemini Flash is free tier. Without rate limiting, one bad actor drains your daily token budget in minutes.

### 2C: Streaming
- Convert the endpoint to stream the formatted answer back word by word
- The SQL generation and execution steps still complete fully before streaming starts
- Only the final human-readable answer streams
- Uses the Web Streams API built into Astro

**Done when:** You can `curl` the endpoint with a wrestling question and see a streaming answer come back. The database is still safe — test by trying to send `DROP TABLE wrestlers` in a question and confirming it gets blocked.

---

## Phase 3: The Frontend
**Goal:** A real UI that makes the pipeline feel like a conversation.**

### 3A: Page layout (`src/pages/index.astro`)
- Clean, centered layout
- Header with KayfabeQuery name and tagline
- Data disclaimer: "Covers WWE 1971 through January 2026"
- The chat area in the middle
- Input at the bottom

### 3B: Example questions (`src/components/ExampleQuestions.astro`)
- 5 clickable questions that pre-fill the input
- Selected based on the 16 questions that best showcase the data
- Disappear once the user starts asking their own questions

### 3C: Chat messages (`src/components/ChatMessage.astro`)
- User question displayed on the right
- Agent answer displayed on the left
- Clean, readable typography
- The generated SQL collapsed below every answer by default, expandable ("How I found this")
  - This proves the answer is real, not hallucinated
  - Shows any technical interviewer exactly what the agent generated
  - One of the clearest signals that this is a production-grade tool, not a demo

### 3D: Chat input (`src/components/ChatInput.astro`)
- Single text input with a send button
- Disabled while a response is streaming
- Clears after submission
- Keyboard accessible: Enter submits, Escape clears

### 3E: Data provenance strip (`src/components/DataProvenance.astro`)
Every answer includes a small honest strip below it:
- Row count: "Based on 847 matches in the database"
- Data window: "Data covers WWE 1971 through January 2026"
- If results are empty: "No matches found — this may be more recent than our data covers"
- This is not a disclaimer tucked in fine print. It is part of the answer.
- **Why this matters:** AI hallucination is a known problem. Showing the data source and row count proves the answer came from real data. No other portfolio SQL agent will have this. It also shows you understand the difference between a demo and a tool people can trust.

### 3F: "What can I ask?" helper (`src/components/WhatCanIAsk.astro`)
- A collapsible panel explaining what data is available
- Covers: time range (1971-Jan 2026), promotions covered, what kinds of questions work
- Lists question categories: match history, title reigns, ratings, win types, factions, head-to-head
- Is honest about limitations: no post-January 2026, no AEW/NJPW, gender data covers ~1,450 of 4,135 wrestlers
- This respects the user's time. They know immediately what to ask and what not to expect.

### 3H: Two-phase loading state
- Phase A ("Thinking..."): while name resolution + SQL generation + execution runs
- Phase B: answer streams in word by word
- No blank white screen at any point

**Done when:** You open the browser, click an example question, watch an answer stream in with a data provenance strip below it, and can expand the SQL to see exactly how it was found. It feels like a conversation with someone who shows their work.

---

## Phase 4: Polish
**Goal:** The thing you show people. GSAP, accessibility, edge cases.**

### 4A: GSAP entrance animations
- Chat messages animate in smoothly
- Example questions stagger in on load
- Nothing jarring, everything purposeful

### 4B: Accessibility (WCAG AA)
- All interactive elements keyboard accessible
- Screen reader announcements for streaming answers
- Color contrast verified
- Focus management when messages appear

### 4C: Edge cases
- Question returns no results → warm explanation, not an empty screen
- Gemini API is down → clear message, not a stack trace
- Rate limit hit → friendly message with a wait time
- Question is not about wrestling → "I only know about WWE wrestling. Try asking about..."

### 4D: The five example questions (to decide together)
These should show off the best of what the database can do.
Candidates:
- "What are the highest rated matches in WrestleMania history?"
- "How many days did CM Punk hold the WWE Championship?"
- "Who has the most submission victories in WWE history?"
- "What were The Shield's most important matches?"
- "How did women's wrestling change between 2015 and 2020?"

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
           Is the endpoint secure and streaming?
           If yes → Phase 3
                ↓
           Phase 3A → 3B → 3C → 3D → 3E
                ↓
           Does it feel like a real product?
           If yes → Phase 4
```

Never skip a phase. The test script in Phase 1G is not optional.
If the pipeline doesn't work in the terminal, it won't work in the browser.
