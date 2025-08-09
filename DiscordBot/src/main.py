import asyncio
import logging 
import logging.config

from src import config

logging.config.dictConfig(config.instance.logging)

from src import globals, bot, redis_app, celery_app

redis_app.setup_redis()
celery_app.setup_celery()

bot.setup_bot()
asyncio.run(bot.run_async(True))
