# -*- coding:utf-8 -*- 
__author__ = 'qiqi'

from datetime import datetime

from extensions import db
# from models.m_user import M_User


class M_User_Manager(object):
    def __init__(self):
        pass

    def add_m_user(self, uid, aid):
        m_user = M_User()
        m_user.uid = uid
        m_user.aid = aid
        m_user.created_at = datetime.now()
        m_user.updated_at = m_user.created_at
        db.session.add(m_user)
        return m_user
