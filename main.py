from nextcord.ext import commands
from nextcord import Embed
from decouple import config

from InspiringCompanion.models import Director, emojis

BOT_URL = config('BOT_URL')
ICON_URL = config('ICON_URL')
BOT_TOKEN = config('BOT_TOKEN')
DATABASE = config('DATABASE', default=':memory:')

client = commands.Bot(command_prefix='!')  # put your own prefix here
director = Director(database=DATABASE)


@client.event
async def on_ready():
    print("Inspiring Companion online")
    return


# Note: in order to implement cogs, I should change the decorator in models.py as it will get the instance as a first
# argument


@client.command()
@director.action
async def inspiration(discord_context):
    """
    Gives some inspiration about the current scene
    """
    message = await discord_context.send(director.inspiration())
    reactions = ["sunrise", "one_minute", "ten_minutes", "one_hour"]
    for e in emojis:
        if emojis[e] in reactions:
            await message.add_reaction(e)
    pass


@client.command()
@director.action
async def gather(discord_context):
    """
    Gather the party for a new adventure
    Whoever wants to join clicks on the ticket reaction.
    """
    message = await discord_context.send(f"{director.inspiration()}\nThe adventure's call lingers in the air...")
    for e in emojis:
        if emojis[e] in ["gather", "disband"]:
            await message.add_reaction(e)
    pass


@client.command()
@director.action
async def moveto(discord_context, *arg):
    """
    Move the party to a new adventurous place, e.g. !moveto Elturel
    """
    destination = " ".join(arg)
    await discord_context.send(director.move_scene_to(destination))
    pass


@client.command()
@director.action
async def addtimer(discord_context, *arg):
    """
    Add a nice timer
    Time is measured in minutes, e.g. !addtimer 22 shield of faith
    """
    minutes = int(arg[0])
    name = " ".join(arg[1:])
    await discord_context.send(director.addtimer(minutes, name=name))
    pass


@client.command()
@director.action
async def additem(discord_context, *arg):
    """
    Add an item
    The second argument is the quantity, e.g. !additem 22 ration
    """
    charges = int(arg[0])
    name = " ".join(arg[1:])
    await discord_context.send(director.additem(charges, name=name))
    pass


@client.command()
@director.action
async def sunrise(discord_context, *arg):
    """
    Let one (or more) day pass, e.g. !sunrise or !sunrise 100
    """
    if len(arg) == 0:
        num_days = 1
    else:
        num_days = int(arg[0])
    await discord_context.send(director.sunrise(None, day=num_days))
    pass


@client.command()
@director.action
async def timegoesby(discord_context, *arg):
    """
    Let some time pass, e.g. !timegoesby 25
    Time is measured in minutes, and it stops if a timer expires
    """
    if len(arg) == 0:
        num_minutes = 1
    else:
        num_minutes = int(arg[0])
    await discord_context.send(director.timegoesby(num_minutes))
    pass


@client.command()
@director.action
async def log(ctx):
    """
    Create a summary of the current scene
    It uses the last messages from the user issuing the command
    """
    messages = []
    async for m in ctx.channel.history(limit=20, oldest_first=False):
        messages.append(m)

    adventure, page, image = director.log(ctx.channel.name, messages, await client.get_prefix(ctx.message))

    nice_log_page = Embed(title=adventure, color=0x109319)
    nice_log_page.set_author(name="Inspiring Companion", url=BOT_URL, icon_url=ICON_URL)
    nice_log_page.add_field(name=director.scene.calendar.description(), value=page, inline=True)
    if image is not None:
        nice_log_page.set_thumbnail(url=image)

    await ctx.send(embed=nice_log_page)

    pass


@client.event
@director.action
async def on_reaction_add(reaction, user):
    if user.bot or reaction.emoji not in emojis.keys():
        return

    channel = client.get_channel(director.channel)
    await channel.send(director.reaction(reaction.emoji, user))

    pass


client.run(BOT_TOKEN)
