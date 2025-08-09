"""
Точка входа для celery воркера
"""

import asyncio
from celery import signals
import threading
import traceback
import sys
import time

from src import globals, bot, redis_app, celery_app


class CeleryConfig:
    worker_proc_alive_timeout = 45    # таймаут ожидания инициализации форка воркера. Увеличен, чтобы бот в форке успевал подключиться


celery_app.setup_celery()
celery = globals.celery
celery.config_from_object(CeleryConfig)
celery.autodiscover_tasks(["src.permission_groups"])

BOT_START_TIMEOUT = 30


@signals.worker_process_init.connect
def on_worker_init(*args, **kwargs):

    redis_app.setup_redis()
    bot.setup_discord_client()  # чистый клиент дискорда без основного функционала бота
    thread = threading.Thread(target=run_bot, daemon=True)
    thread.start()

    is_timeout = not bot.bot_ready_event.wait(30)
    if is_timeout:
        bot.bot_exception = TimeoutError(f"Timeout ({BOT_START_TIMEOUT} s) reached")

    if bot.bot_exception:
        print("Failed to wait for a bot start. Terminating worker...")
        traceback.print_exception(bot.bot_exception)
        time.sleep(10)
        sys.exit(1)

    print("Worker setup completed")


def run_bot():
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(bot.run_async(True))
    except Exception as e:
        print("Failed to run bot. Terminating worker...")
        bot.bot_exception = e
        bot.bot_ready_event.set()


@signals.worker_process_shutdown.connect
def on_worker_shutown(*args, **kwargs):
    try:
        if globals.bot:
            future = asyncio.run_coroutine_threadsafe(globals.bot.close(), globals.bot.loop)
            return future.result()
    except Exception:
        print("Failed to stop bot on worker shutdown")
        traceback.print_exc()
