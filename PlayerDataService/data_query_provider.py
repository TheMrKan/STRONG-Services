from collections import defaultdict
import aiomysql
from redis.asyncio import Redis

import config


class DataQueryProvider:

    REDIS_PREFIX = "player_data:"

    __pool: aiomysql.Pool
    __redis: Redis

    def __init__(self) -> None:
        self.__redis = Redis.from_url(str(config.instance.REDIS_URL), protocol=3)

    async def init_async(self):
        self.__pool = await aiomysql.create_pool(
            host=config.instance.db_host,
            port=config.instance.db_port,
            user=config.instance.db_user,
            password=config.instance.db_password,
            minsize=1,
            maxsize=5,
        )

    async def query_async(self, players: list[int], fields: list[str]) -> dict[int, dict[str, str | None]]:
        cached = await self.__fetch_cached_async(players, fields)
        missing = {field: [] for field in fields}
        for player_id, player_data in cached.items():
            for key, value in player_data.items():
                if not value:
                    missing[key].append(player_id)

        from_source = await self.__fetch_from_source_async(missing)        
        await self.__cache_async(from_source)

        cached.update(from_source)
        return cached

    async def __fetch_cached_async(self, players: list[int], fields: list[str]) -> dict[int, dict[str, str | None]]:
        # список ключей в redis. Все поля из fields для каждого игрока
        # игрок1:поле1, игрок1:поле2, игрок2:поле1, игрок2:поле2
        raw_redis_keys = [f"{self.REDIS_PREFIX}{player}:{field}" for player in players for field in fields]
        # возвращает список значений по порядку ключей в raw_redis_keys
        # если значения нет - None
        flat_result = await self.__redis.mget(*raw_redis_keys)     

        result = {player: {} for player in players}
        flat_result_iterator = iter(flat_result)
        for player_data in result.values():
            for field in fields:
                value = next(flat_result_iterator)
                player_data[field] = value.decode('utf-8') if value else None

        return result

    async def __fetch_from_source_async(self, fields: dict[str, list[int]]) -> dict[int, dict[str, str | None]]:
        result = defaultdict(dict)

        for field_name, players in fields.items():
            if field_name != "display_name":
                raise ValueError(f"Unsupported field: {field_name}")

            values = await self.__fetch_display_name_from_source(players)
            for player_id, value in values.items():
                result[player_id][field_name] = value

        return result

    # временное решение
    async def __fetch_display_name_from_source(self, players: list[int]) -> dict[int, str]:
        if not any(players):
            return {}
        
        async with self.__pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                query = "SELECT Id, DisplayName FROM server_menu.mrkan_servermenu_users WHERE Id IN %s"
                await cursor.execute(query, (tuple(players),))
                rows = await cursor.fetchall()
                return {int(row['Id']): row['DisplayName'] for row in rows}

    async def __cache_async(self, data: dict[int, dict[str, str | None]]) -> None:
        async with self.__redis.pipeline() as pipe:
            for player_id, player_data in data.items():
                for field, value in player_data.items():
                    if value is not None:
                        key = f"{self.REDIS_PREFIX}{player_id}:{field}"
                        pipe.set(key, value, ex=43200)  # 6 часов. TODO: сделать настраиваемым для каждого поля
            await pipe.execute()