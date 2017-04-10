# -*- coding:utf-8 -*-

__author__ = 'pycook'

import copy
import hashlib
from datetime import datetime

import requests
from flask import current_app
from flask import g
from flask.ext.principal import Permission
from flask.ext.principal import RoleNeed
from flask.ext.principal import UserNeed
from flask.ext.sqlalchemy import BaseQuery
from werkzeug.utils import cached_property

from extensions import cache
from extensions import db
from lib.urls import URL_PREFIX
from permissions import admin
from lib.auth import Auth_Manager


class UserQuery(BaseQuery):
    def from_identity(self, identity):
        """
        Loads user from flask.ext.principal.Identity instance and
        assigns permissions from user.

        A "user" instance is monkey patched to the identity instance.

        If no user found then None is returned.
        """

        try:
            _id = identity.id
            if _id:
                _id = int(_id)
            user = self.get(_id)
        except ValueError:
            user = None
        except Exception:
            user = None
        if user:
            identity.provides.update(user.provides)
        identity.user = user
        return user

    def authenticate(self, login, password):
        current_app.logger.info(login)
        user = self.filter(db.or_(User.username == login,
                                  User.email == login,
                                  User.mobile == login,
                                  )).first()
        if user:
            current_app.logger.info(user)
            am = Auth_Manager()
            authenticated = am.username_auth(user.uid, password)
        else:
            authenticated = False
        return user, authenticated

    def authenticate_with_key(self, key, secret, args, path):
        user = self.filter(User.key == key).filter(User.block == 0).first()
        if not user:
            return None, False
        if user and hashlib.sha1('%s%s%s' % (
                path, user.secret, "".join(args))).hexdigest() == secret:
            authenticated = True
        else:
            authenticated = False
        return user, authenticated

    def search(self, key):
        query = self.filter(db.or_(User.email == key,
                                   User.nickname.ilike('%' + key + '%'),
                                   User.username.ilike('%' + key + '%')))
        return query

    def get_by_username(self, username):
        user = self.filter(User.username == username).first()
        return user

    def get_by_nickname(self, nickname):
        user = self.filter(User.nickname == nickname).first()
        return user

    def get(self, uid):
        user = self.filter(User.uid == uid).first()
        return copy.deepcopy(user)

    def is_exits(self, username):
        user = self.filter(User.username == username).first()
        return user is not None

    def email_is_exits(self, email):
        user = self.filter(User.email == email).first()
        return user is not None

    def mobile_is_exits(self, mobile):
        user = self.filter(User.mobile == mobile).first()
        return user is not None


class User(db.Model):
    __tablename__ = 'users'
    # __bind_key__ = "user"
    query_class = UserQuery

    ADMIN = 1
    OP = 2

    uid = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(32), unique=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    mobile = db.Column(db.String(14))
    # _password = db.Column("password", db.String(80))
    date_joined = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, default=datetime.utcnow)
    block = db.Column(db.Boolean, default=False)
    has_logined = db.Column(db.Boolean, default=False)
    logined_num = db.Column(db.Integer, default=0)
    try_time = db.Column(db.DateTime, default=datetime.utcnow)



    class Permissions(object):
        def __init__(self, obj):
            self.obj = obj

        @cached_property
        def is_admin(self):
            return Permission(UserNeed(self.obj.id)) & admin

    def __init__(self, *args, **kwargs):
        super(User, self).__init__(*args, **kwargs)

    def __str__(self):
        return self.username

    # def __repr__(self):
    #    return "<%s>" % self

    @cached_property
    def permissions(self):
        return self.Permissions(self)

    def _get_password(self):
        return self._password

    # def _set_password(self, password):
    #     self._password = hashlib.md5(password).hexdigest()

    # password = db.synonym("_password",
    #                       descriptor=property(_get_password,
    #                                           _set_password))

    # def check_password(self, password):
    #     if self.password is None:
    #         return False
    #     return self.password == hashlib.md5(password).hexdigest()

    @cached_property
    def provides(self):
        needs = [RoleNeed('authenticated'),
                 UserNeed(self.uid)]
        for r in self.rolenames:
            needs.append(RoleNeed(r))
        if self.is_admin:
            needs.append(RoleNeed('admin'))
        return needs

    @property
    def roles(self):
        urs = db.session.query(UserRole.rid).filter(
            UserRole.uid == self.uid).all()
        return [x.rid for x in urs]

    @property
    def rolenames(self):
        roles = list()
        for rid in self.roles:
            role = db.session.query(Role).filter(Role.rid == rid).first()
            roles.append(role.role_name)
        return roles

    @property
    def is_admin(self):
        return self.ADMIN in self.roles

    @property
    def is_cmdb_admin(self):
        return 'cmdb_admin' in self.rolenames

    @property
    def is_op(self):
        return (self.OP in self.roles) or (self.ADMIN in self.roles)

    def is_account_admin(self):
        return 'account_admin' in self.rolenames

    def _get_bu_owner(self, bu):
        try:
            bu_owner = requests.get("{0}/ci/s?q=_type:bu,bu_name:{1}".format(
                URL_PREFIX, bu)).json().get("result")[0].get("bu_owner")
            if bu_owner:
                sep = filter(lambda x: x in bu_owner, [",", ";"])
                if sep:
                    return bu_owner.strip().split(sep[0])
                else:
                    return [bu_owner.strip()]
        except:
            pass
        return []

    def can_edit_device(self, ci):
        if self.is_admin or self.is_cmdb_admin:
            return True

        if ci.get("rd_duty"):
            sep = filter(lambda x: x in ci.get("rd_duty").strip(), [",", ";"])
            rd_duty_list = ci.get("rd_duty").strip().split(sep[0]) if sep \
                else [ci.get("rd_duty").strip()]
            if self.nickname in rd_duty_list:
                return True

        if ci.get("op_duty"):
            sep = filter(lambda x: x in ci.get("op_duty").strip(), [",", ";"])
            op_duty_list = ci.get("op_duty").strip().split(sep[0]) if sep \
                else [ci.get("op_duty").strip()]
            if self.nickname in op_duty_list:
                return True

        if ci.get("i_bu") and \
                (self.username in self._get_bu_owner(ci.get("i_bu")) or
                         self.nickname in self._get_bu_owner(ci.get("i_bu"))):
            return True
        return False

    @property
    def can_batch_update(self):
        if self.is_admin or self.is_cmdb_admin:
            return True
        if g.user.department and \
                (self.username in self._get_bu_owner(g.user.department) or
                         self.nickname in self._get_bu_owner(
                         g.user.department)):
            return True


