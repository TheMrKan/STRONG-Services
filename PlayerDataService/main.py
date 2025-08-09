from typing import Annotated
from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dataclasses import dataclass

from . import data_query_provider


app = FastAPI()


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
    return JSONResponse({"code": code, "detail": detail})


class PlayerDataQueryRequest(BaseModel):
    players: list[int]
    fields: list[str]


class PlayerDataQueryResponse(BaseModel):
    pass


@app.get("/query")
async def query_players_data(query: Annotated[PlayerDataQueryRequest, Query]) -> PlayerDataQueryResponse:
    raise NotImplementedError