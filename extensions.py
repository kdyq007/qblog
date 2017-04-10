# encoding=utf-8


from flask_celery import Celery
from flask_cache import Cache
from flask_sqlalchemy import SQLAlchemy

# from lib.redis import RedisHandler

__all__ = ['mail', 'db', 'cache', 'photos', 'celery']

# mail = Mail()
db = SQLAlchemy()
cache = Cache()
celery = Celery()
# redis = RedisHandler()
