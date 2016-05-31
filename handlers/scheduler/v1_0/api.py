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
from datetime import datetime

try:
    import simplejson as json
except ImportError:
    import json

from tornado.web import HTTPError

from common.base import RequestHandler
from utils.auth import auth
from scheduler_config import scheduler, get_scheduler

logger = logging.getLogger()

global SCHEDULER
SCHEDULER = scheduler


def tick(*args, **kwargs):
    print 'kwargs >> a', kwargs['a']
    print('Tick! The time is: %s' % datetime.now())


class JobHandler(RequestHandler):
    '''
        scheduler组件，Job处理API
    '''
    #@auth
    def get(self, *args, **kwargs):
        job_id = kwargs['job_id']
        job_info = {}
        logger.info("job-id>>>{0}".format(job_id))
        try:
            logger.info(">>>>")
            job = SCHEDULER.get_job(job_id)
            logger.info("get_job >> {0}".format(job.coalesce))
            logger.info("get_job >> {0}".format(job.func))
            logger.info("get_job >> {0}".format(job.id))
            logger.info("get_job >> {0}".format(job.max_instances))
            logger.info("get_job >> {0}".format(job.name))
            logger.info("get_job >> {0}".format(job.next_run_time))
            logger.info("get_job >> {0}".format(job.trigger))
        except:
            logger.error(traceback.format_exc())
        self.finish({"message": 'get job success'})

    #@auth
    def post(self, *args, **kwargs):
        func_kwargs = dict({'a': 1})
        logger.info("add_job >>>> {0}".format(SCHEDULER))
        job = SCHEDULER.add_job(tick, 'interval', kwargs=func_kwargs, seconds=3)
        logger.info("job-id>>>{0}".format(job.id))
        self.finish({'message': 'add success', 'job-id': job.id})

    #@auth
    def put(self, *args, **kwargs):
        pass

    #@auth
    def delete(self, *args, **kwargs):
        job_id = kwargs['job_id']
        logger.info("job-id>>>{0}".format(job_id))
        try:
            SCHEDULER.remove_job(job_id)
        except:
            pass
        self.finish({"message": 'remove job success'})


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

                if not SCHEDULER.running:
                    SCHEDULER.start()
                self.set_status(200)
                self.finish({'message': 'start success'})
            elif op == 'shutdown':
                if SCHEDULER.running:
                    SCHEDULER.shutdown()
                    self._set_scheduler()
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

    def _set_scheduler(self):
        global SCHEDULER
        SCHEDULER = get_scheduler()


