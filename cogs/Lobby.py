import discord
from discord import app_commands
from discord.ext import commands

class LobbyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot # adding a bot attribute for easier access


async def setup(bot):
    await bot.add_cog(LobbyCog(bot=bot))