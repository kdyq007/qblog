# encoding=utf-8

from flask.ext.principal import RoleNeed, Permission

admin = Permission(RoleNeed('admin'))
auth = Permission(RoleNeed('authenticated'))
null = Permission(RoleNeed('null'))
# op = Permission(RoleNeed('op'))
# sys_op = Permission(RoleNeed("sys_op"))
# cmdb_admin = Permission(RoleNeed("cmdb_admin"))
