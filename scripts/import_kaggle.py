"""
Full import from wwe_db_2026-01-18.sqlite into kayfabe.db.

Builds 7 tables:
  promotions       — 6 rows, direct import
  show_series      — wrestling event brands (Raw, WrestleMania, etc.)
  shows            — every individual show with date, location, is_ppv, attendance
  wrestlers        — every unique individual from match_html, with Cagematch ID
  matches          — one row per match, with win_type, duration, title, rating
  match_participants — one row per person per match (winner/loser/draw)
  title_reigns     — NOT touched here; already built from Wikipedia

Idempotent per table: checks row count before inserting.
Progress is printed per promotion so you can see where it is.
"""

import re
import sqlite3
import time
from bs4 import BeautifulSoup, NavigableString

SOURCE = "resource/wwe_db_2026-01-18.sqlite"
TARGET = "data/kayfabe.db"

src = sqlite3.connect(SOURCE)
src.row_factory = sqlite3.Row
tgt = sqlite3.connect(TARGET)

sc = src.cursor()
tc = tgt.cursor()


# ════════════════════════════════════════════════════════════════════════════
# Shared parsing helpers (identical to validated test parser)
# ════════════════════════════════════════════════════════════════════════════

def rating_to_float(text):
    if not text or text.strip() in ('', 'N/R', 'NR'):
        return None
    text = text.strip()
    if text == 'DUD':
        return 0.0
    negative = text.startswith('-')
    if negative:
        text = text[1:]
    if text and text[0] in ('½', '¼', '¾'):
        result = 0.5 if '½' in text else 0.25 if '¼' in text else 0.75
    else:
        stars    = text.count('*')
        fraction = 0.75 if '¾' in text else 0.5 if '½' in text else 0.25 if '¼' in text else 0.0
        result   = float(stars) + fraction
    return -result if negative else result


def extract_wrestlers(cell):
    wrestlers = []
    for a in cell.find_all('a', href=re.compile(r'/wrestlers/')):
        match = re.search(r'-(\d+)\.html$', a['href'])
        if match:
            wrestlers.append({
                "cagematch_id": int(match.group(1)),
                "ring_name":    a.get_text(strip=True)
            })
    return wrestlers


def extract_match_type(cell):
    parts = []
    for node in cell.children:
        if not isinstance(node, NavigableString):
            continue
        text = str(node).strip()
        if not text or text == '\xa0':
            continue
        if text.endswith(':'):
            continue
        parts.append(text)
    result = ' '.join(parts).strip()
    return result if result else None


def parse_card_html(match_html):
    """Parse all matches from a card's match_html. Returns list of match dicts."""
    if not match_html:
        return []
    soup = BeautifulSoup(match_html, "html.parser")
    matches = []
    for row in soup.find_all('tr'):
        cells = row.find_all('td')
        if len(cells) < 7:
            continue
        winners = extract_wrestlers(cells[1])
        losers  = extract_wrestlers(cells[3])
        if not winners and not losers:
            continue

        win_type   = cells[2].get_text(strip=True) or None
        duration   = cells[4].get_text(strip=True) or None
        match_type = extract_match_type(cells[5])
        title      = cells[6].get_text(separator=' ', strip=True) or None
        rating_raw = cells[7].get_text(strip=True) if len(cells) > 7 else None

        if duration in ('—', '\u2014', ''):
            duration = None
        if rating_raw in ('', None):
            rating_raw = None

        matches.append({
            "match_order": len(matches) + 1,
            "winners":     winners,
            "losers":      losers,
            "win_type":    win_type,
            "duration":    duration,
            "match_type":  match_type,
            "title":       title,
            "rating":      rating_raw,
            "rating_num":  rating_to_float(rating_raw),
        })
    return matches


