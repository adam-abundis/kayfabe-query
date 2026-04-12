# KayfabeQuery

> "The fiction is real. The data isn't."

A production-grade AI SQL agent for wrestling data. Type a question in plain English. Get real data back.

KayfabeQuery doesn't just return data. It gives wrestling fans something to argue with.

## The Pitch
Google search for wrestling. Non-technical users (and fans) ask questions naturally. The agent generates SQL, queries the database, returns results beautifully formatted.

## The Three Questions (foundation before any code)

**1. What problem does KayfabeQuery solve and for who?**
It solves the gap between having a wrestling question and getting an answer. The data exists but combining it yourself is too much work. KayfabeQuery does the combining for you and gives you a clear answer backed by real data.

**2. Why does this tech stack solve that problem better than alternatives?**
Astro lets me build the whole thing in one place and deploy it in one step. No two servers to connect, no two environments to manage. One developer, one codebase, one deployment.

**3. What does success look like at the end of Phase 1?**
A user types a question about Shawn Michaels. They get back a simple summary that respects their time. The answer is accurate and pulled from real data.

## Why It Exists
- Demonstrates full-stack AI integration without pretending to be an AI expert
- Shows production thinking: security, cost management, accessibility, error handling
- Built with genuine passion (Adam is a real wrestling fan who got frustrated with existing data sites)
- Memorable in interviews and on LinkedIn

## Stack
- **Frontend:** Astro (server mode) + TypeScript
- **Database:** SQLite locally, Turso for hosting (free tier)
- **LLM:** Gemini Flash via Google AI Studio (free tier)
- **Styling:** Tailwind 4 + GSAP for animations
- **Hosting:** Vercel or Cloudflare Pages (free tier)

## Constraints
- Zero budget to start
- Must be scalable (swap Turso plan, swap LLM provider without rewriting)
- WCAG AA accessible
- Streaming responses

## Security Requirements (non-negotiable)
- Read-only database access (SELECT only, enforced server-side)
- Prompt injection prevention
- Query validation before execution
- Rate limiting on the API route
- No raw SQL ever exposed to the client

## Phase 0: Data Foundation — COMPLETE
- ~~88,230 matches imported from Kaggle WWE SQLite~~ DONE
- ~~9 tables: promotions, show_series, shows, wrestlers, matches, match_participants, title_reigns, factions, faction_members~~ DONE
- ~~Wikidata gender enrichment (~1,450 wrestlers)~~ DONE
- ~~Wikipedia title reigns (683 reigns, 10 championships)~~ DONE
- ~~duration_seconds migration (32,280 matches converted)~~ DONE
- ~~39 factions seeded with verified cagematch_ids~~ DONE
- ~~16 questions the schema can answer~~ DONE

## Phase 1: Prove the Pipeline Works
Five TypeScript functions that solve the translation problem between human, AI, and database. No UI. Runs in the terminal. If it works here, it works in the browser.

1. `resolveNames` — human names → cagematch_ids (wrestlers + factions)
2. `generateSQL` — question + schema → SQL (Gemini call #1)
3. `validateSQL` — SQL → safe SQL (pure code, no AI)
4. `executeQuery` — safe SQL → rows (read-only SQLite)
5. `formatAnswer` — rows + question → human answer (Gemini call #2)

**Done when:** One command in the terminal returns a real, accurate, conversational answer to a real wrestling question.

## Phase 2: Secure API Route
- Astro server endpoint `POST /api/query`
- Rate limiting (10 req/min per IP)
- Streaming response
- API keys server-side only, never in the browser

## Phase 3: Frontend
- Chat UI with streaming responses
- Two-phase loading state ("Thinking..." then answer streams in)
- SQL visible and collapsible per answer ("How I found this") — proves the answer is real, not hallucinated
- Data provenance strip below every answer ("Based on 847 matches. Data covers WWE 1971 through January 2026") — honest about what the data is and where it ends
- "What can I ask?" helper — explains what the database contains, what kinds of questions work, and what the limits are
- 5 example questions on the opening screen — users shouldn't have to guess
- WCAG AA throughout

## Phase 4: Polish
- GSAP animations
- Edge case handling
- Full accessibility audit
- Deploy to Vercel or Cloudflare Pages

## Phase 3: Over the Top UX
- GSAP entrance animations
- Wrestler cards for profile results
- Stats tables with sorting
- Pre-built example queries
- Graceful error states
- Keyboard accessible throughout

## LinkedIn Content Plan
Every build decision is a post:
- "Why I chose Kayfabe as a project name"
- "Why I built this in Astro instead of Next.js"
- "How I prevented my AI agent from dropping my database"
- "What is a SQL injection and why your AI agent is vulnerable"
- "Streaming AI responses: why it matters for UX"
- "I hit the context window limit. Here's what that actually means"
- "I got rate limited, came back, and found a dataset that changed everything" — the pivot from Wikipedia scraping to 88k Cagematch matches

## Data Sources (final stack, as of April 2026)

**Kaggle WWE SQLite** (`wwe_db_2026-01-18.sqlite`) — the foundation. Cagematch.net data covering every WWE show from 1971 to January 2026: house shows, Raw, SmackDown, PPVs. 88,230 matches with star ratings, win types, durations, and individual Cagematch IDs per participant. This dataset replaced the Wikipedia scraping approach entirely.

**Wikidata SPARQL** — wrestler enrichment. Gender, birth date, and nationality matched via P2728 (CageMatch worker ID). Covers ~1,450 notable wrestlers.

**Wikipedia championship pages** — title_reigns table. 683 reigns across 10 championships scraped from Wikipedia history pages. The only data not in the Kaggle set.

**9 tables:** promotions, show_series, shows, wrestlers, matches, match_participants, title_reigns, factions, faction_members
**16 questions** answered (up from the original 10 — ratings data unlocked 6 more)

## Tagline Options
- "The fiction is real. The data isn't."
- "Ask anything. The data never lies."
- "Step inside the squared circle of data."
