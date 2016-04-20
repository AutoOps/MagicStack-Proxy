#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Name    : api.py
# @Date    : 2016-04-18 17:49
# @Author  : AutoOps
# @Link    : http://www.magicstack.cn/
# @Version :

import logging
import traceback
try:
    import simplejson as json
except ImportError:
    import json

from tornado.web import asynchronous
from tornado.gen import coroutine
from tornado.concurrent import run_on_executor
from concurrent.futures import ThreadPoolExecutor

from common.base import RequestHandler
from common.cobbler_api import System
from utils.auth import auth

logger = logging.getLogger()

class ServerActionHandler(RequestHandler):
    """
        服务器操作，批量开机/关机/重启
    """

    #@auth
    def post(self, *args, **kwargs):
        params = json.loads(self.request.body)
        power = params.get('power')
        systems = params.get('systems', None)
        try:
            if power:
                if power.lower() not in ( 'on', 'off', 'reboot', 'status' ):
                    self.write_error(403)
                    return

                if not isinstance(systems, list) and not isinstance(systems, tuple):
                    self.write_error(403)
                    return

                params = {
                    'power' :  power.lower(),
                    'systems' : systems ,
                }
                system = System()
                system.power(params)
                self.set_status(202, 'success')
                self.finish({'messege':'running'})
        except:
            logger.error(traceback.format_exc())
            self.set_status(500, 'failed')
            self.finish({'messege':'failed'})

class ServerHandler(RequestHandler):
    """
        服务器
    """

    #@auth
    def get(self, *args, **kwargs):
        """
            获取服务器信息
        """
        pass

    #@auth
    def post(self, *args, **kwargs):
        """
            创建服务器
        """
        params = json.loads(self.request.body)
        try:

            self.set_status(202, 'success')
            self.finish({'messege':'creating'})
        except:
            logger.error(traceback.format_exc())
            self.set_status(500, 'failed')
            self.finish({'messege':'failed'})

    #@auth
    def put(self, *args, **kwargs):
        """
            修改服务器
        """
        pass

    #@auth
    def delete(self, *args, **kwargs):
        """
            删除服务器
        """
        pass