from typing import TYPE_CHECKING
import redis.asyncio as redislib
from celery import Celery
from discord.client import Client
from asyncio import BaseEventLoop

bot: Client = None # type: ignore
redis: redislib.Redis  = None # type: ignore
celery: Celery = None  # type: ignore