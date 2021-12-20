from typing_extensions import Required
import nextcord
from nextcord.ext import commands
import os
import json

intents = nextcord.Intents.default()
intents.members = True

with open("config.json", encoding="utf-8") as config:
    config = json.load(config)

testing = False

client = commands.Bot(command_prefix=config['prefix'],
                      case_insensitive=True, intents=intents)

client.remove_command('help')


@client.event
async def on_ready():
    print('Entramos como {0.user}'.format(client))

    await client.change_presence(activity=nextcord.Activity(type=nextcord.ActivityType.listening, name="!help"))



for filename in os.listdir('./cogs'):
    if filename.endswith('.py'):
        client.load_extension(f'cogs.{filename[:-3]}')

client.run(config['token'])