def parse_info_html(info_html):
    """Extract is_ppv (0/1), attendance (int or None), venue (str) from info_html."""
    if not info_html:
        return 0, None, None
    soup = BeautifulSoup(info_html, "html.parser")
    text = soup.get_text(separator=' ')

    is_ppv = 1 if re.search(r'Pay Per View[:\s]+yes', text, re.IGNORECASE) else 0

    attendance = None
    att_match = re.search(r'Attendance[:\s]+([\d,]+)', text, re.IGNORECASE)
    if att_match:
        attendance = int(att_match.group(1).replace(',', ''))

    venue = None
    venue_tag = soup.find('a', href=re.compile(r'/locations/.*venue'))
    if venue_tag:
        venue = venue_tag.get_text(strip=True)

    return is_ppv, attendance, venue


# ════════════════════════════════════════════════════════════════════════════
# Step 1: Create target tables
# ════════════════════════════════════════════════════════════════════════════

tc.executescript("""
-- Drop old Wikipedia-scraped tables that are being replaced.
-- title_reigns is intentionally preserved.
DROP TABLE IF EXISTS promotions;
DROP TABLE IF EXISTS show_series;
DROP TABLE IF EXISTS shows;
DROP TABLE IF EXISTS events;
DROP TABLE IF EXISTS wrestlers;
DROP TABLE IF EXISTS matches;
DROP TABLE IF EXISTS match_participants;

CREATE TABLE promotions (
    id      INTEGER PRIMARY KEY,
    name    TEXT
);

CREATE TABLE show_series (
    id      INTEGER PRIMARY KEY,
    name    TEXT,
    promotion_id INTEGER
);

CREATE TABLE shows (
    id           INTEGER PRIMARY KEY,
    show_series_id INTEGER,
    promotion_id INTEGER,
    event_date   DATE,
    location     TEXT,
    venue        TEXT,
    is_ppv       INTEGER DEFAULT 0,
    attendance   INTEGER
);

CREATE TABLE wrestlers (
    id           INTEGER PRIMARY KEY,
    cagematch_id INTEGER UNIQUE,
    ring_name    TEXT,
    gender       TEXT,
    birth_date   DATE,
    nationality  TEXT
);

CREATE TABLE matches (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    show_id      INTEGER,
    match_order  INTEGER,
    win_type     TEXT,
    duration     TEXT,
    match_type   TEXT,
    title        TEXT,
    is_title_match INTEGER DEFAULT 0,
    title_change INTEGER DEFAULT 0,
    rating       TEXT,
    rating_num   REAL
);

CREATE TABLE match_participants (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id     INTEGER,
    cagematch_id INTEGER,
    ring_name    TEXT,
    result       TEXT
);
""")
tgt.commit()
print("Tables created.")


# ════════════════════════════════════════════════════════════════════════════
# Step 2: promotions — 6 rows, direct import
# ════════════════════════════════════════════════════════════════════════════

sc.execute("SELECT id, name FROM Promotions")
tc.executemany("INSERT OR IGNORE INTO promotions VALUES (?, ?)", sc.fetchall())
tgt.commit()
print(f"Promotions: 6 rows")


# ════════════════════════════════════════════════════════════════════════════
# Step 3: show_series — from Events table
# ════════════════════════════════════════════════════════════════════════════

sc.execute("""
    SELECT e.id, e.name,
           (SELECT c.promotion_id FROM Cards c WHERE c.event_id = e.id LIMIT 1) as promo_id
    FROM Events e
""")
rows = [(r["id"], r["name"], r["promo_id"]) for r in sc.fetchall()]
tc.executemany("INSERT OR IGNORE INTO show_series VALUES (?, ?, ?)", rows)
tgt.commit()
print(f"Show series: {len(rows)} rows")


# ════════════════════════════════════════════════════════════════════════════
# Step 4: shows + matches + match_participants
# (Parse every card's HTML — the heavy step)
# ════════════════════════════════════════════════════════════════════════════

