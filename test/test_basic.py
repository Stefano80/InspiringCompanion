import unittest

import InspiringCompanion.models
import InspiringCompanion.writer
from InspiringCompanion import models
from random import seed
from unittest.mock import Mock
from datetime import datetime, timedelta
from . import utils


class TestClock(unittest.TestCase):

    def test_basics(self):
        clock = models.Clock()
        self.assertIsNotNone(clock)
        self.assertEqual(timedelta(hours=8), clock.time)
        p = clock.time_goes_by(12)
        self.assertEqual(None, p)
        self.assertEqual(timedelta(hours=8, minutes=12), clock.time)
        p = clock.time_goes_by(20 * 60)
        self.assertEqual("midnight", p)

    def test_add_timer(self):
        clock = models.Clock()
        self.assertIsNotNone(clock)
        self.assertEqual(timedelta(hours=8), clock.time)
        clock.add_timer("fireball", time_left=60)
        self.assertEqual(timedelta(hours=9), clock.timers["fireball"])
        p = clock.time_goes_by(24 * 60)
        self.assertEqual("fireball", p)

    def test_time_triggers(self):
        clock = models.Clock()
        clock.add_timer("fireball", time_left=60)
        expired = clock.time_goes_by(75)
        self.assertEqual("fireball", expired)

    def test_table(self):
        d = utils.setup_director("default_server", "default_channel")
        d.record_scene()

        select = f"SELECT * FROM Timers WHERE server_id = 'default_server' AND channel_id = 'default_channel'"
        row = d.database.cursor().execute(select).fetchone()

        self.assertEqual("default_server", row[0])
        self.assertEqual("default_channel", row[1])
        self.assertEqual("midnight", row[2])
        self.assertEqual(24 * 60, row[3])

    def test_reactions(self):
        d = utils.setup_director("default_server", "default_channel")

        self.assertEqual("It is 8:01:00.", d.one_minute(None))
        self.assertEqual("It is 8:11:00.", d.ten_minutes(None))
        self.assertEqual("It is 9:11:00.", d.one_hour(None))


class TestInspiration(unittest.TestCase):
    def test_init(self):
        x = models.Inspiration("Elturel")
        self.assertEqual("Elturel", x.name)
        self.assertEqual("Elturel", x.entity_data.name)
        h = models.Inspiration("Hammer")
        self.assertEqual("Hammer", h.entity_data.name)
        c = models.Inspiration("Calendar of Harptos")
        self.assertEqual("Calendar_of_Harptos", c.entity_data.name)
        self.assertEqual("Calendar of Harptos", c.name)
        b = models.Inspiration("baldurs gate")
        self.assertEqual("Baldur%27s_Gate", b.entity_data.name)
        self.assertEqual("Baldurs Gate", b.name)


class TestCalendar(unittest.TestCase):
    def test_calendar_init(self):
        c = models.Calendar("Calendar of Harptos")
        self.assertEqual("Calendar_of_Harptos", c.entity_data.name)
        self.assertEqual(c.minute, 0)
        self.assertEqual(c.hour, 0)
        self.assertEqual(c.day, 0)
        self.assertEqual("Hammer", c.month.name)
        self.assertEqual(c.year, 1)

    def test_month_length(self):
        h = InspiringCompanion.models.find_entity_by_name("Hammer")
        self.assertEqual(h.has_days, 30)

    def test_sunrise_many_years(self):
        c = models.Calendar("Calendar of Harptos")
        c.sunrise(364 * 100 + 20)
        self.assertEqual(c.year, 101)

    def test_calendar_sunrise(self):
        c = models.Calendar("Calendar of Harptos")
        c.sunrise(1)
        self.assertEqual(c.day, 1)
        c.sunrise(1)
        self.assertEqual(c.day, 2)
        c.sunrise(20)
        self.assertEqual(22, c.day)
        self.assertEqual(f"22 Hammer, 1", c.description())
        c.sunrise(9)
        self.assertEqual("Midwinter", c.month.name)
        self.assertEqual(f"Midwinter", c.description())
        c.sunrise(1)
        self.assertEqual("Alturiak", c.month.name)
        c.sunrise(333)
        self.assertEqual("Hammer", c.month.name)
        self.assertEqual(1, c.day)
        self.assertEqual(2, c.year)
        c.sunrise(364 * 1000)
        self.assertEqual(1002, c.year)


class TestOntology(unittest.TestCase):
    def test_existence(self):
        self.assertIsNotNone(models.ONTOLOGY)


