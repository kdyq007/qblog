# -*- coding:utf-8 -*- 
__author__ = 'qiqi'
from functools import wraps

from flask import g
from flask import request
from flask import current_app
from flask.ext.principal import PermissionDenied

# from models.users import Market_Users


def ip_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # close
        return f(*args, **kwargs)

        user = Market_Users.query.get_user_from_uid(g.user.uid)
        ip = user.get("ip")
        if not g.user.is_account_admin() and ip != "*":
            real_ip = request.headers.get("X-Real-Ip")
            current_app.logger.info(user)
            current_app.logger.info(real_ip)
            if not (user and ip and real_ip and ip == real_ip):
                raise PermissionDenied("IP地址不符")
        return f(*args, **kwargs)

    return decorated_function
