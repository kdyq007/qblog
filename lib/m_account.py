# -*- coding:utf-8 -*- 
__author__ = 'qiqi'

from datetime import datetime

from flask import abort

from extensions import db
# from models.m_account import M_Account
from lib.aes import prpcrypt


class M_Account_Manager(object):
    def __init__(self):
        self.pc = prpcrypt()

    def add_m_account(self, mid, account=None, password=None, description=None,
                      invalid_date=None):

        m_account = M_Account()
        m_account.mid = mid
        m_account.account = account
        m_account.password = self.pc.encrypt(str(password))
        m_account.description = description
        if invalid_date == "":
            invalid_date = None
        m_account.invalid_date = invalid_date
        m_account.created_at = datetime.now()
        m_account.updated_at = m_account.created_at
        db.session.add(m_account)
        try:
            db.session.flush()
            return m_account
        except Exception as e:
            db.session.rollback()
            return abort(500,
                         "添加账号密码失败, {0}".format(e))

    def modify_m_account(self, mid, account=None, password=None,
                         description=None,
                         invalid_date=None):
        m_account = db.session.query(M_Account).filter(
            M_Account.mid == mid).first()
        if m_account:
            m_account.mid = mid
            m_account.account = account
            m_account.password = self.pc.encrypt(str(password))
            m_account.description = description
            if invalid_date:
                m_account.invalid_date = invalid_date
            m_account.updated_at = datetime.now()
            db.session.add(m_account)
            try:
                db.session.flush()
                return m_account
            except Exception as e:
                db.session.rollback()
                return abort(500,
                             "修改账号密码失败, {0}".format(e))
        else:
            self.add_m_account(mid, account, password,
                               description,
                               invalid_date)
