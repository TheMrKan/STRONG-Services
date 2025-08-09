from celery import Celery

from src import config, globals

def setup_celery():
    globals.celery = Celery("src", broker=config.instance.REDIS_URL)




