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
from sqlalchemy import desc
from apscheduler.jobstores.base import JobLookupError

from common.base import RequestHandler
from config import scheduler, get_scheduler
from task import TASK
from dbcollections.task.models import Apscheduler_Task
from utils.utils import get_dbsession
from utils.auth import auth

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

    def _check_params(self, params, m_params=[], d_params=[]):

        # 1.原始参数必须是字典
        if not isinstance(params, dict):
            raise ValueError('params must be json')

        # 2.校验必输列表m_params
        for k in m_params:
            if not params.get(k):
                raise ValueError('param \'{0}\' is mandatory'.format(k))

        # 3.校验字典列表d_params
        for k in d_params:
            if not isinstance(params[k], dict):
                raise ValueError('param \'{0}\' must be json'.format(k))


    def _get_job_info(self, job):
        '''
            根据job对象，组织返回前台的job数据字典
        '''
        triggers = dict()
        for filed in job.trigger.fields:
            if not filed.is_default:
                triggers[filed.name] = str(filed)
        job_info = {
            'job_id': job.id,
            'job_trigger': triggers,
            'job_next_run_time': job.next_run_time.strftime("%Y-%m-%d %H:%M:%S")
        }
        return job_info

    #@auth
    def get(self, *args, **kwargs):
        '''
            指定job_id，查询单个job信息
            {
                job_id:''
                job_trigger:{
                    ...,
                },
                job_next_run_time:'yyyy-mm-dd HH:MM:SS'
            }
            如果不指定，则查询所有job信息
            {
                job_id1:{
                    job_trigger:{
                        ...,
                    },
                    job_next_run_time:'yyyy-mm-dd HH:MM:SS'
                },
                job_id2:{
                    job_trigger:{
                        ...,
                    },
                    job_next_run_time:'yyyy-mm-dd HH:MM:SS'
                }
                ...
            }
        '''
        try:
            job_id = kwargs.get('job_id')
            if job_id:
                logger.info("job-id>>>{0}".format(job_id))
                job = SCHEDULER.get_job(job_id)
                if not job:
                    raise HTTPError(404, "job not found")

                logger.info("job_info >> {0}".format(self._get_job_info(job)))
                self.finish({"message": 'get job success', "job": self._get_job_info(job)})
            else:
                jobs = SCHEDULER.get_jobs()
                jobs_info = dict()
                for job in jobs:
                    job_info = self._get_job_info(job)
                    job_id = job_info.pop('job_id')
                    jobs_info[job_id] = job_info

                self.finish({"message": 'get jobs success', "jobs": jobs_info})

        except HTTPError, http_error:
            logger.error(traceback.format_exc())
            self.set_status(http_error.status_code, http_error.log_message)
            self.finish({'messege': http_error.log_message})
        except:
            logger.error(traceback.format_exc())
            self.set_status(500, 'failed')
            self.finish({'messege': 'failed'})

    #@auth
    def post(self, *args, **kwargs):
        '''
            :param dict trigger_kwargs, 使用APScheduler CronTrigger，参数范围和CronTrigger一致
            :param str|unicode task_name, 任务名称，由本地来自定义
            :param dict task_kwargs，任务所需要的参数，根据定义的任务来确定
        '''
        # 必输参数
        _M_PARAMS = ['trigger_kwargs', 'task_name', 'task_kwargs']
        # 字典参数
        _D_PARAMS = ['trigger_kwargs', 'task_kwargs']

        try:
            params = json.loads(self.request.body)

            # 检查参数
            self._check_params(params, _M_PARAMS, _D_PARAMS)
            trigger_kwargs = params.get('trigger_kwargs', {})
            task_name = params.get('task_name', None)
            task_kwargs = params.get('task_kwargs', {})
            if not TASK.get(task_name):
                raise ValueError('task_name \'{0}\' not exists'.format(task_name))

            # 添加调度任务，本地生成id，为后续任务处理保证唯一
            task_kwargs['job_id'] = str(uuid.uuid1())
            logger.info(
                "add job:\n id-[{0}]\n task_name-[{1}]\n task_kwargs-[{2}]\n trigger_kwargs-[{3}] ".format(
                    task_kwargs['job_id'], task_name, task_kwargs, trigger_kwargs))

            job = SCHEDULER.add_job(TASK[task_name], 'cron', kwargs=task_kwargs, id=task_kwargs['job_id'],
                                    **trigger_kwargs)

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


    #@auth
    def put(self, *args, **kwargs):
        '''

        '''
        # 必输参数
        _M_PARAMS = ['trigger_kwargs', ]
        # 字典参数
        _D_PARAMS = ['trigger_kwargs', ]

        try:
            params = json.loads(self.request.body)
            job_id = kwargs['job_id']
            logger.info("job-id>>>{0}".format(job_id))

            # 检查参数
            self._check_params(params, _M_PARAMS, _D_PARAMS)
            trigger_kwargs = params.get('trigger_kwargs', {})

            job = SCHEDULER.reschedule_job(job_id, trigger='cron', **trigger_kwargs)

            self.finish({'message': 'update success', 'job': self._get_job_info(job)})
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

    #@auth
    def delete(self, *args, **kwargs):
        job_id = kwargs['job_id']
        logger.info("job-id>>>{0}".format(job_id))
        try:
            SCHEDULER.remove_job(job_id)
        except JobLookupError, e:
            logger.info("job %s has been removeds".format(job_id))
            self.set_status(200, 'job has been removed')
            self.finish({'messege': 'job has been removed'})
        except:
            logger.error(traceback.format_exc())
            self.set_status(500, 'failed')
            self.finish({'messege': 'failed'})
        self.finish({"message": 'remove job success'})


