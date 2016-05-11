#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Name    : api.py
# @Date    : 2016-04-18 17:49
# @Author  : AutoOps
# @Link    : http://www.magicstack.cn/
# @Version :

import logging
import re
import datetime
import time
import select
import sys
import threading

try:
    import simplejson as json
except ImportError:
    import json

from tornado.websocket import WebSocketHandler, WebSocketClosedError

from common.connect import Tty

logger = logging.getLogger()


class WebTerminalHandler(WebSocketHandler):
    clients = []
    tasks = []

    def __init__(self, *args, **kwargs):
        self.term = None
        self.log_file_f = None
        self.log_time_f = None
        self.log = None
        self.id = 0
        self.user = None
        self.ssh = None
        self.channel = None
        self.threads = []
        super(WebTerminalHandler, self).__init__(*args, **kwargs)

    def check_origin(self, origin):
        return True

    def open(self):
        logger.debug('Websocket: Open request')

        self.term = WebTty(self.user, login_type='web')
        self.term.remote_ip = self.request.headers.get("X-Real-IP")
        if not self.term.remote_ip:
            self.term.remote_ip = self.request.remote_ip
            # ssh方式连接登录
        self.ssh = self.term.get_connection()
        self.channel = self.ssh.invoke_shell(term='xterm')
        # 1.Websocket客户端列表
        WebTerminalHandler.clients.append(self)
        # 2.Websocket处理任务线程
        thread = MyThread(target=self.forward_outbound)
        WebTerminalHandler.tasks.append(thread)
        # 3.客户端关联线程
        self.threads.append(thread)

        # 启动线程
        for t in WebTerminalHandler.tasks:
            if t.is_alive():
                continue
            try:
                t.setDaemon(True)
                t.start()
            except RuntimeError:
                pass

    def on_message(self, message):
        """
            接收客户端数据，并根据数据内容执行相应操作
        """
        jsondata = json.loads(message)
        logger.info("on_message {0}".format(jsondata))
        if not jsondata:
            return

        if 'resize' in jsondata.get('data'):
            self.channel.resize_pty(
                jsondata.get('data').get('resize').get('cols', 80),
                jsondata.get('data').get('resize').get('rows', 24)
            )
        elif jsondata.get('data'):
            self.term.input_mode = True
            if str(jsondata['data']) in ['\r', '\n', '\r\n']:
                if self.term.vim_flag:
                    match = re.compile(r'\x1b\[\?1049', re.X).findall(self.term.vim_data)
                    if match:
                        if self.term.vim_end_flag or len(match) == 2:
                            self.term.vim_flag = False
                            self.term.vim_end_flag = False
                        else:
                            self.term.vim_end_flag = True
                else:
                    result = self.term.deal_command(self.term.data)[0:200]
                    # if len(result) > 0:
                    #     TtyLog(log=self.log, datetime=datetime.datetime.now(), cmd=result).save()
                self.term.vim_data = ''
                self.term.data = ''
                self.term.input_mode = False
            # 执行命令
            self.channel.send(jsondata['data'])
        else:
            pass

    def on_close(self):
        logger.debug('Websocket: Close request')
        if self in WebTerminalHandler.clients:
            WebTerminalHandler.clients.remove(self)
            # 在任务列表中删除子进程     todo，目前暂时未找到杀死子进程的方法，先将其从列表中移除
            for t in self.threads:
                if t in WebTerminalHandler.tasks:
                    WebTerminalHandler.tasks.remove(t)
        try:
            self.log_file_f.write('End time is %s' % datetime.datetime.now())
            # self.log.is_finished = True
            # self.log.end_time = datetime.datetime.now()
            # self.log.save()
            self.log_file_f.close()
            self.log_time_f.close()
            self.ssh.close()
            self.close()
        except AttributeError:
            pass

    def forward_outbound(self):
        self.log_file_f, self.log_time_f = self.term.get_log()
        try:
            data = ''
            pre_timestamp = time.time()
            while True:
                r, w, e = select.select([self.channel, sys.stdin], [], [])
                if self.channel in r:
                    recv = self.channel.recv(1024)
                    logger.info( recv )
                    if not len(recv):
                        return
                    data += recv
                    if self.term.vim_flag:
                        self.term.vim_data += recv
                    try:
                        self.write_message(data.decode('utf-8', 'replace'))
                        now_timestamp = time.time()
                        self.log_time_f.write('%s %s\n' % (round(now_timestamp - pre_timestamp, 4), len(data)))
                        self.log_file_f.write(data)
                        pre_timestamp = now_timestamp
                        self.log_file_f.flush()
                        self.log_time_f.flush()
                        if self.term.input_mode and not self.term.is_output(data):
                            self.term.data += data
                        data = ''
                    except UnicodeDecodeError:
                        pass
        except IndexError:
            pass


class MyThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        super(MyThread, self).__init__(*args, **kwargs)

    def run(self):
        try:
            super(MyThread, self).run()
        except WebSocketClosedError:
            pass


class WebTty(Tty):
    def __init__(self, *args, **kwargs):
        super(WebTty, self).__init__(*args, **kwargs)
        self.ws = None
        self.data = ''
        self.input_mode = False