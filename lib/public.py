# -*- coding:utf-8 -*- 
__author__ = 'qiqi'

import hashlib


def build_key(secret, path, params):
    keys = sorted(params.keys())
    values = [str(params.get(k)) for k in keys]
    return hashlib.sha1('%s%s%s' % (path, secret, "".join(values))).hexdigest()
