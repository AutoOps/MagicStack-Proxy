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
from collections import namedtuple

from ansible.parsing.dataloader import DataLoader
from ansible.vars import VariableManager
from ansible.inventory import Inventory, Host, Group
from ansible.playbook.play import Play
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.executor.playbook_executor import PlaybookExecutor
from ansible.plugins.callback.minimal import CallbackModule as minimal_callback

from dbcollections.task.models import Apscheduler_Task
from utils.utils import get_dbsession
from conf.settings import LOG_DIR, SPECIAL_MODULES, ANSIBLE_PLAYBOOK_PATH, ANSIBLE_SCRIPT_PATH
from display import LogDisplay
from config import CALLBACK, CALLBACKMODULE

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
                                        status='complete', result=result)
            se.begin()
            se.merge(uap_task)
            se.flush()
            se.commit()
        except:
            logger.error(traceback.format_exc())
            se.rollback()
            if task_id:
                uap_task = Apscheduler_Task(id=task_id, end_time=datetime.datetime.now(), is_finished=True,
                                            status='failed', result=traceback.format_exc())
                se.begin()
                se.merge(uap_task)
                se.flush()
                se.commit()
        finally:
            if se:
                se.close()

    return wrapper


@task
def ansible_play(**kwargs):
    logger.info('ansible play output kwargs {0}'.format(kwargs))

    # Ansible Inventory Todo：考虑是否可拿走
    resource = kwargs['resource']
    # 被操作的主机
    host_list = kwargs['host_list']
    # 模块及模块所需参数
    module_name = kwargs['module_name']
    module_args = kwargs['module_args']
    # todo check param

    runner = AnsibleRunner(**kwargs)
    if module_name in SPECIAL_MODULES:
        logger.info("special modeules , result not json")
    result = runner.run_play(host_list, module_name, module_args)

    return result


@task
def ansible_playbook(**kwargs):
    logger.info('ansible playbook output kwargs {0}'.format(kwargs))
    # 应用于执行多ansible playbook的情况
    filenames = kwargs.get('filenames')

    # 实际要保存的内容{文件名:文件内容}
    content = kwargs.get('content', None)
    if content:
        # 查看目录是否存在，不存在，则创建
        try:
            if not os.path.exists(ANSIBLE_PLAYBOOK_PATH):
                os.mkdir(ANSIBLE_PLAYBOOK_PATH)
        except:
            logger.error(traceback.format_exc())
            # 生成文件，为了防止文件名重复，使用job_id
        filename = os.sep.join([ANSIBLE_PLAYBOOK_PATH, '{0}.yml'.format(kwargs.get('job_id'))])
        f = open(filename, 'wb')
        f.write(content)
        f.close()
        filenames = [filename]
    runner = AnsibleRunner(**kwargs)
    result = runner.run_playbook(filenames)

    return result


@task
def shell(**kwargs):
    """
        使用ansible的script模块动态执行脚本
    """
    logger.info('ansible play script{0}'.format(kwargs))

    # 生成shell文件，查看目录是否存在，不存在，则创建
    content = kwargs.get('content', None)
    try:
        if not os.path.exists(ANSIBLE_SCRIPT_PATH):
            os.mkdir(ANSIBLE_SCRIPT_PATH)
    except:
        logger.error(traceback.format_exc())

    # 生成文件，为了防止文件名重复，使用job_id
    filename = os.sep.join([ANSIBLE_SCRIPT_PATH, '{0}.yml'.format(kwargs.get('job_id'))])
    f = open(filename, 'wb')
    f.write(content)
    f.close()

    # 被操作的主机
    host_list = kwargs['host_list']
    # 模块及模块所需参数
    module_name = "script"
    module_args = filename

    runner = AnsibleRunner(**kwargs)
    if module_name in SPECIAL_MODULES:
        logger.info("special modeules , result not json")
    result = runner.run_play(host_list, module_name, module_args)

    return result


