#!/usr/bin/env python
# coding: utf-8

import sys

reload(sys)
sys.setdefaultencoding('utf8')

import os
import re
import time
import datetime
import readline
import paramiko
import pyte
import operator
import fcntl, socket

from common.websocket_api import logger, ServerError, mkdir, CRYPTOR
from conf.settings import LOG_DIR
from dbcollections.logrecords.models import Log
from utils.utils import get_dbsession

try:
    remote_ip = os.environ.get('SSH_CLIENT').split()[0]
except (IndexError, AttributeError):
    remote_ip = os.popen("who -m | awk '{ print $NF }'").read().strip('()\n')

try:
    import termios
    import tty
except ImportError:
    print '\033[1;31m仅支持类Unix系统 Only unix like supported.\033[0m'
    time.sleep(3)
    sys.exit()


def color_print(msg, color='red', exits=False):
    """
    Print colorful string.
    颜色打印字符或者退出
    """
    color_msg = {'blue': '\033[1;36m%s\033[0m',
                 'green': '\033[1;32m%s\033[0m',
                 'yellow': '\033[1;33m%s\033[0m',
                 'red': '\033[1;31m%s\033[0m',
                 'title': '\033[30;42m%s\033[0m',
                 'info': '\033[32m%s\033[0m'}
    msg = color_msg.get(color, 'red') % msg
    print msg
    if exits:
        time.sleep(2)
        sys.exit()
    return msg


def write_log(f, msg):
    msg = re.sub(r'[\r\n]', '\r\n', msg)
    f.write(msg)
    f.flush()


