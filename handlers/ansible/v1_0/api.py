#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re
import traceback
import threading

try:
    import simplejson as json
except ImportError:
    import json

from tornado.websocket import WebSocketHandler, WebSocketClosedError
from tornado.web import RequestHandler, asynchronous, HTTPError
from tornado.gen import coroutine
from concurrent.futures import ThreadPoolExecutor
from ansible_play import MyRunner, MyWSRunner

from all_modules import gen_classify_modules
from ansible_play_book import exec_playbook
from utils.auth import auth

logging.basicConfig(level=logging.DEBUG,
                    format="%(filename)s [line:%(lineno)d]   %(levelname)s   %(message)s")
logger = logging.getLogger('ansible_module')

ANSIBLE_PATHS = {'core': '/usr/lib/python2.7/site-packages/ansible/modules/core',
                 'extra': '/usr/lib/python2.7/site-packages/ansible/modules/extras'}

global res_playbook
res_playbook = None


class GenModulesHandler(RequestHandler):
    """
       获取ansible的所有模块
    """

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
    """
       执行ansible命令 ad-hoc
    """
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
            self.finish({'messege': 'value error'})
        except HTTPError as http_error:
            logger.error(traceback.format_exc())
            self.set_status(http_error.status_code, http_error.log_message)
            self.finish({'messege': http_error.log_message})
        except:
            logger.error(traceback.format_exc())
            self.set_status(500, 'failed')
            self.finish({'messege': 'failed'})


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
    """
       执行ansible playbook
    """
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


class ExecHandler(WebSocketHandler):
    clients = []
    tasks = []

    def __init__(self, *args, **kwargs):
        self.id = 0
        self.user = None
        self.role = None
        self.runner = None
        self.assets = []
        self.perm = {}
        self.remote_ip = ''
        super(ExecHandler, self).__init__(*args, **kwargs)

    def check_origin(self, origin):
        return True

    def open(self):
        logger.info('Websocket: Open exec request')
        role_name = self.get_argument('role', 'sb')
        self.remote_ip = self.request.headers.get("X-Real-IP")
        if not self.remote_ip:
            self.remote_ip = self.request.remote_ip
        logger.info('Web exec cmd: request user %s' % role_name)
        # 1.根据角色获取权限 TODO
        #self.role = get_object(PermRole, name=role_name)
        # 2.根据用户获取权限     TODO
        #self.perm = get_group_user_perm(self.user)
        # 3.验证用户是否满足权限
        # roles = self.perm.get('role').keys()
        # if self.role not in roles:
        #     self.write_message('No perm that role %s' % role_name)
        #     self.close()
        # self.assets = self.perm.get('role').get(self.role).get('asset')
        # 4.获取用户可用资产
        #res = gen_resource({'user': self.user, 'asset': self.assets, 'role': self.role})
        # 5.输出可操作资产
        #TODO
        res = [{'username': u'****', 'ip': u'123.57.209.233', 'hostname': u'123.57.209.233', 'port': 22, 'password':'****'}]
        self.runner = MyWSRunner(res)
        #message = '有权限的主机: ' + ', '.join([asset.hostname for asset in self.assets])
        self.__class__.clients.append(self)
        #self.write_message(message)
        self.write_message('please enter command')

    def on_message(self, message):
        data = json.loads(message)
        pattern = data.get('pattern', '')
        self.command = data.get('command', '')
        self.asset_name_str = ''
        if pattern and self.command:
            for inv in self.runner.inventory.get_hosts(pattern=pattern):
                self.asset_name_str += '%s ' % inv.name
            self.write_message('...: ' + self.asset_name_str)
            self.write_message('<span style="color: yellow">Ansible> %s</span>\n\n' % self.command)
            self.__class__.tasks.append(MyThread(target=self.run_cmd, args=(self.command, pattern)))

        for t in self.__class__.tasks:
            if t.is_alive():
                continue
            try:
                t.setDaemon(True)
                t.start()
            except RuntimeError:
                pass

    def run_cmd(self, command, pattern):

        # 1.根据pattern获取host_list #TODO
        host_list = ['123.57.209.233'] # pattern=pattern
        res_play = self.runner.run(host_list, 'shell', command)
        print res_play
        # 1.记录日志 TODO
        # ExecLog(host=self.asset_name_str, cmd=self.command, user=self.user.username,
        #         remote_ip=self.remote_ip, result=self.runner.results).save()
        newline_pattern = re.compile(r'\n')
        for k, v in res_play.items():
            for host, output in v.items():
                output = newline_pattern.sub('<br />', output)
                if k == 'success':
                    header = "<span style='color: green'>[ %s => %s]</span>\n" % (host, 'Ok')
                else:
                    header = "<span style='color: red'>[ %s => %s]</span>\n" % (host, 'failed')
                self.write_message(header)
                self.write_message(output)

        self.write_message('\n~o~ Task finished ~o~\n')

    def on_close(self):
        logger.debug('关闭web_exec请求')


class MyThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        super(MyThread, self).__init__(*args, **kwargs)

    def run(self):
        try:
            super(MyThread, self).run()
        except WebSocketClosedError:
            pass
