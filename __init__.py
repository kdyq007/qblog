# encoding=utf-8

import logging
import os
from logging.handlers import SMTPHandler
from logging.handlers import TimedRotatingFileHandler

from flask import Flask
from flask import current_app
from flask import flash
from flask import g
from flask import jsonify
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for
from flask.ext.assets import Bundle
from flask.ext.assets import Environment
from flask.ext.babel import Babel
from flask.ext.principal import PermissionDenied
from flask.ext.principal import Principal
from flask.ext.principal import identity_loaded

import views
from extensions import cache

from extensions import celery
from extensions import db
# from extensions import mail
from lib import filters
from models.user import User

APP_NAME = "qblog"

MODULES = (
    (views.index, ""),
    (views.account, "/account"),
)


class ReverseProxied(object):
    '''Wrap the application in this middleware and configure the
    front-end server to add these headers, to let you quietly bind
    this to a URL other than / and to an HTTP scheme that is
    different than what is used locally.

    In nginx:
    location /myprefix {
        proxy_pass http://192.168.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Scheme $scheme;
        proxy_set_header X-Script-Name /myprefix;
        }

    :param app: the WSGI application
    '''

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        script_name = environ.get('HTTP_X_SCRIPT_NAME', '')
        if script_name:
            environ['SCRIPT_NAME'] = script_name
            path_info = environ['PATH_INFO']
            if path_info.startswith(script_name):
                environ['PATH_INFO'] = path_info[len(script_name):]

        scheme = environ.get('HTTP_X_SCHEME', '')
        if scheme:
            environ['wsgi.url_scheme'] = scheme
        return self.app(environ, start_response)


def make_app(config=None, modules=None):
    modules = modules
    if not modules:
        modules = MODULES
    app = Flask(APP_NAME)
    app.config.from_pyfile(config)
    configure_extensions(app)
    configure_i18n(app)
    configure_identity(app)
    configure_blueprints(app, modules)
    configure_logging(app)
    configure_template_filters(app)
    exception_handler_configure(app)
    configure_assets(app)
    app.wsgi_app = ReverseProxied(app.wsgi_app)
    return app


def configure_extensions(app):
    db.app = app
    celery.init_app(app)
    db.init_app(app)
    # mail.init_app(app)
    cache.init_app(app)


def configure_i18n(app):
    babel = Babel(app)

    @babel.localeselector
    def get_locale():
        accept_languages = app.config.get('ACCEPT_LANGUAGES', ['en', 'zh'])
        return request.accept_languages.best_match(accept_languages)


def configure_modules(app, modules):
    for module, url_prefix in modules:
        app.register_module(module, url_prefix=url_prefix)


def configure_blueprints(app, modules):
    for module, url_prefix in modules:
        app.register_blueprint(module, url_prefix=url_prefix)


def configure_identity(app):
    principal = Principal(app)

    @identity_loaded.connect_via(app)
    def on_identity_loaded(sender, identity):
        g.user = User.query.from_identity(identity)


def configure_logging(app):
    hostname = os.uname()[1]
    mail_handler = SMTPHandler(
        app.config['MAIL_SERVER'],
        app.config['DEFAULT_MAIL_SENDER'],
        app.config['ADMINS'],
        '[%s] cmdb application error' % hostname,
        (
            app.config['MAIL_USERNAME'],
            app.config['MAIL_PASSWORD'],
        )
    )
    mail_formater = logging.Formatter(
        "%(asctime)s %(levelname)s %(pathname)s %(lineno)d\n%(message)s")
    mail_handler.setFormatter(mail_formater)
    mail_handler.setLevel(logging.ERROR)
    if not app.debug:
        app.logger.addHandler(mail_handler)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(pathname)s %(lineno)d - %(message)s")
    log_file = app.config['LOG_PATH']
    file_handler = TimedRotatingFileHandler(log_file,
                                            when='d',
                                            interval=1,
                                            backupCount=7)
    file_handler.setLevel(getattr(logging, app.config['LOG_LEVEL']))
    file_handler.setFormatter(formatter)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(getattr(logging, app.config['LOG_LEVEL']))


def configure_template_filters(app):
    for name in dir(filters):
        if callable(getattr(filters, name)):
            app.add_template_filter(getattr(filters, name))


def configure_assets(app):
    assets = Environment(app)
    css = Bundle(
        'bootstrap/bootstrap.min.css',
        'dist/css/flat-ui.min.css',
        'bootstrap-datetimepicker/css/bootstrap-datetimepicker.css',
        # 'bootstrap/bootstrap-theme.min.css',
        # 'others/select2/select2.min.css',
        # 'others/smartwizard/smart_wizard.css',
        # 'fonts/font-awesome.min.css',
        'main.css',
        filters="cssmin", output='temp/common_packed.css')
    js = Bundle(
        'dist/js/vendor/jquery.min.js',
        'jquery/jquery.form.js',
        'dist/js/vendor/video.js',
        'dist/js/flat-ui.min.js',
        'bootstrap-datetimepicker/js/bootstrap-datetimepicker.js',
        'bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.zh-CN.js',
        'message.js',
        # 'others/particles/particles.js',
        # 'others/select2/select2.full.min.js',
        # 'others/jquery.sortable.min.js',
        # 'others/smartwizard/jquery.smartWizard.js',
        'main.js',
        filters='jsmin', output='temp/common_packed.js')
    assets.register('css_common', css)
    assets.register('js_common', js)


def exception_handler_configure(app):
    old_handler = app.handle_exception

    def exception_handler(e):
        if isinstance(e, PermissionDenied):
            error = 'Sorry, page not allowed'
            if request.is_xhr:
                return jsonify(error=error)
            try:
                if g.user:
                    if request.referrer:
                        flash(u"您的权限不够, 请联系相关管理员来申请相应权限", "error")
                        return redirect(request.referrer)
                    else:
                        flash(u"您的权限不够, 请联系相关管理员来申请相应权限", "error")
                        return redirect(url_for("account.login"))

            except AttributeError:
                pass
            _next = request.url.replace("&", "%26")
            return redirect(url_for('account.login', next=_next))
        else:
            import traceback

            current_app.logger.error("server internal error, %s" %
                                     traceback.format_exc())
            if request.is_xhr:
                return jsonify(code=400, message=str(e))
            return render_template("500.html", error=str(e))

    app.handle_exception = exception_handler
