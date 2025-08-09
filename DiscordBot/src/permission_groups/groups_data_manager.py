from dataclasses import dataclass
from typing import Awaitable, Callable
import logging
import asyncio

from src import globals, config


logger = logging.getLogger(__name__)


REDIS_PREFIX = "permission_groups:"
REDIS_UPDATES_CHANNEL = REDIS_PREFIX + "updates"
REDIS_TRACKED_GROUPS = REDIS_PREFIX + "tracked_groups"

@dataclass
class GroupData:
    id: str
    prefix: str
    members: list[str]


on_update_received: Callable[[str, ], Awaitable] | None = None


async def send_tracked_groups_async():
    groups = set()
    for category in config.instance.permission_groups.categories:
        groups.update(category.groups)

    await globals.redis.json().set(REDIS_TRACKED_GROUPS, ".", list(groups))  # type: ignore


async def fetch_group_async(group_id: str) -> GroupData | None:
    group_data = await globals.redis.json().get(REDIS_PREFIX + group_id.lower(), ".")  # type: ignore
    if not group_data:
        return None

    group = GroupData(group_data["id"], group_data["prefix"], group_data["members"])
    return group


def run_listener():
    asyncio.ensure_future(__updates_channel_listener(), loop=globals.bot.loop)


async def __updates_channel_listener():
    async with globals.redis.pubsub() as pubsub:
        await pubsub.subscribe(REDIS_UPDATES_CHANNEL)

        logger.info("Listening for updates on channel: %s", REDIS_UPDATES_CHANNEL)
        while True:
            try:
                message = await pubsub.get_message(ignore_subscribe_messages=True)
                if message is None:
                    continue

                decoded = message["data"].decode()
                if on_update_received:
                    await on_update_received(decoded)
            except Exception as e:
                logger.exception(
                    "An error occured in __updates_channel_listener", exc_info=e
                )
                # TODO: логи
