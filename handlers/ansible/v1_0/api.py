#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
try:
    import simplejson as json
except ImportError:
    import json

from tornado.web import RequestHandler, asynchronous, HTTPError
from tornado.gen import coroutine
from tornado.concurrent import run_on_executor
from concurrent.futures import ThreadPoolExecutor
from ansible_play import MyRunner
from all_modules import gen_classify_modules
from ansible_play_book import exec_playbook
from utils.auth import auth
import traceback

logging.basicConfig(level=logging.DEBUG,
                    format="%(filename)s [line:%(lineno)d]   %(levelname)s   %(message)s")
logger = logging.getLogger('ansible_module')

ANSIBLE_PATHS = {'core': '/usr/lib/python2.7/site-packages/ansible/modules/core', 'extra': '/usr/lib/python2.7/site-packages/ansible/modules/extras'}


global res_playbook
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

    @auth
    def post(self, *args, **kwargs):
        try:
            param = json.loads(self.request.body)
            mod_name = param.get('mod_name')
            resource = param.get('resource')
            host_list = param.get('hosts')
            mod_args = param.get('mod_args')
            my_runner = MyRunner(resource)
            res_play = my_runner.run(host_list, mod_name, mod_args)
            self.set_status(200, 'success')
            self.finish({'messege': res_play})
        except ValueError:
            logger.error(traceback.format_exc())
            self.set_status(400, 'value error')
            self.finish({'messege':'value error'})
        except HTTPError as http_error:
            logger.error(traceback.format_exc())
            self.set_status(http_error.status_code, http_error.log_message)
            self.finish({'messege':http_error.log_message})
        except:
            logger.error(traceback.format_exc())
            self.set_status(500, 'failed')
            self.finish({'messege':'failed'})


class ExecPlayResultHandler(RequestHandler):
    executor = ThreadPoolExecutor(2)

    @asynchronous
    @coroutine
    def get(self, *args, **kwargs):
        self.write({
            'result': 'res_play',
        })
        self.finish()


class ExecPlayBookHandler(RequestHandler):
    executor = ThreadPoolExecutor(2)

    @asynchronous
    @coroutine
    def post(self, *args, **kwargs):
        param = json.loads(self.request.body)
        file_name = param['name']
        global res_playbook
        res_playbook = exec_playbook(file_name)
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
