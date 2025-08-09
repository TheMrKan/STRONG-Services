import asyncio

from src import celery_app, redis_app, globals, config
from src.permission_groups.tasks import request_category_update_async

if __name__ == "__main__":
    redis_app.setup_redis()
    celery_app.setup_celery()

    category = config.instance.permission_groups.categories[0]
    asyncio.run(request_category_update_async(category))
