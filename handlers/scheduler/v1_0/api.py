#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2016 MagicStack 
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import logging
import traceback
import os
import uuid

try:
    import simplejson as json
except ImportError:
    import json

from tornado.web import HTTPError

from common.base import RequestHandler
from utils.auth import auth
from scheduler_config import scheduler

logger = logging.getLogger()


class JobHandler(RequestHandler):
    '''
        scheduler组件，Job处理API
    '''
    #@auth
    def get(self, *args, **kwargs):
        pass

    #@auth
    def post(self, *args, **kwargs):
        pass

    #@auth
    def put(self, *args, **kwargs):
        pass

    #@auth
    def delete(self, *args, **kwargs):
        pass


class SchedulerHandler(RequestHandler):
    '''
        scheduler组件，scheduler处理
    '''

    #@auth
    def post(self, *args, **kwargs):
        try:
            params = json.loads(self.request.body)
            op = params.get('op', 'start')
            if op == 'start':
                if not scheduler.running:
                    scheduler.start()
                self.set_status(200)
                self.finish({'message': 'start success'})
            elif op == 'shutdown':
                if scheduler.running:
                    scheduler.shutdown()
                self.set_status(200)
                self.finish({'message': 'shutdown success'})
            else:
                raise ValueError("don't support command <{0}>".format(op))
        except ValueError, error:
            logger.error(traceback.format_exc())
            self.set_status(400, error.message)
            self.finish({'messege': error.message})
        except HTTPError, http_error:
            logger.error(traceback.format_exc())
            self.set_status(http_error.status_code, http_error.log_message)
            self.finish({'messege': http_error.log_message})
        except:
            logger.error(traceback.format_exc())
            self.set_status(500, 'failed')
            self.finish({'messege': 'failed'})