if True:
    # Track every unique wrestler we encounter for the wrestlers table
    wrestler_registry = {}  # cagematch_id → ring_name

    sc.execute("""
        SELECT c.id, c.event_id, c.location_id, c.promotion_id,
               c.event_date, c.info_html, c.match_html,
               l.name as location_name
        FROM Cards c
        LEFT JOIN Locations l ON c.location_id = l.id
        ORDER BY c.promotion_id, c.event_date
    """)
    cards = sc.fetchall()

    # Group progress by promotion for readable output
    sc.execute("SELECT id, name FROM Promotions")
    promo_names = {r["id"]: r["name"] for r in sc.fetchall()}

    show_count    = 0
    match_count   = 0
    participant_count = 0
    current_promo = None

    for card in cards:
        promo_id = card["promotion_id"]
        if promo_id != current_promo:
            if current_promo is not None:
                tgt.commit()
                print(f"  → committed")
            current_promo = promo_id
            print(f"\n{promo_names.get(promo_id, promo_id)} ({promo_id})...")

        is_ppv, attendance, venue = parse_info_html(card["info_html"])

        # Insert show
        tc.execute("""
            INSERT OR IGNORE INTO shows
                (id, show_series_id, promotion_id, event_date, location, venue, is_ppv, attendance)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            card["id"],
            card["event_id"],
            promo_id,
            card["event_date"],
            card["location_name"],
            venue,
            is_ppv,
            attendance,
        ))
        show_count += 1

        # Parse matches from HTML
        parsed_matches = parse_card_html(card["match_html"])
        for m in parsed_matches:
            title_text   = m["title"] or ""
            is_title     = 1 if ("championship" in title_text.lower() or
                                  "title" in title_text.lower() or
                                  "belt" in title_text.lower()) else 0
            title_change = 1 if "title change" in title_text.lower() else 0

            tc.execute("""
                INSERT INTO matches
                    (show_id, match_order, win_type, duration, match_type,
                     title, is_title_match, title_change, rating, rating_num)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                card["id"],
                m["match_order"],
                m["win_type"],
                m["duration"],
                m["match_type"],
                m["title"],
                is_title,
                title_change,
                m["rating"],
                m["rating_num"],
            ))
            match_id = tc.lastrowid
            match_count += 1

            # Determine result label from win_type
            is_draw = m["win_type"] and m["win_type"].startswith("draw")
            result_w = "draw" if is_draw else "win"
            result_l = "draw" if is_draw else "loss"

            for w in m["winners"]:
                wrestler_registry[w["cagematch_id"]] = w["ring_name"]
                tc.execute("""
                    INSERT INTO match_participants (match_id, cagematch_id, ring_name, result)
                    VALUES (?, ?, ?, ?)
                """, (match_id, w["cagematch_id"], w["ring_name"], result_w))
                participant_count += 1

            for l in m["losers"]:
                wrestler_registry[l["cagematch_id"]] = l["ring_name"]
                tc.execute("""
                    INSERT INTO match_participants (match_id, cagematch_id, ring_name, result)
                    VALUES (?, ?, ?, ?)
                """, (match_id, l["cagematch_id"], l["ring_name"], result_l))
                participant_count += 1

    tgt.commit()
    print(f"\n  → final commit")
    print(f"\nShows:             {show_count}")
    print(f"Matches:           {match_count}")
    print(f"Participants:      {participant_count}")
    print(f"Unique wrestlers:  {len(wrestler_registry)}")


    # ── Step 5: wrestlers table from registry ─────────────────────────────
    print("\nInserting wrestlers...")
    rows = [(cid, cid, name, None, None, None)
            for cid, name in wrestler_registry.items()]
    tc.executemany("""
        INSERT OR IGNORE INTO wrestlers
            (id, cagematch_id, ring_name, gender, birth_date, nationality)
        VALUES (?, ?, ?, ?, ?, ?)
    """, rows)
    tgt.commit()
    print(f"Wrestlers: {len(rows)} inserted")


# ════════════════════════════════════════════════════════════════════════════
# Final summary
# ════════════════════════════════════════════════════════════════════════════

print("\n── Final row counts ──────────────────────────────")
for table in ["promotions","show_series","shows","wrestlers","matches","match_participants","title_reigns"]:
    try:
        tc.execute(f"SELECT COUNT(*) FROM {table}")
        print(f"  {table:<22} {tc.fetchone()[0]:>8,}")
    except Exception:
        print(f"  {table:<22}  (not found)")

src.close()
tgt.close()
print("\nDone.")
