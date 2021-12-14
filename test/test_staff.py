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

    def test_director(self):
        director = utils.setup_director("default", "default")
        self.assertEqual("Elturel", director.scene.location.name)

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

        t = director.scene.weather.local_temperature()
        d = director.scene.calendar.day
        text = director.move_scene_to("baldurs Gate")
        self.assertEqual("We move to Baldurs Gate", text)
        self.assertEqual(t, director.scene.weather.local_temperature())
        self.assertEqual(d, director.scene.calendar.day)
        director.move_scene_to("Neverwinter")
        self.assertEqual(t - 8, director.scene.weather.local_temperature())
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

    def test_addtriger(self):
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
        mock_i.author = "Me"
        mock_you = Mock()
        mock_you.content = "You"
        mock_you.author = "Me"
        mock_he = Mock()
        mock_he.content = "He"
        mock_he.author = "Me"

        res = writer.stick_messages_together([mock_i, mock_you, mock_he], "")
        self.assertEqual("He You ", res)

        mock_he.author = "he"
        res = writer.stick_messages_together([mock_i, mock_you, mock_he], "")
        self.assertEqual("You ", res)

        mock_you.content = "#You"
        mock_he.author = "Me"

        res = writer.stick_messages_together([mock_i, mock_you, mock_he], "#")
        self.assertEqual("He ", res)
