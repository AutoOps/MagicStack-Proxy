#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Name    : cobbler_api
# @Date    : 2016-04-18 16:10
# @Author  : AutoOps
# @Link    : http://www.magicstack.cn/
# @Version :

import xmlrpclib
import traceback
import logging
import functools
import uuid
import os
import subprocess
import re
import time

import conf.settings as settings

logger = logging.getLogger()

class Cobbler(object):

    def __init__(self, username=settings.COBBLER_USERNAME, password=settings.COBBLER_PASSWORD):
        self.username = username
        self.password = password
        self.api_url  = settings.COBBLER_RPC_URL

    def get_remote(self):
        remote = xmlrpclib.Server(self.api_url)
        return remote

    def get_token(self):
        remote = self.get_remote()
        try:
            token = remote.login( self.username, self.password )
        except:
            logging.error(traceback.format_exc())
            raise RuntimeError( 'get cobbler token error' )
        return token

    def get_fileds(self):
        """
            获取需要参数值
        """
        pass

    def execute_cmd(self, params):
        """
            1通用执行命令函数
            @params: list or tuple
            return (bool, stdout, error_msg)
        """
        if not isinstance(params, (list, tuple)):
            raise RuntimeError( 'params must be list or tuple' )
        pop = subprocess.Popen(params, stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)

        code = pop.wait()
        if code == 0:
            return ( True, pop.stdout.read(), '')
        else:
            return ( False, pop.stdout.read(), pop.stderr.read())



class System(Cobbler):

    def get_fileds(self):

        return {
            'name':None,
            'uid':None,

        }

    def power(self, params):
        remote = self.get_remote()
        token = self.get_token()
        logger.debug('systems[{0}] power{1}'.format(params.get('systems'), params.get('power')))
        result = remote.background_power_system(params,token)

    def create(self, params):
        remote = self.get_remote()
        token = self.get_token()
        logger.debug('create system params:{0}'.format(params))
        name = params.get('name')


    def modify(self, params):
        remote = self.get_remote()
        token = self.get_token()
        logger.debug('modify system params:{0}'.format(params))

    def delete(self, params):
        remote = self.get_remote()
        token = self.get_token()

class Distros(Cobbler):

    def _check_iso(self, path):

        if not os.path.exists(path):
            raise RuntimeError('{0} does not exist'.format(path))

    def get_fileds(self):

        return {
            'path':[True, False, [], '', u'镜像地址'], # [bool(是否必须),bool(是否对值有限制),限制函数或列表,default,字段含义]
            'name':[True, False, [], '', u'distros名字'],
            'arch':[False, True, ['i386',
                                  'x86_64',
                                  'ia64',
                                  'ppc',
                                  'ppc64',
                                  's390',
                                  's390x',
                                  'arm'], 'i386', u'镜像类型'],
            'breed':[False, True, ['redhat',
                                   'debian',
                                   'ubuntu',
                                   'suse'], 'redhat', u'镜像系统']
        }

    def upload(self, params):
        """
            1. mount  dvd
            2. import dvd
            3. umount dvd
        """
        path = params.get('path')
        osname = params.get('filename')
        name = params.get('name')
        dvd = '/'.join([path, osname])
        logger.info( "check iso {0}".format(dvd) )
        self._check_iso(dvd)
        mnt_sub = "/mnt/{0}".format(name)
        mnt_sub_cmd = ['mkdir', mnt_sub]
        mount_cmd = ['mount', '-o', 'loop', dvd, mnt_sub]
        umount_cmd = ["umount", mnt_sub]
        del_mnt_sub_cmd = ['rm', '-rf', mnt_sub]
        logger.info('create temp dir %s' % str(mnt_sub))
        ret, out_info, error_msg = self.execute_cmd(mnt_sub_cmd)
        if not ret:
            logger.error('execute {0} error{1}'.format(mnt_sub_cmd, error_msg))
            raise RuntimeError('execute {0} error{1}'.format(mnt_sub_cmd, error_msg))
        logger.info("mount iso {0}".format(dvd))
        ret, out_info, error_msg = self.execute_cmd(mount_cmd)
        if not ret:
            logger.error('execute {0} error{1}'.format(mount_cmd, error_msg))
            raise RuntimeError('execute {0} error{1}'.format(mount_cmd, error_msg))
        remote = self.get_remote()
        token = self.get_token()
        logger.info("async import iso")
        task_name = remote.background_import(params, token)
        logger.info("check task {0} result".format(task_name))
        status = remote.get_task_status(task_name)
        while status[2] not in ('complete', 'failed'):
            status = remote.get_task_status(task_name)
        logger.info("task execute complete - result[{0}]".format(status[2]))

        # re_task = re.compile('.*?### TASK (COMPLETE|FAILED) ###', re.S)
        # log_last = remote.get_event_log(task_name).strip('\n').split('\n')[-1]
        # while not re_task.match(log_last):
        #     time.sleep(5)
        #     log_last = remote.get_event_log(task_name).strip('\n').split('\n')[-1]

        logger.info("umount iso {0}".format(mnt_sub))
        ret, out_info, error_msg = self.execute_cmd(umount_cmd)
        if not ret:
            logger.error('execute {0} error{1}'.format(umount_cmd, error_msg))
        logger.info("delete temp dir{0}".format(mnt_sub))
        ret, out_info, error_msg = self.execute_cmd(del_mnt_sub_cmd)
        if not ret:
            logger.error('execute {0} error{1}'.format(del_mnt_sub_cmd, error_msg))
        return status[2], task_name

def cobbler_token(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        cobbler = Cobbler()
        token = cobbler.get_token()
        while token is None:
            token = cobbler.get_token()
        return func(token=token, *args, **kwargs)
    return wrapper


if __name__ == "__main__":
    cobbler = Cobbler()
    remote = cobbler.get_remote()
    data = remote.get_event_log('2016-04-18_170033_import')
    s = data.strip('\n').split('\n')[-1]


    #
    # re_task = re.compile('.*?### TASK (COMPLETE|FAILED) ###', re.S)
    # s = [ "### TASK COMPLETE ###", "### TASK FAILED ###"]
    # for row in s:
    #     print re_task.match(row)
    status = remote.get_task_status('2016-04-18_170033_import')
    print status
