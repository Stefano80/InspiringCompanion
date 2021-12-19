from InspiringCompanion.utils import add_column
from InspiringCompanion.models import create_table
from InspiringCompanion.utils import rename_column
import sqlite3

con = sqlite3.connect("inspirations.db")
create_table(con) # this creates the bulk table

rename_column("inspirations.db", "Items", "quantity", "charges")
rename_column("inspirations.db", "Items", "max_quantity", "max_charges")

con.cursor().execute("INSERT INTO Bulks SELECT * FROM Items WHERE name = 'Ration';")
con.cursor().execute("DELETE FROM Items WHERE name = 'Ration';")
con.cursor().execute("DROP INDEX idx_items;")


con.commit()

print(con.cursor().execute("SELECT * FROM Items").fetchall())
print(con.cursor().execute("SELECT * FROM Bulks").fetchall())



