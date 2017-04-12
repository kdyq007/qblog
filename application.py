#-*- coding:utf8 -*-
__author__ = 'qiqi'

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
# from flask_openid import OpenID
import sys

reload(sys)
sys.setdefaultencoding('utf8')

app = Flask(__name__)
app.config.from_pyfile('config.py')
db = SQLAlchemy(app)
lm = LoginManager(app)
# oid = OpenID(app,'/tmp')