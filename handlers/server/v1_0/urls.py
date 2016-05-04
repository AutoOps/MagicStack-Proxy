#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Name    : urls.py
# @Date    : 2016-04-18 17:49
# @Author  : AutoOps
# @Link    : http://www.magicstack.cn/
# @Version :

from tornado.web import url
from handlers.server.v1_0.api import SystemActionHandler, SystemHandler, DistrosHandler, \
    EventSingalHandler, FileHandler, ProfileHandler

VERSION = 'v1.0' # API Version

urls = [
    url(r'/system/action$', SystemActionHandler),
    url(r'/system$', SystemHandler),
    url(r'/system/(?P<system_id>.*)$', SystemHandler),
    url(r'/distro?$', DistrosHandler),
    url(r'/distro/(?P<distro_id>.*)$', DistrosHandler),
    url(r'/event/(?P<event_id>.*)$', EventSingalHandler),
    url(r'/profile/?$', ProfileHandler),
    url(r'/upload/?$', FileHandler)
]