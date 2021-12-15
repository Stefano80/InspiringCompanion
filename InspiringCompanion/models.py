from difflib import SequenceMatcher
from sqlite3 import connect
from functools import wraps
from owlready2 import get_ontology
from random import randint
from numpy import clip
from datetime import timedelta
from bs4 import BeautifulSoup
from collections import OrderedDict
from decouple import config
from requests import get
from validators import url

from InspiringCompanion.archivist import Archivist
from InspiringCompanion import writer

TEMPERATURE_VAR = 2
WIND_STRENGTH_VAR = 2
WIND_DIRECTION_VAR = 60
PRECIPITATION_VAR = 20
ONTOLOGY_PATH = config('ONTOLOGY_PATH', default='./resources/inspiration.owl')

ONTOLOGY = get_ontology(ONTOLOGY_PATH).load()


class Director(object):
    def __init__(self, database=":memory:"):
        self.channel = None
        self.server = None
        self.scene = None
        self.database = connect(database)

    def action(self, func):
        @wraps(func)
        async def decorator(ctx, *args, **kwargs):
            self.set_scene_from(ctx.message)
            return await func(ctx, *args, **kwargs)

        decorator.__name__ = func.__name__

        return decorator

    def reaction(self, emoji, user):
        return getattr(self, emojis[emoji])(user)

    def inspiration(self):
        return f"{self.scene.calendar.description()}\n" \
               f"{self.scene.description()}\n" \
               f"{writer.compile_log(self.find_characters(), '', '')}"

    def call_archivist(self):
        return Archivist(self.database, self.server, self.channel)

    def record_scene(self):
        return self.call_archivist().record_scene(self.scene)

    def find_scene(self):
        return self.call_archivist().find_scene()

    def record_character(self, name, user_id):
        return self.call_archivist().record_character(name, user_id)

    def record_my_pc(self, display_name, user_id, provider, provider_id):
        return self.call_archivist().record_my_pc(display_name, user_id, provider, provider_id)

    def find_characters(self):
        return self.call_archivist().find_characters()

    def delete_characters(self):
        return self.call_archivist().delete_characters()

    def find_timers(self):
        return self.call_archivist().find_timers()

    def delete_timers(self):
        return self.call_archivist().delete_timers()

    def find_items(self):
        return self.call_archivist().find_items()

    def set_scene_from(self, message):
        self.server = message.guild.id
        self.channel = message.channel.id

        scene_data = self.find_scene()
        timers_data = self.find_timers()
        inventory_data = self.find_items()

        self.scene = Scene(scene_data, timers_data, inventory_data)

        if scene_data is None:
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

    def sunrise(self, _, day=1):
        sunrise_text = self.scene.sunrise(day)
        self.record_scene()
        self.delete_timers()

        return f" {sunrise_text}...\n\n{self.inspiration()}"

    def gather(self, user):
        self.record_character(user.display_name, user.id)
        return f"{user.display_name} heeds the call to adventure!"

    def disband(self, _):
        self.delete_characters()
        return f"There is nothing to see here"

    def mypc(self, user, provider, provider_id):
        self.record_my_pc(user.display_name, user.id, provider, provider_id)
        return f"{user.display_name} assigned.\nhttps://{provider}.ac/characters/{provider_id}/"

    def one_minute(self, _):
        return self.timegoesby(1)

    def ten_minutes(self, _):
        return self.timegoesby(10)

    def one_hour(self, _):
        return self.timegoesby(60)

    def timegoesby(self, minutes):
        t = self.scene.clock.time_goes_by(minutes)
        output = ""
        if t is not None:
            output += f"The timer {t} just expired. "

        self.record_scene()

        return f"{output}It is {self.scene.clock.time}."

    def addtimer(self, minutes, name=""):
        self.scene.clock.add_timer(name, time_left=minutes)
        self.record_scene()
        return f"{name} timer is set at {self.scene.clock.timers[name]}"

    def additem(self, charges, name):
        self.scene.inventory.add_item(charges, name)
        self.record_scene()
        return f"{charges} {name} added to the scene"

    def log(self, channel_name, messages,):
        user_text = writer.stick_messages_together(messages)
        page = writer.compile_log(self.find_characters(), self.scene.description(), user_text)
        adventure = writer.normalize_entity_name(channel_name).capitalize()
        image = self.scene.location.image_url()
        return adventure, page, image


