from unittest.mock import Mock
from InspiringCompanion import models


def setup_director(server, channel):
    mock = Mock()
    mock.guild.id = server
    mock.channel.id = channel

    director = models.Director()
    models.create_table(director.database)
    director.set_scene_from(mock)
    return director
