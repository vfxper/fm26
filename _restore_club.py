"""Maintenance:
  1. Wipe all careers + per-career data
  2. Re-seed players.club from CSV in ONE transaction
"""
import csv
import sqlite3
import sys
import time

CSV_PATH = "2600球员属性.csv"
DB_PATH = "fm26_local.db"

WIPE_CAREERS = "--wipe" in sys.argv

con = sqlite3.connect(DB_PATH, timeout=60)

if WIPE_CAREERS:
    print("Wiping all careers + per-career rows...")
    cascading = [
        "squad_players", "calendar_events", "inbox_messages",
        "matches", "ai_transfers",
        "transfer_offers", "ai_window_quota", "scout_assignments",
        "scout_knowledge", "player_injuries", "player_promises",
        "career_tactics", "match_sessions", "ucl_phase_matchups",
        "ucl_standings", "ucl_participants", "ucl_ties",
        "competitions", "competition_rounds",
        "career_saves", "player_match_stats", "fixtures",
        "league_configs", "recurring_templates",
    ]
    for t in cascading:
        try:
            cur = con.execute(f"DELETE FROM {t}")
            print(f"  {t}: deleted {cur.rowcount}")
        except Exception as e:
            pass
    con.execute("DELETE FROM careers")
    con.commit()
    print("Wipe done.")

print("\nReading CSV...")
updates = []
with open(CSV_PATH, encoding="utf-8-sig") as f:
    reader = csv.reader(f)
    next(reader)
    for row in reader:
        if len(row) < 50:
            continue
        name = row[0].strip()
        paren = name.find("(")
        if paren > 0:
            name = name[:paren].strip()
        if not name:
            continue
        original_club = (row[6] or "").strip() or "Free Agent"
        updates.append((original_club, name))

print(f"Restoring club for {len(updates)} CSV rows in batch transaction...")
t0 = time.time()
con.executemany(
    "UPDATE players SET club = ? WHERE name = ? AND club != ?",
    [(c, n, c) for c, n in updates],
)
con.commit()
elapsed = time.time() - t0
print(f"Done in {elapsed:.1f}s.")

con.close()
