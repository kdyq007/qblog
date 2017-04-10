# -*- coding:utf-8 -*- 
__author__ = 'qiqi'

from datetime import datetime

from flask import current_app

from extensions import db
# from models.market import Market


class Market_Manager(object):
    def __init__(self):
        pass

    def add_market(self, name, url=None, description=None):
        name = self.auto_change_name(name)
        market = Market()
        market.name = name
        market.url = url
        market.description = description
        market.created_at = datetime.now()
        market.updated_at = market.created_at
        db.session.add(market)
        try:
            db.session.flush()
            return market, u"添加市场成功"
        except Exception as e:
            db.session.rollback()
            current_app.logger.info(u"添加市场失败, {0}".format(e))
            return None, u"添加市场失败, {0}".format(e)

    def modify_market(self, mid, name, url=None, description=None):
        market = db.session.query(Market).filter(Market.mid == mid).first()
        if not market:
            current_app.logger.info(u"市场不存在!无法修改")
            return None, u"市场不存在!无法修改"
        market.name = name
        market.url = url
        market.description = description
        market.updated_at = datetime.now()
        try:
            db.session.flush()
            return market, u"市场修改成功！"
        except Exception as e:
            db.session.rollback()
        current_app.logger.info(u"修改市场失败, {0}".format(e))
        return None, u"修改市场失败, {0}".format(e)

    def is_exist(self, name):
        market = db.session.query(Market).filter(Market.name == name).first()
        if market:
            current_app.logger.info(u"市场已存在!无法添加")
            return True
        return False

    def auto_change_name(self, name):
        n = 0
        _name = name
        while(self.is_exist(_name)):
            n += 1
            _name = name + str(n)
        return _name

