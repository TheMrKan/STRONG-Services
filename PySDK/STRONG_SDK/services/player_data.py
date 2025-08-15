import httpx
from typing import Literal, Final

from STRONG_SDK.exceptions import ServiceError


class PlayerDataServiceError(ServiceError):
    pass


class PlayerDataService:

    DISPLAY_NAME: Final = "display_name"

    __FIELD_NAME = Literal["display_name"]

    
    def __init__(self):
        pass

    async def query_async(self, players: list[int], fields: list[__FIELD_NAME]) -> dict[int, dict[str, str | None]]:
        """
        Запрос данных игроков.
        :param players: Список SteamID64 игроков.
        :param fields: Список полей, которые нужно запросить. См. константы в PlayerDataService.
        :return: Словарь, где ключ - идентификатор игрока, значение - словарь с полями и их значениями.
        """

        if not any(fields):
            raise ValueError("Fields list cannot be empty")
        
        if not any(players):
            raise ValueError("Players list cannot be empty")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get("http://player-data-service/query/", params={'fields': fields, 'players': players})
                response.raise_for_status()
                return response.json()
            except httpx.TimeoutException:
                raise PlayerDataServiceError("Request timeout")
            except httpx.HTTPStatusError as e:
                json = response.json()
                raise PlayerDataServiceError(f"Code: {json['code']}. Detail: {json['detail']}")
            except httpx.HTTPError as e:
                raise PlayerDataServiceError(f"Unexpected HTTP error: {e} {response.text}")
            except Exception as e:
                raise PlayerDataServiceError(f"Unhandled SDK error: {e}")