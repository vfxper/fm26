import sqlite3
c = sqlite3.connect("fm26_local.db")
print("Top 10 priciest players:")
for r in c.execute(
    "SELECT name, position, age, ca, pa, club, price, wage FROM players "
    "ORDER BY CAST(price AS INTEGER) DESC LIMIT 10"
):
    print(" ", r)
print("\nHaaland:")
for r in c.execute("SELECT name, ca, pa, club, price, wage FROM players WHERE name LIKE '%Haaland%'"):
    print(" ", r)
c.close()
