#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Name    : api.py
# @Date    : 2016-04-18 17:49
# @Author  : AutoOps
# @Link    : http://www.magicstack.cn/
# @Version :

import logging
import traceback
import os
import uuid
try:
    import simplejson as json
except ImportError:
    import json

from tornado.web import asynchronous
from tornado.gen import coroutine
from tornado.concurrent import run_on_executor
from concurrent.futures import ThreadPoolExecutor

from common.base import RequestHandler
from common.cobbler_api import System, Distros
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

                if not isinstance(systems, (list, tuple)):
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

class DistrosHandler(RequestHandler):

    executor = ThreadPoolExecutor(2)

    def _check(self, params, target):
        for k, v in target.items():
            tv = params.get(k)
            if v[0]:
                if not tv:
                    raise RuntimeError('Variable {0} is mandatory'.format(k))
            if v[1]:
                if tv:
                    if tv.lower() not in v[2]:
                        raise RuntimeError('Variable {0} value is Error, must in {1}'.format(k, v[2]))

    @asynchronous
    @coroutine
    def post(self, *args, **kwargs):
        try:
            params = json.loads(self.request.body)
            distros = Distros()
            # 1.校验值
            self._check(params, distros.get_fileds())
            # 2.校验文件是否存在
            path = params['path']
            name = params['name']
            osname = '/'.join([path, name])
            if not os.path.exists(osname):
                raise RuntimeError('File {0} is not exist'.format(osname))
            params['filename'] = name
            params['name'] = '{0}-{1}'.format(str(uuid.uuid1()),params['arch'])
            # self.upload(params=params, distros=distros)
            status, task_name = distros.upload(params)
            result = {
                'message':"",
                'distros':{
                    'name':'{0}'.format(params['name']),
                    'task_name': task_name
                }
            }
            if status == 'complete':
                self.set_status('201', 'ok')
                result['message'] = 'import success'
            else:
                self.set_status('405', 'failed')
                result['message'] = "import failed, views event log %s"%task_name
            self.finish(result)
        except:
            # todo 定制异常
            logger.error(traceback.format_exc())
            self.set_status(500, 'failed')
            self.finish({'messege':'failed'})

    def delete(self, *args, **kwargs):
        pass

    def get(self, *args, **kwargs):
        pass

    def put(self, *args, **kwargs):
        pass

    @run_on_executor
    def upload(self, *args, **kwargs):
        try:
            distros = kwargs.pop('distros')
            params = kwargs.pop('params')
            distros.upload(params)
        except:
            logger.error(traceback.format_exc())
