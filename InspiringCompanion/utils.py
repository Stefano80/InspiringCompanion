from . import models
import sqlite3, os
from shutil import copyfile


def recreate_tables(database):
    if os.path.exists(database):
        copyfile(database, f"{database}.backup")
        os.remove(database)
    c = sqlite3.connect(database)
    models.create_table(c)


def add_column(ddl, database, table):
    c = sqlite3.connect(database)
    new_column = f"ALTER TABLE {table} ADD COLUMN {ddl}"

    c.cursor().execute(new_column)
    c.commit()
    c.close()


def rename_column(database, table, old, new):
    c = sqlite3.connect(database)
    new_column = f"ALTER TABLE {table} RENAME COLUMN '{old}' TO '{new}'"

    c.cursor().execute(new_column)
    c.commit()
    c.close()
