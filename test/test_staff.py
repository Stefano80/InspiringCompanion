import asyncio
import unittest

import InspiringCompanion.models
import InspiringCompanion.writer
from InspiringCompanion import models, writer
from unittest.mock import Mock
import datetime
from . import utils


class TestArchivist(unittest.TestCase):

    def test_disband(self):
        director = utils.setup_director("default_server", "default_channel")
        director.record_character("Alwen", "Ste")
        self.assertEqual(1, len(director.find_characters()))
        director.disband(None)
        self.assertEqual(0, len(director.find_characters()))


class TestDirector(unittest.TestCase):

    def testAddingItems(self):
        director = utils.setup_director("default_server", "default_channel")
        director.additem(13, "Wand of Fireballs")

        self.assertEqual(1, len(director.scene.inventory.items))
        mock = Mock()
        mock.guild.id = "default_server"
        mock.channel.id = "default_channel"

        director.set_scene_from(mock)
        director.additem(18, "Wand of Fireballs")
        self.assertEqual(2, len(director.scene.inventory.items))

        director.set_scene_from(mock)
        self.assertEqual(2, len(director.scene.inventory.items))

    def testBulkCharging(self):
        director = utils.setup_director("default_server", "default_channel")
        mock = Mock()
        mock.id = "user1"
        mock.display_name = "pc1"
        director.gather(mock)
        mock.id = "user2"
        mock.display_name = "pc2"
        director.gather(mock)
        director.additem(1, "Ration")
        director.scene.inventory.items[0].charges = 100
        director.sunrise(None)
        self.assertEqual(98, director.scene.inventory.items[0].charges)
        mock.id = "user3"
        mock.display_name = "pc3"
        director.gather(mock)
        director.sunrise(None)
        self.assertEqual(95, director.scene.inventory.items[0].charges)
        director.sunrise(None)

        mock = Mock()
        mock.guild.id = "default_server"
        mock.channel.id = "default_channel"
        director.set_scene_from(mock)

        self.assertEqual(92, director.scene.inventory.items[0].charges)

    def testNormalItems(self):
        director = utils.setup_director("default_server", "default_channel")
        director.additem(13, "Wand of Fireballs")

        self.assertEqual(1, len(director.scene.inventory.items))
        director.additem(18, "Wand of Fireballs")
        self.assertEqual(2, len(director.scene.inventory.items))
        director.additem(4, "Wand of Fireballs")
        self.assertEqual(3, len(director.scene.inventory.items))

        mock = Mock()
        mock.guild.id = "default_server"
        mock.channel.id = "default_channel"

        director.set_scene_from(mock)
        self.assertEqual(3, len(director.scene.inventory.items))
        self.assertEqual(13, director.scene.inventory.items[0].charges)
        self.assertEqual(18, director.scene.inventory.items[1].charges)
        self.assertEqual(4, director.scene.inventory.items[2].charges)

        director.sunrise(None)
        self.assertEqual(3, len(director.scene.inventory.items))

    def testNormalCharging(self):
        director = utils.setup_director("default_server", "default_channel")
        director.additem(0, "Wand of Fireballs")
        self.assertEqual(0, director.scene.inventory.items[0].charges)
        mock = Mock()
        mock.guild.id = "default_server"
        mock.channel.id = "default_channel"
        director.set_scene_from(mock)

        def f():
            return director.scene.inventory.items[0].charges

        old_charges = f()
        self.assertEqual(0, old_charges)

        for n in range(20):
            director.sunrise(None)
            director.set_scene_from(mock)
            f() > old_charges
            old_charges = f()

    def test_log(self):
        mock_i = Mock()
        mock_i.content = "log"
        mock_i.author.display_name = "Me"
        mock_i.bot = False
        mock_you = Mock()
        mock_you.content = "You"
        mock_you.author.display_name = "Me"
        mock_you.author.bot = False

        director = utils.setup_director("default_server", "default_channel")
        director.log("default_channel", [mock_i, mock_you])

    def test_gather(self):
        director = utils.setup_director("default_server", "default_channel")
        mock = Mock()
        mock.id = "A user"
        mock.display_name = "A character"
        director.gather(mock)
        chars = director.find_characters()
        self.assertEqual({"A character"}, chars)

    def test_dismiss(self):
        director = utils.setup_director("default_server", "default_channel")
        mock = Mock()
        mock.id = "A user"
        mock.display_name = "A character"
        director.gather(mock)
        chars = director.find_characters()
        self.assertEqual({"A character"}, chars)
        director.dismiss("character")
        self.assertEqual({"A character"}, chars)
        director.dismiss("A character")
        chars = director.find_characters()
        self.assertEqual(set(), chars)

    def test_action(self):
        director = utils.setup_director("default", "default")

        async def test_function(_):
            return 1

        decorator = director.action(test_function)
        decorated = decorator(test_function)

        self.assertEqual(decorator.__name__, "test_function")
        self.assertTrue(asyncio.iscoroutine(decorated))

    def test_director(self):
        director = utils.setup_director("default", "default")
        self.assertEqual("Elturel", director.scene.location.name)

    def test_reaction(self):
        director = utils.setup_director("default", "default")
        rev = {value: key for (key, value) in models.emojis.items()}
        self.assertEqual("It is 8:01:00.", director.reaction(rev["one_minute"], None))
        self.assertEqual("It is 8:11:00.", director.reaction(rev["ten_minutes"], None))
        self.assertEqual("It is 9:11:00.", director.reaction(rev["one_hour"], None))
        self.assertEqual("The party has been disbanded", director.reaction(rev["disband"], None))

    def test_database_commit(self):
        director = utils.setup_director("default02", "default02")

        row = director.database.cursor().execute(
            "SELECT server_id, day FROM Scenes WHERE channel_id = 'default02'").fetchone()
        self.assertEqual("default02", row[0])
        self.assertEqual(1, row[1])

        director.sunrise(None, day=10)
        row = director.database.cursor().execute(
            "SELECT server_id, day FROM Scenes WHERE channel_id = 'default02'").fetchone()
        self.assertEqual("default02", row[0])
        self.assertEqual(11, row[1])

        mock = Mock()
        mock.guild.id = "default02"
        mock.channel.id = "default02"

        director.set_scene_from(mock)
        row = director.database.cursor().execute(
            "SELECT server_id, day FROM Scenes WHERE channel_id = 'default02'").fetchone()
        self.assertEqual("default02", row[0])
        self.assertEqual(11, row[1])

    def test_moveto(self):
        director = utils.setup_director("default_server", "default_channel")
        neutral = models.ONTOLOGY.search(iri="*NeutralSeason")[0]

        t = director.scene.weather.local_temperature(neutral)
        d = director.scene.calendar.day
        text = director.move_scene_to("baldurs Gate")
        self.assertEqual("We move to Baldurs Gate", text)
        self.assertEqual(t, director.scene.weather.local_temperature(neutral))
        self.assertEqual(d, director.scene.calendar.day)
        director.move_scene_to("Neverwinter")
        self.assertEqual(t - 8, director.scene.weather.local_temperature(neutral))
        text = director.move_scene_to("Neverwinter")
        self.assertEqual("We already are in Neverwinter", text)

        mock = Mock()
        mock.guild.id = "default_server"
        mock.channel.id = "default_channel"
        director.set_scene_from(mock)
        self.assertEqual("Neverwinter", director.scene.location.name)

    def test_sunrise(self):
        director = utils.setup_director("default_server", "default_channel")

        director.sunrise(None, day=3)
        self.assertEqual(3, director.scene.calendar.day)

        mock = Mock()
        mock.guild.id = "default_server"
        mock.channel.id = "default_channel"
        director.set_scene_from(mock)
        self.assertEqual(3, director.scene.calendar.day)

    def test_record_character(self):
        director = utils.setup_director("default_server", "default_channel")

        director.record_character("Dorn", "default")
        row = director.database.cursor().execute(
            "SELECT server_id, name FROM Characters WHERE server_id = 'default_server'").fetchone()

        self.assertEqual("Dorn", row[1])

    def test_find_characters(self):
        director = utils.setup_director("default_server", "default_channel")

        director.record_character("Dorn", "default01")
        director.record_character("Alwen Moonruby", "default02")

        self.assertEqual({"Dorn", "Alwen Moonruby"}, director.find_characters())

    def test_addtrigger(self):
        director = utils.setup_director("default_server", "default_channel")

        director.addtimer(60, "fireball")

        self.assertEqual(2, len(director.scene.clock.timers))
        self.assertTrue("fireball" in director.scene.clock.timers.keys())
        self.assertTrue("midnight" in director.scene.clock.timers.keys())
        self.assertEqual(datetime.timedelta(hours=9), director.scene.clock.timers["fireball"])
        self.assertEqual(datetime.timedelta(hours=24), director.scene.clock.timers["midnight"])

    def test_timegoesby(self):
        director = utils.setup_director("default_server", "default_channel")
        director.addtimer(60, "fireball")
        director.timegoesby(75)
        self.assertEqual(datetime.timedelta(hours=9), director.scene.clock.time)

        mock = Mock()
        mock.guild.id = "default_server"
        mock.channel.id = "default_channel"
        director.set_scene_from(mock)
        director.timegoesby(60)
        self.assertEqual(datetime.timedelta(hours=10), director.scene.clock.time)

    def test_mypc(self):
        director = utils.setup_director("default_server", "default_channel")
        director.record_character("Alwen Moonruby", "default_user")
        mock = Mock()
        mock.display_name = "Alwen Moonruby"
        mock.id = "default_user"
        director.mypc(mock, 'ddb', '19323298')
        select = f"SELECT provider, provider_id FROM Characters WHERE name = 'Alwen Moonruby'"
        row = director.database.cursor().execute(select).fetchone()
        self.assertEqual('ddb', row[0])
        self.assertEqual('19323298', row[1])


