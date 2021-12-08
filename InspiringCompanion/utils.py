from .import models
import sqlite3, os
from shutil import copyfile
from decouple import config


def recreate_tables(database):
    if os.path.exists(database):
        copyfile(database, f"{database}.backup")
        os.remove(database)
    c = sqlite3.connect(database)
    models.create_table(c)

