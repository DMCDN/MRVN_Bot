import discord
from discord import app_commands
from discord.ext import commands

import json
from os import listdir
from datetime import datetime
import logging

logging.basicConfig(filename='MRVNLOG.log', filemode='a', level=logging.DEBUG)

TOKEN = ""

class MRVNBot(commands.Bot):
    def __init__(self):
        self.DEVlist = [429640904463351818,525665069128744962]
        super().__init__(
            command_prefix="!",
            intents=discord.Intents.all()
        )
        

    async def on_ready(self):
        print(">>mrvn is online,good luck,have fun,dont die<<")
        print (f'### {self.user}')
        game = discord.Game(f'')

        slash = await self.tree.sync()
        print(f"載入 {len(slash)} 個slash cmd")
        await self.change_presence(status=discord.Status.idle, activity=game)

            
    async def setup_hook(self):
        await self.load_extension(f'cogs.cog_ext')
        await self.load_extension(f'cogs.cog_apex')
        #await self.load_extension(f'cogs.cog_valorant')
        #for cog in listdir('./cogs'):
        #    if cog.endswith('.py') == True:
        #        await self.load_extension(f'cogs.{cog[:-3]}')
        #await self.tree.sync()


MRVNBot().run(TOKEN)


