#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Name    : urls.py
# @Date    : 2016-04-13 11:25
# @Author  : AutoOps
# @Link    : http://www.magicstack.cn/
# @Version :

from tornado.web import url
from handlers.zoos.v1_0.api import ZooHandler

VERSION = 'v1.0' # API Version

urls = [
    url(r'/zoos/?$', ZooHandler)
]

