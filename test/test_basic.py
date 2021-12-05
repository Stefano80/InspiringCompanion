import unittest

import InspiringCompanion.models
import InspiringCompanion.writer
from InspiringCompanion import models
from random import seed
from unittest.mock import Mock


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
        self.assertEqual(f"22 Hammer, 1", c.status_text())
        c.sunrise(9)
        self.assertEqual("Midwinter", c.month.name)
        self.assertEqual(f"Midwinter", c.status_text())
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
        scene = models.Scene(calendar="Calendar of Harptos", location="Elturel")
        w.sunrise(1)
        self.assertIsNotNone(scene)

    def test_sqlite_connection(self):
        d = models.Director(channel="default_channel", server="default_server")

        models.create_table(d.database)

        select = f"SELECT * FROM Scenes WHERE guild_id = 'default_server' AND channel_id = 'default_channel'"
        row = d.database.cursor().execute(select).fetchone()
        self.assertEqual('default_server', row[0])
        self.assertEqual('default_channel', row[1])
        self.assertEqual('Elturel', row[2])

    def test_set_scene(self):
        mock = Mock()
        mock.guild.id = "default"
        mock.channel.id = "default"

        director = models.Director(channel="default", server="default")
        models.create_table(director.database)
        director.set_scene_from(mock)
        self.assertEqual(1, director.scene.calendar.day)

    def test_scene_description(self):
        scene = models.Scene(calendar="Calendar_of_Harptos", location="Elturel")
        self.assertIsNotNone(scene.description())
        self.assertTrue("We are in Elturel" in scene.description())


class TestLocation(unittest.TestCase):
    def test_image_url(self):
        with open("elturel_page.html", "r") as file:
            data = file.read().replace('\n', '')

        # this is a bit of a cheat that I am using to avoid hitting the fandom page continuously
        self.assertIsNotNone(models.Location("Elturel").image_url(html=data))
        self.assertIsNone(models.Location("NorthClimate").image_url())


