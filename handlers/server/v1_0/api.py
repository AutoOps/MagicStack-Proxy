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
from common.cobbler_api import System, Distros, Event, Profile
from utils.utils import get_dbsession
from utils.auth import auth
from conf.settings import UPLOAD_PATH
from dbcollections.nodes.models import Node

logger = logging.getLogger()


class SystemActionHandler(RequestHandler):
    """
        服务器操作，批量开机/关机/重启
    """

    @auth
    def post(self, *args, **kwargs):
        try:
            params = json.loads(self.request.body)
            power = params.get('power')
            rebuild = params.get('rebuild', None)
            systems = params.get('systems', None)
            system = System()
            if not isinstance(systems, (list, tuple)):
                self.write_error(403)
                return

            if power:
                if power.lower() not in ( 'on', 'off', 'reboot', 'status' ):
                    self.write_error(403)
                    return
                params = {
                    'power': power.lower(),
                    'systems': systems,
                }
                task_name = system.power(params)
                self.set_status(200, 'success')
                self.finish({'messege': 'running', 'task_name': task_name})
            elif rebuild:
                profile = params.get('profile')
                rebuild_params = {
                    'systems': systems,
                    'netboot_enabled': True,
                }
                if profile: # Todo check exists
                    rebuild_params['profile'] = profile
                task_name = system.rebuild(rebuild_params)
                self.set_status(200, 'success')
                self.finish({'messege': 'running', 'task_name': task_name})

        except ValueError:
            logger.error(traceback.format_exc())
            self.set_status(400, 'value error')
            self.finish({'messege': 'value error'})
        except HTTPError, http_error:
            logger.error(traceback.format_exc())
            self.set_status(http_error.status_code, http_error.log_message)
            self.finish({'messege': http_error.log_message})
        except:
            logger.error(traceback.format_exc())
            self.set_status(500, 'failed')
            self.finish({'messege': 'failed'})


