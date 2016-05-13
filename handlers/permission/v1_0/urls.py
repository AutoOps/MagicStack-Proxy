# -*- coding:utf-8 -*-
from tornado.web import url
from handlers.permission.v1_0.api import *

VERSION = 'v1.0'

urls = [
    url(r'^/permission/role/(?P<role_id>.*)$', PermInfoHandler),
]
