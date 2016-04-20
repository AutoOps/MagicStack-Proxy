#! /usr/bin/env python
# -*- coding:utf-8 -*-

from tornado.web import url
from handlers.ansible.v1_0.api import GenModulesHandler,ExecPlayHandler,ExecPlayBookHandler

VERSION = 'v1.0'

urls = [
    url(r'/modules/all/?$', GenModulesHandler),
    url(r'/modules/$', ExecPlayHandler),
    url(r'/modules/file/$', ExecPlayBookHandler)
]

