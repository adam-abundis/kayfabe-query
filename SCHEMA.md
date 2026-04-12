# KayfabeQuery Database Schema

This file defines every table in the database. Each table has:
- What it stores
- Which of the 16 questions it helps answer
- The exact columns with types and where the data comes from

## Data Sources

- **Cagematch.net via Kaggle** (`wwe_db_2026-01-18.sqlite`): promotions, show_series, shows, matches, match_participants, and the core wrestlers table. Covers all WWE shows from 1971 to January 2026, including house shows, Raw, SmackDown, and PPVs. 88,230 matches total.
- **Wikidata SPARQL (P2728)**: gender, birth_date, nationality enrichment for wrestlers. Matched via CageMatch worker ID property. Covers ~1,450 notable wrestlers.
- **Wikipedia championship history pages**: title_reigns table. 683 reigns across 10 active championships, 1971 to present.

---

## Table 1: promotions

**What it stores:** The 6 WWE brand promotions in the dataset (WWE, WWF, WCW, ECW, NXT, etc.)

**Answers questions:** context for shows

| Column | Type | Source | Why |
|---|---|---|---|
| id | INTEGER | Cagematch | Primary key, links to show_series and shows |
| name | TEXT | Cagematch | Promotion name ("WWE", "WWF", "NXT") |

---

## Table 2: show_series

**What it stores:** Event brands — the named series a show belongs to. WrestleMania is a show_series. Raw is a show_series. SummerSlam is a show_series. There are 6,046 distinct series.

**Answers questions:** 4, 12

| Column | Type | Source | Why |
|---|---|---|---|
| id | INTEGER | Cagematch | Primary key |
| name | TEXT | Cagematch | Series name ("WrestleMania", "Monday Night Raw") |
| promotion_id | INTEGER | Cagematch | Links to promotions table |

---

## Table 3: shows

**What it stores:** One row per individual show. 14,399 shows from 1971 to January 2026.

**Answers questions:** 4, 12, 14, 15

| Column | Type | Source | Why |
|---|---|---|---|
| id | INTEGER | Cagematch | Primary key, links to matches |
| show_series_id | INTEGER | Cagematch | Which event brand this show belongs to |
| promotion_id | INTEGER | Cagematch | Which promotion ran the show |
| event_date | DATE | Cagematch | When it happened — enables date-range filtering |
| location | TEXT | Cagematch | City/region name |
| venue | TEXT | Cagematch | Arena name ("Madison Square Garden") |
| is_ppv | INTEGER | Parsed from info_html | 1 = pay-per-view, 0 = TV or house show |
| attendance | INTEGER | Parsed from info_html | Crowd size when available |

---

## Table 4: wrestlers

**What it stores:** One row per unique wrestler who appeared in at least one match. 4,135 wrestlers total.

**Answers questions:** 1, 2, 5, 6, 10

| Column | Type | Source | Why |
|---|---|---|---|
| id | INTEGER | Cagematch | Primary key |
| cagematch_id | INTEGER | Parsed from match_html URLs | Foreign key into Cagematch. Links wrestlers to Wikidata enrichment. |
| ring_name | TEXT | Cagematch | The name they used in the ring |
| gender | TEXT | Wikidata P2728 | "male", "female", "trans woman" — needed for question 10. ~1,450 wrestlers enriched. |
| birth_date | DATE | Wikidata P2728 | Career era context |
| nationality | TEXT | Wikidata P2728 | Where they are from |

---

## Table 5: matches

**What it stores:** One row per match. 88,230 matches total.

**Answers questions:** 2, 6, 7, 11, 12, 13, 14, 16

| Column | Type | Source | Why |
|---|---|---|---|
| id | INTEGER | (generated) | Primary key |
| show_id | INTEGER | Cagematch | Links match to its show |
| match_order | INTEGER | Parsed from match_html | Position on the card (1 = opener, higher = main event) |
| win_type | TEXT | Parsed from match_html | "pinfall", "submission", "DQ", "count out", etc. — needed for question 13 |
| duration | TEXT | Parsed from match_html | Match length as text ("18:05") — kept for display |
| duration_seconds | INTEGER | Migrated from duration | Match length as total seconds (1085). Used for all time calculations — question 7 |
| match_type | TEXT | Parsed from match_html | "Battle Royal", "Ladder Match", etc. NULL for standard singles/tag |
| title | TEXT | Parsed from match_html | Championship name if this was a title match |
| is_title_match | INTEGER | Derived from title column | 1 if title/championship/belt mentioned |
| title_change | INTEGER | Derived from title column | 1 if "title change" mentioned |
| rating | TEXT | Parsed from match_html | Raw star rating text ("***½", "DUD") |
| rating_num | REAL | Parsed from match_html | Numeric rating for sorting (3.5, 0.0, -1.0). Cagematch community ratings. |

