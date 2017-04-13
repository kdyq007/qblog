# -*- coding:utf-8 -*-
__author__ = 'qiqi'

import StringIO
import datetime

import redis
import json
from flask import Blueprint
from flask import current_app
from flask import g
from flask import jsonify
from flask import redirect
from flask import render_template
from flask import request
from flask import session
from flask import url_for
from flask.ext.sqlalchemy import Pagination

from extensions import db
from lib.aes import prpcrypt
# from lib.imagechar import ImageChar
from lib.ip_required import ip_required
from lib.m_account import M_Account_Manager
from lib.m_user import M_User_Manager
from lib.market import Market_Manager
from models.user import User
from models.user import UserCache
# from models.m_account import M_Account
# from models.m_user import M_User
# from models.market import Market
# from models.users import Market_Users
from permissions import auth


index = Blueprint("index", __name__)


@index.route('/', methods=['GET'])
# @auth.require()
# @ip_required
def home():
#     if g.user.is_account_admin():
#         return redirect(url_for('index.admin_index'))
#     else:
#         return redirect(url_for('index.employee_index'))
    from forms.account import LoginForm
    form = LoginForm(login=request.args.get('login', None),
                         next=request.args.get('next', None),
                         password=request.args.get("password", None),
                         verification=request.args.get('verification', None))
    return render_template('index.html', form=form)

@index.route('/admin_index', methods=['GET'])
@auth.require()
@ip_required
def admin_index():
    if not g.user.is_account_admin():
        return redirect(url_for('index.employee_index'))
    page = int(request.values.get("page", 1))
    page_size = int(request.values.get("page_size", 10))
    market_name = request.values.get("search_market_name", "")
    numfound, total, markets = Market.query.get_all_markets(market_name, page, page_size)
    pagination = Pagination(None, page, page_size, numfound, None)
    return render_template('account_manage.html', numfound=numfound,
                           page=page, page_size=page_size,
                           pagination=pagination,
                           markets=markets,
                           market_name=market_name)


@index.route('/employee_index', methods=['GET'])
@auth.require()
@ip_required
def employee_index():
    m_users = db.session.query(M_User).filter(M_User.uid == g.user.uid).all()
    markets = []
    pc = prpcrypt()
    for m_user in m_users:
        m_accounts = db.session.query(M_Account).filter(
            M_Account.a_id == m_user.aid).all()
        for m_account in m_accounts:
            data = {
                "aid": m_account.a_id,
                "name": m_account.market.name,
                "url": m_account.market.url,
                "account": m_account.account,
                "password": pc.decrypt(str(m_account.password)),
                "invalid_date": m_account.invalid_date,
                "updated_at": m_account.updated_at,
            }
            markets.append(data)
    return render_template('employee_index.html', markets=markets)


@index.route('/', methods=['PUT'])
@auth.require()
@ip_required
def add_market():
    if not g.user.is_account_admin():
        return jsonify({"status": 400, "message": "无权限的操作！"})
    market_name = request.values.get("market_name").strip()
    market_url = request.values.get("market_url").strip()
    market_description = request.values.get("market_description").strip()
    market_account = request.values.get("market_account").strip()
    market_password = request.values.get("market_password").strip()
    invalid_date = request.values.get("invalid_date").strip()

    market_manager = Market_Manager()
    market, message = market_manager.add_market(market_name, market_url,
                                                market_description)
    if market is not None:
        m_account_manager = M_Account_Manager()
        m_account = m_account_manager.add_m_account(market.mid,
                                                    market_account,
                                                    market_password,
                                                    description=None,
                                                    invalid_date=invalid_date)
        if m_account:
            db.session.commit()
            return jsonify({"status": 200})
    db.session.rollback()
    return jsonify({"status": 400, "message": message})


@index.route("/excel_import", methods=["POST"])
@auth.require()
@ip_required
def excel_import():
    if not g.user.is_account_admin:
        return jsonify({"status": 400, "message": "无权限的操作！"})
    import os
    import xlrd
    UPLOAD_FOLDER = 'static/excel'
    if not os.path.isdir(UPLOAD_FOLDER):
        os.mkdir(UPLOAD_FOLDER)
    f = request.files.get('market_file')
    file_name = datetime.datetime.strftime(datetime.datetime.now(),
                                           '%Y%m%d%H%M%S')
    f_path = os.path.join(UPLOAD_FOLDER, file_name + '.xlsx')
    f.save(f_path)
    if os.path.isfile(f_path):
        data = xlrd.open_workbook(f_path)
        table = data.sheets()[0]
        for i in range(table.nrows):
            if i != 0:
                row = table.row_values(i)
                market_manager = Market_Manager()
                market, message = market_manager.add_market(
                    str(row[0]).strip(),
                    str(row[1]).strip())
                if market is not None:
                    m_account_manager = M_Account_Manager()
                    m_account = m_account_manager.add_m_account(market.mid,
                                                                str(row[
                                                                        2]).strip(),
                                                                str(row[
                                                                        3]).strip())
        try:
            db.session.commit()
            return jsonify({"status": 200, "message": "导入成功，请刷新页面！"})
        except Exception as e:
            db.session.rollback()
            return jsonify({"status": 400, "message": "导入失败，请重试！"})
    else:
        return jsonify({"status": 400, "message": "未找到excel文件！"})


