#!/usr/bin/env python3
# -*- coding:utf-8 -*-
__author__ = 'qiqi'

import json
from flask import current_app
from flask import session
from flask import request
from lib.geetest import GeetestLib


class GeetestManage():

    pc_geetest_id = ""
    pc_geetest_key = ""

    def __init__(self):
        self.pc_geetest_id = current_app.config.get("GEETEST_ID")
        self.pc_geetest_key = current_app.config.get("GEETEST_KEY")

    def get_captcha(self):
        user_id = 'test'
        gt = GeetestLib(self.pc_geetest_id, self.pc_geetest_key)
        status = gt.pre_process(user_id)
        session[gt.GT_STATUS_SESSION_KEY] = status
        session["user_id"] = user_id
        response_str = gt.get_response_str()
        return response_str

    def validata_captcha(self):
        gt = GeetestLib(self.pc_geetest_id, self.pc_geetest_key)
        challenge = request.form[gt.FN_CHALLENGE]
        validate = request.form[gt.FN_VALIDATE]
        seccode = request.form[gt.FN_SECCODE]
        status = session[gt.GT_STATUS_SESSION_KEY]
        user_id = session["user_id"]
        if status:
            result = gt.success_validate(challenge, validate, seccode, user_id,
                                         data='', userinfo='')
        else:
            result = gt.failback_validate(challenge, validate, seccode)
        return True if result else False

