# -*- coding:utf-8 -*-
from tornado.web import url
from handlers.permission.v1_0.api import *

VERSION = 'v1.0'

urls = [
    url(r'/permission/(?P<obj_name>.*)/(?P<obj_id>.*)$', PermObjectsHandler), #获取所有的对象
    url(r'/permission/event$', PushEventHandler)
]
