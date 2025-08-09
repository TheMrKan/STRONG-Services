import a2s
from discord.ext import commands, tasks
from discord import (Client, Status, Activity, ActivityType, TextChannel,
                     Message, Embed)
import discord.colour
import traceback
import datetime

from src import config


class ServerInfoCog(commands.Cog):
    bot: Client
    channel: TextChannel
    message: Message | None

    current_displayed_online: int

    def __init__(self, bot: Client):
        self.bot = bot
        self.current_displayed_online = 0

    async def cog_load(self):
        self.channel = await self.bot.fetch_channel(config.instance.server_info.channel)
        self.message = await self.find_status_message_async()

        self.server_info_updater.start()

    async def find_status_message_async(self) -> Message | None:
        async for message in self.channel.history(limit=10):
            if message.author == self.bot.user:
                return message

    def cog_unload(self):
        self.server_info_updater.cancel()

    @tasks.loop(seconds=config.instance.server_info.interval)
    async def server_info_updater(self):
        await self.update_server_info_async()

    @server_info_updater.before_loop
    async def before_updater(self):
        await self.bot.wait_until_ready()

    async def update_server_info_async(self):
        info = await self.get_server_info_async()
        if info.player_count == self.current_displayed_online:
            return

        self.current_displayed_online = info.player_count
        try:
            await self.update_status_async(info.player_count, info.max_players)
        except:
            traceback.print_exc()

        try:
            await self.update_message_async(info.player_count, info.max_players, info.server_name, config.instance.server_info.server[0], info.port)
        except:
            traceback.print_exc()

    @staticmethod
    async def get_server_info_async():
        return await a2s.ainfo(config.instance.server_info.server)

    async def update_status_async(self, current_players: int, max_players: int):
        await self.bot.change_presence(
            status=Status.online,
            activity=Activity(
                name=f"Онлайн: {current_players}/{max_players}",
                type=ActivityType.watching))

    async def update_message_async(self, current_players: int, max_players: int, server_name: str, host: str, port: int):
        embed = self.build_status_message_embed(current_players, max_players, server_name, host, port)
        if self.message:
            await self.message.edit(embed=embed)
        else:
            self.message = await self.channel.send(embed=embed)

    @staticmethod
    def build_status_message_embed(current_players, max_players, server_name, host, port) -> Embed:
        embed = Embed(title="Информация о сервере",
                      color=discord.colour.parse_hex_number("008000"),
                      description=f"**Текущий онлайн:** {current_players}/{max_players}",
                      timestamp=datetime.datetime.now())
        embed.add_field(name=f"**{server_name}**", value=f"IP: `{host}:{port}`")
        return embed
