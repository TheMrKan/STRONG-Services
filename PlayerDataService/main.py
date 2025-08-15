from typing import Annotated
from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dataclasses import dataclass
from contextlib import asynccontextmanager

import data_query_provider


@asynccontextmanager
async def lifespan(app: FastAPI):
    global provider

    provider = data_query_provider.DataQueryProvider()
    await provider.init_async()
    yield


app = FastAPI(lifespan=lifespan)
provider: data_query_provider.DataQueryProvider


class APIException(Exception):
    code: int
    detail: str

    def __init__(self, code: int, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(detail)


@app.exception_handler(Exception)
async def exception_handler(request: Request, exc: Exception):
    if isinstance(exc, APIException):
        code = exc.code
        detail = exc.detail
    else:
        code = 500
        detail = f"Unhandled internal error: {str(exc)}"
    return JSONResponse({"code": code, "detail": detail}, status_code=code)


@app.get("/query/")
async def query_players_data(players: Annotated[list[int], Query()], fields: Annotated[list[str], Query()]) -> dict[str, dict[str, str | None]]:
    data = await provider.query_async(players, fields)
    return {str(player_id): player_data for player_id, player_data in data.items()}    # ключи в JSON объектах должны быть строками