class TestFindEntityByName(unittest.TestCase):
    def test_some(self):
        self.assertEqual(InspiringCompanion.models.find_entity_by_name("Hammer").name, "Hammer")
        self.assertEqual(InspiringCompanion.models.find_entity_by_name("baldurs gate").name, "Baldur%27s_Gate")
        self.assertTrue("forgottenrealms.fandom.com" in InspiringCompanion.models.find_entity_by_name("Elturel").iri)
        pass


class TestWeather(unittest.TestCase):
    def test_existence(self):
        c = models.Weather("North Climate")
        self.assertEqual("North Climate", c.name)
        self.assertEqual("NorthClimate", c.entity_data.name)

    def test_init(self):
        c = models.Weather("North Climate")
        self.assertEqual(c.entity_data.has_temperature, c.temperature)
        self.assertEqual(c.entity_data.has_wind_strength, c.wind_strength)
        self.assertEqual(c.entity_data.has_wind_direction, c.wind_direction)
        self.assertEqual(c.entity_data.has_precipitation, c.precipitation)

    def test_sunrise(self):
        c = models.Weather("North Climate")

        seed(121)
        c.sunrise(1)
        self.assertEqual(4.0, c.temperature)
        self.assertEqual("16°C", c.temperature_text())

        self.assertEqual(4.0, c.wind_strength)
        self.assertEqual("weak winds", c.wind_strength_text())

        self.assertEqual(104.0, c.wind_direction)
        self.assertEqual("from the west", c.wind_direction_text())

        self.assertEqual(35.0, c.precipitation)
        self.assertEqual("is cloudy", c.precipitation_text())


class TestScene(unittest.TestCase):

    def test_exist(self):
        w = models.Weather("North Climate")
        scene = models.Scene()
        w.sunrise(1)
        self.assertIsNotNone(scene)

    def test_sqlite_connection(self):
        d = models.Director()
        d.server = "default_server"
        d.channel = "default_channel"

        models.create_table(d.database)

        select = f"SELECT * FROM Scenes WHERE server_id = 'default_server' AND channel_id = 'default_channel'"
        row = d.database.cursor().execute(select).fetchone()
        self.assertEqual('default_server', row[0])
        self.assertEqual('default_channel', row[1])
        self.assertEqual('Elturel', row[2])

    def test_set_scene(self):
        director = utils.setup_director("default", "default")
        self.assertEqual(1, director.scene.calendar.day)

    def test_scene_description(self):
        scene = models.Scene()
        self.assertIsNotNone(scene.description())
        self.assertTrue("We are in Elturel" in scene.description())


class TestLocation(unittest.TestCase):
    def test_image_url(self):
        data = '<meta property="og:image" content="https://static.wikia.nocookie.net/forgottenrealms/images/3/35' \
               '/Hellrider_ward_token.jpg/revision/latest?cb=20190919135150"/> '

        self.assertIsNotNone(models.Location("Elturel").image_url(html=data))
        self.assertIsNone(models.Location("NorthClimate").image_url())


class TestItems(unittest.TestCase):
    def testCharging(self):
        ration = models.InventoryItem("ration")
        ration.charges = 1
        self.assertIsNotNone(ration.entity_data)
        self.assertEqual(("-", "1", "1w1"), ration.parse_charging_formula())
        ration.recharge()
        self.assertEqual(0, ration.charges)

        wand = models.InventoryItem("wand of fireballs")
        for n in range(10):
            wand.charges = 10
            wand.recharge()
            self.assertLess(10, wand.charges)
            self.assertLess(wand.charges, 15)

        wand.entity_data.has_charging_formula = "1/0w20"
        for n in range(20):
            wand.charges = n
            wand.recharge()
            self.assertEqual(n, wand.charges)

    def testSceneIntegration(self):
        mock = Mock()
        mock.guild.id = "default"
        mock.channel.id = "default"

        director = utils.setup_director(mock.guild.id, mock.channel.id)
        director.additem(20, "ration")
        self.assertEqual(20, director.scene.inventory.items[0].charges)

        director.set_scene_from(mock)
        self.assertEqual(20, director.scene.inventory.items[0].charges)

        director.additem(20, "ration")

        director.set_scene_from(mock)
        self.assertEqual(40, director.scene.inventory.items[0].charges)
        self.assertEqual(1, len(director.scene.inventory.items))

        director.sunrise(None, 1)
        self.assertEqual(39, director.scene.inventory.items[0].charges)
        self.assertEqual(1, len(director.scene.inventory.items))

        director.additem(-10, "ration")
        self.assertEqual(29, director.scene.inventory.items[0].charges)
