#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re
import traceback
import threading
import datetime
try:
    import simplejson as json
except ImportError:
    import json

from tornado.websocket import WebSocketHandler, WebSocketClosedError
from tornado.web import RequestHandler, asynchronous, HTTPError
from tornado.gen import coroutine
from tornado.concurrent import run_on_executor
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy.orm import sessionmaker
from ansible_play import MyRunner, MyWSRunner
from all_modules import gen_classify_modules
from ansible_play_book import exec_playbook
from utils.auth import auth
from utils.utils import get_dbsession
from dbcollections.task.models import Task
from dbcollections.permission.models import PermPush
from conf.settings import engine
from uuid import uuid4
from handlers.permission.v1_0.resource import get_one_object
from jinja2 import Environment, FileSystemLoader, TemplateNotFound


logging.basicConfig(level=logging.DEBUG,
                    format="%(filename)s [line:%(lineno)d]   %(levelname)s   %(message)s")
logger = logging.getLogger('ansible_module')

ANSIBLE_PATHS = {'core': '/usr/lib/python2.7/site-packages/ansible/modules/core',
                 'extra': '/usr/lib/python2.7/site-packages/ansible/modules/extras'}


def task_record(task_name, result=None, action='save'):
    # 记录,更新task
    Session = sessionmaker()
    Session.configure(bind=engine)
    session = Session()
    try:
        if action == 'save':
            ansi_task = Task()
            ansi_task.task_name = task_name
            ansi_task.start_time = datetime.datetime.now()
            ansi_task.status = 'running'
            session.add(ansi_task)
            session.commit()
        else:
            ansi_task = session.query(Task).filter_by(task_name=task_name).first()
            ansi_task.status = 'complete'
            ansi_task.result = json.dumps(result)
            session.add(ansi_task)
            session.commit()
    except Exception as e:
        logger.error(e)
    finally:
        session.close()


def permpush_record(param, result=None, action='save'):
    """
    记录,更新permpush
    """
    Session = sessionmaker()
    Session.configure(bind=engine)
    session = Session()
    try:
        if action == 'save':
            permpush = PermPush()
            permpush.role_name = param['role_name']
            permpush.date_added = datetime.datetime.now()
            permpush.assets = str(param['hosts'])
            session.add(permpush)
            session.commit()
        else:
            permpush = session.query(PermPush).filter_by(role_name=param['role_name']).first()
            permpush.result = json.dumps(result)
            permpush.success_assets = str(result['success'].keys())
            session.add(permpush)
            session.commit()
    except Exception as e:
        logger.error(e)
    finally:
        session.close()


def get_template_param(role_name, sudo_uuids):
    """
    渲染模板文件
    """
    kwds = {}
    try:
        sudo_commands = []
        for item in sudo_uuids:
            obj = get_one_object('PermSudo', item)
            commands = obj['commands'].split(',')
            for cmd in commands:
                sudo_commands.append(cmd.strip())
        logger.info('sudo_commands:%s'%sudo_commands)
        kwds['username'] = role_name
        kwds['cmdList'] = sudo_commands
    except Exception as e:
        logger.error(e)
    return kwds



class ExecPlayHandler(RequestHandler):
    """
       执行ansible命令 ad-hoc
    """
    executor = ThreadPoolExecutor(2)

    @asynchronous
    @coroutine
    @auth
    def post(self, *args, **kwargs):
        try:
            param = json.loads(self.request.body)
            run_action = param.get('run_action')         # 判断是同步执行还是异步执行 sync 同步   async 异步
            if run_action == 'sync':
                mod_name = param.get('mod_name', '')
                resource = param.get('resource', '')
                host_list = param.get('hosts', '')
                mod_args = param.get('mod_args', '')
                my_runner = MyRunner(resource)
                my_runner.run(host_list, mod_name, mod_args)
                res_play_resut = my_runner.get_result()
                self.set_status(200, 'success')
                self.finish({'messege': res_play_resut})
            elif run_action == 'async':
                role_name = param.get('role_name')
                tk_name = role_name+'_'+uuid4().hex
                task_record(tk_name)
                permpush_record(param)
                self.set_backgroud_task(param,tk_name)
                self.set_status(200, 'success')
                self.finish({'messege': 'running', 'task_name': tk_name})
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

    @run_on_executor
    def set_backgroud_task(self, param, task_name):
        try:
            mod_name = param.get('mod_name')
            resource = param.get('resource')
            host_list = param.get('hosts')
            mod_args = param.get('mod_args')
            my_runner = MyRunner(resource)
            if param.get('run_type') == 'ad-hoc':                        # 判断是执行ad-hoc还是 playbook
                    my_runner.run(host_list, mod_name, mod_args)
            else:
                # if param.get('isTemplate', ''):
                role_name = param.get('role_name', '')
                sudo_uuids = param.get('sudo_uuids', [])
                role_uuid = param.get('role_uuid', role_name)    # 用role的uuid_id来命名sudoers.d目录下的文件,如果uuid_id为空,用role_name来命名
                logger.info('推送sudo  sudo_uuids:%s'%sudo_uuids)
                # 获取模板 user.js 所需的参数
                temp_param = get_template_param(role_name, sudo_uuids)
                logger.info(u'模板user.j2所需的参数:%s'%temp_param)
                my_runner.run_playbook(host_list, role_name, role_uuid, temp_param)

            res_play = my_runner.get_result()
            task_record(task_name, res_play, action='update')
            permpush_record(param, res_play, action='update')
        except Exception as e:
            logger.error(e)

    def render_template(self, template_name, **kwargs):
        """
        渲染 模板
        """
        template_dirs = []
        if self.settings.get('template_path', ''):
            template_dirs.append(
                self.settings["template_path"]
            )

        env = Environment(loader=FileSystemLoader(template_dirs))

        try:
            template = env.get_template(template_name)
        except TemplateNotFound:
            raise TemplateNotFound(template_name)
        content = template.render(kwargs)
        return content


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
        self.host_list = []
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
        # 1.根据角色获取权限
        se = get_dbsession()
        self.role = se.query(PermRole).filter_by(name=role_name).all()
        # 2.根据用户获取权限
        self.perm = get_group_user_perm(se, self.user)
        # 3.验证用户是否满足权限
        roles = self.perm.get('role').keys()
        if self.role not in roles:
            self.write_message('No perm that role %s' % role_name)
            self.close()
        self.assets = self.perm.get('role').get(self.role).get('asset')
        # 4.获取用户可用资产
        res = gen_resource(se, {'user': self.user, 'asset': self.assets, 'role': self.role})
        for r in res:
            self.host_list.append(r['ip'])

        # 5.输出可操作资产
        self.runner = MyWSRunner(res)
        message = ', '.join([asset.hostname for asset in self.assets])
        self.__class__.clients.append(self)
        self.write_message(message)

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

        res_play = self.runner.run(self.host_list, 'shell', command)

        # 记录日志
        execlog = ExecLog(host=self.asset_name_str,
                          cmd=command,
                          user=self.user.username,
                          remote_ip=self.remote_ip,
                          result=self.runner.results)
        se = get_dbsession()
        se.add(execlog)

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
