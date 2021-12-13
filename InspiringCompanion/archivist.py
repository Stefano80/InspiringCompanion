class Archivist(object):

    def __init__(self, database, server, channel):
        self.server = server
        self.channel = channel
        self.database = database

        pass

    def record_scene(self, scene):
        scenes_upsert = f"INSERT OR REPLACE INTO Scenes (server_id, channel_id, location, " \
                        f"day, wind_strength, wind_direction, rain, temperature, active_calendar, minutes) " \
                        f"VALUES( '{self.server}', '{self.channel}', " \
                        f"'{scene.location.name}', {scene.calendar.epoch}, '{scene.weather.wind_strength}', " \
                        f"'{scene.weather.wind_direction}', '{scene.weather.precipitation}', '{scene.weather.temperature}'," \
                        f"'{scene.calendar.name}', '{int(scene.clock.time.total_seconds()) // 60}'); "

        self.database.cursor().execute(scenes_upsert)

        for t in scene.clock.timers.keys():
            timers_upsert = f"INSERT OR REPLACE INTO Timers (server_id, channel_id, name, minutes) " \
                            f"VALUES( '{self.server}', '{self.channel}', " \
                            f"'{t}', '{int(scene.clock.timers[t].total_seconds()) // 60}');"

            self.database.cursor().execute(timers_upsert)

        for item in scene.inventory.items:
            items_upsert = f"INSERT OR REPLACE INTO Items (server_id, channel_id, name, quantity, max_quantity, " \
                           f"next_recharge) VALUES( '{self.server}', '{self.channel}', '{item.entity_data.name}', " \
                           f"'{item.charges}', NULL, NULL); "

            self.database.cursor().execute(items_upsert)

        self.database.commit()

        pass

    def record_character(self, name, user_id):
        upsert = f"INSERT OR REPLACE INTO Characters (server_id, channel_id, name, user_id) " \
                 f"VALUES( '{self.server}', '{self.channel}', '{name}', '{user_id}');"

        self.database.cursor().execute(upsert)
        self.database.commit()

        pass

    def find_characters(self):
        select = f"SELECT name FROM Characters WHERE server_id = '{self.server}' AND channel_id = '{self.channel}'"
        rows = self.database.execute(select).fetchall()
        return {r[0] for r in rows}

    def find_timers(self):
        select = f"SELECT name, minutes FROM Timers WHERE server_id = '{self.server}' AND channel_id = '{self.channel}'"
        return self.database.cursor().execute(select).fetchall()

    def delete_timers(self):
        delete = f"DELETE FROM Timers WHERE server_id = '{self.server}' AND channel_id = '{self.channel}'"
        self.database.cursor().execute(delete)
        self.database.commit()
        pass

    def find_items(self):
        select = f"SELECT name, quantity, max_quantity, next_recharge FROM Items WHERE server_id = '{self.server}' " \
                 f"AND channel_id = '{self.channel}' "
        return self.database.cursor().execute(select).fetchall()

    def delete_items(self):
        delete = f"DELETE FROM Timers WHERE server_id = '{self.server}' AND channel_id = '{self.channel}'"
        self.database.cursor().execute(delete)
        self.database.commit()
        pass

    def find_scene(self):
        select = f"SELECT * FROM Scenes WHERE server_id = '{self.server}' AND channel_id = '{self.channel}'"
        return self.database.cursor().execute(select).fetchone()
