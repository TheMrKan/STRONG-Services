import logging
from typing import Iterable
from discord.ext.commands import Cog
from mysql.connector.aio import MySQLConnectionAbstract
import mysql.connector.aio
import asyncio

from src.config import instance as config


logger = logging.getLogger(__name__)


class PlayersCog(Cog):

    __conn: MySQLConnectionAbstract | None
    __lock: asyncio.Lock

    def __init__(self, bot):
        self.bot = bot
        self.__conn = None
        self.__lock = asyncio.Lock()

    async def get_db_connection_async(self) -> MySQLConnectionAbstract:
        async with self.__lock:
            if self.__conn and await self.__conn.is_connected():
                return self.__conn

        self.__conn = await mysql.connector.aio.connect(host=config.DB_HOST,
                                                        port=config.DB_PORT,
                                                        user=config.DB_USER,
                                                        password=config.DB_PASSWORD)
        return self.__conn

    async def cog_load(self):
        try:
            await self.get_db_connection_async()
        except mysql.connector.Error as err:
            logger.exception("Failed to establish database connection", exc_info=err)

    async def get_player_names_async(self, ids: Iterable[int]) -> dict[int, str]:
        names = {}
        ids = tuple(ids)
        if not any(ids):
            return {}

        async with await (await self.get_db_connection_async()).cursor() as cursor:
            async with self.__lock:
                await cursor.execute(f"SELECT Id, DisplayName FROM server_menu.mrkan_servermenu_users where Id in ({', '.join(['%s'] * len(ids))})", ids)
                result = await cursor.fetchall()

            for i, n in result:
                names[i] = n

        return names