class TestWriter(unittest.TestCase):

    def test_log_entry(self):
        log_entry = writer.compile_log(["Dorn", "Alwen Moonruby"], "A nice scene.", "We lorem ipsum in the table.")
        expected = "Dorn, Alwen Moonruby heeded the adventure's call. A nice scene. We lorem ipsum in the table."

        self.assertEqual(expected, log_entry)

        log_entry = writer.compile_log(["Alwen Moonruby"], "A nice scene.", "We lorem ipsum in the table.")
        expected = "Alwen Moonruby heeded the adventure's call. A nice scene. We lorem ipsum in the table."

        self.assertEqual(expected, log_entry)

        log_entry = writer.compile_log([], "A nice scene.", "We lorem ipsum in the table.")
        expected = "A nice scene. We lorem ipsum in the table."

        self.assertEqual(expected, log_entry)

        log_entry = writer.compile_log(["Dorn", "Alwen Moonruby"], "A nice scene.", '')
        expected = "Dorn, Alwen Moonruby heeded the adventure's call. A nice scene. "

        self.assertEqual(expected, log_entry)

        pass

    def test_normalizer(self):
        self.assertEqual("baldurs gate", InspiringCompanion.writer.normalize_entity_name("baldurs_gate"))
        self.assertEqual("Baldurs Gate", InspiringCompanion.writer.normalize_entity_name(
            InspiringCompanion.models.find_entity_by_name("baldurs gate").name))
        self.assertEqual("the goal", InspiringCompanion.writer.normalize_entity_name("the-goal"))

    def test_stick_messages(self):
        mock_i = Mock()
        mock_i.content = "log"
        mock_i.author.display_name = "Me"
        mock_i.author.bot = False

        mock_you = Mock()
        mock_you.content = "You"
        mock_you.author.display_name = "Me"
        mock_you.author.bot = False
        mock_he = Mock()
        mock_he.content = "He"
        mock_he.author.display_name = "Me"
        mock_he.author.bot = False

        res = writer.stick_messages_together([mock_i, mock_you, mock_he])
        self.assertEqual("He You ", res)

        mock_he.author.display_name = "he"
        mock_he.author.bot = False
        res = writer.stick_messages_together([mock_i, mock_you, mock_he])
        self.assertEqual("He You ", res)

        mock_you.content = "§You"
        mock_he.author.display_name = "Me"
        mock_he.author.bot = False

        res = writer.stick_messages_together([mock_i, mock_you, mock_he])
        self.assertEqual("He ", res)
