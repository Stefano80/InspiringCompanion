from nextcord.ext import commands
from nextcord import Embed
import os
from decouple import config

import InspiringCompanion.writer
from InspiringCompanion import models, writer

BOT_URL = config('BOT_URL')
ICON_URL = config('ICON_URL')
BOT_TOKEN = config('BOT_TOKEN')
DATABASE = config('DATABASE', default=':memory:')

client = commands.Bot(command_prefix='!')  # put your own prefix here
director = models.Director(database=DATABASE)

if not os.path.exists(DATABASE):
    models.create_table(director.database)


@client.event
async def on_ready():
    print("Inspiring Companion online")
    return


@client.command()
@director.action
async def inspiration(discord_context):
    """
    Gives some inspiration about the current scene
    """
    message = await discord_context.send(director.short_log())
    for e in models.emojis:
        if models.emojis[e] == "sunrise":
            await message.add_reaction(e)
    pass


@client.command()
@director.action
async def gather(discord_context):
    """
    Gather the party for a new adventure
    """
    message = await discord_context.send(f"{director.short_log()}\nThe adventure's call lingers in the air...")
    for e in models.emojis:
        if models.emojis[e] == "gather":
            await message.add_reaction(e)
    pass


@client.command()
@director.action
async def moveto(discord_context, *arg):
    """
    Move the party to a new adventurous place
    """
    destination = " ".join(arg)
    await discord_context.send(director.move_scene_to(destination))
    pass


@client.command()
@director.action
async def sunrise(discord_context, *arg):
    """
    Let one day pass
    """
    if len(arg) == 0:
        num_days = 1
    else:
        num_days = int(arg[0])
    await discord_context.send(director.sunrise(None, day=num_days))
    pass


@client.command()
@director.action
async def log(discord_context):
    """
    Create a summary of the current day using the last messages from the user
    """
    adventure = InspiringCompanion.writer.normalize_entity_name(discord_context.channel.name).capitalize()
    image = director.scene.location.image_url()
    user_text = await writer.stick_messages_together(discord_context.channel, [discord_context.prefix])

    page = writer.compile_log(director.find_characters(), director.scene.description(), user_text)

    nice_log_page = Embed(title=adventure, color=0x109319)
    nice_log_page.set_author(name="Inspiring Companion", url=BOT_URL, icon_url=ICON_URL)
    nice_log_page.add_field(name=director.scene.calendar.status_text(), value=page, inline=True)

    if image is not None:
        nice_log_page.set_thumbnail(url=image)

    message = await discord_context.send(embed=nice_log_page)

    pass


@client.event
@director.action
async def on_reaction_add(reaction, user):
    if user.bot or reaction.emoji not in models.emojis.keys():
        return

    channel = client.get_channel(director.channel)
    await channel.send(director.reaction(reaction.emoji, user))

    pass


client.run(BOT_TOKEN)
