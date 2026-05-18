import sqlite3
c = sqlite3.connect('fm26_local.db')
print("Top wage players:")
for row in c.execute("SELECT name, ca, age, wage FROM players ORDER BY wage DESC LIMIT 10"):
    print(f"  {row[0]:30s} CA={row[1]} age={row[2]} wage=€{row[3]:>10,d}/wk")
print()
print("Mid-tier sample (CA 90-100):")
for row in c.execute("SELECT name, ca, age, wage FROM players WHERE ca BETWEEN 90 AND 100 LIMIT 5"):
    print(f"  {row[0]:30s} CA={row[1]} age={row[2]} wage=€{row[3]:>10,d}/wk")
print()
print("Low CA sample:")
for row in c.execute("SELECT name, ca, age, wage FROM players WHERE ca < 60 LIMIT 5"):
    print(f"  {row[0]:30s} CA={row[1]} age={row[2]} wage=€{row[3]:>10,d}/wk")
