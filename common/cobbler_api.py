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

from tornado.web import HTTPError

import conf.settings as settings

logger = logging.getLogger()


class Cobbler(object):

    TYPE = None

    def __init__(self, username=settings.COBBLER_USERNAME, password=settings.COBBLER_PASSWORD):
        self.username = username
        self.password = password
        self.api_url = settings.COBBLER_RPC_URL

    def get_remote(self):
        remote = xmlrpclib.Server(self.api_url)
        return remote

    def get_token(self):
        remote = self.get_remote()
        try:
            token = remote.login(self.username, self.password)
        except:
            logging.error(traceback.format_exc())
            raise RuntimeError('get cobbler token error')
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
            raise HTTPError(400, 'params must be list or tuple')
        pop = subprocess.Popen(params, stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)

        code = pop.wait()
        if code == 0:
            return ( True, pop.stdout.read(), '')
        else:
            return ( False, pop.stdout.read(), pop.stderr.read())

class System(Cobbler):

    TYPE = 'system'

    def get_fileds(self):

        interface = {
            'mac_address': [True, False, [], '', u'mac地址'],
            'connected_mode': [False, False, [], '', ''],
            'mtu': [False, False, [], '', ''],
            'ip_address': [True, False, [], '', u'ip地址'],
            'interface_type': [False, False, [], '', u'接口类型'],
            'interface_master': [False, False, [], '', ''],
            'bonding_opts': [False, False, [], '', ''],
            'bridge_opts': [False, False, [], '', ''],
            'management': [False, False, [], '', ''],
            'static': [False, False, [], '', u'是否静态地址'],
            'netmask': [False, False, [], '', ''],
            'if_gateway': [False, False, [], '', ''],
            'dhcp_tag': [False, False, [], '', ''],
            'dns_name': [False, False, [], '', u'dns名字'],
            'static_routes': [False, False, [], '', ''],
            'virt_bridge': [False, False, [], '', ''],
            'ipv6_address': [False, False, [], '', ''],
            'ipv6_prefix': [False, False, [], '', ''],
            'ipv6_secondaries': [False, False, [], '', ''],
            'ipv6_mtu': [False, False, [], '', ''],
            'ipv6_static_routes': [False, False, [], '', ''],
            'ipv6_default_gateway': [False, False, [], '', ''],
            'cnames': [False, False, [], '', ''],
        }
        fileds = {
            'name': [True, False, [], '', u'资源名字'],
            'owners': [False, False, [], '', ''],
            'profile': [True, False, [], '', u'profile文件'],
            'image': [False, False, [], '', ''],
            'status': [False, False, [], '', ''],
            'kernel_options': [False, False, [], '', ''],
            'kernel_options_post': [False, False, [], '', ''],
            'ks_meta': [False, False, [], '', ''],
            'enable_gpxe': [False, False, [], '', ''],
            'proxy': [False, False, [], '', ''],
            'netboot_enabled': [False, False, [], '', ''],
            'kickstart': [False, False, [], '', ''],
            'comment': [False, False, [], '', ''],
            'depth': [False, False, [], '', ''],
            'server': [False, False, [], '', ''],
            'virt_path': [False, False, [], '', ''],
            'virt_type': [False, False, [], '', ''],
            'virt_cpus': [False, False, [], '', ''],
            'virt_file_size': [False, False, [], '', ''],
            'virt_disk_driver': [False, False, [], '', ''],
            'virt_ram': [False, False, [], '', ''],
            'virt_auto_boot': [False, False, [], '', ''],
            'virt_pxe_boot': [False, False, [], '', ''],
            'ctime': [False, False, [], '', ''],
            'mtime': [False, False, [], '', ''],
            'power_type': [True, False, [], '', ''],
            'power_address': [True, False, [], '', ''],
            'power_user': [True, False, [], '', ''],
            'power_pass': [True, False, [], '', ''],
            'power_id': [False, False, [], '', ''],
            'hostname': [False, False, [], '', ''],
            'gateway': [False, False, [], '', ''],
            'name_servers': [False, False, [], '', ''],
            'name_servers_search': [False, False, [], '', ''],
            'ipv6_default_device': [False, False, [], '', ''],
            'ipv6_autoconfiguration': [False, False, [], '', ''],
            'network_widget_a': [False, False, [], '', ''],
            'network_widget_b': [False, False, [], '', ''],
            'network_widget_c': [False, False, [], '', ''],
            'mgmt_classes': [False, False, [], '', ''],
            'mgmt_parameters': [False, False, [], '', ''],
            'boot_files': [False, False, [], '', ''],
            'fetchable_files': [False, False, [], '', ''],
            'template_files': [False, False, [], '', ''],
            'redhat_management_key': [False, False, [], '', ''],
            'redhat_management_server': [False, False, [], '', ''],
            'template_remote_kickstarts': [False, False, [], '', ''],
            'repos_enabled': [False, False, [], '', ''],
            'ldap_enabled': [False, False, [], '', ''],
            'ldap_type': [False, False, [], '', ''],
            'monit_enabled': [False, False, [], '', ''],
            'interface': interface}
        return fileds

    def _check_fileds(self, fileds, params):
        # 1.校验必输项
        mandatory_fileds = filter(lambda x: fileds[x][0], fileds.keys())
        for k in mandatory_fileds:
            if not params.get(k, None):
                raise HTTPError(400,'Variable "{0}" is mandatory, check your params.'.format(k))

        # 2.校验输入项范围
        scode_fileds = filter(lambda x: fileds[x][1], fileds.keys())
        for k in scode_fileds:
            val = params.get(k)
            if val:
                if val not in fileds[k][2]:
                    raise HTTPError(400,'Variable {0} value is Error, must in {1}'.format(k, fileds[k][2]))

    def check_fileds(self, params):

        fileds = self.get_fileds()
        interface_fileds = fileds.pop('interface')
        interfaces = params.get('interfaces')
        if interfaces:
            for interface_name, interface in interfaces.items():
                self._check_fileds(interface_fileds, interface)
        self._check_fileds(fileds, params)

    def power(self, params):
        remote = self.get_remote()
        token = self.get_token()
        logger.debug('systems[{0}] power{1}'.format(params.get('systems'), params.get('power')))
        result = remote.background_power_system(params, token)
        return result

    def rebuild(self, params):
        """
            重装系统有三个步骤
            1.设置新的profile（可选）
            2.设置Netboot Enabled为true
            3.重启电源
        """
        logger.info("rebuild set param")
        systems = params.pop('systems')
        import datetime
        print datetime.datetime.now()
        for system_name in systems:
            self.modify(system_name,params)
        print datetime.datetime.now()
        # build power params
        power_data = {
            'power':'reboot',
            'systems':systems # todo 考虑批量操作
        }
        logger.info('rebuild power reboot')
        result = self.power(power_data)
        print datetime.datetime.now()
        return result

    def create(self, params):
        remote = self.get_remote()
        token = self.get_token()
        logger.debug('create system params:{0}'.format(params))
        # 1.检查参数
        self.check_fileds(params)
        # 2.新建system
        system_id = remote.new_system(token)
        logger.info("new system id {0}".format(system_id))
        interfaces = {}
        if params.has_key('interfaces'):
            interfaces = params.pop('interfaces')
        for key, val in params.items():
            remote.modify_system(system_id,key,val,token)
            logger.info("set params {0} = {1}".format(key, val))

        for interface_name, params in interfaces.items():
            # 重新构造数据，将interface的参数修改为 interface_name+key
            temp_dict = {}
            logger.info("struct interface params {0}".format(interface_name))
            for key, val in params.items():
                temp_dict['%s-%s'%(key, interface_name)] = val
            logger.info("update interface {0}".format(temp_dict))
            remote.modify_system(system_id, 'modify_interface',
                                 temp_dict, token)
            del temp_dict
        logger.info("save system {0}".format(system_id))
        remote.save_system(system_id,token)
        logger.info("sync system info")
        remote.sync(token)
        return system_id

    def modify(self, system_name, params):
        remote = self.get_remote()
        token = self.get_token()
        logger.debug('modify system params:{0}'.format(params))
        interfaces = {}
        if params.has_key('interfaces'):
            interfaces = params.pop('interfaces')

        # check todo
        if not remote.has_item(self.TYPE, system_name):
            raise HTTPError(404,'System {0} not found'.format(system_name))

        system_id = remote.get_system_handle(system_name, token)

        for key, val in params.items():
            logger.info("set params {0} = {1}".format(key, val))
            remote.modify_system(system_id,key,val,token)

        for interface_name, params in interfaces.items():
            # 重新构造数据，将interface的参数修改为 interface_name+key
            temp_dict = {}
            logger.info("struct interface params {0}".format(interface_name))
            for key, val in params.items():
                temp_dict['%s-%s'%(key, interface_name)] = val
            logger.info("update interface {0}".format(temp_dict))
            remote.modify_system(system_id, 'modify_interface',
                                 temp_dict, token)
            del temp_dict
        logger.info("save system {0}".format(system_id))
        remote.save_system(system_id,token)
        logger.info("sync system info")
        sync_task = remote.sync(token)
        return sync_task

    def delete(self, params):
        remote = self.get_remote()
        token = self.get_token()

    def get_item(self, system_name):
        remote = self.get_remote()
        token = self.get_token()
        result = remote.get_system(system_name, token)
        if not isinstance(result, dict):
            raise HTTPError(404, 'system not found')
        return result




