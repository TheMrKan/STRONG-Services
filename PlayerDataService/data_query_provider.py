from typing import Any
import aiomysql

from . import config


class DataQueryProvider:

    __pool: aiomysql.Pool

    def __init__(self) -> None:
        pass

    async def init_async(self):
        self.__pool = await aiomysql.create_pool(
            host=config.instance.db_host,
            port=config.instance.db_port,
            user=config.instance.db_user,
            password=config.instance.db_password,
            db=config.instance.db_dbname,
            minsize=1,
            maxsize=5,
        )

    async def query_async(self, players: list[int], fields: list[str]) -> dict[int, dict[str, Any]]:
        raise NotImplementedError
