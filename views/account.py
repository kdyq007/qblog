# -*- coding:utf-8 -*-

__author__ = 'pycook'

import sys

reload(sys)
sys.setdefaultencoding("utf-8")
import random
import string
import uuid
import json
from functools import wraps
from tasks.mail import send_reg_mail
from flask import Blueprint
from flask import make_response
from flask import request
from flask import flash
from flask import current_app
from flask import redirect
from flask import render_template
from flask import g
from flask import jsonify
from flask import session
from flask import url_for
from flask.ext.principal import identity_changed, Identity, AnonymousIdentity
from flask.ext.babel import gettext as _

from extensions import db
from models.user import User, UserRole, Role
from permissions import auth
from models.user import UserCache
from lib.decorator import templated
from forms.account import LoginForm
from forms.account import RegistForm
from forms.account import ChangePasswordForm
from lib.account import Account_Manager
from lib.auth import Auth_Manager

account = Blueprint('account', __name__)


def auth_with_key(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if isinstance(getattr(g, 'user', None), User):
            identity_changed.send(current_app._get_current_object(),
                                  identity=Identity(g.user.uid))
            return func(*args, **kwargs)
        ip = request.remote_addr
        if ip.strip() in current_app.config.get("WHITE_LIST"):
            key = request.values.get("_key")
            user = UserCache.get(key)
            if user:
                g.user = user
                return func(*args, **kwargs)
            else:
                identity_changed.send(current_app._get_current_object(),
                                      identity=AnonymousIdentity())
                return jsonify(code=400, message="invalid _key and _secret")
        key = request.values.get('_key')
        secret = request.values.get('_secret')
        path = request.path
        keys = sorted(request.values.keys())
        req_args = [request.values[k] for k in keys if
                    str(k) not in ("_key", "_secret")]
        current_app.logger.debug('args is %s' % req_args)
        user, authenticated = User.query.authenticate_with_key(key, secret,
                                                               req_args, path)
        if user and authenticated:
            identity_changed.send(current_app._get_current_object(),
                                  identity=Identity(user.uid))
            return func(*args, **kwargs)
        else:
            identity_changed.send(current_app._get_current_object(),
                                  identity=AnonymousIdentity())
            return jsonify(code=400, message="invalid _key and _secret")

    return wrapper


@account.route("/login", methods=("GET", "POST"))
@templated("account/login.html")
def login():

    # send_reg_mail.delay("kdyq@vip.qq.com")
    # send_reg_mail.apply_async(("kdyq@vip.qq.com",), queue="qblog_async")

    if hasattr(g, 'user') and hasattr(g.user, 'uid') \
            and request.method == 'GET':
        # flash(u'您已登陆成功，但不允许访问，请联系管理员！', 'danger')
        return redirect(url_for('index.home'))
    form = LoginForm(login=request.args.get('login', None),
                     next=request.args.get('next', None),
                     password=request.args.get("password", None),
                     verification=request.args.get('verification', None))
    form_regist = RegistForm(login=request.args.get('login', None),
                             password=request.args.get('password', None),
                             nickname=request.args.get('nickname', None),
                             mobile=request.args.get('mobile', None),
                             employee_id=request.args.get('employee_id', None),
                             department=request.args.get('department', None),
                             next=request.args.get('next', None),
                             verification=request.args.get('verification', None))
    user = None
    authenticated = False
    account_manager = Account_Manager()
    if not account_manager.ip_limit():
        flash(u"由于您的操作错误太过频繁，请于30分钟之后再做尝试！", "danger")
        return render_template("account/login.html", form=form,
                               form_regist=form_regist, action="login")

    current_app.logger.info(form.validate_on_submit())
    if form.validate_on_submit():
        if not account_manager.verification_code(form.verification.data):
            flash(u"验证码错误！", "danger")
            account_manager.regist_failed()
            return render_template("account/login.html", form=form,
                                   form_regist=form_regist)
        if not account_manager.can_login(form.login.data):
            flash(u"密码错误次数太多，请于24小时后再尝试登陆 或 联系管理员！", "danger")
            return render_template("account/login.html", form=form,
                                   form_regist=form_regist)
        user, authenticated = User.query.authenticate(form.login.data,
                                                      form.password.data)
        if not authenticated:
            logined_num = account_manager.login_failed(form.login.data)
            if logined_num is None:
                flash(u"账号或密码错误！", "danger")
            else:
                flash(u"账号或密码错误！还可以登录{0}次。".format(logined_num), "danger")
            return render_template("account/login.html", form=form,
                                   form_regist=form_regist)

    if request.method == "POST" and user and authenticated:
        session.permanent = form.remember.data
        identity_changed.send(current_app._get_current_object(),
                              identity=Identity(user.uid))
        user.logined_num = 0
        db.session.commit()
        next_url = form.next.data
        current_app.logger.info(next_url)
        if not next_url or next_url == request.path:
            next_url = url_for('index.home')
        return redirect(next_url)
    elif request.method == "POST":
        flash(u"登陆失败，请重试！", "danger")
        return render_template("account/login.html", form=form,
                               form_regist=form_regist)
    return dict(form=form, form_regist=form_regist)



@account.route("/logout")
def logout():
    anon = AnonymousIdentity()
    identity_changed.send(current_app._get_current_object(), identity=anon)
    g.user = None
    # next_url = request.referrer
    # next_url = "%s?next=%s" % (url_for("account.login"), next_url)
    # current_app.logger.info(next_url)
    # if next_url:
    #     return redirect(next_url)
    return redirect(url_for('account.login'))


@account.route("/regist", methods=["GET", "POST"])
def regist():
    form = LoginForm(login=request.args.get('login', None),
                     next=request.args.get('next', None),
                     verification=request.args.get('verification', None))
    form_regist = RegistForm(login=request.args.get('login', None),
                             password=request.args.get('password', None),
                             email=request.args.get('email', None),
                             next=request.args.get('next', None),
                             verification=request.args.get('verification', None))
    account_manager = Account_Manager()
    if not account_manager.ip_limit():
        flash(u"由于您的操作错误太过频繁，请于30分钟之后再做尝试！", "danger")
        return render_template("account/login.html", form=form,
                               form_regist=form_regist, action="regist")
    if form_regist.validate_on_submit():
        if not account_manager.verification_code(form.verification.data):
            flash(u"验证码错误！", "danger")
            account_manager.regist_failed()
            return render_template("account/login.html", form=form,
                                   form_regist=form_regist, action="regist")
        is_username_exits = User.query.is_exits(form_regist.login.data)
        is_email_exits = User.query.email_is_exits(form_regist.email.data)
        # is_mobile_is_exits = User.query.mobile_is_exits(
        #     form_regist.mobile.data)
        if is_username_exits:
            flash(u"用户名已存在，请直接登录！", "danger")
            account_manager.regist_failed()
            return render_template("account/login.html", form=form,
                                   form_regist=form_regist, action="regist")
        if is_email_exits:
            flash(u"邮箱已被注册，请检查！", "danger")
            account_manager.regist_failed()
            return render_template("account/login.html", form=form,
                                   form_regist=form_regist, action="regist")
        # if is_mobile_is_exits:
        #     flash(u"手机号已被注册，请检查！", "danger")
        #     account_manager.regist_failed()
        #     return render_template("account/login.html", form=form,
        #                            form_regist=form_regist, action="regist")
        account_manager = Account_Manager()
        user = account_manager.add_user(form_regist.login.data,
                                        form_regist.email.data)
        if not user:
            flash(u"注册失败，请重试！", "danger")
            return render_template("account/login.html", form=form,
                                   form_regist=form_regist, action="regist")
        am = Auth_Manager()
        am.add_username_auth(user.uid, form_regist.password.data)
        identity_changed.send(current_app._get_current_object(),
                              identity=Identity(user.uid))
        # next_url = form_regist.next.data
        # current_app.logger.info(next_url)
        # if not next_url or next_url == request.path:
        #     next_url = url_for('index.home')
        # return redirect(next_url)


        #close IP Request
        #flash(u"注册成功，请通知管理员申请登陆权限，需要自己的本地IP地址！", "success")
        flash(u"注册成功，已发送一封激活邮件到您的邮箱，请注意查收！", "success")
        send_reg_mail.delay("kdyq@vip.qq.com")
        return render_template("account/login.html", form=form,
                           form_regist=form_regist, action="login")
    return render_template("account/login.html", form=form,
                           form_regist=form_regist, action="regist")


@account.route("/profile", methods=("GET", "POST"))
@auth.require()
def profile():
    user = User.query.get(g.user.uid)
    if not user:
        flash(_("the user is null or no permission"), "warn")
        return redirect(request.referrer)
    if request.method == "POST":
        username = request.form.get("user[name]", None)
        if username:
            user.username = username
        else:
            flash("username cannot be empty")
            return redirect(request.referrer)
        user.nickname = request.form.get("user[nickname]", user.username)
        user.email = request.form.get("user[email]", None)
        user.mobile = request.form.get("user[mobile]", None)
        user.catalog = request.form.get("user[catalog]", None)
        user.department = request.form.get("user[department]", None)
        db.session.add(user)
        try:
            db.session.commit()
            flash(_("update profile success"), "success")
        except Exception as e:
            db.session.rollback()
            current_app.logger.warn("edit user profile is error, %s" % str(e))
            flash(_("edit user profile is error, duplicated key"), "error")
        UserCache.clean(g.user)
        return redirect(request.referrer)
    username = g.user.username if g.user.username else ""
    nickname = g.user.nickname if g.user.nickname else g.user.username
    email = g.user.email if g.user.email else ""
    mobile = g.user.mobile if g.user.mobile else ""
    department = g.user.department if g.user.department else ""
    catalog = g.user.catalog if g.user.catalog else ""
    departments = current_app.config.get("DEPARTMENT")
    catalogs = current_app.config.get("CATALOG")[department] if department \
        else current_app.config.get("CATALOG")[departments[0]]
    catalogs = [c.decode("utf-8") for c in catalogs]
    return render_template("account/s_home.html", username=username,
                           nickname=nickname, email=email, mobile=mobile,
                           departments=departments, department=department,
                           catalogs=catalogs, catalog=catalog,
                           rolenames=g.user.rolenames)


@account.route("/profile/catalog")
def get_catalog():
    department = request.args.get("department")
    if not department:
        return jsonify(code=200, catalogs=[])
    return jsonify(code=200,
                   catalogs=current_app.config.get("CATALOG")[department])


@account.route("/password")
@account.route("/password/<string:action>", methods=("GET", "POST"))
@auth.require()
def password_get(action=None):
    user = User.query.get(g.user.uid)
    if not user:
        flash(_("the user is null or no permission"), "warn")
        return redirect(request.referrer)
    if request.method == "POST" and action == "reset_key":
        _uuid = uuid.uuid4().hex
        user.key = _uuid
        user.secret = ''.join(
            random.sample(string.ascii_letters + string.digits + '~!@#$%^&*?',
                          32))
        db.session.add(user)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error("set key error, %s" % str(e))
            flash(_("set key errors, {0:s}".format(str(e))), "error")
        UserCache.clean(user)
        return redirect(url_for('account.password_get'))
    return render_template("account/s_account.html")


@account.route("/password/update_password", methods=("POST",))
@auth.require()
def password_post():
    user = User.query.get(g.user.uid)
    if not user:
        flash(_("the user is null or no permission"), "warn")
        return redirect(request.referrer)
    old_passwd = request.form.get('old_passwd')
    passwd = request.form.get("passwd")
    confirm = request.form.get("confirm")
    if not user.check_password(old_passwd):
        flash("Invalid old password", 'error')
        return redirect(url_for('account.password_get'))
    if not (passwd and confirm and passwd == confirm):
        flash(_("Password cannot be empty, two inputs must be the same"),
              "warn")
        return redirect(url_for('account.password_get'))
    user.password = passwd
    db.session.add(user)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error("set password error, %s" % str(e))
        flash(_("set password errors, {0:s}".format(str(e))), "error")
    UserCache.clean(user)
    flash(_('you need login'), "warn")
    return redirect(url_for('account.login'))


@account.route("/roles")
@account.route("/roles/<string:action>", methods=("GET", "POST"))
@auth.require()
def role(action=None):
    user = User.query.get(g.user.uid)
    if not user:
        flash(_("the user is null or no permission"), "warn")
        return redirect(request.referrer)
    roles = Role.query.filter().all()
    if request.method == "POST":
        if action == "new_role":
            role_name = request.form.get("role-name")
            role = Role.query.filter(Role.role_name == role_name).first()
            if not role:
                role = Role()
                role.role_name = role_name
                db.session.add(role)
                try:
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.warn(
                        "add a new role error, %s" % str(e))
                    flash(_("add a new role error"), "error")
            else:
                flash(_("this role is existed"), "warn")
            return redirect(request.referrer)
        elif action == "assign_role":
            users = request.form.get("users", "")
            roles = request.form.get("roles", "")
            users = users.strip().split(";")
            roles = roles.strip().split(";")
            current_app.logger.info(users)
            if not roles[-1]:
                roles.pop(-1)
            if not users[0] or not roles[0]:
                return make_response(
                    json.dumps(dict(code=400, message="check input")))

            role_ids = [Role.query.filter(Role.role_name == role).first().rid
                        for role in roles if role]
            user_ids = [User.query.filter(User.username == user).first().uid
                        for user in users if
                        User.query.filter(User.username == user).first()]
            for user_id in user_ids:
                for role_id in role_ids:
                    user_role = UserRole.query.filter(
                        UserRole.uid == user_id,
                        UserRole.rid == role_id).first()
                    if not user_role:
                        user_role = UserRole()
                        user_role.uid = user_id
                        user_role.rid = role_id
                        db.session.add(user_role)
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                current_app.logger.warn(
                    "assign role error, {0:s}".format(str(e)))
                flash(_("assign role error"), "error")
                return make_response(
                    json.dumps(dict(code=400, message=str(e))))
            return make_response(json.dumps(dict(code=200)))
        elif action in ("all_users", "all_roles"):
            username = request.form.get("username", "").strip()
            rolename = request.form.get("rolename", "").strip()
            current_app.logger.info(username + rolename)
            user = User.query.filter(User.username == username).first()
            role = Role.query.filter(Role.role_name == rolename).first()
            user_role = None
            if user and role:
                user_role = UserRole.query.filter(
                    UserRole.uid == user.uid,
                    UserRole.rid == role.rid).first()
            if not user_role:
                return make_response(json.dumps(
                    dict(code=400, message="the role is not existed")))
            db.session.delete(user_role)
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                flash(_("delete role error"), "error")
                current_app.logger.error(str(e))
                return make_response(
                    json.dumps(dict(code=400, message="delete role error")))
            return make_response(json.dumps(dict(code=200)))
    elif request.method == "GET":
        if action == "del_role":
            role_id = request.args.get("role_id")
            if role_id:
                role_id = int(role_id)
            role = Role.query.filter(Role.rid == role_id).first()
            if not role:
                flash(_("role is not existed"), "warn")
            db.session.delete(role)
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                current_app.logger.warn("del role is error, %s" % str(e))
                flash("del role cannot be deleted")
            return redirect(request.referrer)
        elif action == "role_users":
            role_id = request.args.get("role_id")
            if role_id:
                role_id = int(role_id)
            role = Role.query.filter(Role.rid == role_id).first()
            if not role:
                flash(_("role is not existed"), "warn")
            role_users = UserRole.query.filter(UserRole.rid == role_id).all()
            users = [User.query.filter(User.uid == role_user.uid).first() for
                     role_user in role_users]
            return make_response(json.dumps(users))
        elif action == "all_users":
            users = User.query.filter().all()
            roles = [user.rolenames for user in users]
            return render_template("account/s_roles_user.html", users=users,
                                   roles=roles)

        elif action == "all_roles":
            role_id = request.args.get("role_id")
            if role_id:
                role_id = int(role_id)
                role = Role.query.filter(Role.rid == role_id).first()
                role_users = UserRole.query.filter(
                    UserRole.rid == role_id).all()
                users = [User.query.filter(User.uid == role_user.uid).first()
                         for role_user in role_users]
                return render_template("account/s_roles_manager_user.html",
                                       users=users, role=role)
            return render_template("account/s_roles_manager.html", roles=roles)

    return render_template("account/s_roles_home.html", roles=roles)


@account.route("/api")
@auth.require()
def api():
    user = User.query.get(g.user.uid)
    if not user:
        flash(_("the user is null or no permission"), "warn")
        return redirect(request.referrer)
    q = request.args.get("q")
    t = request.args.get("t")
    usernames = list()
    if not q:
        return make_response(json.dumps(usernames))
    if t == "user":
        users = User.query.search(q)
        usernames = [user.username for user in users]
        return make_response(json.dumps(usernames))
    elif t == "usernick":
        users = User.query.search(q)
        users = ['%s|%s' % (user.nickname, user.username) for user in users]
        return make_response(json.dumps(users))
    else:
        roles = Role.query.filter(Role.role_name.ilike("%" + q + "%")).all()
        rolenames = [role.role_name for role in roles]
        return make_response(json.dumps(rolenames))


@account.route('/change_password', methods=['GET', 'POST'])
@templated("account/update_password.html")
@auth.require()
def change_password():
    form = ChangePasswordForm(
        old_password=request.args.get('password', None),
        password=request.args.get('password', None),
        password1=request.args.get('password', None),
        next=request.args.get('next', None),
        verification=request.args.get('verification', None))
    if request.method == 'GET':
        return render_template('account/update_password.html', form=form)
    else:
        account_manager = Account_Manager()
        if not account_manager.ip_limit():
            flash(u"由于您的操作错误太过频繁，请于30分钟之后再做尝试！", "danger")
            return render_template(url_for('index.home'))
        if form.validate_on_submit():
            if not account_manager.verification_code(form.verification.data):
                flash(u"验证码错误！", "danger")
                account_manager.regist_failed()
                return render_template("account/update_password.html", form=form)
            user = User.query.get(g.user.uid)
            old_password = form.old_password.data
            password = form.password.data
            password1 = form.password1.data
            if not user.check_password(old_password):
                flash(u"原始密码错误", 'danger')
                return render_template("account/update_password.html",
                                       form=form)
            if not (password and password1 and password == password1):
                flash(u"密码不能为空，两次密码必须相等！", 'error')
                return render_template("account/update_password.html",
                                       form=form)
            user._set_password(password)
            db.session.add(user)
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(u"修改密码错误：%s" % str(e))
                flash(_(u"修改密码错误：{0:s}".format(str(e))), "danger")
            UserCache.clean(user)
            anon = AnonymousIdentity()
            identity_changed.send(current_app._get_current_object(),
                                  identity=anon)
            g.user = None
            return redirect(url_for('account.login'))
        else:
            flash(u"修改失败，请重试！", "danger")
            return render_template("account/update_password.html", form=form)

