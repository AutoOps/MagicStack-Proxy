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
import traceback
import os

try:
    import simplejson as json
except ImportError:
    import json

from tornado.websocket import WebSocketHandler
from tornado.web import HTTPError

from dbcollections.logrecords.models import TermLog
from dbcollections.asset.models import Asset
from dbcollections.account.models import User
from common.base import RequestHandler
from utils.auth import auth
from utils.utils import get_dbsession, user_have_perm
from util import renderJSON, WebTty, MyThread


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
        self.se = get_dbsession()
        super(WebTerminalHandler, self).__init__(*args, **kwargs)

    def check_origin(self, origin):
        return True

    #@auth
    def open(self):
        logger.debug('Websocket: Open request')
        role_name = self.get_argument('role', 'sb')
        asset_id = self.get_argument('id', 9999)
        user_id = self.get_argument('user_id', -1)
        asset = self.se.query(Asset).filter_by(id=asset_id)
        self.user = self.se.query(User).filter_by(id=user_id)
        self.termlog = self.se.query(TermLog).filter(user=self.user)
        if asset:
            roles = user_have_perm(self.user, asset)
            logger.debug(roles)
            login_role = ''
            for role in roles:
                if role.name == role_name:
                    login_role = role
                    break
            if not login_role:
                logger.warning('Websocket: Not that Role %s for Host: %s User: %s ' % (role_name, asset.hostname,
                                                                                       self.user.username))
                self.close()
                return
        else:
            logger.warning('Websocket: No that Host: %s User: %s ' % (asset_id, self.user.username))
            self.close()
            return
        logger.debug('Websocket: request web terminal Host: %s User: %s Role: %s' % (asset.hostname, self.user.username,
                                                                                     login_role.name))
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
                    logger.info(recv)
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


class  LogInfoHandler(RequestHandler):
    def get(self, *args, **kwargs):
        try:
            # 1获取ID
            log_id = kwargs.get('log_id')
            # 2数据库获取信息     todo
            # 3读取文件，返回信息
            timef = "/home/flask/projects/jumpserver/jumpserver/logs/tty/20160511/test_123.57.209.233_135417.time"
            scriptf = "/home/flask/projects/jumpserver/jumpserver/logs/tty/20160511/test_123.57.209.233_135417.log"
            if os.path.isfile(scriptf) and os.path.isfile(timef):
                content = renderJSON(scriptf, timef)
                self.set_status(200)
                self.finish({'content':content})
            else:
                raise HTTPError(404)
        except ValueError:
            logger.error(traceback.format_exc())
            self.set_status(400, 'value error')
            self.finish({'messege': 'value error'})
        except HTTPError, http_error:
            logger.error(traceback.format_exc())
            self.set_status(http_error.status_code, http_error.log_message)
            self.finish({'messege': http_error.log_message})
        except:
            logger.error(traceback.format_exc())
            self.set_status(500, 'failed')
            self.finish({'messege': 'failed'})