#! /usr/bin/env python
# -*- coding:utf-8 -*-

from tornado.web import url
from handlers.ansible.v1_0.api import *

VERSION = 'v1.0'

urls = [
    url(r'/ws/exec', ExecHandler),
    url(r'/module$', ExecPlayHandler),
]

