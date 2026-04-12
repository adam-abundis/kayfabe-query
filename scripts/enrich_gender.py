"""
Enriches the wrestlers table with gender, birth_date, and nationality
from Wikidata using the Cagematch ID property (P2685).

This is exact-match enrichment — no name guessing. Wikidata P2685 is a
direct foreign key from a Wikidata entity to a Cagematch wrestler profile.
Every match is factual and unambiguous.

Idempotent: only updates wrestlers where gender IS NULL.
"""

import time
import sqlite3
import requests

TARGET = "data/kayfabe.db"
SPARQL  = "https://query.wikidata.org/sparql"
HEADERS = {
    "User-Agent": "KayfabeQuery/1.0 (educational project; contact: adamjabundis@gmail.com)",
    "Accept":     "application/json"
}

conn = sqlite3.connect(TARGET)
cursor = conn.cursor()

# ── Step 0: discover the correct Wikidata property for Cagematch IDs ─────────

def find_cagematch_property():
    """Search Wikidata for an external ID property with 'cagematch' in the label."""
    query = """
SELECT ?prop ?propLabel WHERE {
  ?prop a wikibase:Property .
  ?prop wikibase:propertyType wikibase:ExternalId .
  ?prop rdfs:label ?propLabel .
  FILTER(CONTAINS(LCASE(STR(?propLabel)), "cagematch"))
  FILTER(LANG(?propLabel) = "en")
}"""
    r = requests.post(SPARQL, data={"query": query}, headers=HEADERS, timeout=30)
    results = r.json()["results"]["bindings"]
    for row in results:
        pid = row["prop"]["value"].split("/")[-1]
        label = row["propLabel"]["value"]
        print(f"  Found property: {pid} = {label}")
    # Prefer "worker" property — that's individual wrestlers.
    # Tag team (P2939) and stable (P3042) IDs won't have gender data.
    for row in results:
        label = row["propLabel"]["value"].lower()
        if "worker" in label:
            return row["prop"]["value"].split("/")[-1]
    # Fallback to first result if no worker property found
    if results:
        return results[0]["prop"]["value"].split("/")[-1]
    return None

print("Looking up Cagematch property in Wikidata...")
CAGEMATCH_PROP = find_cagematch_property()
if not CAGEMATCH_PROP:
    print("ERROR: Could not find Cagematch property in Wikidata. Exiting.")
    conn.close()
    exit(1)
print(f"Using property: {CAGEMATCH_PROP}\n")

# Fetch all Cagematch IDs that still need enrichment
cursor.execute("SELECT cagematch_id FROM wrestlers WHERE gender IS NULL")
all_ids = [str(row[0]) for row in cursor.fetchall()]
print(f"Wrestlers needing enrichment: {len(all_ids)}")

# ── Batch SPARQL via P2685 ────────────────────────────────────────────────────

def fetch_profiles_by_cagematch_ids(cagematch_ids):
    """
    Query Wikidata for all items that have P2685 (Cagematch ID) matching
    one of our IDs. Returns {cagematch_id_str: {gender, birth_date, nationality}}.
    """
    values = " ".join(f'"{cid}"' for cid in cagematch_ids)
    query = f"""
SELECT ?cagematchId ?genderLabel ?birthDate ?citizenshipLabel
WHERE {{
  ?wrestler wdt:{CAGEMATCH_PROP} ?cagematchId .
  VALUES ?cagematchId {{ {values} }}
  OPTIONAL {{ ?wrestler wdt:P21 ?gender }}
  OPTIONAL {{ ?wrestler wdt:P569 ?birthDate }}
  OPTIONAL {{ ?wrestler wdt:P27 ?citizenship }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" }}
}}"""

    r = requests.post(
        SPARQL,
        data={"query": query},
        headers=HEADERS,
        timeout=60
    )
    if r.status_code != 200:
        print(f"  SPARQL error {r.status_code}")
        return {}

    results = {}
    for row in r.json()["results"]["bindings"]:
        cid = row["cagematchId"]["value"]
        if cid not in results:
            results[cid] = {
                "gender":      row.get("genderLabel", {}).get("value"),
                "birth_date":  (row.get("birthDate", {}).get("value") or "")[:10] or None,
                "nationality": row.get("citizenshipLabel", {}).get("value"),
            }
        else:
            # Fill any missing fields from duplicate rows (dual nationality etc.)
            p = results[cid]
            if not p["gender"] and row.get("genderLabel"):
                p["gender"] = row["genderLabel"]["value"]
            if not p["nationality"] and row.get("citizenshipLabel"):
                p["nationality"] = row["citizenshipLabel"]["value"]
    return results


# ── Run in batches of 150 ─────────────────────────────────────────────────────

BATCH = 150
total_updated = 0
total_matched = 0

for i in range(0, len(all_ids), BATCH):
    batch = all_ids[i:i + BATCH]
    batch_num = i // BATCH + 1
    total_batches = (len(all_ids) + BATCH - 1) // BATCH
    print(f"Batch {batch_num}/{total_batches} ({len(batch)} IDs)...", end=" ", flush=True)

    profiles = fetch_profiles_by_cagematch_ids(batch)
    total_matched += len(profiles)

    for cid_str, p in profiles.items():
        cursor.execute("""
            UPDATE wrestlers
            SET gender = ?, birth_date = ?, nationality = ?
            WHERE cagematch_id = ?
        """, (p["gender"], p["birth_date"], p["nationality"], int(cid_str)))
        total_updated += cursor.rowcount

    conn.commit()
    print(f"{len(profiles)} matched")
    time.sleep(0.5)

# ── Summary ───────────────────────────────────────────────────────────────────

print(f"\nWikidata matched:  {total_matched} wrestlers")
print(f"Rows updated:      {total_updated}")

cursor.execute("SELECT COUNT(*) FROM wrestlers WHERE gender IS NOT NULL")
has_gender = cursor.fetchone()[0]
cursor.execute("SELECT gender, COUNT(*) FROM wrestlers WHERE gender IS NOT NULL GROUP BY gender")
breakdown = cursor.fetchall()

print(f"\nGender coverage:   {has_gender} / {len(all_ids) + total_updated} wrestlers")
for gender, count in breakdown:
    print(f"  {gender}: {count}")

conn.close()
print("\nDone.")
