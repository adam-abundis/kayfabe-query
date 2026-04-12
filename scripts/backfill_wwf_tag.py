"""
One-time backfill: imports the 1971-2002 unified WWF Tag Team Championship
history from Wikipedia. Stops at 2002-10-20 (the brand split date when the
Raw-exclusive era begins, which is already covered by Raw Tag Team Championship).

Safe to re-run: skips if 'WWF Tag Team Championship' already has rows.
"""
import re
import requests
import sqlite3
from datetime import datetime
from bs4 import BeautifulSoup

conn = sqlite3.connect('data/kayfabe.db')
cursor = conn.cursor()

# Idempotency check
cursor.execute("SELECT COUNT(*) FROM title_reigns WHERE title_name = 'WWF Tag Team Championship'")
if cursor.fetchone()[0] > 0:
    print("WWF Tag Team Championship already in database — nothing to do.")
    conn.close()
    exit()

headers = {
    "User-Agent": "KayfabeQuery-Scraper/1.0 (educational project; contact: adamjabundis@gmail.com)"
}

# Brand split date: Raw-exclusive era starts here. Anything on or after this
# date is already covered by the Raw Tag Team Championship rows in the DB.
BRAND_SPLIT_CUTOFF = "2002-10-20"

DATE_PATTERN = re.compile(
    r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)'
    r'\s+\d{1,2},\s+\d{4}\b'
)
FOOTNOTE = re.compile(r'\[\s*\d+\s*\]')


def clean(text):
    return ' '.join(FOOTNOTE.sub('', text).split()).strip()


def parse_date(text):
    text = clean(text)
    m = DATE_PATTERN.search(text)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(0), "%B %d, %Y").strftime("%Y-%m-%d")
    except ValueError:
        return None


def parse_days(text):
    text = clean(text)
    if not text or text in ('—', '\u2014'):
        return None, False
    is_current = '+' in text
    digits = re.sub(r'[^\d]', '', text)
    return (int(digits) if digits else None), is_current


response = requests.get(
    "https://en.wikipedia.org/wiki/List_of_WWF_Tag_Team_Champions",
    headers=headers
)

if response.status_code != 200:
    print(f"HTTP {response.status_code} — cannot fetch page")
    conn.close()
    exit()

soup = BeautifulSoup(response.text, "html.parser")

# Find the reigns table (same logic as scrape_title_reigns.py)
reigns_table = None
for table in soup.find_all('table'):
    rows = table.find_all('tr')
    hits = sum(
        1 for row in rows
        if len(row.find_all(['td', 'th'])) >= 5
        and DATE_PATTERN.search(row.find_all(['td', 'th'])[2].get_text())
    )
    if hits >= 3:
        reigns_table = table
        break

if not reigns_table:
    print("No reigns table found — check page structure")
    conn.close()
    exit()

# Parse all rows, filter to pre-split only
all_reigns = []
for row in reigns_table.find_all('tr'):
    cells = row.find_all(['td', 'th'])
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
    all_reigns.append({
        "wrestler_name": wrestler_name,
        "won_date": date_won,
        "won_event": won_event or None,
        "days_held": days_held,
        "lost_date": None,
        "lost_to": None,
    })

# Lookahead pass: fill lost_date and lost_to from next row
for i in range(len(all_reigns) - 1):
    all_reigns[i]["lost_date"] = all_reigns[i + 1]["won_date"]
    all_reigns[i]["lost_to"]   = all_reigns[i + 1]["wrestler_name"]

# Keep only pre-split reigns, skip Vacated rows
pre_split = [
    r for r in all_reigns
    if r["won_date"] < BRAND_SPLIT_CUTOFF
    and r["wrestler_name"].lower() != "vacated"
]

for reign in pre_split:
    cursor.execute("""
        INSERT INTO title_reigns
            (wrestler_name, wrestler_id, title_name, won_date, lost_date, days_held, won_event, lost_to)
        VALUES (?, NULL, 'WWF Tag Team Championship', ?, ?, ?, ?, ?)
    """, (
        reign["wrestler_name"],
        reign["won_date"],
        reign["lost_date"],
        reign["days_held"],
        reign["won_event"],
        reign["lost_to"],
    ))

conn.commit()
conn.close()
print(f"Done — {len(pre_split)} WWF Tag Team Championship reigns inserted (1971–2002).")
