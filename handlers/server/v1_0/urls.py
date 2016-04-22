#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Name    : urls.py
# @Date    : 2016-04-18 17:49
# @Author  : AutoOps
# @Link    : http://www.magicstack.cn/
# @Version :

from tornado.web import url
from handlers.server.v1_0.api import SystemActionHandler, SystemHandler, DistrosHandler, EventSingalHandler

VERSION = 'v1.0' # API Version

urls = [
    url(r'/system/action?$', SystemActionHandler),
    url(r'/system?$', SystemHandler),
    url(r'/distros?$', DistrosHandler),
    url(r'/(?P<event_id>.*)/event?$', EventSingalHandler)
]
