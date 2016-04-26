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

from tornado.web import asynchronous, HTTPError
from tornado.gen import coroutine
from tornado.concurrent import run_on_executor
from concurrent.futures import ThreadPoolExecutor

from common.base import RequestHandler
from common.cobbler_api import System, Distros, Event
from utils.auth import auth

logger = logging.getLogger()

class SystemActionHandler(RequestHandler):
    """
        服务器操作，批量开机/关机/重启
    """

    #@auth
    def post(self, *args, **kwargs):
        try:
            params = json.loads(self.request.body)
            power = params.get('power')
            systems = params.get('systems', None)
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
                task_name = system.power(params)
                self.set_status(200, 'success')
                self.finish({'messege':'running', 'task_name':task_name})
        except ValueError:
            logger.error(traceback.format_exc())
            self.set_status(400, 'value error')
            self.finish({'messege':'value error'})
        except HTTPError, http_error:
            logger.error(traceback.format_exc())
            self.set_status(http_error.status_code, http_error.log_message)
            self.finish({'messege':http_error.log_message})
        except:
            logger.error(traceback.format_exc())
            self.set_status(500, 'failed')
            self.finish({'messege':'failed'})

class SystemHandler(RequestHandler):
    """
        服务器
    """

    #@auth
    def get(self, *args, **kwargs):
        system_id = kwargs.get('system_id')
        try:
            system = System()
            if system_id:
                info = system.get_item(system_id)
            else:
                # todo 尝试分页等操作
                info = {}
            self.set_status(200, 'ok')
            self.finish(info)
        except HTTPError, http_error:
            logger.error(traceback.format_exc())
            self.set_status(http_error.status_code, http_error.log_message)
            self.finish({'messege':http_error.log_message})
        except:
            # todo 定制异常
            logger.error(traceback.format_exc())
            self.set_status(500, 'failed')
            self.finish({'messege':'failed'})


    #@auth
    def post(self, *args, **kwargs):
        """
            创建服务器
        """
        try:
            params = json.loads(self.request.body)
            system = System()
            system.create(params)
            self.set_status(200, 'success')
            self.finish({'messege':'created'})
        except ValueError:
            logger.error(traceback.format_exc())
            self.set_status(400, 'value error')
            self.finish({'messege':'value error'})
        except HTTPError, http_error:
            logger.error(traceback.format_exc())
            self.set_status(http_error.status_code, http_error.log_message)
            self.finish({'messege':http_error.log_message})
        except:
            logger.error(traceback.format_exc())
            self.set_status(500, 'failed')
            self.finish({'messege':'failed'})

    #@auth
    def put(self, *args, **kwargs):
        """
            修改服务器
        """
        try:
            system_id = kwargs.get('system_id')
            params = json.loads(self.request.body)
            system = System()
            system.modify(system_id, params)
            self.set_status(200, 'success')
            self.finish({'messege':'success'})
        except ValueError:
            logger.error(traceback.format_exc())
            self.set_status(400, 'value error')
            self.finish({'messege':'value error'})
        except HTTPError, http_error:
            logger.error(traceback.format_exc())
            self.set_status(http_error.status_code, http_error.log_message)
            self.finish({'messege':http_error.log_message})
        except:
            logger.error(traceback.format_exc())
            self.set_status(500, 'failed')
            self.finish({'messege':'failed'})

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
                    raise HTTPError(400, 'Variable {0} is mandatory'.format(k))
            if v[1]:
                if tv:
                    if tv.lower() not in v[2]:
                        raise HTTPError(400, 'Variable {0} value is Error, must in {1}'.format(k, v[2]))

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
                raise HTTPError(404, 'File {0} is not exist'.format(osname))
            params['filename'] = name
            params['name'] = '{0}-{1}'.format(str(uuid.uuid1()),params['arch'])
            task_name, mnt_sub= distros.upload(params)
            result = {
                'message':"importing...",
                'distros':{
                    'name':'{0}'.format(params['name']),
                    'task_name': task_name
                }
            }
            self.after_upload(task_name=task_name, mnt_sub=mnt_sub, distros=distros)
            self.set_status(201, 'ok')
            self.finish(result)
        except ValueError:
            logger.error(traceback.format_exc())
            self.set_status(400, 'value error')
            self.finish({'messege':'value error'})
        except HTTPError, http_error:
            logger.error(traceback.format_exc())
            self.set_status(http_error.status_code, http_error.log_message)
            self.finish({'messege':http_error.log_message})
        except:
            # todo 定制异常
            logger.error(traceback.format_exc())
            self.set_status(500, 'failed')
            self.finish({'messege':'failed'})

    def delete(self, *args, **kwargs):
        pass

    def get(self, *args, **kwargs):
        distro_id = kwargs.get('distro_id')
        try:
            distro = Distros()
            if distro_id:
                info = distro.get_item(distro_id)
            else:
                # todo 尝试分页及不分页
                info = {}
                pass
            self.set_status(200, 'ok')
            self.finish(info)
        except HTTPError, http_error:
            logger.error(traceback.format_exc())
            self.set_status(http_error.status_code, http_error.log_message)
            self.finish({'messege':http_error.log_message})
        except:
            # todo 定制异常
            logger.error(traceback.format_exc())
            self.set_status(500, 'failed')
            self.finish({'messege':'failed'})

    def put(self, *args, **kwargs):
        pass

    @run_on_executor
    def after_upload(self, *args, **kwargs):
        try:
            distros = kwargs.pop('distros')
            task_name = kwargs.pop('task_name')
            mnt_sub = kwargs.pop('mnt_sub')
            distros.after_upload(task_name, mnt_sub)
        except:
            logger.error(traceback.format_exc())

class EventSingalHandler(RequestHandler):

    def get(self, event_id, *args, **kwargs):
        try:
           event = Event()
           info = event.get_event(event_id)
           self.set_status(200, 'ok')
           self.finish(info)
        except HTTPError, http_error:
            logger.error(traceback.format_exc())
            self.set_status(http_error.status_code, http_error.log_message)
            self.finish({'messege':http_error.log_message})
        except:
            # todo 定制异常
            logger.error(traceback.format_exc())
            self.set_status(500, 'failed')
            self.finish({'messege':'failed'})


# class EventHandler(RequestHandler):
#
#     def get(self, *args, **kwargs):
#         try:
#            params = json.loads(self.request.body)
#
#         except ValueError:
#             logger.error(traceback.format_exc())
#             self.set_status(400, 'value error')
#             self.finish({'messege':'value error'})
#         except HTTPError, http_error:
#             logger.error(traceback.format_exc())
#             self.set_status(http_error.status_code, http_error.log_message)
#             self.finish({'messege':http_error.log_message})
#         except:
#             # todo 定制异常
#             logger.error(traceback.format_exc())
#             self.set_status(500, 'failed')
#             self.finish({'messege':'failed'})



