# -*- coding:utf-8 -*- 

import hashlib

from extensions import db

from functools import wraps

from flask import current_app, g, request, jsonify, abort
from flask.ext.principal import identity_changed, Identity, AnonymousIdentity

from models.auth import Auth

class Auth_Manager(object):
    def __init__(self):
        pass

    def add_username_auth(self, uid, password):
        auth = Auth()
        auth.uid = uid
        auth.auth_hash = hashlib.md5(password).hexdigest()
        auth.auth_type = 0
        db.session.add(auth)
        try:
            db.session.commit()
            return auth
        except Exception as e:
            db.session.rollback()
            return abort(500,
                         u"注册用户失败, {0}".format(e))

    def username_auth(self, uid, password, auth_type=0):
        if password is None:
            return False
        auth = Auth.query.filter(db.and_(
            Auth.uid == uid,
            Auth.auth_type == auth_type
        )).first()
        return auth.auth_hash == hashlib.md5(password).hexdigest()




def auth_with_key(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        key = request.values.get('_key')
        secret = request.values.get('_secret')
        current_app.logger.debug(key)
        path = request.path
        keys = sorted(request.values.keys())
        req_args = [request.values[k] for k in keys
                    if str(k) not in ("_key", "_secret")]
        user, authenticated = User.query.authenticate_with_key(
            key, secret, req_args, path)
        if user and authenticated:
            g.user = user
            current_app.logger.info(user.uid)
            identity_changed.send(current_app._get_current_object(),
                                  identity=Identity(user.uid))
            return func(*args, **kwargs)
        else:
            identity_changed.send(current_app._get_current_object(),
                                  identity=AnonymousIdentity())
            return jsonify(code=400, message="invalid _key and _secret")

    return wrapper
