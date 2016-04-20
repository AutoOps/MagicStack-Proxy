#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
try:
    import simplejson as json
except ImportError:
    import json

from tornado.web import RequestHandler
from tornado.web import asynchronous
from tornado.gen import coroutine
from tornado.concurrent import run_on_executor
from concurrent.futures import ThreadPoolExecutor
from ansible_play import exec_play
from all_modules import gen_classify_modules
from ansible_play_book import exec_playbook

logging.basicConfig(level=logging.DEBUG,
                    format="%(filename)s [line:%(lineno)d]   %(levelname)s   %(message)s")
logger = logging.getLogger('ansible_module')

ANSIBLE_PATHS = {'core': '/usr/lib/python2.7/site-packages/ansible/modules/core', 'extra': '/usr/lib/python2.7/site-packages/ansible/modules/extras'}

class GenModulesHandler(RequestHandler):
    executor = ThreadPoolExecutor(2)

    def get(self, *args, **kwargs):
        ansi_all_modules = gen_classify_modules(ANSIBLE_PATHS)
        self.write({
            'ansi_core_modules': ansi_all_modules['core'],
            'ansi_extra_modules': ansi_all_modules['extra']
        })
        self.finish()

class ExecPlayHandler(RequestHandler):
    def post(self, *args, **kwargs):
        param = json.loads(self.request.body)
        mod_name = param['name']
        result = exec_play(mod_name, {})
        self.write({
            'result': result,
        })
        self.finish()


class ExecPlayBookHandler(RequestHandler):
    def post(self, *args, **kwargs):
        param = json.loads(self.request.body)
        file_name = param['name']
        result = exec_playbook(file_name)
        self.write({
            'result': result,
        })
        self.finish()