class JobActionHandler(RequestHandler):
    '''
        scheduler组件，job动作处理
        pause: 暂停job运行
        resume: 恢复job运行
    '''

    #@auth
    def post(self, *args, **kwargs):
        try:
            params = json.loads(self.request.body)
            action = params.get('action', 'pause')
            job_id = kwargs.get('job_id')
            if action == 'pause':
                SCHEDULER.pause_job(job_id)
            elif action == 'resume':
                SCHEDULER.resume_job(job_id)
            else:
                raise ValueError("don't support action <{0}>".format(action))
            self.set_status(200)
            self.finish({'message': '{0} success'.format(action)})
        except ValueError, error:
            logger.error(traceback.format_exc())
            self.set_status(400, error.message)
            self.finish({'messege': error.message})
        except JobLookupError, error:
            logger.error(traceback.format_exc())
            self.set_status(404, error.message)
            self.finish({'messege': error.message})
        except HTTPError, http_error:
            logger.error(traceback.format_exc())
            self.set_status(http_error.status_code, http_error.log_message)
            self.finish({'messege': http_error.log_message})
        except:
            logger.error(traceback.format_exc())
            self.set_status(500, 'failed')
            self.finish({'messege': 'failed'})


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


class JobExecHandler(RequestHandler):
    '''
        scheduler组件，Job任务执行结果查询
    '''
    #@auth
    def get(self, *args, **kwargs):
        '''
            单个job执行结果，支持参数
                limit
                offset
            给定job_id，查询结果如下
                [
                    {
                        id:'',
                        start_time:'',
                        end_time:'',
                        status:'',
                        result:'',
                    },
                    {
                        id:'',
                        start_time:'',
                        end_time:'',
                        status:'',
                        result:'',
                    },
                    ...
                ]
            如果不指定，则查询所有job信息
                # todo
                {
                    job_id1:{
                        last_exec_time:
                        detail_url:
                    },
                    job_id2:{

                    }
                    ...
                }
        '''
        try:
            job_id = kwargs.get('job_id')
            # 查询过滤
            if job_id:
                result = {}
                # 获取分页信息
                limit = int(self.get_argument('limit', 10))
                page = int(self.get_argument('page', 1))
                offset = (page - 1) * limit
                se = get_dbsession()
                tasks = se.query(Apscheduler_Task).filter(Apscheduler_Task.job_id == job_id).order_by(
                    desc(Apscheduler_Task.id))
                # 总条数
                total_count = tasks.count()
                result['total_count'] = total_count
                logger.info('job [{0}] total_count [{1}]'.format(job_id, total_count))
                tasks = tasks.limit(limit)
                if offset > 0:
                    tasks = tasks.offset(offset)

                # 查看任务配置触发器已经完全失效，通过查看apscheduler的表中是否存在
                job = se.execute("select * from apscheduler_jobs where id = '{0}'".format(job_id)).first()
                logger.info("job>>>>{0}".format(job))
                result['job'] = {'next_run_time': job[1]} if job else ()
                result['tasks'] = [task.to_dict() for task in tasks]
                self.finish({"message": 'get job success', "result": result})
            else:
                pass
        except HTTPError, http_error:
            logger.error(traceback.format_exc())
            self.set_status(http_error.status_code, http_error.log_message)
            self.finish({'messege': http_error.log_message})
        except Exception, e:
            logger.error(traceback.format_exc())
            self.set_status(500, 'failed')
            self.finish({'messege': e.message})


class JobExecReplayHandler(RequestHandler):
    '''
        scheduler组件，Job任务执行结果回放
    '''
    #@auth
    def get(self, *args, **kwargs):
        '''

        '''
        try:
            id = kwargs.get('task_id')
            se = get_dbsession()
            task = se.query(Apscheduler_Task).get(id)
            self.set_status(200)
            self.finish({'content': task.result})
        except HTTPError, http_error:
            logger.error(traceback.format_exc())
            self.set_status(http_error.status_code, http_error.log_message)
            self.finish({'messege': http_error.log_message})
        except Exception, e:
            logger.error(traceback.format_exc())
            self.set_status(500, 'failed')
            self.finish({'messege': e.message})