class SystemHandler(RequestHandler):
    """
        服务器
    """

    @auth
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
            self.finish({'messege': http_error.log_message})
        except:
            # todo 定制异常
            logger.error(traceback.format_exc())
            self.set_status(500, 'failed')
            self.finish({'messege': 'failed'})


    @auth
    def post(self, *args, **kwargs):
        """
            创建服务器
        """
        se = None
        try:
            params = json.loads(self.request.body)
            # 本地数据记录，用户ssh登录
            se = get_dbsession()
            se.begin()
            id_unique = params.pop("id_unique")
            interfaces = params.get("interfaces", {})
            # 暂时不考虑多网卡，故只取一个IP
            ip = None
            for k, inter_params in interfaces.items():
                ip = inter_params.get('ip_address')
            if not id_unique or not ip:
                raise ValueError("id_unique and ip is mandatory ")
            node = Node(id=id_unique, ip=ip)
            se.add(node)
            # 创建节点
            system = System()
            system.create(params)
            se.commit()
            self.set_status(200, 'success')
            self.finish({'messege': 'created'})
        except ValueError:
            se.rollback()
            logger.error(traceback.format_exc())
            self.set_status(400, 'value error')
            self.finish({'messege': 'value error'})
        except HTTPError, http_error:
            se.rollback()
            logger.error(traceback.format_exc())
            self.set_status(http_error.status_code, http_error.log_message)
            self.finish({'messege': http_error.log_message})
        except:
            se.rollback()
            logger.error(traceback.format_exc())
            self.set_status(500, 'failed')
            self.finish({'messege': 'failed'})
        finally:
            if se:
                se.flush()
                se.close()

    @auth
    def put(self, *args, **kwargs):
        """
            修改服务器
        """
        try:
            system_id = kwargs.get('system_id')
            params = json.loads(self.request.body)
            interfaces = params.get("interfaces", {})
            system = System()
            system.modify(system_id, params)
            id_unique = params.pop("id_unique")
            ip = None
            # 暂时不考虑多网卡，故只取一个IP
            for k, inter_params in interfaces.items():
                ip = inter_params.get('ip_address')

            # 修改数据库中参数
            update_db = True
            if ip:
                se = None
                try:
                    se = get_dbsession()
                    se.begin()
                    node = Node(id=id_unique, ip=ip)
                    se.merge(node)
                    se.commit()
                except:
                    update_db = False
                    se.rollback()
                finally:
                    se.flush()
                    se.close()

            self.set_status(200, 'success')
            self.finish({'messege': 'success', 'update_db': update_db})
        except ValueError:
            logger.error(traceback.format_exc())
            self.set_status(400, 'value error')
            self.finish({'messege': 'value error'})
        except HTTPError, http_error:
            logger.error(traceback.format_exc())
            self.set_status(http_error.status_code, http_error.log_message)
            self.finish({'messege': http_error.log_message})
        except:
            logger.error(traceback.format_exc())
            self.set_status(500, 'failed')
            self.finish({'messege': 'failed'})

    #@auth
    def delete(self, *args, **kwargs):
        """
            删除服务器
        """
        se = None
        try:
            params = json.loads(self.request.body)
            system = System()
            system_names = params.get('names', None)
            id_unique = params.pop("id_unique")
            error_info = system.delete(system_names)
            self.set_status(200)
            if error_info:
                self.finish({'messege': error_info})
            else:
                delete_db = True
                try:
                    se = get_dbsession()
                    se.begin()
                    node = Node(id=id_unique)
                    se.delete(node)
                    se.commit()
                except:
                    se.rollback()
                    delete_db = False
                finally:
                    se.flush()
                    se.close()
                self.finish({'messege': 'success', 'delete_db': delete_db})

        except ValueError:
            logger.error(traceback.format_exc())
            self.set_status(400, 'value error')
            self.finish({'messege': 'value error'})
        except HTTPError, http_error:
            logger.error(traceback.format_exc())
            self.set_status(http_error.status_code, http_error.log_message)
            self.finish({'messege': http_error.log_message})
        except:
            logger.error(traceback.format_exc())
            self.set_status(500, 'failed')
            self.finish({'messege': 'failed'})


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
    @auth
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
            params['name'] = '{0}-{1}'.format(str(uuid.uuid1()), params['arch'])
            task_name, mnt_sub = distros.upload(params)
            result = {
                'message': "importing...",
                'distros': {
                    'name': '{0}'.format(params['name']),
                    'task_name': task_name
                }
            }
            self.after_upload(task_name=task_name, mnt_sub=mnt_sub, distros=distros)
            self.set_status(201, 'ok')
            self.finish(result)
        except ValueError:
            logger.error(traceback.format_exc())
            self.set_status(400, 'value error')
            self.finish({'messege': 'value error'})
        except HTTPError, http_error:
            logger.error(traceback.format_exc())
            self.set_status(http_error.status_code, http_error.log_message)
            self.finish({'messege': http_error.log_message})
        except:
            # todo 定制异常
            logger.error(traceback.format_exc())
            self.set_status(500, 'failed')
            self.finish({'messege': 'failed'})

    @auth
    def delete(self, *args, **kwargs):
        pass

    @auth
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
            self.finish({'messege': http_error.log_message})
        except:
            logger.error(traceback.format_exc())
            self.set_status(500, 'failed')
            self.finish({'messege': 'failed'})

    @auth
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
    @auth
    def get(self, event_id, *args, **kwargs):
        try:
            event = Event()
            info = event.get_event(event_id)
            self.set_status(200, 'ok')
            self.finish(info)
        except HTTPError, http_error:
            logger.error(traceback.format_exc())
            self.set_status(http_error.status_code, http_error.log_message)
            self.finish({'messege': http_error.log_message})
        except:
            # todo 定制异常
            logger.error(traceback.format_exc())
            self.set_status(500, 'failed')
            self.finish({'messege': 'failed'})


class ProfileHandler(RequestHandler):
    @auth
    def get(self, *args, **kwargs):
        try:
            profile = Profile()
            item_names = profile.get_item_names()
            if len(item_names) == 0:
                self.set_status(404)
                self.finish()
            else:
                self.set_status(200, 'ok')
                self.finish({'profiles': item_names})

        except HTTPError, http_error:
            logger.error(traceback.format_exc())
            self.set_status(http_error.status_code, http_error.log_message)
            self.finish({'messege': http_error.log_message})
        except:
            # todo 定制异常
            logger.error(traceback.format_exc())
            self.set_status(500, 'failed')
            self.finish({'messege': 'failed'})


class FileHandler(RequestHandler):
    @auth
    def post(self, *args, **kwargs):
        try:
            file_metas = self.request.files['file'] # 提取表单中name为file的文件元数据
            for meta in file_metas:
                filename = meta['filename'].split(os.path.sep)[-1]
                filepath = os.path.join(UPLOAD_PATH, filename)
                print filepath
                with open(filepath, 'wb') as up:      # 有些文件需要已二进制的形式存储，实际中可以更改
                    up.write(meta['body'])
                self.set_status(200, 'ok')
                self.finish()
        except ValueError:
            logger.error(traceback.format_exc())
            self.set_status(400, 'value error')
            self.finish({'messege': 'value error'})
        except HTTPError, http_error:
            logger.error(traceback.format_exc())
            self.set_status(http_error.status_code, http_error.log_message)
            self.finish({'messege': http_error.log_message})
        except:
            # todo 定制异常
            logger.error(traceback.format_exc())
            self.set_status(500, 'failed')
            self.finish({'messege': 'failed'})



