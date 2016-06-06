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

import sys
import errno
import os
import datetime
import time
import json
import math
from io import open as ioopen
from contextlib import closing

from ansible import constants as C
from ansible.utils.color import stringc
from ansible.utils.unicode import to_bytes, to_unicode
from ansible.utils.display import Display

from conf.settings import LOG_DIR


class LogDisplay(Display):
    def __init__(self, logname=None, verbosity=0):
        """
            :param is string, 生成日志的名称，实质为APScheduler的job_id

            pre_timestamp，用于记录初次创建ansible任务的时间表，对于后续的日志写入及回放做开始时间记录。
        """
        self.logname = logname
        self.pre_timestamp = time.time()
        self._initialize_log()

        super(LogDisplay, self).__init__(verbosity)

    def _initialize_log(self):
        """
            初始化日志文件
            根据初始化job_id（用于和APScheduler关联）创建日志文件
        """
        ansible_log_dir = os.path.join(LOG_DIR, 'ansible')
        # ansible_log_path = os.path.dirname(ansible_log_dir)
        date_today = datetime.datetime.now()
        date_start = date_today.strftime('%Y%m%d')
        time_start = date_today.strftime('%H%M%S')
        today_connect_log_dir = os.path.join(ansible_log_dir, date_start)
        # today_connect_log_path = os.path.dirname(today_connect_log_dir)
        self.log_file_path = os.path.join(today_connect_log_dir, '%s_%s' % (self.logname, time_start))
        try:
            if not os.path.isdir(ansible_log_dir):
                os.makedirs(ansible_log_dir)
                os.chmod(ansible_log_dir, 0777)

            if not os.path.isdir(today_connect_log_dir):
                os.makedirs(today_connect_log_dir)
                os.chmod(today_connect_log_dir, 0777)

        except OSError:
            raise RuntimeError(u'创建目录 %s 失败，请修改%s目录权限' % (today_connect_log_dir, ansible_log_dir))


    def _log(self, msg):
        """
            记录time日志和file日志
        """
        # 打开日志文件
        log_file_f = open(self.log_file_path + '.log', 'a')
        log_time_f = open(self.log_file_path + '.time', 'a')

        # 写入文件
        # file文件直接写入
        log_file_f.write(msg)
        # time文件格式time len(msg) 记录上一次到现在的时间间隔，第二个为写入字符的长度，用于在file文件中读取
        now_timestamp = time.time()
        log_time_f.write('%s %s\n' % (round(now_timestamp - self.pre_timestamp, 4), len(msg)))
        self.pre_timestamp = now_timestamp

        # 关闭日志文件
        log_file_f.close()
        log_time_f.close()

    def get_log_json(self):
        """
            返回日志内容，用于回放使用
        """

        # 使用io.open打开命令文件
        with ioopen(self.log_file_path + '.log', encoding='utf-8', errors='replace', newline='\r\n') as scriptf:
            # 打开时间记录文件
            with open(self.log_file_path + '.time') as timef:
                timing = self._getTiming(timef)
                ret = {}
                with closing(scriptf):
                    offset = 0
                    for t in timing:
                        dt = scriptf.read(t[1])
                        offset += t[0]
                        ret[str(offset / float(1000))] = dt.decode('utf-8', 'replace')

        return json.dumps(ret)


    def _getTiming(self, timef):
        timing = None
        with closing(timef):
            timing = [l.strip().split(' ') for l in timef]
            timing = [(int(math.ceil(float(r[0]) * 1000)), int(r[1])) for r in timing]
        return timing


    def display(self, msg, color=None, stderr=False, screen_only=False, log_only=False):
        """ Display a message to the user

        Note: msg *must* be a unicode string to prevent UnicodeError tracebacks.

        上述为系统自带display操作
        可以输出信息到屏幕之外，同时写入到日志文件中

        此类保留，原有的输出屏幕不变之外。
        将对写入日志进行改造，日志内容分为时间和内容两部分，分别储存到不同的文件中，用于进行录像回放。
        """

        nocolor = msg
        if color:
            msg = stringc(msg, color)

        if not msg.endswith(u'\n'):
            msg2 = msg + u'\n'
        else:
            msg2 = msg

        msg2 = to_bytes(msg2, encoding=self._output_encoding(stderr=stderr))
        if sys.version_info >= (3,):
            # Convert back to text string on python3
            # We first convert to a byte string so that we get rid of
            # characters that are invalid in the user's locale
            msg2 = to_unicode(msg2, self._output_encoding(stderr=stderr))

        if not stderr:
            fileobj = sys.stdout
        else:
            fileobj = sys.stderr

        fileobj.write(msg2)

        # 写入日志
        self._log(msg2)

        try:
            fileobj.flush()
        except IOError as e:
            # Ignore EPIPE in case fileobj has been prematurely closed, eg.
            # when piping to "head -n1"
            if e.errno != errno.EPIPE:
                raise


