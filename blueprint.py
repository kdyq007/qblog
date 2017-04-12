#-*- coding:utf8 -*-
__author__ = 'qiqi'

from application import app
# from apis import *
from views.index import *
from views.user import *

MODULES = (
    (indexBp, ''),
    (userBp, '/user'),
)


def setting_modules(app, modules):
    """ 注册Blueprint模块 """
    for module, url_prefix in modules:
        app.register_blueprint(module, url_prefix=url_prefix)

setting_modules(app, MODULES)