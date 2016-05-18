# -*- coding:utf-8 -*-
from tornado.web import url
from handlers.account.v1_0.api import *

VERSION = 'v1.0'

urls = [
    url(r'/account/(?P<role_id>.*)/(?P<role_id>.*)$', UserHandler),
]
