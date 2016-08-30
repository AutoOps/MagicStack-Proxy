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
from handlers.scheduler.v1_0.config import scheduler, get_scheduler
from handlers.scheduler.v1_0.task import TASK

logger = logging.getLogger()

global SCHEDULER
SCHEDULER = scheduler


class AppHandler(RequestHandler):
    def _check_params(self, params, *args, **kwargs):
        '''
            校验参数
        '''
        return True

    def _get_job_info(self, job):
        '''
            根据job对象，组织返回前台的job数据字典
        '''
        job_info = {
            'job_id': job.id,
            'job_trigger': str(job.trigger),
            'job_next_run_time': job.next_run_time.strftime("%Y-%m-%d %H:%M:%S")
        }
        return job_info


    #@auth
    def post(self, *args, **kwargs):
        '''
            :param dict trigger_kwargs, 使用APScheduler CronTrigger，参数范围和CronTrigger一致
            :param str|unicode task_name, 任务名称，由本地来自定义
            :param dict task_kwargs，任务所需要的参数，根据定义的任务来确定
        '''

        try:
            params = json.loads(self.request.body)

            # 检查参数
            self._check_params(params)
            task_kwargs = {}
            task_kwargs['host_list'] = params.get('host_list')
            task_kwargs['playbook_basedir'] = params.get('playbook_basedir')
            task_kwargs['playbooks'] = params.get('playbooks')
            job_id = params.get('job_id', None)

            # 添加调度任务，本地生成id，为后续任务处理保证唯一，如果指定ID，则使用指定ID
            job_id = job_id if job_id else str(uuid.uuid1())
            task_kwargs['job_id'] = job_id
            logger.info("add job:\n id-[{0}]\n ".format(job_id))

            job = SCHEDULER.add_job(TASK['playbooks'], 'date', kwargs=task_kwargs, id=task_kwargs['job_id'], )

            self.finish({'message': 'add success', 'job': self._get_job_info(job)})
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