class Distros(Cobbler):
    def _check_iso(self, path):

        if not os.path.exists(path):
            raise HTTPError(400,'{0} does not exist'.format(path))

    def get_fileds(self):

        return {
            'path': [True, False, [], '', u'镜像地址'], # [bool(是否必须),bool(是否对值有限制),限制函数或列表,default,字段含义]
            'name': [True, False, [], '', u'distros名字'],
            'arch': [False, True, ['i386',
                                   'x86_64',
                                   'ia64',
                                   'ppc',
                                   'ppc64',
                                   's390',
                                   's390x',
                                   'arm'], 'i386', u'镜像类型'],
            'breed': [False, True, ['redhat',
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
        osname = params.pop('filename')
        name = params.get('name')
        dvd = '/'.join([path, osname])
        logger.info("check iso {0}".format(dvd))
        self._check_iso(dvd)
        mnt_sub = "/mnt/{0}".format(name)
        params['path'] = mnt_sub
        mnt_sub_cmd = ['mkdir', mnt_sub]
        mount_cmd = ['mount', '-o', 'loop', dvd, mnt_sub]
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
        return task_name, mnt_sub

    def after_upload(self, task_name, mnt_sub):
        """
            导入完成后，卸载硬盘，并删除目录
        """
        remote = self.get_remote()
        token = self.get_token()
        umount_cmd = ["umount", mnt_sub]
        del_mnt_sub_cmd = ['rm', '-rf', mnt_sub]
        logger.info("check task {0} result".format(task_name))
        status = remote.get_task_status(task_name)
        while status[2] not in ('complete', 'failed'):
            status = remote.get_task_status(task_name)
        logger.info("task execute complete - result[{0}]".format(status[2]))
        logger.info("sync info")
        remote.sync(token)
        logger.info("umount iso {0}".format(mnt_sub))
        ret, out_info, error_msg = self.execute_cmd(umount_cmd)
        if not ret:
            logger.error('execute {0} error{1}'.format(umount_cmd, error_msg))
        logger.info("delete temp dir{0}".format(mnt_sub))
        ret, out_info, error_msg = self.execute_cmd(del_mnt_sub_cmd)
        if not ret:
            logger.error('execute {0} error{1}'.format(del_mnt_sub_cmd, error_msg))

    def get_item(self, distros_name):
        remote = self.get_remote()
        token = self.get_token()
        result = remote.get_distro(distros_name, token)
        if not isinstance(result, dict):
            raise HTTPError(404, 'distro not found')
        return result

class Profile(Cobbler):
    def get_items(self, name=None):
        pass

    def get_item(self, name):
        return self.get_items(name)

class Event(Cobbler):

    def get_event(self, event_id):
        """
            1.获取任务结果
            2.获取日志信息
            retrun {
                status:''
                loginfo:''
            }
        """
        result = {}
        try:
            remote = self.get_remote()
            status = remote.get_task_status(event_id)
            loginfo = remote.get_event_log(event_id)
            result['status'] = status[2]
            result['event_log'] = loginfo
        except xmlrpclib.Fault, msg:
            re_no_event = re.compile('.*?no event with that id.*?', re.S)
            if re.findall(re_no_event, msg.faultString):
                raise HTTPError(404, 'no event with that id')
        return result

    def get_events(self):
        # todo 进行分页等操作
        remote = self.get_remote()
        events = remote.get_events()
        result = {}
        for event_id in events.keys():
            single_info = self.get_event(event_id)
            result[event_id] = single_info
        return result

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
    # try:
    #     cobbler.execute_cmd('1')
    # except HTTPError, msg:
    #     print msg.status_code, msg.log_message
    # remote = cobbler.get_remote()
    # data = remote.get_event_log('2016-04-18_170033_import')
    # s = data.strip('\n').split('\n')[-1]
    # # re_task = re.compile('.*?### TASK (COMPLETE|FAILED) ###', re.S)
    # # s = [ "### TASK COMPLETE ###", "### TASK FAILED ###"]
    # # for row in s:
    # #     print re_task.match(row)
    # status = remote.get_task_status('2016-04-18_170033_import')
    # print status
    # params = {
    #     "name": "test123",
    #     "profile": "28a17fb4-0786-11e6-83a2-fa163e763553-x86_64",
    #     "power_type": 'ipmilan',
    #     "power_address": '172.16.10.210',
    #     "power_user": 'root',
    #     "power_pass": 'admin',
    #     "interfaces": {
    #         "eth0":{
    #             "mac_address": "fa:16:3e:76:35:53",
    #             "ip_address": "192.160.10.30"
    #         },
    #         "eth1":{
    #             "mac_address": "fa:16:3e:76:35:53",
    #             "ip_address": "192.160.10.30"
    #         }
    #     }
    # }
    # sys = System()
    # #sys.check_fileds(params)
    # sys.create(params)

    #event = Event()
    # try:
    #     print event.get_event('2016-04-21_155639_power')
    # except HTTPError, msg:
    #     print msg.status_code
    # print event.get_events(['2016-04-21_155639_power', '2016-04-21_134947_import'])
    #
    # cobbler = Cobbler()
    # remote = cobbler.get_remote()
    # print remote.get_event_log()
    #print event.get_events()
    system = System()
    system.get('test123456')