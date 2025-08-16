import celery
import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Any
import uuid
from billiard.exceptions import SoftTimeLimitExceeded
import discord
import discord.colour as dscolor
import datetime
import redis.asyncio as redislib
import traceback
import hashlib
import httpx


from src import globals, config, bot
from . import groups_data_manager
from STRONG_SDK.services.player_data import PlayerDataService


INTERNAL_STATE_STORAGE_PREFIX = groups_data_manager.REDIS_PREFIX + "internal:"

ATTEMPT_TIMEOUT = 30
PENDING_DURATION = 5
RETRY_INTERVAL = 10


async def should_be_updated_async(category_name: str):
    category_config = __get_category_config(category_name)
    groups_data = await __get_groups_data_async(category_config.groups)
    try:
        player_names = await __get_player_names_async([m for g in groups_data for m in g.members])
    except Exception:
        print(f"Failed to fetch player names:")
        traceback.print_exc()
        player_names = {}

    hash = __get_hash(groups_data, player_names)
    remote_hash = await __fetch_category_state_partial_async(category_name, "current_remote_hash", None)
    return hash != remote_hash


async def request_category_update_async(
    category: config.PermissionCategoryProtocol, instant: bool = False
):
    """
    Запрашивает обновление категории.
    - Если обновление не запланировано, то планирует обновление с задержкой
    - Если обновление запланировано, то сбрасывает таймер
    - Если обновление выполняется, то ждет завершения операции и после этого принимает решение
    - Если идет ожидание ретрая после ошибки, то просто дополняет список групп для обновления

    :param instant: Если True, то обновление запустится без задержки.
    """

    # ждем завершения попытки обновления, чтобы current_remote_hashes точно были актуальными
    retries = ATTEMPT_TIMEOUT
    category_state = None
    while retries:
        category_state = await __fetch_category_state_async(category.name)

        if category_state.deadline and category_state.deadline < datetime.datetime.now():
            # TODO: лог
            if category_state.task_id:
                globals.celery.control.revoke(category_state.task_id)  # отменяем зависшую задачу
                category_state.task_id = None
                await __update_category_state_partial_async(category.name, "task_id", None)

            category_state.deadline = None
            await __update_category_state_partial_async(category.name, "deadline", None)

            # можно не сохранять в редис, т. к. сохранится при запуске задачи
            category_state.status = TaskStatus.NOT_PLANNED
            break

        if category_state.status == TaskStatus.EXECUTING:
            retries -= 1
            await asyncio.sleep(1)
            continue

        break

    assert category_state is not None  # чтобы Pylance не жаловался

    if category_state.status == TaskStatus.EXECUTING:
        # TODO: обработка крайнего случая
        raise TimeoutError()

    if category_state.status == TaskStatus.PENDING:
        if category_state.task_id is None:
            # TODO: обработка крайнего случая
            raise Exception("Task id is None")

        globals.celery.control.revoke(category_state.task_id)  # отменяем запланированную задачу
        category_state.status = TaskStatus.NOT_PLANNED

    if category_state.status == TaskStatus.NOT_PLANNED:
        delay = None if instant else PENDING_DURATION
        category_state.task_id = str(uuid.uuid4())

        await __update_category_state_partial_async(
            category_state.name, "status", TaskStatus.PENDING.value
        )
        await __update_category_state_partial_async(
            category_state.name, "task_id", category_state.task_id
        )
        await __update_category_state_partial_async(
            category_state.name, "deadline", datetime.datetime.now().timestamp() + ((delay or 0) * 2)
        )

        # планируем обновление с задержкой
        update_category.apply_async(
            (category_state.name,),  # type: ignore
            countdown=delay,
            task_id=category_state.task_id,
        )


class TaskStatus(Enum):
    NOT_PLANNED = "not_planned"
    """
    Обновление категории не запланировано
    """
    PENDING = "pending"
    """
    Ожидание таймера после запроса
    """
    EXECUTING = "executing"
    """
    Выполняется обновление сообщения
    """
    RETRY = "retry"
    """
    Предыдущая попытка обновления завершилась с ошибкой. Ожидание ретрая.
    """


@dataclass
class CategoryState:
    name: str
    task_id: str | None
    status: TaskStatus
    deadline: datetime.datetime | None
    """
    Если задача висит в ретрае или выполняется после этого времени, значит она зависла
    """
    current_remote_hash: int


async def __fetch_category_state_async(category_name: str) -> CategoryState:
    data = await globals.redis.json().get(INTERNAL_STATE_STORAGE_PREFIX + category_name, ".")  # type: ignore

    if not data:    # если данных нет, то создаем состояние по умолчанию и сохраняем в редис
        data = {
            "name": category_name,
            "task_id": None,
            "status": TaskStatus.NOT_PLANNED.value,
            "deadline": None,
            "current_remote_hash": 0
            
        }
        await globals.redis.json().set(INTERNAL_STATE_STORAGE_PREFIX + category_name, ".", data) # type: ignore

    category_state = CategoryState(
        category_name,
        data["task_id"],
        TaskStatus(data["status"]),
        datetime.datetime.fromtimestamp(data["deadline"]) if data["deadline"] else None,
        data["current_remote_hash"],
    )

    return category_state


