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

from tornado.web import url
from handlers.scheduler.v1_0.api import *

VERSION = 'v1.0'

urls = [
    url(r'/job', JobHandler),
    url(r'/job/(?P<job_id>.*)/action/$', JobActionHandler),
    url(r'/job/(?P<job_id>.*)$', JobHandler),
    url(r'/scheduler', SchedulerHandler),
    url(r'/job_task/(?P<job_id>.*)$', JobExecHandler),
    url(r'/job_task_replay/(?P<task_id>.*)$', JobExecReplayHandler),
]