class Scene(object):

    def __init__(self, scene_data=None, timers_data=None, inventory_data=None):

        if scene_data is None:
            active_calendar = "Calendar of Harptos"
            location = "Elturel"
            day = 1
            weather_data = (0, 0, 0, 0)
            minutes = 8 * 60
        else:
            location = scene_data[2]
            day = int(scene_data[3])
            weather_data = scene_data[4:8]
            active_calendar = scene_data[8]
            minutes = scene_data[9]

        self.calendar = Calendar(active_calendar)
        self.calendar.sunrise(day)

        self.location = Location(location)

        self.weather = Weather(self.location.entity_data.has_climate.name)
        self.weather.seed(weather_data)

        self.clock = Clock()
        self.clock = Clock(time=timedelta(minutes=minutes))

        self.inventory = Inventory()

        if timers_data is not None:
            for r in timers_data:
                if timedelta(minutes=r[1]) > self.clock.time:
                    self.clock.add_timer(r[0], expiring_time=r[1])

        if inventory_data is not None:
            for record in inventory_data:
                self.inventory.add_item(record[1], record[0])

        pass

    def description(self):
        description = f"We are in {self.location.name}. It is {self.clock.time}.\n" \
                      f"It {self.weather.precipitation_text()}. " \
                      f"The temperature is {self.weather.temperature_text()} with {self.weather.wind_strength_text()}"

        if self.weather.wind_strength_text() != "no winds":
            description += f" {self.weather.wind_direction_text()}"

        for n, r in enumerate(self.clock.timers.keys()):
            if r == "midnight":
                break
            if n == 0:
                description += ".\n\nUpcoming events:\n"
            description += f"{r}: {self.clock.timers[r]}\n"

        for n, item in enumerate(self.inventory.items):
            if n == 0:
                description += "\nInventory:\n"
            description += f"{item.charges} {item.name}\n"

        return description

    def sunrise(self, num_sunrises):
        self.calendar.sunrise(num_sunrises)
        self.weather.sunrise(num_sunrises)
        self.inventory.sunrise(num_sunrises)
        self.clock = Clock()
        if num_sunrises == 1:
            return f"One day has passed"
        else:
            return f"Many days have passed"


class Inspiration(object):

    def __init__(self, name):
        self.entity_data = find_entity_by_name(name)
        self.name = writer.normalize_entity_name(self.entity_data.name)


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

    def description(self):
        if self.month.has_days == 1:
            return self.month.name
        else:
            return f"{self.day} {self.month.name}, {self.year}"


class Clock(object):

    def __init__(self, time=timedelta(hours=8)):
        self.time = time
        self.timers = OrderedDict()
        self.add_timer("midnight", expiring_time=24 * 60)

    def time_goes_by(self, minutes):

        target_time = self.time + timedelta(minutes=minutes)
        next_timer = next(iter(self.timers.items()))

        if target_time < next_timer[1]:
            self.time = target_time
            return None
        else:
            self.time = next_timer[1]
            self.timers.pop(next_timer[0])
            return next_timer[0]

    def add_timer(self, name, time_left=None, expiring_time=None):
        if time_left is None and expiring_time is None:
            return
        if time_left is not None and expiring_time is not None:
            return

        if time_left is not None:
            self.timers[name] = self.time + timedelta(minutes=time_left)

        if expiring_time is not None:
            self.timers[name] = timedelta(minutes=expiring_time)

        self.timers = OrderedDict(sorted(self.timers.items(), key=lambda x: x[1]))
        return


class Inventory(object):
    def __init__(self):
        self.items = []

    def add_item(self, charges, name):
        candidate = InventoryItem(name)
        item = next((x for x in self.items if x.entity_data.iri == candidate.entity_data.iri), None)
        if item is None:
            item = InventoryItem(name)
        item.charges += charges
        self.items.append(item)

    def sunrise(self, num_sunrises):
        for item in self.items:
            for n in range(num_sunrises):
                item.recharge()


