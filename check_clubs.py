import sqlite3
c = sqlite3.connect('fm26_local.db')
r = c.execute("SELECT DISTINCT club FROM players WHERE club LIKE '%adrid%' OR club LIKE '%eal M%' LIMIT 10")
print("Madrid clubs:", [x[0] for x in r.fetchall()])
r = c.execute("SELECT budget FROM careers LIMIT 5")
print("Career budgets:", [x[0] for x in r.fetchall()])
c.close()