---

## Table 6: match_participants

**What it stores:** One row per person per match. 246,878 rows total. This is the join table that connects wrestlers to their matches.

**Answers questions:** 2, 5, 6, 7, 8, 10, 13, 14

| Column | Type | Source | Why |
|---|---|---|---|
| id | INTEGER | (generated) | Primary key |
| match_id | INTEGER | (from parent match) | Links to matches table |
| cagematch_id | INTEGER | Parsed from match_html href | Links to wrestlers table |
| ring_name | TEXT | Parsed from match_html | Name as displayed in that specific match |
| result | TEXT | Derived from win/loss position | "win", "loss", or "draw" |

---

## Table 7: title_reigns

**What it stores:** One row per championship reign. 683 reigns across 10 titles, from 1971 to present.

**Answers questions:** 1, 3, 8, 9

**Source:** Scraped from Wikipedia championship history pages. Titles covered: WWE Championship, Universal Championship, Women's Championship, SmackDown Women's, Raw Women's, Intercontinental, United States, Raw Tag Team, SmackDown Tag Team, WWF Tag Team (1971-2002).

| Column | Type | Source | Why |
|---|---|---|---|
| id | INTEGER | (generated) | Primary key |
| wrestler_name | TEXT | Wikipedia | Who held the title |
| wrestler_id | INTEGER | (unlinked) | Not yet matched to wrestlers table |
| title_name | TEXT | Wikipedia | "WWE Championship", "Intercontinental Championship", etc. |
| won_date | DATE | Wikipedia | When the reign started |
| lost_date | DATE | Wikipedia | When the reign ended (NULL = current champion) |
| days_held | INTEGER | Wikipedia | Length of reign — question 9 |
| won_event | TEXT | Wikipedia | Where they won it |
| lost_to | TEXT | Wikipedia | Who ended the reign |

---

## Table 8: factions

**What it stores:** 39 named WWE factions and stables from the Attitude Era through 2026.

**Answers questions:** name resolution for faction-based queries

| Column | Type | Source | Why |
|---|---|---|---|
| id | INTEGER | (generated) | Primary key |
| name | TEXT | Hand-curated | Faction name as a user would say it ("The Shield", "D-Generation X") |
| era | TEXT | Hand-curated | "Attitude Era", "Ruthless Aggression", "PG Era", "Modern Era" |

---

## Table 9: faction_members

**What it stores:** One row per wrestler per faction. Maps faction names to individual cagematch_ids. 39 factions, ~140 member entries.

**Answers questions:** name resolution — the bridge between a faction name and real match data

| Column | Type | Source | Why |
|---|---|---|---|
| faction_id | INTEGER | (from factions table) | Links to the faction |
| cagematch_id | INTEGER | Verified against match_participants | Links to the wrestler's actual match history |
| ring_name | TEXT | Hand-curated | Name as it appears in match_participants |

**Why this table exists:** "The Shield" doesn't exist in match data. Only Roman Reigns, Seth Rollins, and Dean Ambrose do. This table lets the agent resolve "The Shield" to three cagematch_ids before generating any SQL.

---

## The 16 Questions This Schema Answers

### Original 10

1. What was Macho Man Randy Savage's championship history? → wrestlers + title_reigns
2. What were Bret Hart's biggest matches? → wrestlers + matches + match_participants + shows
3. Who are the current WWE champions? → title_reigns (where lost_date is NULL)
4. What happened in WWE while I stopped watching? → shows (filter by date range)
5. Who are the up and coming superstars today? → wrestlers + match_participants + matches (recent win rates)
6. How many matches did The Undertaker have in WWE? → match_participants (count by wrestler)
7. Who has the longest cumulative match time? → matches + match_participants (sum duration)
8. Top 5 most successful tag team champions? → title_reigns + match_participants (tag matches)
9. Top 5 longest title reigns across all championships? → title_reigns (order by days_held)
10. Top 5 men's and women's wrestlers of the last 5 years? → wrestlers (gender) + match_participants + matches (filter by date)

### Unlocked by the Kaggle dataset (ratings + full match history)

11. What are the highest rated matches of all time? → matches (order by rating_num desc)
12. What is the best WrestleMania match ever? → matches + shows + show_series (filter by series name, order by rating_num)
13. Who has the most submission wins? → matches + match_participants (win_type = "submission", result = "win")
14. How does a wrestler's PPV win rate compare to their TV win rate? → match_participants + matches + shows (group by is_ppv)
15. Which venues have hosted the most matches? → shows (group by venue, order by count)
16. How has average match quality changed by year? → matches (avg rating_num group by year) — reveals the Attitude Era, PG Era, etc.
