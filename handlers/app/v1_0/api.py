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
import zipfile
from datetime import datetime

try:
    import simplejson as json
except ImportError:
    import json

from tornado.web import HTTPError

from conf.settings import UPLOAD_PATH, ANSIBLE_PLAYBOOK_PATH
from common.base import RequestHandler
from handlers.scheduler.v1_0.config import scheduler, get_scheduler
from handlers.scheduler.v1_0.task import TASK
from dbcollections.apps.models import App
from utils.utils import ZFile, get_dbsession

logger = logging.getLogger()

global SCHEDULER
SCHEDULER = scheduler


class AppActionHandler(RequestHandler):
    """
        应用部署，所有动作处理接口
    """

    def _vefiry_app(self):
        return True

    def post(self, *args, **kwargs):
        if self.get_arguments('action'):
            params = dict(action=self.get_argument('action'))
        else:
            params = json.loads(self.request.body)
        kwargs['params'] = params
        action = params.get('action', '').lower()
        action_method = "_{action}_action".format(action=action)
        if not hasattr(self, action_method):
            self.set_status(403, "action not exists")
            self.finish({'messege': "Action not exists"})
        else:
            action_method = getattr(self, action_method)
            try:
                action_method(*args, **kwargs)
                self.set_status(200)
                self.finish({'messege': 'upload success'})
            except HTTPError, http_error:
                logger.error(traceback.format_exc())
                self.set_status(http_error.status_code, http_error.log_message)
                self.finish({'messege': http_error.log_message})
            except Exception, e:
                logger.error(traceback.format_exc())
                self.set_status(500, 'failed')
                self.finish({'messege': e.message})


    def _upload_action(self, *args, **kwargs):
        """
            上传部署文件
            1. 上传文件放入到上传目录
            2. 解压文件放到相应目录
            3. 数据库中记录下信息
        """
        filepath = None
        file_metas = self.request.files['file']  # 提取表单中name为file的文件元数据
        for meta in file_metas:
            filename = meta['filename'].split(os.path.sep)[-1]
            filepath = os.path.join(UPLOAD_PATH, filename)
            with open(filepath, 'wb') as up:
                up.write(meta['body'])

        app_uuid = self.get_argument('app_uuid')
        if not zipfile.is_zipfile(filepath):
            raise HTTPError(status_code=400,
                            log_message='file type must be zip')
        uuid_path = os.sep.join([ANSIBLE_PLAYBOOK_PATH, app_uuid])
        z = ZFile(filepath)
        z.extract_to(uuid_path)
        z.close()

        # 存入数据库
        se = get_dbsession()
        se.begin()

        app = App(uuid=app_uuid,
                  desc=self.get_argument('desc'),
                  type=self.get_argument('type'),
                  basedir=os.sep.join([app_uuid, self.get_argument('basedir')]),
                  playbooks=self.get_argument('playbooks')
                  )
        se.merge(app)
        se.commit()


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

    def get(self, *args, **kwargs):
        try:
            app_uuid = kwargs.get('app_uuid')
            # 查询过滤
            if not app_uuid:
                self.set_status(400, 'app_uuid required')
                self.finish({"message": 'app_uuid required'})
                return

            se = get_dbsession()
            app = se.query(App).filter(App.uuid == app_uuid).first()
            if not app:
                self.set_status(404)
                self.finish({"message": 'app not exists'})

            self.set_status(200)
            self.finish({"message": "ok", "app": app.to_dict()})

        except HTTPError, http_error:
            logger.error(traceback.format_exc())
            self.set_status(http_error.status_code, http_error.log_message)
            self.finish({'messege': http_error.log_message})
        except Exception, e:
            logger.error(traceback.format_exc())
            self.set_status(500, 'failed')
            self.finish({'messege': e.message})

    # @auth
    def post(self, *args, **kwargs):
        '''
        '''

        try:
            task_kwargs = {}
            params = json.loads(self.request.body)
            app_uuid = task_kwargs['app_uuid'] = params.get('app_uuid')

            # 检查参数
            self._check_params(params)
            se = get_dbsession()
            app = se.query(App).get(app_uuid)
            if not app:
                self.set_status(404)
                self.finish({'messege': 'app not exist, please upload app.'})

            task_kwargs['host_list'] = params.get('host_list')
            task_kwargs['group_vars'] = params.get('group_vars')
            task_kwargs['groups'] = params.get('groups')

            # 从数据库获取playbookdir及playbooks列表
            task_kwargs['playbook_basedir'] = app.basedir
            task_kwargs['playbooks'] = app.playbooks.strip(',').split(',')
            job_id = params.get('job_id', None)

            # 添加调度任务，本地生成id，为后续任务处理保证唯一，如果指定ID，则使用指定ID
            job_id = job_id if job_id else str(uuid.uuid1())
            task_kwargs['job_id'] = job_id
            logger.info("add job:\n id-[{0}]\n ".format(job_id))

            job = SCHEDULER.add_job(TASK['playbooks'], 'date',
                                    kwargs=task_kwargs,
                                    id=task_kwargs['job_id'], )

            self.finish(
                {'message': 'add success', 'job': self._get_job_info(job)})
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
