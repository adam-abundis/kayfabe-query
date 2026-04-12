"""
Scrapes championship history from Wikipedia and builds the title_reigns table.

The Kaggle dataset has match data but not title reign data — it doesn't
track who held a championship or for how long. That information lives on
Wikipedia's championship history pages and needed to be brought in separately.

This script scrapes 10 championship pages, parses the reigns table from each,
and inserts one row per reign into title_reigns. A lookahead pass fills in
lost_date and lost_to by reading the next row in each table.

Idempotent: skips any title already in the database, so it is safe to re-run
if new championships need to be added later.

Run from the project root: python scripts/scrape_title_reigns.py
"""
import re
import requests
import sqlite3
from datetime import datetime
from bs4 import BeautifulSoup

conn = sqlite3.connect('data/kayfabe.db')
cursor = conn.cursor()

headers = {
    "User-Agent": "KayfabeQuery-Scraper/1.0 (educational project; contact: adamjabundis@gmail.com)"
}

# All 11 championship history pages.
# title_name is the canonical label stored in the DB.
# slug is the Wikipedia article slug.
TITLES = [
    ("WWE Championship",                 "List_of_WWE_Champions"),
    ("Universal Championship",           "List_of_WWE_Universal_Champions"),
    ("Women's World Championship",       "List_of_WWE_Women%27s_World_Champions"),
    ("Raw Women's Championship",         "List_of_WWE_Raw_Women%27s_Champions"),
    ("SmackDown Women's Championship",   "List_of_WWE_SmackDown_Women%27s_Champions"),
    ("Women's Championship",             "List_of_WWE_Women%27s_Champions_(1956%E2%80%932010)"),
    ("WWE Tag Team Championship",        "List_of_WWE_Tag_Team_Champions"),
    ("Raw Tag Team Championship",        "List_of_WWE_Raw_Tag_Team_Champions"),
    ("SmackDown Tag Team Championship",  "List_of_WWE_SmackDown_Tag_Team_Champions"),
    ("NXT Championship",                 "List_of_NXT_Champions"),
]

cursor.execute("""
    CREATE TABLE IF NOT EXISTS title_reigns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        wrestler_name TEXT,
        wrestler_id INTEGER,
        title_name TEXT,
        won_date DATE,
        lost_date DATE,
        days_held INTEGER,
        won_event TEXT,
        lost_to TEXT
    )
""")
conn.commit()

# Date pattern: "January 14, 2001" or "September 18, 1956"
DATE_PATTERN = re.compile(
    r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)'
    r'\s+\d{1,2},\s+\d{4}\b'
)

FOOTNOTE = re.compile(r'\[\s*\d+\s*\]')


def clean(text):
    """Strip footnote references and collapse whitespace."""
    return ' '.join(FOOTNOTE.sub('', text).split()).strip()


def parse_date(text):
    """Convert 'April 1, 1963' to '1963-04-01'. Returns None if unparseable."""
    text = clean(text)
    # Some cells have extra text after the date — extract just the date portion
    match = DATE_PATTERN.search(text)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(0), "%B %d, %Y").strftime("%Y-%m-%d")
    except ValueError:
        return None


def parse_days(text):
    """
    Parse days-held cell. Returns (days_int_or_None, is_current_bool).
    '2,803' → (2803, False)
    '33+'   → (33, True)   — still reigning, store what we know
    '—'     → (None, False)
    """
    text = clean(text)
    if not text or text in ('—', '\u2014'):
        return None, False
    is_current = '+' in text
    digits = re.sub(r'[^\d]', '', text)
    return (int(digits) if digits else None), is_current


def is_reigns_table(table):
    """
    Identify the championship history table vs. navboxes, legend tables, etc.
    All confirmed reigns tables have dates in cells[2] and at least 5 columns per row.
    The name-history table (also has dates) only has 2 columns — excluded by the >= 5 check.
    Require at least 3 matching rows to avoid false positives.
    """
    hits = 0
    for row in table.find_all('tr'):
        cells = row.find_all(['td', 'th'])
        if len(cells) >= 5 and DATE_PATTERN.search(cells[2].get_text()):
            hits += 1
        if hits >= 3:
            return True
    return False


