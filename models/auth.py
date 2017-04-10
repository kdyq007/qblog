# -*- coding:utf-8 -*-
__author__ = 'qiqi'

from extensions import db


# auth_type
# 0:账号登录
# 1:微博登录
# 2:QQ登录
# 3:微信登录
class Auth(db.Model):
    __tablename__ = 'auths'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uid = db.Column(db.Integer, db.ForeignKey("users.uid",
                                              ondelete="CASCADE"))
    user = db.relationship("User", backref="auths")
    #auths = db.relationship("User", backref="auths")
    auth_type = db.Column(db.Integer)
    auth = db.Column(db.String(32), default="")
    auth_hash = db.Column(db.String(100), nullable=False)