class Tty(object):
    """
    A virtual tty class
    一个虚拟终端类，实现连接ssh和记录日志，基类
    """

    def __init__(self, user_id, node, role, login_type='ssh'):
        self.ip = None
        self.port = 22
        self.ssh = None
        self.channel = None
        self.user_id = user_id
        self.node = node
        self.role = role
        self.remote_ip = ''
        self.login_type = login_type
        self.vim_flag = False
        self.vim_end_flag = False
        self.vim_end_pattern = re.compile(r'\x1b\[\?1049', re.X)
        self.vim_pattern = re.compile(r'\W?vi[m]?\s.* | \W?fg\s.*', re.X)
        self.vim_data = ''
        self.stream = None
        self.screen = None
        self.__init_screen_stream()

    def __init_screen_stream(self):
        """
        初始化虚拟屏幕和字符流
        """
        self.stream = pyte.ByteStream()
        self.screen = pyte.Screen(100, 24)
        self.stream.attach(self.screen)

    @staticmethod
    def is_output(strings):
        newline_char = ['\n', '\r', '\r\n']
        for char in newline_char:
            if char in strings:
                return True
        return False

    def command_parser(self, command):
        """
        处理命令中如果有ps1或者mysql的特殊情况,极端情况下会有ps1和mysql
        :param command:要处理的字符传
        :return:返回去除PS1或者mysql字符串的结果
        """
        result = None
        match = re.compile('\[?.*@.*\]?[\$#]\s').split(command)
        if match:
            # 只需要最后的一个PS1后面的字符串
            result = match[-1].strip()
        else:
            # PS1没找到,查找mysql
            match = re.split('mysql>\s', command)
            if match:
                # 只需要最后一个mysql后面的字符串
                result = match[-1].strip()
        return result

    def deal_command(self, data):
        """
        处理截获的命令
        :param data: 要处理的命令
        :return:返回最后的处理结果
        """
        command = ''
        try:
            self.stream.feed(data)
            # 从虚拟屏幕中获取处理后的数据
            for line in reversed(self.screen.buffer):
                line_data = "".join(map(operator.attrgetter("data"), line)).strip()
                if len(line_data) > 0:
                    parser_result = self.command_parser(line_data)
                    if parser_result is not None:
                        # 2个条件写一起会有错误的数据
                        if len(parser_result) > 0:
                            command = parser_result
                    else:
                        command = line_data
                    break
            if command != '':
                # 判断用户输入的是否是vim 或者fg命令
                if self.vim_pattern.search(command):
                    self.vim_flag = True
                    # 虚拟屏幕清空
            self.screen.reset()
        except Exception:
            pass
        return command

    def get_log(self):
        """
        Logging user command and output.
        记录用户的日志
        """
        tty_log_dir = os.path.join(LOG_DIR, 'tty')
        date_today = datetime.datetime.now()
        date_start = date_today.strftime('%Y%m%d')
        time_start = date_today.strftime('%H%M%S')
        today_connect_log_dir = os.path.join(tty_log_dir, date_start)
        log_file_path = os.path.join(today_connect_log_dir, '%s_%s_%s' % (self.user_id, self.node.id, time_start))

        try:
            mkdir(os.path.dirname(today_connect_log_dir), mode=0777)
            mkdir(today_connect_log_dir, mode=0777)
        except OSError:
            logger.debug(u'创建目录 %s 失败，请修改%s目录权限' % (today_connect_log_dir, tty_log_dir))
            raise ServerError(u'创建目录 %s 失败，请修改%s目录权限' % (today_connect_log_dir, tty_log_dir))

        try:
            log_file_f = open(log_file_path + '.log', 'a')
            log_time_f = open(log_file_path + '.time', 'a')
        except IOError:
            logger.debug(u'创建tty日志文件失败, 请修改目录%s权限' % today_connect_log_dir)
            raise ServerError(u'创建tty日志文件失败, 请修改目录%s权限' % today_connect_log_dir)

        if self.login_type == 'ssh':  # 如果是ssh连接过来，记录connect.py的pid，web terminal记录为日志的id
            pid = os.getpid()
            self.remote_ip = remote_ip  # 获取远端IP
        else:
            pid = 0

        log = Log(user_id=self.user_id, node_id=self.node.id, remote_ip=self.remote_ip, login_type=self.login_type,
                  log_path=log_file_path, start_time=date_today, pid=pid)
        log_id = None
        se = get_dbsession()
        if self.login_type == 'web':
            log.pid = log.id  # 设置log id为websocket的id, 然后kill时干掉websocket
        try:
            se.begin()
            se.add(log)
            se.commit()
            log_id = log.id
        except:
            se.rollback()
        finally:
            se.flush()
            se.close()

        log_file_f.write('Start at %s\r\n' % datetime.datetime.now())
        return log_file_f, log_time_f, log_id

    def get_connect_info(self):
        """
        获取需要登陆的主机的信息和映射用户的账号密码
        """

        role_key = self.role.key_path  # 获取角色的key，因为ansible需要权限是600，所以统一生成用户_角色key
        role_pass = CRYPTOR.decrypt(self.role.password)

        connect_info = {'user': self.user_id, 'ip': self.node.ip,
                        'port': int(self.node.port), 'name': self.role.name,
                        'pass': role_pass, 'key': role_key}
        logger.debug(connect_info)
        return connect_info

    def get_connection(self):
        """
        获取连接成功后的ssh
        """
        connect_info = self.get_connect_info()

        # 发起ssh连接请求 Make a ssh connection
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            role_key = os.sep.join((connect_info.get('key'), 'id_rsa'))
            if role_key and os.path.isfile(role_key):
                try:
                    ssh.connect(connect_info.get('ip'),
                                port=connect_info.get('port'),
                                username=connect_info.get('name'),
                                password=connect_info.get('pass'),
                                key_filename=role_key,
                                look_for_keys=False)
                    return ssh
                except (paramiko.ssh_exception.AuthenticationException, paramiko.ssh_exception.SSHException):
                    logger.warning(u'使用ssh key %s 失败, 尝试只使用密码' % role_key)
                    pass

            ssh.connect(connect_info.get('ip'),
                        port=connect_info.get('port'),
                        username=connect_info.get('name'),
                        password=connect_info.get('pass'),
                        allow_agent=False,
                        look_for_keys=False)

        except paramiko.ssh_exception.AuthenticationException, paramiko.ssh_exception.SSHException:
            raise ServerError('认证失败 Authentication Error.')
        except socket.error:
            raise ServerError('端口可能不对 Connect SSH Socket Port Error, Please Correct it.')
        else:
            self.ssh = ssh
            return ssh


if __name__ == '__main__':
    pass