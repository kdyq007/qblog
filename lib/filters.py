# -*- coding:utf-8 -*- 

__author__ = 'pycook'

import re

from flask import Markup

from models.user import UserCache


def markup(content):
    return Markup(content)


def split_br(content, sep=','):
    if content:
        return Markup("<br>".join(content.split(sep)))
    else:
        return ""


def datetime_simple(content):
    if content:
        a, b = content.split("T")
        m, d = a.split("-")[1], a.split("-")[2]
        hour, minute = b.split(":")[0], b.split(":")[1]
        return "%s:%s" % (hour, minute)
    else:
        return ""


def datetime_format(content):
    if content:
        a, b = content.split("T")
        return "%s %s" % (a, b.split("+")[0])
    else:
        return ""


def is_list(arg):
    if isinstance(arg, list):
        return True
    return False


def split_right(arg):
    return arg.split(u"】")[-1]


def split_comma(arg):
    return arg.split(u",")


def username2alias(arg):
    u = UserCache.get(arg)
    if u:
        return u.nickname
    else:
        return arg


def split(arg, pat, idx):
    try:
        if idx == 0 or idx:
            return arg.split(pat)[idx]
        return arg.split(pat)
    except:
        return


def list_br(arg):
    if isinstance(arg, list):
        return Markup("<br>".join(map(str, arg)))
    return ""


def format_output(arg):
    if isinstance(arg, list):
        arg = filter(lambda x: x != "", arg)
        if arg:
            return Markup("<br>".join(map(str, arg)))
        else:
            return ""
    elif isinstance(arg, basestring) and len(arg) > 30:
        return arg[:30] + " ..."
    elif not arg:
        return ""
    else:
        return arg


def public_ip_format(arg):
    res = []
    if arg.get("cmc_ip"):
        res.append(u"移动: %s" % arg.get("cmc_ip"))
    if arg.get("cnc_ip"):
        res.append(u"网通: %s" % arg.get("cnc_ip"))
    if arg.get("ctc_ip"):
        res.append(u"电信: %s" % arg.get("ctc_ip"))
    if res:
        return Markup("<br>".join(res))
    else:
        return ""


def format_output_not_cut(arg):
    if isinstance(arg, list):
        return ",".join(map(str, arg))
    elif arg:
        return arg
    else:
        return ""


def os_version(arg):
    a = re.compile("\d\.\d")
    if arg:
        b = a.findall(arg)
        if b:
            return b[0]
    else:
        return ""
