import sqlite3
c = sqlite3.connect("fm26_local.db")
print("Last 3 careers:")
for r in c.execute("SELECT id, manager_name, club_id, created_at FROM careers ORDER BY id DESC LIMIT 5"):
    print(" ", r)
print("\nsquad_players по карьерам:")
for r in c.execute("SELECT career_id, COUNT(*) FROM squad_players GROUP BY career_id"):
    print(" ", r)
print("\nХоланд в squad_players (если он есть):")
for r in c.execute(
    "SELECT sp.career_id, p.name, p.club, sp.status FROM squad_players sp "
    "JOIN players p ON p.id = sp.player_id WHERE p.name LIKE '%Haaland%'"
):
    print(" ", r)
c.close()
