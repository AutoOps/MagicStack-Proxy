#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Name    : urls.py
# @Date    : 2016-04-13 11:20
# @Author  : AutoOps
# @Link    : http://www.magicstack.cn/
# @Version :

import importlib
import logging
logger = logging.getLogger()
urls = []

models = [
    "versions.urls",
    "zoos.v1_0.urls",
    "server.v1_0.urls",
    "ansible.v1_0.urls",
    "websocket.v1_0.urls",
    "account.v1_0.urls",
    "permission.v1_0.urls",
    "scheduler.v1_0.urls",
]

for mod in models:
    url_mod = importlib.import_module('handlers.' + mod)
    for _url in getattr(url_mod, 'urls'):
        if hasattr(url_mod, 'VERSION' ):
            version = getattr(url_mod, 'VERSION')
            old = _url.regex.pattern
            new = "^/{0}{1}".format(version, old)
            urls.append((new, _url.handler_class, _url.kwargs))
        else:
            urls.append(_url)