@task
def playbook(**kwargs):
    group_vars = kwargs['group_vars']
    groups = kwargs['groups']
    host_list = kwargs['host_list']
    playbook_basedir = os.sep.join([ANSIBLE_PLAYBOOK_PATH, kwargs['playbook_basedir']])
    playbooks = []
    for pb in kwargs['playbooks']:
        playbooks.append(os.sep.join([playbook_basedir, pb]))

    job_id = kwargs['job_id']
    loader = DataLoader()
    vars = VariableManager()
    # 指定inventory为一个目录，设置所有主机，包含group和host
    invertory = Inventory(loader, vars,
                          host_list=host_list)

    invertory.set_playbook_basedir(playbook_basedir)
    for group_name, hosts in groups.items():
        t_group = Group(group_name)
        for host in hosts:
            t_host = Host(host)
            t_group.add_host(t_host)
        invertory.add_group(t_group)

    vars.set_inventory(invertory)
    display = LogDisplay(logname=job_id)
    callback = CALLBACKMODULE[CALLBACK](display=display)
    Options = namedtuple('Options', ['connection', 'module_path', 'forks', 'timeout', 'remote_user',
                                     'ask_pass', 'private_key_file', 'ssh_common_args', 'ssh_extra_args',
                                     'sftp_extra_args', 'scp_extra_args', 'become', 'become_method', 'become_user',
                                     'ask_value_pass', 'verbosity', 'check', 'listhosts',
                                     'listtags', 'listtasks', 'syntax'])

    options = Options(connection='smart', module_path='/usr/share/ansible', forks=100, timeout=10,
                      remote_user='root', ask_pass=False, private_key_file=None, ssh_common_args=None,
                      ssh_extra_args=None, sftp_extra_args=None, scp_extra_args=None, become=None,
                      become_method=None, become_user='root', ask_value_pass=False, verbosity=None,
                      check=False, listhosts=None, listtags=None, listtasks=None, syntax=None)

    passwords = dict()
    pb_executor = PlaybookExecutor(playbooks, invertory, vars, loader, options, passwords)
    pb_executor._tqm._stdout_callback = callback
    pb_executor.run()
    return display.get_log_json()


class AnsibleInventory(Inventory):
    """
    this is my ansible inventory object.
    """

    def __init__(self, resource, loader, variable_manager):
        """
        resource的数据格式是一个列表字典，比如
            {
                "group1": {
                    "hosts": [{"hostname": "10.10.10.10", "port": "22", "username": "test", "password": "mypass"}, ...],
                    "vars": {"var1": value1, "var2": value2, ...}
                }
            }

        如果你只传入1个列表，这默认该列表内的所有主机属于my_group组,比如
            [{"hostname": "10.10.10.10", "port": "22", "username": "test", "password": "mypass"}, ...]
        """
        self.resource = resource
        self.inventory = Inventory(loader=loader, variable_manager=variable_manager)
        self.gen_inventory()

    def my_add_group(self, hosts, groupname, groupvars=None):
        """
        add hosts to a group
        """
        my_group = Group(name=groupname)

        # if group variables exists, add them to group
        if groupvars:
            for key, value in groupvars.iteritems():
                my_group.set_variable(key, value)

        # add hosts to group
        for host in hosts:
            # set connection variables
            hostname = host.get("hostname")
            hostip = host.get('ip', hostname)
            hostport = host.get("port")
            username = host.get("username")
            password = host.get("password")
            ssh_key = host.get("ssh_key")
            # TODO Ansible2.0 参数已经废弃
            my_host = Host(name=hostname, port=hostport)
            my_host.set_variable('ansible_ssh_host', hostip)
            my_host.set_variable('ansible_ssh_port', hostport)
            my_host.set_variable('ansible_ssh_user', username)
            my_host.set_variable('ansible_ssh_pass', password)
            my_host.set_variable('ansible_ssh_private_key_file', ssh_key)

            # set other variables
            for key, value in host.iteritems():
                if key not in ["hostname", "port", "username", "password"]:
                    my_host.set_variable(key, value)
                    # add to group
            my_group.add_host(my_host)

        self.inventory.add_group(my_group)

    def gen_inventory(self):
        """
        add hosts to inventory.
        """
        if isinstance(self.resource, list):
            self.my_add_group(self.resource, 'default_group')
        elif isinstance(self.resource, dict):
            for groupname, hosts_and_vars in self.resource.iteritems():
                self.my_add_group(hosts_and_vars.get("hosts"), groupname, hosts_and_vars.get("vars"))