async def __fetch_category_state_partial_async(category_name: str, key: str, default: Any) -> Any:
    try:
        raw_data = await globals.redis.json().get(INTERNAL_STATE_STORAGE_PREFIX + category_name, f".{key}")  # type: ignore
    except redislib.ResponseError:
        return default
    
    return raw_data


async def __update_category_state_partial_async(category_name: str, key: str, value: Any):
    await globals.redis.json().set(
        INTERNAL_STATE_STORAGE_PREFIX + category_name, f".{key}", value
    )  # type: ignore


@celery.shared_task(
    bind=True,
    soft_time_limit=ATTEMPT_TIMEOUT,
    time_limit=ATTEMPT_TIMEOUT * 2,
    auto_retry_for=(BaseException, SoftTimeLimitExceeded),
    retry_kwargs={'max_retries': None, "countdown": RETRY_INTERVAL},
)
def update_category(self: celery.Task, category_name: str):
    print(f"Running update task for category {category_name}")
    future = asyncio.run_coroutine_threadsafe(__update_category_async(category_name), globals.bot.loop)
    return future.result()


async def __update_category_async(category_name: str):
    try:
        await __update_category_state_partial_async(category_name, "deadline", 
                                                    datetime.datetime.now().timestamp() + ATTEMPT_TIMEOUT * 2)
        await __update_category_state_partial_async(category_name, "status", TaskStatus.EXECUTING.value)

        print("Preparing data...")

        category_config = __get_category_config(category_name)
        groups_data = await __get_groups_data_async(category_config.groups)
        try:
            player_names = await __get_player_names_async([m for g in groups_data for m in g.members])
        except Exception:
            print(f"Failed to fetch player names:")
            traceback.print_exc()
            player_names = {}

        embed = __build_category_message(category_config, groups_data, player_names)

        print("Editing message...")
        await __edit_message_async(category_config.channel_id, category_config.message_id, embed)

        print("Saving result...")
        hash = __get_hash(groups_data, player_names)
        await __update_category_state_partial_async(category_name, "current_remote_hash", hash)
        await __update_category_state_partial_async(category_name, "deadline", None)
        await __update_category_state_partial_async(category_name, "status", TaskStatus.NOT_PLANNED.value)
        await __update_category_state_partial_async(category_name, "task_id", None)
        print(f"Task completed for category {category_name}")
    except:
        print("Exception caught in async function. Saving retry state...")
        traceback.print_exc()
        await __update_category_state_partial_async(category_name, "deadline", 
                                                    datetime.datetime.now().timestamp() + RETRY_INTERVAL * 2)
        await __update_category_state_partial_async(category_name, "status", TaskStatus.RETRY.value)
        raise


def __get_category_config(category_name: str) -> config.PermissionCategoryProtocol:
    """
    ValueError, если конфиг не найден
    """
    search = [c for c in config.instance.permission_groups.categories if c.name == category_name]
    if not any(search):
        raise ValueError(f"Failed to find config for category {category_name}")
    
    return search[0]


async def __get_groups_data_async(groups: list[str]) -> list[groups_data_manager.GroupData]:
    raw_data = await asyncio.gather(*[groups_data_manager.fetch_group_async(g) for g in groups])
    result = []
    for i in range(len(raw_data)):
        if raw_data[i] is not None:
            result.append(raw_data[i])

        # TODO: логгирование

    return result


def __get_hash(data: list[groups_data_manager.GroupData], player_names: dict[str, str]) -> int:
    groups = []
    for g in data:
        members = "".join([f"{m}{player_names.get(m, '')}" for m in g.members])
        groups.append(f"{g.id}{g.prefix}{members}")
    return int(hashlib.sha1("".join(groups).encode("utf-8")).hexdigest(), 16) % (10**16)


async def __edit_message_async(channel_id: int, message_id: int, embed: discord.Embed):
    channel: discord.TextChannel = globals.bot.get_channel(channel_id)  # type: ignore
    if not channel:
        channel = await globals.bot.fetch_channel(channel_id)
        if not channel:
            raise Exception(f"Channel {channel_id} not found")

    if isinstance(channel, discord.Thread) and channel.archived:
        await channel.edit(archived=False)  # type: ignore

    message = await channel.fetch_message(message_id)
    await message.edit(content="", embed=embed)
    # TODO: лог


async def __get_player_names_async(players: list[str]) -> dict[str, str]:
    if not any(players):
        return {}
    query_result = await PlayerDataService().query_async(players, [PlayerDataService.DISPLAY_NAME])
    return {str(player_id): player_data[PlayerDataService.DISPLAY_NAME] for player_id, player_data in query_result.items()}


def __build_category_message(
    category: config.PermissionCategoryProtocol,
    category_groups: list[groups_data_manager.GroupData],
    player_names: dict[str, str],
):
    color = dscolor.parse_hex_number(category.color.strip("#"))
    embed = discord.Embed(
        title=category.title, color=color, timestamp=datetime.datetime.now()
    )

    description_list = []
    for group in category_groups:
        members_list = []
        for i, member in enumerate(group.members):
            name = player_names.get(member, "UNKNOWN")
            members_list.append(f"  {i+1}. {member} - {name}")

        if category.show_group_id:
            description_list.append(
                f"- **{group.prefix}** - *{group.id}*\n{'\n'.join(members_list)}"
            )
        else:
            description_list.append(f"- **{group.prefix}**\n{'\n'.join(members_list)}")
    embed.description = "\n-\n".join(description_list).strip(" \n\r\t")

    return embed
