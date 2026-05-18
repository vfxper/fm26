import sqlite3
c = sqlite3.connect('fm26_local.db')
print("UCL standings with played > 0:")
rows = c.execute("""
    SELECT p.club_name, s.played, s.won, s.drawn, s.lost, s.goals_for, s.goals_against, s.points, s.rank
    FROM ucl_standings s 
    JOIN ucl_participants p ON p.id = s.participant_id 
    WHERE s.played > 0
    ORDER BY s.rank ASC
""").fetchall()
print(f"Total clubs played: {len(rows)}")
for r in rows:
    print(f"  rank={r[8]:>2} {r[0]:30s} P={r[1]} W={r[2]} D={r[3]} L={r[4]} GF={r[5]} GA={r[6]} Pts={r[7]}")
print()
print("Locked match events (played):")
locked = c.execute("""
    SELECT id, description, home_club_id, away_club_id 
    FROM calendar_events 
    WHERE career_id=1 AND event_type='match' AND is_locked=1 
    ORDER BY id
""").fetchall()
print(f"Total locked: {len(locked)}")
for r in locked[:10]:
    print(f"  id={r[0]} home={r[2]} away={r[3]} desc={r[1]}")
