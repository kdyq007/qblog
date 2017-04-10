# -*- coding:utf-8 -*- 

from functools import wraps

from flask import render_template
from flask import request


class ArgumentRequiredError(Exception):
    def __init__(self, arg_tuple):
        self.arg_tuple = arg_tuple

    def __str__(self):
        return "ArgumentRequiredError: %s must be required" % str(
            self.arg_tuple)


def templated(template=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            template_name = template
            if template_name is None:
                template_name = request.endpoint.replace('.', '/') + '.html'
            ctx = f(*args, **kwargs)
            if ctx is None:
                ctx = {}
            elif not isinstance(ctx, dict):
                return ctx
            return render_template(template_name, **ctx)

        return decorated_function

    return decorator


def argument_required1(*args_required):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            for arg in args_required:
                if request.values.get(arg, None) is None:
                    raise ArgumentRequiredError(args_required)
            return f(*args, **kwargs)

        return decorated_function

    return decorator


class argument_required(object):
    def __init__(self, *args):
        self.args = args

    def __enter__(self):
        for arg in self.args:
            if not request.values.get(arg):
                raise ArgumentRequiredError(self.args)

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