class InventoryItem(Inspiration):
    def __init__(self, name):
        super().__init__(name)
        self.charges = 0

    def parse_charging_formula(self):
        p = self.entity_data.has_charging_formula.split("/")
        sign = p[0][0]
        freq = p[0][1:]
        return sign, freq, p[1]

    def recharge(self):
        f = self.parse_charging_formula()
        dices = f[2].split("w")
        dices.append(1)  # in case the 1 was omitted
        change = sum([randint(1, int(dices[1])) for _ in range(int(dices[0]))])
        if f[0] == "-":
            self.charges -= change
        else:
            self.charges += change

        self.charges = max(0, self.charges)


class Weather(Inspiration):

    def __init__(self, name):
        super().__init__(name)
        self.temperature = self.entity_data.has_temperature
        self.wind_strength = self.entity_data.has_wind_strength
        self.wind_direction = self.entity_data.has_wind_direction
        self.precipitation = self.entity_data.has_precipitation

    def seed(self, data):
        self.wind_strength = data[0]
        self.wind_direction = data[1]
        self.precipitation = data[2]
        self.temperature = data[3]

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

        if not url(self.entity_data.iri):
            return None

        if html is None:
            html = get(self.entity_data.iri).text

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
                                        active_calendar ui_text NOT NULL,
                                        minutes int NOT NULL); """

    sql_scene_index = f"CREATE UNIQUE INDEX idx_scenes ON Scenes (server_id, channel_id)"

    sql_default_values = f"INSERT OR REPLACE INTO Scenes (server_id, channel_id, location, " \
                         f"day, wind_strength, wind_direction, rain, temperature, active_calendar, minutes) " \
                         f"VALUES( 'default_server', 'default_channel', " \
                         f"'Elturel', '0', '0', " \
                         f"'0', '0', '0', 'Calendar_of_Harptos', '480'); "

    sql_create_characters_table = """ CREATE TABLE IF NOT EXISTS Characters (
                                        server_id ui_text NOT NULL,
                                        channel_id ui_text NOT NULL,
                                        name ui_text NOT NULL,
                                        user_id ui_text NOT NULL,
                                        provider ui_text,
                                        provider_id ui_text); """

    sql_characters_index = f"CREATE UNIQUE INDEX idx_characters ON Characters (name, user_id)"

    sql_create_timers_table = """ CREATE TABLE IF NOT EXISTS Timers (
                                        server_id ui_text NOT NULL,
                                        channel_id ui_text NOT NULL,
                                        name ui_text NOT NULL,
                                        minutes int NOT NULL); """

    sql_create_items_table = """ CREATE TABLE IF NOT EXISTS Items (
                                        server_id ui_text NOT NULL,
                                        channel_id ui_text NOT NULL,
                                        name ui_text NOT NULL,
                                        quantity int NOT NULL,
                                        max_quantity int,
                                        next_recharge int); """

    sql_items_index = f"CREATE UNIQUE INDEX idx_items ON Items (server_id, channel_id, name)"

    # create tables
    if con is not None:
        # create projects table
        con.cursor().execute(sql_create_scene_table)
        con.cursor().execute(sql_scene_index)
        con.cursor().execute(sql_default_values)

        con.cursor().execute(sql_create_characters_table)
        con.cursor().execute(sql_characters_index)
        con.cursor().execute(sql_create_timers_table)
        con.cursor().execute(sql_create_items_table)
        con.cursor().execute(sql_items_index)

    con.commit()

    pass


emojis = {
    "\U0001F304": "sunrise",
    "\U0001F39F": "gather",
    "\U0001F550": "one_minute",
    "\U0001F51F": "ten_minutes",
    u"\u26FA": "one_hour",
    u"\U0001F6D6": "disband"
}


def find_entity_by_name(to_find):
    max_distance = 0
    found = None

    for f in ONTOLOGY.individuals():
        data = writer.normalize_entity_name(f.name)

        m = SequenceMatcher(None, data, to_find).ratio()

        if m > max_distance:
            max_distance = m
            found = f
        if max_distance >= 1.0:
            return f

    return found