def parse_reigns_from_table(table):
    """
    Parse all data rows from a reigns table.
    Column layout (confirmed across all 11 pages tested):
      [0] No.  [1] Champion  [2] Date  [3] Event  [4] Location
      [5] Reign#  [6] Days  [7] Days recog.  [8] Notes  [9] Refs

    Returns a list of dicts. Includes 'Vacated' rows so the lookahead
    pass can derive the correct lost_date for the preceding reign.
    lost_date and lost_to are filled in by the caller after parsing.
    """
    reigns = []
    for row in table.find_all('tr'):
        cells = row.find_all(['td', 'th'])
        # Must have enough columns and a real date in col 2
        if len(cells) < 5:
            continue
        date_won = parse_date(cells[2].get_text(separator=' '))
        if not date_won:
            continue

        wrestler_name = clean(cells[1].get_text(separator=' '))
        won_event = clean(cells[3].get_text(separator=' ')) if len(cells) > 3 else None
        days_held, _ = parse_days(cells[6].get_text(separator=' ') if len(cells) > 6 else '')

        if not wrestler_name:
            continue

        reigns.append({
            "wrestler_name": wrestler_name,
            "won_date": date_won,
            "won_event": won_event or None,
            "days_held": days_held,
            "lost_date": None,   # filled by lookahead pass
            "lost_to": None,     # filled by lookahead pass
        })

    return reigns


def fill_lookahead(reigns):
    """
    Walk the reigns list and derive lost_date and lost_to for each reign.
    For reign[i]:
      lost_date = reign[i+1].won_date
      lost_to   = reign[i+1].wrestler_name  (may be 'Vacated')
    The last reign has lost_date = None and lost_to = None (active champion).
    """
    for i in range(len(reigns) - 1):
        reigns[i]["lost_date"] = reigns[i + 1]["won_date"]
        reigns[i]["lost_to"]   = reigns[i + 1]["wrestler_name"]
    return reigns


# ── Main scrape loop ──────────────────────────────────────────────────────────

# Idempotency: skip any title we already have data for
cursor.execute("SELECT DISTINCT title_name FROM title_reigns")
already_scraped = {row[0] for row in cursor.fetchall()}

for title_name, slug in TITLES:
    if title_name in already_scraped:
        print(f"SKIP {title_name} — already in database")
        continue

    url = f"https://en.wikipedia.org/wiki/{slug}"
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"SKIP {title_name} ({response.status_code})")
        continue

    soup = BeautifulSoup(response.text, "html.parser")

    reigns_table = None
    for table in soup.find_all('table'):
        if is_reigns_table(table):
            reigns_table = table
            break

    if not reigns_table:
        print(f"SKIP {title_name} — no reigns table found")
        continue

    reigns = parse_reigns_from_table(reigns_table)
    if not reigns:
        print(f"SKIP {title_name} — table found but 0 reigns parsed")
        continue

    fill_lookahead(reigns)

    # Filter out Vacated rows AFTER lookahead so preceding reigns get correct lost_date.
    # "Vacated" as lost_to is preserved in the preceding row — it tells us why the reign ended.
    insertable = [r for r in reigns if r["wrestler_name"].lower() != "vacated"]

    for reign in insertable:
        cursor.execute("""
            INSERT INTO title_reigns
                (wrestler_name, wrestler_id, title_name, won_date, lost_date, days_held, won_event, lost_to)
            VALUES (?, NULL, ?, ?, ?, ?, ?, ?)
        """, (
            reign["wrestler_name"],
            title_name,
            reign["won_date"],
            reign["lost_date"],
            reign["days_held"],
            reign["won_event"],
            reign["lost_to"],
        ))

    conn.commit()
    print(f"OK {title_name} — {len(insertable)} reigns")

conn.close()
print("Done.")
