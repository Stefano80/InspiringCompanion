from difflib import SequenceMatcher

from owlready2 import get_ontology
from random import randint
from numpy import clip
from datetime import timedelta
import sqlite3
import functools
from bs4 import BeautifulSoup
import requests
import validators
from collections import OrderedDict

from InspiringCompanion.writer import normalize_entity_name

TEMPERATURE_VAR = 2
WIND_STRENGTH_VAR = 2
WIND_DIRECTION_VAR = 60
PRECIPITATION_VAR = 20
ONTOLOGY = get_ontology(
    "https://gist.githubusercontent.com/Stefano80/aa461b12305647eac19d34a8e9a20fd5/raw/45bffe3b1ea643c7d45688b721fc196ee0c77f31/inspiration.owl").load()


class Director(object):
    def __init__(self, channel=None, server=None, database=":memory:"):
        self.channel = channel
        self.server = server
        self.database = sqlite3.connect(database)
        self.scene = None

    def action(self, func):
        @functools.wraps(func)
        async def decorator(ctx, *args, **kwargs):
            self.set_scene_from(ctx.message)
            return await func(ctx, *args, **kwargs)

        decorator.__name__ = func.__name__

        return decorator

    def reaction(self, emoji, user):
        return getattr(self, emojis[emoji])(user)

    def short_log(self):
        return f"{self.scene.calendar.status_text()}\n{self.scene.description()}"

    def record_scene(self):

        scenes_upsert = f"INSERT OR REPLACE INTO Scenes (server_id, channel_id, location, " \
                        f"day, wind_strength, wind_direction, rain, temperature, active_calendar) " \
                        f"VALUES( '{self.server}', '{self.channel}', " \
                        f"'{self.scene.location.name}', {self.scene.calendar.epoch}, '{self.scene.weather.wind_strength}', " \
                        f"'{self.scene.weather.wind_direction}', '{self.scene.weather.precipitation}', '{self.scene.weather.temperature}'," \
                        f"'{self.scene.calendar.name}'); "

        self.database.cursor().execute(scenes_upsert)

        for t in self.scene.clock.triggers.keys():
            triggers_upsert = f"INSERT OR REPLACE INTO Triggers (server_id, channel_id, name, minutes) " \
                              f"VALUES( '{self.server}', '{self.channel}', " \
                              f"'{t}', '{int(self.scene.clock.triggers[t].total_seconds()) // 60}');"

            self.database.cursor().execute(triggers_upsert)

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

    def set_scene_from(self, message):
        self.server = message.server.id
        self.channel = message.channel.id

        select = f"SELECT * FROM Scenes WHERE server_id = '{self.server}' AND channel_id = '{self.channel}'"
        row_scenes = self.database.cursor().execute(select).fetchone()

        weather_data = {}

        if row_scenes is None:
            active_calendar = "Calendar of Harptos"
            location = "Elturel"
            day = 1
            weather_data["wind_strength"] = 0
            weather_data["wind_direction"] = 0
            weather_data["precipitation"] = 0
            weather_data["temperature"] = 0
        else:
            location = row_scenes[2]
            day = int(row_scenes[3])
            weather_data["wind_strength"] = int(row_scenes[4])
            weather_data["wind_direction"] = int(row_scenes[5])
            weather_data["precipitation"] = int(row_scenes[6])
            weather_data["temperature"] = int(row_scenes[7])
            active_calendar = row_scenes[8]

        self.scene = Scene(calendar=active_calendar, location=location, weather=weather_data)
        self.scene.calendar.sunrise(day)

        select = f"SELECT name, minutes FROM Triggers WHERE server_id = '{self.server}' AND channel_id = '{self.channel}'"
        row_triggers = self.database.cursor().execute(select).fetchall()

        if row_triggers is None:
            self.scene.clock = Clock()
        else:
            for r in row_triggers:
                self.scene.clock.add_trigger(r[0], trigger_time=r[1])

        if row_scenes is None:
            self.record_scene()

        pass

    def move_scene_to(self, new_location):

        new_location = Location(new_location)

        if new_location.entity_data == self.scene.location.entity_data:
            message = f"We already are in {self.scene.location.name}"

        else:
            self.scene.location = new_location
            self.scene.weather.entity_data = find_entity_by_name(self.scene.location.entity_data.has_climate.name)
            self.record_scene()

            message = f"We move to {self.scene.location.name}"

        return message

    def sunrise(self, user, day=1):
        sunrise_text = self.scene.sunrise(day)
        self.record_scene()
        return f" {sunrise_text}...\n\n {self.short_log()}."

    def gather(self, user):
        self.record_character(user.display_name, user.id)
        return f"{user.display_name} heeds the call to adventure!"

    def timegoesby(self, minutes):
        self.scene.clock.time_goes_by(minutes)
        return f"Time is {self.scene.clock.time}"

    def addtrigger(self, minutes, name=""):
        self.scene.clock.add_trigger(name, time_left=minutes)
        return f"Trigger {name} is set at {self.scene.clock.triggers[name]}"