@index.route('/<int:mid>', methods=['POST'])
@auth.require()
@ip_required
def modify_market(mid):
    if not g.user.is_account_admin():
        return jsonify({"status": 400, "message": "无权限的操作！"})
    market_name = request.values.get("market_name")
    market_url = request.values.get("market_url")
    market_description = request.values.get("market_description")
    market_account = request.values.get("market_account")
    market_password = request.values.get("market_password")
    invalid_date = request.values.get("invalid_date")

    market_manager = Market_Manager()
    market, message = market_manager.modify_market(mid, market_name,
                                                   market_url,
                                                   market_description)
    if market is not None:
        m_account_manager = M_Account_Manager()
        m_account = m_account_manager.modify_m_account(market.mid,
                                                       market_account,
                                                       market_password,
                                                       description=None,
                                                       invalid_date=invalid_date)
        if m_account:
            db.session.commit()
            return jsonify({"status": 200})
    db.session.rollback()
    return jsonify({"status": 400, "message": message})


@index.route('/', methods=['DELETE'])
@auth.require()
@ip_required
def delete_market():
    if not g.user.is_account_admin():
        return jsonify({"status": 400, "message": "无权限的操作！"})
    mid = request.values.get("mid")
    db.session.query(Market).filter(Market.mid == mid).delete()
    try:
        db.session.commit()
        return jsonify({"status": 200})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": 400, "message": "市场删除失败！"})


@index.route('/get_m_users_from_mid/<int:mid>', methods=['GET'])
@auth.require()
@ip_required
def get_m_users_from_mid(mid):
    all_users = Market_Users.query.get_all_users()
    m_account = db.session.query(M_Account).filter(
        M_Account.mid == mid).first()
    if m_account:
        m_users = db.session.query(M_User).filter(
            M_User.aid == m_account.a_id).all()
        select_users = []
        for m_user in m_users:
            select_users.append(m_user.uid)
        return jsonify({"all_users": all_users, "select_users": select_users})
    return jsonify({"all_users": all_users, "select_users": []})


