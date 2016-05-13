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
from resource import get_perm_info

logger = logging.getLogger()


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