class Scene(object):

    def __init__(self, calendar=None, location=None, weather=None):
        self.calendar = Calendar(calendar)
        self.location = Location(location)
        self.weather = Weather(self.location.entity_data.has_climate.name)
        self.clock = Clock()

        if weather is not None:
            self.weather.seed(weather)

    def description(self):
        description = f"We are in {self.location.name}. It {self.weather.precipitation_text()}. " \
                      f"The temperature is {self.weather.temperature_text()} with {self.weather.wind_strength_text()}"

        if self.weather.wind_strength_text() != "no winds":
            description += f" {self.weather.wind_direction_text()}"

        description += "."

        return description

    def sunrise(self, num_sunrises):
        self.calendar.sunrise(num_sunrises)
        self.weather.sunrise(num_sunrises)
        if num_sunrises == 1:
            return f"One day has passed"
        else:
            return f"Many days have passed"


class Inspiration(object):

    def __init__(self, name):
        self.entity_data = find_entity_by_name(name)
        self.name = normalize_entity_name(self.entity_data.name)

    def status_text(self):
        pass


class Calendar(Inspiration):

    def __init__(self, name):
        super().__init__(name)
        self.minute = 0
        self.hour = 0
        self.day = 0
        self.month = self.entity_data.starts_with
        self.year = 1
        self.epoch = 0

    def sunrise(self, num_sunrises):

        self.epoch += num_sunrises
        self.year += int(num_sunrises / self.entity_data.has_days)
        self.day += num_sunrises % self.entity_data.has_days

        while self.day > self.month.has_days:
            self.day = self.day - self.month.has_days
            self.month = self.month.precedes
            if self.month == self.entity_data.starts_with:
                self.year += 1

        pass

    def status_text(self):
        if self.month.has_days == 1:
            return self.month.name
        else:
            return f"{self.day} {self.month.name}, {self.year}"


class Clock(object):

    def __init__(self, time=timedelta(hours=8)):
        self.time = time
        self.triggers = OrderedDict()
        self.add_trigger("midnight", trigger_time=24 * 60)

    def time_goes_by(self, minutes):
        self.time += timedelta(minutes=minutes)

        expired_triggers = {k: self.triggers[k] for k in self.triggers if self.triggers[k] <= self.time}
        self.triggers = {k: self.triggers[k] for k in self.triggers if self.triggers[k] > self.time}

        return expired_triggers

    def add_trigger(self, name, time_left=None, trigger_time=None):
        if time_left is None and trigger_time is None:
            return
        if time_left is not None and trigger_time is not None:
            return

        if time_left is not None:
            self.triggers[name] = self.time + timedelta(minutes=time_left)

        if trigger_time is not None:
            self.triggers[name] = timedelta(minutes=trigger_time)

        self.triggers = OrderedDict(sorted(self.triggers.items(), key=lambda x: x[1]))
        return self.triggers


