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

global res_play
global res_playbook
res_play = None
res_playbook = None


class GenModulesHandler(RequestHandler):
    executor = ThreadPoolExecutor(2)

    @asynchronous
    @coroutine
    def get(self, *args, **kwargs):
        ansi_all_modules = gen_classify_modules(ANSIBLE_PATHS)
        self.write({
            'ansi_core_modules': ansi_all_modules['core'],
            'ansi_extra_modules': ansi_all_modules['extra']
        })
        self.finish()


class ExecPlayHandler(RequestHandler):
    executor = ThreadPoolExecutor(2)

    @asynchronous
    @coroutine
    def post(self, *args, **kwargs):
        param = json.loads(self.request.body)
        mod_name = param['name']
        global res_play
        res_play = exec_play(mod_name, {})
        self.write({
            'state': '正在执行命令.....',
        })
        self.finish()


class ExecPlayResultHandler(RequestHandler):
    executor = ThreadPoolExecutor(2)

    @asynchronous
    @coroutine
    def get(self, *args, **kwargs):
        self.write({
            'result': res_play,
        })
        self.finish()


class ExecPlayBookHandler(RequestHandler):
    executor = ThreadPoolExecutor(2)

    @asynchronous
    @coroutine
    def post(self, *args, **kwargs):
        param = json.loads(self.request.body)
        file_name = param['name']
        result = exec_playbook(file_name)
        self.write({
            'state': '正在执行中......',
        })
        self.finish()


class ExecPBResultHandler(RequestHandler):
    executor = ThreadPoolExecutor(2)

    @asynchronous
    @coroutine
    def get(self, *args, **kwargs):
        self.write({
            'result': res_playbook,
        })

        self.finish()