class AnsibleRunner(object):
    def __init__(self, **kwargs):
        self.resource = kwargs['resource']
        self._initialize_data()
        self.job_id = kwargs['job_id']

    def _initialize_data(self):

        Options = namedtuple('Options', ['connection', 'module_path', 'forks', 'timeout', 'remote_user',
                                         'ask_pass', 'private_key_file', 'ssh_common_args', 'ssh_extra_args',
                                         'sftp_extra_args', 'scp_extra_args', 'become', 'become_method', 'become_user',
                                         'ask_value_pass', 'verbosity', 'check', 'listhosts',
                                         'listtags', 'listtasks', 'syntax'])

        self.variable_manager = VariableManager()
        self.loader = DataLoader()
        self.options = Options(connection='smart', module_path='/usr/share/ansible', forks=100, timeout=10,
                               remote_user='root', ask_pass=False, private_key_file=None, ssh_common_args=None,
                               ssh_extra_args=None, sftp_extra_args=None, scp_extra_args=None, become=None,
                               become_method=None, become_user='root', ask_value_pass=False, verbosity=None,
                               check=False, listhosts=None, listtags=None, listtasks=None, syntax=None)

        self.passwords = dict()
        self.inventory = AnsibleInventory(self.resource, self.loader, self.variable_manager).inventory
        self.variable_manager.set_inventory(self.inventory)

    def run_play(self, host_list, module_name, module_args):
        """
        run play
        :param host_list is list,
        :param module_name is string
        :param module_args is string
        """
        play = None
        # create play with tasks
        play_source = dict(
            name="Ansible Play",
            hosts=host_list,
            gather_facts='no',
            tasks=[dict(action=dict(module=module_name, args=module_args))]
        )
        play = Play().load(play_source, variable_manager=self.variable_manager, loader=self.loader)
        # actually run it
        tqm = None
        display = LogDisplay(logname=self.job_id)
        callback = CALLBACKMODULE[CALLBACK](display=display)
        if module_name == 'backup':
            # 对于备份模块，特殊处理，必须使用minimal，才能获取到文件名属性
            callback = minimal_callback(display=display)

        try:
            tqm = TaskQueueManager(
                inventory=self.inventory,
                variable_manager=self.variable_manager,
                loader=self.loader,
                options=self.options,
                passwords=self.passwords,
            )
            tqm._stdout_callback = callback
            tqm.run(play)
        finally:
            if tqm is not None:
                tqm.cleanup()

        return display.get_log_json()

    def run_playbook(self, filenames, fork=5):
        '''
             :param filenames is list ,
             :param fork is interge, default 5
        '''
        display = LogDisplay(logname=self.job_id)
        callback = CALLBACKMODULE[CALLBACK](display=display)
        # actually run it
        executor = PlaybookExecutor(
            playbooks=filenames, inventory=self.inventory, variable_manager=self.variable_manager, loader=self.loader,
            options=self.options, passwords=self.passwords,
        )
        executor._tqm._stdout_callback = callback
        executor.run()

        return display.get_log_json()


TASK = {
    'ansible': ansible_play,
    'ansible-pb': ansible_playbook,
    'shell': shell,
    'playbooks': playbook
}

if __name__ == "__main__":
    resource = [
        {'hostname': '172.16.30.136',
         'port': 22,
         'username': 'root',
         'password': '123456'}
    ]
    h_list = ['172.16.30.136']

    ar = AnsibleRunner(resource)