class Weather(Inspiration):

    def __init__(self, name):
        super().__init__(name)
        self.temperature = self.entity_data.has_temperature
        self.wind_strength = self.entity_data.has_wind_strength
        self.wind_direction = self.entity_data.has_wind_direction
        self.precipitation = self.entity_data.has_precipitation

    def seed(self, data):
        self.temperature = data["temperature"]
        self.wind_strength = data["wind_strength"]
        self.wind_direction = data["wind_direction"]
        self.precipitation = data["precipitation"]

    def sunrise(self, num_sunrises):
        for n in range(min(num_sunrises, 20)):
            self.temperature += randint(-TEMPERATURE_VAR, TEMPERATURE_VAR) - self.temperature / 2
            self.wind_strength += randint(-WIND_STRENGTH_VAR, WIND_STRENGTH_VAR) - self.wind_strength / 2
            self.wind_direction += randint(-WIND_DIRECTION_VAR, WIND_DIRECTION_VAR) - self.wind_direction / 2
            self.precipitation += randint(-PRECIPITATION_VAR, PRECIPITATION_VAR) - self.precipitation / 2
        pass

    def local_wind_strength(self):
        return self.entity_data.has_wind_strength + self.wind_strength

    def wind_strength_text(self):
        winds_strength = ["no", "weak", "strong", "very strong", "hurricane like"]
        ws = self.local_wind_strength()
        ws = clip(int(ws / 10), 0, 5)
        return f"{winds_strength[ws]} winds"

    def local_wind_direction(self):
        return self.entity_data.has_wind_direction + self.wind_direction

    def wind_direction_text(self):

        if self.wind_strength_text() == "no winds":
            return ""
        else:
            winds_direction = ["south", "south-east", "east", "north-east", "north", "north-west", "west", "south-west"]
            wd = self.entity_data.has_wind_direction + self.wind_direction
            wd = int(8.0 * wd / 360) % 8
            return f"from the {winds_direction[wd]}"

    def local_precipitation(self):
        return self.entity_data.has_precipitation + self.precipitation

    def precipitation_text(self):
        rain_strength = ["is a sunny day", "is cloudy", "rains", "rains strongly"]
        rd = self.local_precipitation()
        rd = clip(int(rd / 50), 0, 3)
        return f"{rain_strength[rd]}"

    def local_temperature(self):
        return self.entity_data.has_temperature + self.temperature

    def temperature_text(self):

        r = round(self.local_temperature())
        return f"{r}°C"


class Location(Inspiration):
    def __init__(self, name):
        super().__init__(name)

    def image_url(self, html=None):

        if not validators.url(self.entity_data.iri):
            return None

        if html is None:
            html = requests.get(self.entity_data.iri).text

        return BeautifulSoup(html, "html.parser").findAll("meta", property="og:image")[0]["content"]


def create_table(con):
    sql_create_scene_table = """ CREATE TABLE IF NOT EXISTS Scenes (
                                        server_id ui_text NOT NULL,
                                        channel_id ui_text NOT NULL,
                                        location ui_text NOT NULL,
                                        day int NOT NULL,
                                        wind_strength int NOT NULL,
                                        wind_direction int NOT NULL,
                                        rain int NOT NULL,
                                        temperature int NOT NULL,
                                        active_calendar ui_text NOT NULL); """

    sql_scene_index = f"CREATE UNIQUE INDEX idx_scenes ON Scenes (server_id, channel_id)"

    sql_default_values = f"INSERT OR REPLACE INTO Scenes (server_id, channel_id, location, " \
                         f"day, wind_strength, wind_direction, rain, temperature, active_calendar) " \
                         f"VALUES( 'default_server', 'default_channel', " \
                         f"'Elturel', '0', '0', " \
                         f"'0', '0', '0', 'Calendar_of_Harptos'); "

    sql_create_characters_table = """ CREATE TABLE IF NOT EXISTS Characters (
                                        server_id ui_text NOT NULL,
                                        channel_id ui_text NOT NULL,
                                        name ui_text NOT NULL,
                                        user_id ui_text NOT NULL); """

    sql_characters_index = f"CREATE UNIQUE INDEX idx_characters ON Characters (name, user_id)"

    sql_create_triggers_table = """ CREATE TABLE IF NOT EXISTS Triggers (
                                        server_id ui_text NOT NULL,
                                        channel_id ui_text NOT NULL,
                                        name ui_text NOT NULL,
                                        minutes int NOT NULL); """

    sql_triggers_index = f"CREATE UNIQUE INDEX idx_triggers ON Triggers (server_id, channel_id)"

    # create tables
    if con is not None:
        # create projects table
        con.cursor().execute(sql_create_scene_table)
        con.cursor().execute(sql_scene_index)
        con.cursor().execute(sql_create_characters_table)
        con.cursor().execute(sql_characters_index)
        con.cursor().execute(sql_create_triggers_table)
        con.cursor().execute(sql_triggers_index)
        con.cursor().execute(sql_default_values)

    con.commit()


emojis = {
    "\U0001F304": "sunrise",
    "\U0001F39F": "gather"
}


def find_entity_by_name(to_find):
    max_distance = 0
    found = None

    for f in ONTOLOGY.individuals():
        data = normalize_entity_name(f.name)

        m = SequenceMatcher(None, data, to_find).ratio()

        if m > max_distance:
            max_distance = m
            found = f
        if max_distance >= 1.0:
            return f

    return found
