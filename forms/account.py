# -*- coding:utf-8 -*-

from flask.ext.wtf import Form
from wtforms import BooleanField
from wtforms import HiddenField
from wtforms import PasswordField
from wtforms import StringField
from wtforms import SubmitField
from wtforms import validators


class LoginForm(Form):
    username = StringField(u"用户名/邮箱/手机号码", [
        validators.required(message=u"请输入用户名/邮箱/手机号码")
    ])
    password = PasswordField(u"密码", [validators.required(message=u'请输入密码'),
                                     validators.length(6, 12,
                                                       message=u'密码长度在6到12位')])
    # verification = StringField(u"验证码", [validators.required(message=u'请输入验证码')])
    remember = BooleanField(u"记住我")
    next = HiddenField()
    submit = SubmitField(u"登陆")


class RegistForm(Form):
    login = StringField(u"用户名", [
        validators.required(message=u"请输入用户名")
    ])
    password = PasswordField(u"密码", [validators.required(message=u'请输入密码'),
                                     validators.length(6, 12,
                                                       message=u'密码长度在6到12位')])

    password1 = PasswordField(u'确认密码', [validators.required(message=u'请输入密码'),
                                        validators.length(6, 12,
                                                          message=u'密码长度在6到12位'),
                                        validators.EqualTo('password',
                                                           message=u'密码必须一致')])

    email = StringField(u" 邮箱", [
        validators.required(message=u"请输入您的邮箱")
    ])
    # mobile = StringField(u"手机号码", [
    #     validators.required(message=u"请输入手机号码"),
    #     validators.regexp('^1[34578]\d{9}$', message=u"请输入11位数的手机号码")
    # ])
    # verification = StringField(u"验证码",
    #                            [validators.required(message=u'请输入验证码')])
    next = HiddenField()
    submit = SubmitField(u"注册")


class ChangePasswordForm(Form):
    old_password = PasswordField(u"原始密码", [validators.required(message=u'请输入原始密码'),
                                     validators.length(6, 12,
                                                       message=u'密码长度在6到12位')])
    password = PasswordField(u"新密码", [validators.required(message=u'请输入新密码'),
                                     validators.length(6, 12,
                                                       message=u'密码长度在6到12位')])
    password1 = PasswordField(u'重复新密码', [validators.required(message=u'请重复输入新密码'),
                                        validators.length(6, 12,
                                                          message=u'密码长度在6到12位'),
                                        validators.EqualTo('password',
                                                           message=u'密码必须一致')])
    # verification = StringField(u"验证码",
    #                            [validators.required(message=u'请输入验证码')])
    next = HiddenField()
    submit = SubmitField(u"注册")
