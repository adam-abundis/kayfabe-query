"""
Phase 0B: create and seed the factions and faction_members tables.

The problem: "The Shield" does not exist anywhere in the match data.
Only "Roman Reigns", "Seth Rollins", and "Dean Ambrose" do. Without a
translation layer, any question about a faction returns nothing.

This script creates two tables:
  factions        — 39 named stables from the Attitude Era through 2026
  faction_members — maps each faction to the cagematch_ids of its members

Every cagematch_id was verified against live match_participants data
before being added. If a name wasn't found in the database, it wasn't
included. The agent uses these tables to resolve faction names to real
wrestler IDs before generating any SQL.

Safe to re-run: drops and recreates both tables each time.
Run from the project root: python scripts/seed_factions.py
"""
import sqlite3

conn = sqlite3.connect("data/kayfabe.db")
cur = conn.cursor()

# Drop and recreate so this script is safe to re-run
cur.execute("DROP TABLE IF EXISTS faction_members")
cur.execute("DROP TABLE IF EXISTS factions")

cur.execute("""
    CREATE TABLE factions (
        id   INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        era  TEXT
    )
""")

cur.execute("""
    CREATE TABLE faction_members (
        faction_id   INTEGER,
        cagematch_id INTEGER,
        ring_name    TEXT
    )
""")

