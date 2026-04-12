"""
Phase 0A: migrate match duration from text to integer seconds.

The Kaggle dataset stores duration as a string like "18:05". That format
is fine for display, but you can't do math on text. Answering questions
like "who has the most cumulative match time" requires addition, which
means the database needs numbers.

This script adds a duration_seconds INTEGER column to the matches table
and converts every existing value. "18:05" becomes 1085. The original
text column is preserved for display purposes.

Run once from the project root: python scripts/migrate_duration.py
"""
import sqlite3

conn = sqlite3.connect("data/kayfabe.db")
cur = conn.cursor()

# Add the new column
cur.execute("ALTER TABLE matches ADD COLUMN duration_seconds INTEGER")

# Fetch every match that has a duration value
cur.execute("SELECT id, duration FROM matches WHERE duration IS NOT NULL")
rows = cur.fetchall()

for row in rows:
    match_id = row[0]
    duration = row[1]

    # Split "18:05" into ["18", "05"]
    parts = duration.split(":")

    # Convert to total seconds
    seconds = int(parts[0]) * 60 + int(parts[1])

    # Write it back
    cur.execute(
        "UPDATE matches SET duration_seconds = ? WHERE id = ?",
        (seconds, match_id)
    )

conn.commit()
conn.close()
print("Done.")