class Role(db.Model):
    __tablename__ = 'roles'

    rid = db.Column(db.Integer, primary_key=True, autoincrement=True)
    role_name = db.Column(db.String(64), nullable=False, unique=True)


class UserRole(db.Model):
    __tablename__ = 'users_roles'

    uid = db.Column(db.Integer, db.ForeignKey('users.uid'), primary_key=True)
    rid = db.Column(db.Integer, db.ForeignKey('roles.rid'), primary_key=True)


class UserCache(object):
    @classmethod
    def get(cls, key):
        user = cache.get("User::uid::%s" % key) or \
               cache.get("User::username::%s" % key) or \
               cache.get("User::nickname::%s" % key)
        if not user:
            user = User.query.get(key) or \
                   User.query.get_by_username(key) or \
                   User.query.get_by_nickname(key)
        if user:
            cls.set(user)
        return user

    @classmethod
    def set(cls, user):
        cache.set("User::uid::%s" % user.uid, user)
        cache.set("User::username::%s" % user.username, user)
        cache.set("User::nickname::%s" % user.nickname, user)

    @classmethod
    def clean(cls, user):
        cache.delete("User::uid::%s" % user.uid)
        cache.delete("User::username::%s" % user.username)
        cache.delete("User::nickname::%s" % user.nickname)


class SpecialPermissionCache(object):
    @classmethod
    def get(cls, uid):
        sp = cache.get("SpecialPermission::uid::%s" % uid)
        return sp

    @classmethod
    def set(cls, uid):
        cache.set("SpecialPermission::uid::%s" % uid, "Y", timeout=60 * 60 * 2)


class FixLengthList(object):
    def __init__(self):
        self.queue = list()

    def push(self, elem):
        if elem not in self.queue:
            if len(self.queue) < 4:
                self.queue.insert(0, elem)
            else:
                self.queue.pop(3)
                self.queue.insert(0, elem)
        else:
            self.queue.remove(elem)
            self.queue.insert(0, elem)


class RoleCache(object):
    @classmethod
    def get(cls, rid):
        role = None
        if isinstance(rid, (int, long)):
            role = cache.get("Role::rid::%s" % rid)
            if not role:
                role = db.session.query(Role).filter(Role.rid == rid).first()
                cls.set(role)
        elif isinstance(rid, basestring):
            role = cache.get("Role::role_name::%s" % rid)
            if not role:
                role = db.session.query(Role).filter(
                    Role.role_name == rid).first()
                cls.set(role)
        return role

    @classmethod
    def set(cls, role):
        cache.set("Role::rid::%s" % role.rid, role)
        cache.set("Role::role_name::%s" % role.role_name, role)

    @classmethod
    def clean(cls, role):
        cache.delete("Role::rid::%s" % role.rid, role)
        cache.delete("Role::role_name::%s" % role.role_name, role)
