# KayfabeQuery Decision Log

Every technical choice and the reasoning behind it.

---

## 001: Project Name - "KayfabeQuery"
**Date:** 2026-04-06
**Decision:** Named the project KayfabeQuery.
**Why:** Kayfabe is a wrestling term for maintaining the fiction as reality. The name is niche enough to be memorable, broad enough to be intriguing. It sounds like a product, not a homework assignment. It makes me laugh.

---

## 002: Frontend Framework - Astro
**Date:** 2026-04-07
**Decision:** Build the frontend in Astro with server mode, not Next.js.
**Why:** One codebase, one deployment, one developer. Astro handles API routes built in so there's no need for a separate backend server. Zero budget means I can't afford to manage two production environments. Astro's island architecture also means the page is static by default and only the chat interface is interactive, which is exactly what this app needs.

---

## 003: Database - SQLite + Turso
**Date:** 2026-04-07
**Decision:** SQLite for local development, Turso for hosting.
**Why:** SQLite is a file. No server, no credentials, no connection pool to manage. Turso puts that same file on their edge network for free (9GB storage, 1 billion reads/month). When the project needs to scale, I upgrade the Turso plan. The code doesn't change.

---

## 004: LLM - Gemini Flash
**Date:** 2026-04-07
**Decision:** Use Google's Gemini Flash via Google AI Studio.
**Why:** Zero budget. Gemini Flash is free (15 requests/minute, 1 million tokens/day). The LLM's job in KayfabeQuery is generating SQL queries, not writing poetry. It doesn't need to be the most powerful model. When budget allows, swapping to Claude or GPT-4 is one import and one API key change.

---

## 005: Data Source - TheSportsDB API
**Date:** 2026-04-07
**Decision:** Use TheSportsDB's free API as the primary data source. Not Kaggle, not Cagematch, not manually curated.
**Why:** Cagematch explicitly blocks scrapers (527 second crawl delay, /database/ disallowed in robots.txt). Kaggle datasets were incomplete and not mine. Manual curation doesn't scale. TheSportsDB is a free, legal API with a Creative Commons license and WWE data going back to 1984. One API call per season returns full match cards, results, venues, and match durations. One player lookup returns full bios, career history, and images. The data gets pulled once and loaded into SQLite. KayfabeQuery queries local data, not the API.

---

## 006: Schema - 5 Tables, 10 Questions
**Date:** 2026-04-07
**Decision:** Start with 5 tables: wrestlers, matches, match_participants, title_reigns, events. Designed to answer exactly 10 fan questions.
**Why:** Every table must earn its place by answering at least one of the 10 questions. No speculative tables. No designing for hypothetical future questions. When a real question comes along that the schema can't answer, that's when a new table gets added. Not before.

---

## 007: Phase 1 Definition of Done
**Date:** 2026-04-07
**Decision:** Phase 1 is complete when a user types a question about Shawn Michaels and gets back a simple, accurate summary pulled from real data.
**Why:** Needed a concrete definition of done to avoid endless planning. Not a feature list. One moment: question in, clear answer out. Everything else (animations, streaming, security hardening) comes after this moment exists.

---

## 008: Data Source for Events and Matches - Wikipedia
**Date:** 2026-04-09
**Decision:** Use Wikipedia PPV event pages as the primary source for events, matches, and match participants.
**Why:** I wanted the easy way out. I tried to find a dataset or API I could just port directly into SQLite. TheSportsDB was exciting until the 15-event limit killed it. I kept researching but nothing clean came up. Then it clicked: I didn't need an API. Wikipedia is open data. Python and BeautifulSoup are literally built for this: scrape a page, filter what matters, clean it, import it into SQLite. Having the schema already built gave me the confidence to know the script had a clear destination. One script, runs once, data is in. 568 WWE PPV events from 1985 to 2026, consistent Results table format verified across 3 decades and 2 event types, CC license, free public API.

---

## 009: TheSportsDB Scoped to Wrestlers Table Only
**Date:** 2026-04-09
**Decision:** Keep TheSportsDB but limit its use to populating the wrestlers table only. It does not provide event or match data.
**Why:** TheSportsDB's individual player lookup has no per-season limit and returns rich wrestler bios, physical stats, debut dates, and image URLs. That is exactly what the wrestlers table needs and what Wikipedia does not provide.

---

## 010: User Experience Goal - The Store Analogy
**Date:** 2026-04-09
**Decision:** The experience KayfabeQuery delivers is warm, fast, and human. Not robotic.
**Why:** Most people my age watched wrestling in the 90s and 00s. KayfabeQuery is for them. It's the alternative to Googling three different sources and stitching the answer together in your head. The experience I'm after is the feeling you get when you ask a question at a store and someone answers it quickly, clearly, and warmly. That human warmth is what I want to bring to the web. You have a question. You write it down. The answer comes back. The agent doesn't sound like a robot because it doesn't have to. AI gives us the tools to be warm and aware, not cold and mechanical. Wrestling is silly, but if you can build a SQL agent with wrestling knowledge that feels like a real conversation, you can do it for marketing data, company analytics, anything. That's the real point.

