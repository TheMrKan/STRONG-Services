from typing import TYPE_CHECKING
from discord.ext import commands
import discord
import asyncio
import logging

from src import config, globals
from . import tasks, groups_data_manager


logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from bot import MyBot

    
class PermissionGroupsCog(commands.Cog):
    bot: 'MyBot'
    
    player_names: dict[int, str]
    category_channels: dict[str, discord.TextChannel]
    category_messages: dict[str, discord.Message]

    def __init__(self, bot):
        self.bot = bot
    
    async def cog_load(self):
        groups_data_manager.on_update_received = self.on_update_received
        groups_data_manager.run_listener()
        await groups_data_manager.send_tracked_groups_async()

        await self.update_all_if_needed_async(True)

    async def on_update_received(self, group: str):
        logger.info("Received groups update: %s", group)
        if group == "*":
            await self.update_all_if_needed_async(False)
        else:
            category = self.__get_group_category(group)
            if category is None:
                logger.error("Failed to find category for tracked group %s", group)
                return
            
            await self.update_if_needed_async(category, False)
        
    def __get_group_category(self, group: str) -> config.PermissionCategoryProtocol | None:
        for c in config.instance.permission_groups.categories:
            if c.name == group:
                return c
        return None

    async def update_all_if_needed_async(self, instant: bool):
        logger.info("Updating all categories (instant: %s)...", instant)
        try:
            result = await asyncio.gather(
                *(self.update_if_needed_async(c, instant) for c in config.instance.permission_groups.categories)
                )
            logger.info("Verifying %s categories. (%s / %s changed)", len(result), sum(result), len(result))
        except Exception as e:
            logger.exception("An error occured while updating all categories", exc_info=e)

    async def update_if_needed_async(self, category: config.PermissionCategoryProtocol, instant: bool) -> bool:
        """
        Запускает обновление категории, если текущие данные не совпадают с последними отправленными.
        :return: True, если данные не совпадали и обновление запущено; иначе False.
        """

        if not await tasks.should_be_updated_async(category.name):
            logger.debug("Category %s is up to date.", category.name)
            return False
        
        logger.info("Category %s needs to be updated. Requesting (instant: %s)...", category.name, instant)
        await tasks.request_category_update_async(category, instant)
        return True
    