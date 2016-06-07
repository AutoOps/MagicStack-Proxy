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

# Define APScheduler Job Stores / Triggers / Executors / Scheduler
from apscheduler.schedulers.tornado import TornadoScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ProcessPoolExecutor, ThreadPoolExecutor

# ansible callback plugin
from ansible.plugins.callback.default import CallbackModule as defaul_callback
from ansible.plugins.callback.minimal import CallbackModule as minimal_callback

from conf.settings import BASE_DIR

CALLBACKMODULE = {
    'default': defaul_callback,
    'minimal': minimal_callback,
}

CALLBACK = 'default'


def get_scheduler():
    # define job stores
    jobstores = {
        'default': SQLAlchemyJobStore(url='sqlite:///{0}/magicstack.db'.format(BASE_DIR))
    }

    # define executors
    executors = {
        'default': ThreadPoolExecutor(5)
    }

    # define job
    job_defaults = {
        'coalesce': False,
        'max_instances': 3
    }
    return TornadoScheduler(jobstores=jobstores, executors=executors,
                            job_defaults=job_defaults)


scheduler = get_scheduler()

