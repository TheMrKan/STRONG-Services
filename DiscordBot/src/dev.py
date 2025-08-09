from discord.ext.commands import Cog
import discord

from src import config


class DevCog(Cog):
    def __init__(self, bot):
        self.bot = bot

    @Cog.listener("on_message")
    async def on_message(self, message: discord.Message):
        if message.content != "#STRONG message":
            return

        if message.author.id not in config.instance.owners:
            return

        reply = await message.channel.send("Message")
        await reply.edit(content=f"**Channel ID:** {reply.channel.id}\n**Message ID:** {reply.id}")
