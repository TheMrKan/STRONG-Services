from redis.asyncio import Redis

from src import config, globals

def setup_redis():
    if not globals.redis:
        globals.redis = Redis.from_url(str(config.instance.REDIS_URL), protocol=3)
