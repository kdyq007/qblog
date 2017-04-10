# -*- coding:utf-8 -*- 
__author__ = 'qiqi'

import datetime
import redis

from flask import abort
from flask import current_app
from flask import request
from flask import session

from extensions import db
# from extensions import redis
from models.user import User



class Account_Manager(object):
    def __init__(self):
        pass

    def add_user(self, username, email):
        user = User()
        user.username = username
        user.email = email
        user.date_joined = datetime.datetime.now()
        user.has_logined = 0
        db.session.add(user)
        try:
            db.session.commit()
            return user
        except Exception as e:
            db.session.rollback()
            return abort(500,
                         u"注册用户失败, {0}".format(e))


    def login_failed(self, username):
        user = db.session.query(User).filter(User.username == username).first()
        if user:
            user.logined_num += 1
            user.try_time = datetime.datetime.now()
            db.session.commit()
            return 5 - user.logined_num

    def can_login(self, username):
        user = db.session.query(User).filter(User.username == username).first()
        if user:
            if user.try_time is not None and user.try_time + \
                    datetime.timedelta(days=1) > datetime.datetime.now():
                if user.logined_num >= 5:
                    return False
            else:
                user.logined_num = 0
                db.session.commit()
        return True

    def verification_code(self, verification):
        verification1 = verification.strip()
        redis_client = redis.StrictRedis(
            host=current_app.config.get("CACHE_REDIS_HOST"),
            port=current_app.config.get("CACHE_REDIS_PORT"),
            db=current_app.config.get("REDIS_DB"), password="")
        _uuid = session.get("uuid")
        verification2 = redis_client.hget("verification", _uuid)
        redis_client.hdel("verification", _uuid)
        if verification1 and verification2 and verification1 == verification2:
            current_app.logger.info(u"验证成功！")
            return True
        current_app.logger.info(u"验证失败！")
        return False

    def regist_failed(self):
        ip = request.headers.get("X-Real-Ip")
        if ip is None:
            return
        redis_client = redis.StrictRedis(host=current_app.config.get("CACHE_REDIS_HOST"),
                port=current_app.config.get("CACHE_REDIS_PORT"),
                db=current_app.config.get("REDIS_DB"), password="")
        num = redis_client.hget(ip, "num")
        if num is None:
            num = 0
        redis_client.hset(ip, "num", int(num) + 1)
        _time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        redis_client.hset(ip, "time", _time)
        current_app.logger.info(
            u"操作错误！IP:" + ip + u", 错误次数：" + num + u", 操作时间：" + _time)

    def ip_limit(self):
        ip = request.headers.get("X-Real-Ip")
        if ip is None:
            return True
        redis_client = redis.StrictRedis(
            host=current_app.config.get("CACHE_REDIS_HOST"),
            port=current_app.config.get("CACHE_REDIS_PORT"),
            db=current_app.config.get("REDIS_DB"), password="")
        num = redis_client.hget(ip, "num")
        if num and int(num) >= 10:
            _time = redis_client.hget(ip, "time")
            out_time = (
                datetime.datetime.now() - datetime.timedelta(
                    minutes=30)).strftime(
                "%Y-%m-%d %H:%M:%S")
            if _time <= out_time:
                redis_client.hset(ip, "num", "0")
                return True
            return False
        return True
