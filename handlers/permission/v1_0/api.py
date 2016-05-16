# -*- coding:utf-8 -*-
import logging
import traceback
try:
    import simplejson as json
except ImportError:
    import json

from tornado.web import asynchronous, HTTPError
from tornado.gen import coroutine
from tornado.concurrent import run_on_executor
from concurrent.futures import ThreadPoolExecutor
from common.base import RequestHandler
from utils.auth import auth
from resource import get_perm_info, get_all_objects

logger = logging.getLogger()


class PermObjectsHandler(RequestHandler):
    """
       获取所有的object对象
    """
    @auth
    def get(self, *args, **kwargs):
        try:
            obj_name = kwargs.get('obj_name')
            perm_objs = get_all_objects(obj_name)
            self.set_status(200, 'success')
            self.finish({'messege': perm_objs})
        except ValueError:
            logger.error(traceback.format_exc())
            self.set_status(400, 'value error')
            self.finish({'messege':'value error'})
        except HTTPError as http_error:
            logger.error(traceback.format_exc())
            self.set_status(http_error.status_code, http_error.log_message)
            self.finish({'messege':http_error.log_message})
        except:
            logger.error(traceback.format_exc())
            self.set_status(500, 'failed')
            self.finish({'messege':'failed'})


class PermObjectSaveHandler(RequestHandler):
    """
       把object对象保存到数据库中
    """
    @auth
    def get(self, *args, **kwargs):
        try:
            obj_name = kwargs.get('obj_name')
            perm_objs = get_all_objects(obj_name)
            self.set_status(200, 'success')
            self.finish({'messege': perm_objs})
        except ValueError:
            logger.error(traceback.format_exc())
            self.set_status(400, 'value error')
            self.finish({'messege':'value error'})
        except HTTPError as http_error:
            logger.error(traceback.format_exc())
            self.set_status(http_error.status_code, http_error.log_message)
            self.finish({'messege':http_error.log_message})
        except:
            logger.error(traceback.format_exc())
            self.set_status(500, 'failed')
            self.finish({'messege':'failed'})

class PermInfoHandler(RequestHandler):
    """
        获取推送用户所需的信息，asset, user, permrole
    """
    @auth
    def get(self, *agrs, **kwargs):
        try:
            role_id = kwargs.get('role_id')
            perm_info = get_perm_info(role_id)
            self.set_status(200, 'success')
            self.finish({'messege': perm_info})
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





