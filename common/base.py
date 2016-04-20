#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Name    : base.py
# @Date    : 2016-04-15 18:06
# @Author  : AutoOps
# @Link    : http://www.magicstack.cn/
# @Version :

import tornado.web

class RequestHandler(tornado.web.RequestHandler):

    def write_error(self, status_code, **kwargs):
        error_message = kwargs.get('error_message')
        if status_code == 401:
            self.set_status(401, error_message or 'Unauthorized')
            self.finish("401 Unauthorized")
        else:
            self.set_status(403)
            super(RequestHandler, self).write_error(status_code, **kwargs)