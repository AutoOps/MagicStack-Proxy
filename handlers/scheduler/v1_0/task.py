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

import functools
import traceback
import logging
import os
import datetime

from dbcollections.task.models import Apscheduler_Task
from utils.utils import get_dbsession
from conf.settings import LOG_DIR

handler = logging.handlers.RotatingFileHandler(os.sep.join([LOG_DIR, 'apscheduler.log']), maxBytes=1024 * 1024,
                                               backupCount=5)
fmt = '%(asctime)s - %(filename)s:%(lineno)s - %(name)s - %(message)s'
formatter = logging.Formatter(fmt)   # 实例化formatter
handler.setFormatter(formatter)      # 为handler添加formatter
logger = logging.getLogger('apscheduler.job')
logger.addHandler(handler)


def task(func):
    '''
        执行任务前，将任务信息写入数据库
    '''

    @functools.wraps(func)
    def wrapper(**kwargs):
        se = None
        task_id = None
        try:
            # insert databse
            logger.info('task [{0}] start'.format(kwargs.get('job_id')))
            se = get_dbsession()
            se.begin()
            ap_task = Apscheduler_Task(job_id=kwargs.get('job_id'))
            se.add(ap_task)
            se.flush()
            se.commit()
            task_id = ap_task.id

            # exec task func
            result = func(**kwargs)

            # update database
            logger.info('task [{0}] end'.format(kwargs.get('job_id')))
            uap_task = Apscheduler_Task(id=task_id, end_time=datetime.datetime.now(), is_finished=True,
                                        status=1, result=result)
            se.begin()
            se.merge(uap_task)
            se.flush()
            se.commit()
        except:
            logger.error(traceback.format_exc())
            se.rollback()
            if task_id:
                uap_task = Apscheduler_Task(id=task_id, end_time=datetime.datetime.now(), is_finished=True,
                                            status=2, result=traceback.format_exc())
                se.begin()
                se.merge(uap_task)
                se.flush()
                se.commit()
        finally:
            if se:
                se.close()

    return wrapper


@task
def ansible(**kwargs):
    logger.info('ansible output kwargs {0}'.format(kwargs))


@task
def ansible_playbook(**kwargs):
    pass


TASK = {
    'ansible': ansible,
    'ansible-pb': ansible_playbook,
}

if __name__ == "__main__":
    d = {'a': 1, 'b': 2}
    ansible(**d)

