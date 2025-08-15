import discord
from discord.ext.commands import Bot
import asyncio
import logging
from discord import utils
from typing import TYPE_CHECKING
from threading import Event

from src import globals, config


logger = logging.getLogger("main")
bot_ready_event = Event()
bot_exception : Exception | None = None


class MyBot(Bot):
    
    async def on_ready(self):
        from src.server_info import ServerInfoCog
        from src.permission_groups.cog import PermissionGroupsCog
        from src.dev import DevCog

        info_cog = self.add_cog(ServerInfoCog(self))
        permissions_cog = self.add_cog(PermissionGroupsCog(self))
        dev_cog = self.add_cog(DevCog(self))

        await asyncio.gather(info_cog, permissions_cog, dev_cog)
        bot_ready_event.set()
        logger.info("Custom bot is ready")


def setup_bot():
    intents = discord.Intents.default()
    intents.message_content = True

    globals.bot = MyBot("!", intents=intents)


def setup_discord_client():
    intents = discord.Intents.default()
    intents.message_content = True

    globals.bot = discord.Client(intents=intents)

    @globals.bot.event
    async def on_ready():
        print("Bot is ready. Setting event...")
        bot_ready_event.set()


async def run_async(setup_logging: bool = True):
    # из discord.client.Client.run

    async def runner():
        try:
            async with globals.bot:
                await globals.bot.start(str(config.instance.BOT_TOKEN), reconnect=True)
        except Exception as e:
            global bot_exception
            bot_exception = e
            bot_ready_event.set()

    if setup_logging:
        utils.setup_logging(
            handler=utils.MISSING,
            formatter=utils.MISSING,
            level=utils.MISSING,
            root=False,
        )

    try:
        await runner()
    except KeyboardInterrupt:
        # nothing to do here
        # `asyncio.run` handles the loop cleanup
        # and `self.start` closes all sockets and the HTTPClient instance.
        return