@index.route('/modify_m_users_from_mid/<int:mid>', methods=['POST'])
@auth.require()
@ip_required
def modify_m_users_from_mid(mid):
    if not g.user.is_account_admin():
        return jsonify({"status": 400, "message": "无权限的操作！"})
    uids = request.form.getlist("uids[]")
    m_account = db.session.query(M_Account).filter(
        M_Account.mid == mid).first()
    if not m_account:
        m_account_manage = M_Account_Manager()
        m_account = m_account_manage.add_m_account(mid)
        if not m_account:
            current_app.logger.info("账号记录不存在，且添加失败！")
            return jsonify({"status": 400, "message": "修改使用人失败"})

    m_users = db.session.query(M_User).filter(
        M_User.aid == m_account.a_id).delete()
    # for m_user in m_users:
    #     if str(m_user.uid) in uids:
    #         db.session.delete(m_user)
    for uid in uids:
        m_user_manage = M_User_Manager()
        m_user_manage.add_m_user(int(uid), m_account.a_id)
    try:
        db.session.commit()
        return jsonify({"status": 200, "message": "修改使用人成功！"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": 400, "message": "修改使用人失败"})


@index.route('/users_list', methods=['GET'])
@auth.require()
@ip_required
def users_list():
    if not g.user.is_account_admin():
        return redirect(url_for('index.employee_index'))
    m_users = Market_Users.query.get_all_users()
    users = db.session.query(User).all()
    users_datas = []
    for user in users:
        users_datas.append(user.username)
        users_datas.append(user.nickname)
    return render_template('users_list.html', m_users=m_users,
                           users_datas=users_datas)


@index.route('/user_manage/<int:uid>', methods=['GET'])
@auth.require()
@ip_required
def user_manage(uid):
    if not g.user.is_account_admin():
        return redirect(url_for('index.employee_index'))
    m_user = Market_Users.query.get_user_from_uid(uid)
    m_accounts = M_Account.query.get_user_accounts(uid)
    return render_template('user_manage.html', m_accounts=m_accounts,
                           m_user=m_user)


@index.route('/add_user', methods=['PUT'])
@auth.require()
@ip_required
def add_user():
    if not g.user.is_account_admin():
        return jsonify({"status": 400, "message": "无权限的操作！"})
    nickname = request.values.get("nickname")
    employee_id = request.values.get("employee_id")
    department = request.values.get("department")
    mobile = request.values.get("mobile")
    ip = request.values.get("ip")

    user = UserCache.get(nickname)
    if not user:
        return jsonify({"status": 400, "message": "没有找到该用户，请注意是否打错！"})
    market_user = db.session.query(Market_Users).filter(
        Market_Users.uid == user.uid).first()
    if market_user:
        return jsonify({"status": 400, "message": "用户已存在！"})
    market_user = Market_Users()
    market_user.uid = user.uid
    market_user.ip = ip
    db.session.add(market_user)

    _user = db.session.query(User).filter(User.uid == user.uid).first()
    if _user is not None:
        _user.department = department
        _user.mobile = mobile
        _user.employee_id = employee_id
        UserCache.clean(_user)
    try:
        db.session.commit()
        return jsonify({"status": 200})
    except Exception as e:
        return jsonify({"status": 400, "message": "添加用户失败！"})


@index.route('/modify_user', methods=['POST'])
@auth.require()
@ip_required
def modify_user():
    if not g.user.is_account_admin():
        return jsonify({"status": 400, "message": "无权限的操作！"})
    nickname = request.values.get("nickname")
    employee_id = request.values.get("employee_id")
    department = request.values.get("department")
    mobile = request.values.get("mobile")
    ip = request.values.get("ip")

    user = UserCache.get(nickname)
    if not user:
        return jsonify({"status": 400, "message": "CMDB没有找到该用户，请注意是否打错！"})
    market_user = db.session.query(Market_Users).filter(
        Market_Users.uid == user.uid).first()
    if not market_user:
        return jsonify({"status": 400, "message": "没有找到该用户，请注意是否打错！"})
    market_user.uid = user.uid
    market_user.ip = ip

    _user = db.session.query(User).filter(User.uid == user.uid).first()
    if _user is not None:
        _user.department = department
        _user.mobile = mobile
        _user.employee_id = employee_id
        UserCache.clean(_user)
    try:
        db.session.commit()
        return jsonify({"status": 200})
    except Exception as e:
        return jsonify({"status": 400, "message": "修改用户失败！"})


@index.route('/delete_user', methods=['DELETE'])
@auth.require()
@ip_required
def delete_user():
    if not g.user.is_account_admin():
        return jsonify({"status": 400, "message": "无权限的操作！"})
    uid = request.values.get("uid")
    db.session.query(M_User).filter(M_User.uid == uid).delete()
    db.session.query(Market_Users).filter(Market_Users.uid == uid).delete()
    try:
        db.session.commit()
        return jsonify({"status": 200})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": 400, "message": "删除用户失败！"})


@index.route('/get_user_data', methods=['GET'])
@auth.require()
@ip_required
def get_user_data():
    name = request.values.get("name")
    user = UserCache.get(name)
    if user:
        data = {
            "department": user.department,
            "mobile": user.mobile,
            "employee_id": user.employee_id
        }
        market_user = db.session.query(Market_Users).filter(
            Market_Users.uid == user.uid).first()
        if market_user is not None:
            data["ip"] = market_user.ip
        return jsonify({"status": 200, "data": data})
    return jsonify({"status": 400})


@index.route('/get_market_data/<int:mid>', methods=['GET'])
@auth.require()
@ip_required
def get_market_data(mid):
    market = db.session.query(Market).filter(Market.mid == mid).first()
    if market:
        if market.m_account[0].invalid_date:
            date = datetime.datetime.strftime(market.m_account[0].invalid_date,
                                              '%Y-%m-%d')
        else:
            date = market.m_account[0].invalid_date
        pc = prpcrypt()
        data = {
            "name": market.name,
            "url": market.url,
            "description": market.description,
            "account": market.m_account[0].account,
            "password": pc.decrypt(market.m_account[0].password),
            "invalid_date": date
        }
        return jsonify({"status": 200, "data": data})
    return jsonify({"status": 400, "message": "获取数据失败！"})


@index.route('/release_user', methods=['GET'])
@auth.require()
def release_user():
    if not g.user.is_account_admin():
        return jsonify({"status": 400, "message": u"无权限的操作！"})
    username = request.values.get("username")
    user = db.session.query(User).filter(User.username == username).first()
    if user is not None:
        user.logined_num = 0
        try:
            db.session.commit()
        except:
            return jsonify({"status": 400, "message": u"解禁用户失败！"})
        return jsonify({"status": 200, "message": u"解禁用户成功！"})
    return jsonify({"status": 400, "message": u"未找到该用户！"})


@index.route('/release_ip', methods=['GET'])
@auth.require()
def release_ip():
    if not g.user.is_account_admin():
        return jsonify({"status": 400, "message": u"无权限的操作！"})
    ip = request.values.get("ip")
    redis_client = redis.StrictRedis(
        host=current_app.config.get("CACHE_REDIS_HOST"),
        port=current_app.config.get("CACHE_REDIS_PORT"),
        db=current_app.config.get("REDIS_DB"), password="")
    num = redis_client.hget(ip, "num")
    if num is not None:
        redis_client.hset(ip, "num", "0")
        return jsonify({"status": 200, "message": u"解禁IP成功！"})
    return jsonify({"status": 400, "message": u"未找到该IP！"})