# Each entry: (faction name, era, [(ring_name, cagematch_id), ...])
FACTIONS = [

    # Attitude Era (1997-2002)
    ("D-Generation X", "Attitude Era", [
        ("Shawn Michaels", 96), ("Triple H", 193), ("Chyna", 282),
        ("X-Pac", 163), ("Road Dogg", 192), ("Billy Gunn", 158),
    ]),
    ("The Kliq", "Attitude Era", [
        ("Shawn Michaels", 96), ("Triple H", 193), ("X-Pac", 163),
        ("Razor Ramon", 147), ("Diesel", 167),
    ]),
    ("Nation of Domination", "Attitude Era", [
        ("The Rock", 229), ("Mark Henry", 213), ("D-Lo Brown", 247),
        ("Owen Hart", 101), ("Faarooq", 218),
    ]),
    ("Ministry of Darkness", "Attitude Era", [
        ("The Undertaker", 124), ("Mideon", 206), ("Viscera", 170),
        ("Bradshaw", 207), ("Faarooq", 218),
    ]),
    ("APA", "Attitude Era", [
        ("Bradshaw", 207), ("Faarooq", 218),
    ]),
    ("Hardy Boyz", "Attitude Era", [
        ("Matt Hardy", 288), ("Jeff Hardy", 289),
    ]),
    ("Dudley Boyz", "Attitude Era", [
        ("Bubba Ray Dudley", 294), ("D-Von Dudley", 295),
    ]),
    ("Edge and Christian", "Attitude Era", [
        ("Edge", 273), ("Christian", 277),
    ]),
    ("The Brood", "Attitude Era", [
        ("Edge", 273), ("Christian", 277), ("Gangrel", 275),
    ]),
    ("Too Cool", "Attitude Era", [
        ("Scotty 2 Hotty", 261), ("Grandmaster Sexay", 241),
    ]),

    # Ruthless Aggression (2002-2008)
    ("Evolution", "Ruthless Aggression", [
        ("Triple H", 193), ("Ric Flair", 138),
        ("Randy Orton", 384), ("Batista", 357),
    ]),
    ("The Legacy", "Ruthless Aggression", [
        ("Randy Orton", 384), ("Cody Rhodes", 2805), ("Ted DiBiase Jr.", 3275),
    ]),
    ("Rated-RKO", "Ruthless Aggression", [
        ("Edge", 273), ("Randy Orton", 384),
    ]),
    ("MNM", "Ruthless Aggression", [
        ("Joey Mercury", 423), ("John Morrison", 377),
    ]),
    ("Cryme Tyme", "Ruthless Aggression", [
        ("JTG", 459), ("Shad Gaspard", 460),
    ]),

    # PG Era (2008-2014)
    ("Straight Edge Society", "PG Era", [
        ("CM Punk", 467), ("Luke Gallows", 448),
        ("Serena", 1934), ("Joey Mercury", 423),
    ]),
    ("The Nexus", "PG Era", [
        ("Wade Barrett", 6096), ("Justin Gabriel", 1471),
        ("Heath Slater", 3407), ("David Otunga", 6094),
        ("Darren Young", 3424), ("Ezekiel Jackson", 3443),
    ]),
    ("The Corre", "PG Era", [
        ("Wade Barrett", 6096), ("Ezekiel Jackson", 3443),
        ("Justin Gabriel", 1471), ("Heath Slater", 3407),
    ]),
    ("The Shield", "PG Era", [
        ("Roman Reigns", 6728), ("Seth Rollins", 3328), ("Dean Ambrose", 3069),
    ]),
    ("The Wyatt Family", "PG Era", [
        ("Bray Wyatt", 6287), ("Luke Harper", 3461),
        ("Erick Rowan", 5369), ("Braun Strowman", 9702),
    ]),
    ("The Real Americans", "PG Era", [
        ("Cesaro", 1874), ("Jack Swagger", 3410),
    ]),
    ("The Prime Time Players", "PG Era", [
        ("Darren Young", 3424), ("Titus O Neil", 3271),
    ]),

    # Modern Era (2014-2026)
    ("The New Day", "Modern Era", [
        ("Kofi Kingston", 3295), ("Big E", 6446), ("Xavier Woods", 3272),
    ]),
    ("The Club", "Modern Era", [
        ("AJ Styles", 752), ("Karl Anderson", 3250), ("Luke Gallows", 448),
    ]),
    ("League of Nations", "Modern Era", [
        ("Sheamus", 5000), ("Alberto Del Rio", 2883),
        ("Rusev", 7415), ("King Barrett", 6096),
    ]),
    ("The Hurt Business", "Modern Era", [
        ("Bobby Lashley", 434), ("MVP", 840),
        ("Cedric Alexander", 6075), ("Shelton Benjamin", 361),
    ]),
    ("Imperium", "Modern Era", [
        ("Gunther", 5395), ("Marcel Barthel", 8220),
        ("Fabian Aichner", 12756),
    ]),
    ("The Four Horsewomen", "Modern Era", [
        ("Charlotte Flair", 9274), ("Becky Lynch", 5418),
        ("Sasha Banks", 9409), ("Bayley", 8206),
    ]),
    ("The Usos", "Modern Era", [
        ("Jimmy Uso", 6303), ("Jey Uso", 6302),
    ]),
    ("The Bar", "Modern Era", [
        ("Cesaro", 1874), ("Sheamus", 5000),
    ]),
    ("The Bloodline", "Modern Era", [
        ("Roman Reigns", 6728), ("Jimmy Uso", 6303), ("Jey Uso", 6302),
        ("Solo Sikoa", 17257), ("Sami Zayn", 1861),
    ]),
    ("The Judgment Day", "Modern Era", [
        ("Finn Bálor", 3023), ("Damian Priest", 11382),
        ("Rhea Ripley", 13596), ("Dominik Mysterio", 17377),
    ]),
    ("Damage CTRL", "Modern Era", [
        ("Bayley", 8206), ("Dakota Kai", 9542), ("Iyo Sky", 7183),
    ]),
    ("Street Profits", "Modern Era", [
        ("Angelo Dawkins", 9426), ("Montez Ford", 12075),
    ]),
    ("Viking Raiders", "Modern Era", [
        ("Erik", 3781), ("Ivar", 3793),
    ]),
    ("RK-Bro", "Modern Era", [
        ("Randy Orton", 384), ("Riddle", 12135),
    ]),
    ("Brawling Brutes", "Modern Era", [
        ("Sheamus", 5000), ("Ridge Holland", 14048), ("Butch", 9700),
    ]),
    ("Alpha Academy", "Modern Era", [
        ("Chad Gable", 10613), ("Otis", 12822),
    ]),
    ("Jeri-KO", "Modern Era", [
        ("Chris Jericho", 296), ("Kevin Owens", 1862),
    ]),
]

for name, era, members in FACTIONS:
    cur.execute(
        "INSERT INTO factions (name, era) VALUES (?, ?)",
        (name, era)
    )
    faction_id = cur.lastrowid
    for ring_name, cagematch_id in members:
        cur.execute(
            "INSERT INTO faction_members (faction_id, cagematch_id, ring_name) VALUES (?, ?, ?)",
            (faction_id, cagematch_id, ring_name)
        )

conn.commit()
conn.close()
print(f"Done. {len(FACTIONS)} factions seeded.")