---

## 011: Data Source Pivot - Kaggle WWE SQLite
**Date:** 2026-04-10
**Decision:** Replaced Wikipedia scraping and TheSportsDB as primary data sources with a Kaggle SQLite dataset (`wwe_db_2026-01-18.sqlite`) containing Cagematch.net match data.
**Why:** Got rate-limited from Claude Code mid-session. Went back to Kaggle with a different search and found a SQLite file with every WWE show from 1971 to January 2026: 88,230 matches, Cagematch community star ratings, win types, and individual wrestler URLs with Cagematch IDs embedded. The first Kaggle search had turned up nothing useful. The second one changed everything. The Cagematch IDs in the match HTML were the key: they enabled exact-match enrichment via Wikidata P2728 (CageMatch worker ID), which is how we got gender, birth date, and nationality without guessing. Wikipedia scraping was 568 PPV events. This is 14,399 total shows. The schema and question count both grew as a result.

---

## 012: Duration Stored as Seconds (INTEGER), Not Text
**Date:** 2026-04-11
**Decision:** Added a `duration_seconds` INTEGER column to the `matches` table. Migration script converts "18:05" to 1085 on every row.
**Why:** The raw data stored duration as text like "18:05". You can't do math on text. To answer questions like "who has the most cumulative match time," SQL needs numbers. Converting to seconds at import time means every future query is simple addition. Leaving it as text would require parsing the string inside every SQL query, which is fragile and slow. Store data in the format you need to calculate with, not the format it arrived in.

---

## 013: Factions as a Separate Table, Not LIKE Queries
**Date:** 2026-04-11
**Decision:** Created two new tables: `factions` and `faction_members`. 39 factions seeded from the Attitude Era forward, each with verified cagematch_ids.
**Why:** "The Shield" doesn't exist in the database. Only "Roman Reigns," "Seth Rollins," and "Dean Ambrose" do. A LIKE query on ring_name would miss wrestlers who used different names at different times and would return false matches for similar names. The factions table is a clean translation layer: faction name maps to exact cagematch_ids, which maps to every match those wrestlers ever had. Without this table, any question about a faction returns nothing or returns wrong results. The user never knows why. They just think the tool is broken.

---

## 014: Gemini Client — Single Entry Point
**Date:** 2026-04-13
**Decision:** Created `src/lib/gemini.ts` as the only place the Gemini client is initialized. Both `generateSQL` and `formatAnswer` import `getModel()` from here.
**Why:** Both functions need the same client. Duplicating the initialization means two places to update when the model name changes or the provider changes. One file means one change. The calling functions don't need to know anything about the provider — they just call `getModel()`. When Gemini releases a better model or we switch to Claude, it's a one-line change in one file.

---

## 015: process.env Over import.meta.env
**Date:** 2026-04-13
**Decision:** All environment variable access uses `process.env`, not `import.meta.env`.
**Why:** `import.meta.env` is Astro/Vite-specific syntax. It works inside the Astro build but returns undefined when running TypeScript directly with tsx. The test script runs outside Astro. `process.env` works in both contexts — Astro's server runtime and plain Node. Using `import.meta.env` in lib files would mean the pipeline can only be tested through the framework, which makes debugging harder and slower.

---

## 016: Test Script — Three Layers, Independent
**Date:** 2026-04-13
**Decision:** The pipeline test is structured in three sections: pure logic (no DB, no API), DB only (no API), then full pipeline (DB + API).
**Why:** If something breaks, you need to know which layer broke. A single end-to-end test that fails tells you nothing about where the failure is. Section 1 catches validation logic errors with no external dependencies. Section 2 catches database and name resolution issues without spending API tokens. Section 3 only runs if the foundation is solid. Running them in order also means the cheapest tests always run first.

---

## 017: Prompt Guardrails for Exact Column Values
**Date:** 2026-04-13
**Decision:** The SQL generation prompt explicitly lists the valid values for result ('win', 'loss', 'draw'), win_type ('pinfall', 'submission', 'DQ', 'count out'), and is_ppv (0 or 1). Show series names always use LIKE, never exact match.
**Why:** LLMs guess. When Gemini sees a column called result with no guidance, it generates 'winner' instead of 'win'. The query runs, returns 0 rows, and the answer says the wrestler has no wins. No error is thrown. The user just gets a wrong answer. Listing exact values in the prompt eliminates the guess. The database is the source of truth — the prompt has to reflect it precisely.

---

## 018: Rate Limit Set to 5 to Match Gemini Free Tier

**Date:** 2026-04-21
**Decision:** Set IP rate limit to 5 requests per minute, not 10.
**Why:** Gemini Flash free tier caps at 5 requests per minute per model. Setting our limit higher means requests 6-10 reach Gemini and fail anyway. Matching the limit stops the request before it wastes a round trip.
