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
import uuid
import zipfile
import pyte

try:
    import simplejson as json
except ImportError:
    import json

from tornado.websocket import WebSocketHandler
from tornado.web import HTTPError

from sqlalchemy.orm import sessionmaker

from dbcollections.nodes.models import Node
from dbcollections.permission.models import PermRole
from dbcollections.logrecords.models import TermLog, Log, TtyLog, ExecLog
from common.base import RequestHandler
from utils.auth import auth
from utils.utils import get_dbsession
from conf.settings import LOG_DIR,engine
from util import renderJSON, WebTty, MyThread
from handlers.ansible.v1_0.ansible_play import MyRunner


logger = logging.getLogger()


class WebTerminalKillHandler(RequestHandler):
    #@auth
    def get(self):
        try:
            ws_id = self.get_argument('id')
            se = get_dbsession()
            EXSITS = False
            for ws in WebTerminalHandler.clients:
                if ws.id == int(ws_id):
                    logger.info("Kill log id %s" % ws_id)
                    EXSITS = True
                    ws.on_close()

            if not EXSITS:
                raise HTTPError(404, 'WebTerminal Not Found')

            log = se.query(Log).get(ws_id).to_dict()
            self.set_status(200)
            self.finish({'message': 'success', 'data': log})
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


class WebTerminalHandler(WebSocketHandler):
    clients = []
    tasks = []

    def __init__(self, *args, **kwargs):
        self.term = None
        self.log_file_f = None
        self.log_time_f = None
        self.log = None
        self.id = 0
        self.sendlog2browser = False
        self.user = None
        self.ssh = None
        self.channel = None
        self.threads = []
        self.se = get_dbsession()
        super(WebTerminalHandler, self).__init__(*args, **kwargs)

    def check_origin(self, origin):
        return True

    # @auth
    def open(self):
        logger.debug('Websocket: Open request')
        role_id = self.get_argument('role_id', -1)
        node_id = self.get_argument('id', -1)
        user_id = self.get_argument('user_id', -1)

        node = self.se.query(Node).filter_by(id=node_id).first()
        if not node:
            raise RuntimeError("Node {0} is no exists".format(node_id))
        role = self.se.query(PermRole).filter_by(id=role_id).first()
        if not role:
            raise RuntimeError("Role {0} is no exists".format(role_id))
        self.termlog = TermLogRecorder(user=user_id)
        self.term = WebTty(user_id, node, role, login_type='web')
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
            self.termlog.recoder = True
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
                    if len(result) > 0:
                        tlog = TtyLog(log_id=self.log, cmd=result)
                        self.se.begin()
                        self.se.add(tlog)
                        self.se.commit()
                        self.se.flush()
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
            # 在任务列表中删除子进程
            for t in self.threads:
                if t in WebTerminalHandler.tasks:
                    WebTerminalHandler.tasks.remove(t)
        try:
            self.log_file_f.write('End time is %s' % datetime.datetime.now())
            # 保存termlog
            self.termlog.save()

            # 保存日志
            log = Log(id=self.log, is_finished=True, end_time=datetime.datetime.now(), filename=self.termlog.filename)
            self.se.begin()
            self.se.merge(log)
            self.se.flush()
            self.se.commit()
            self.log_file_f.close()
            self.log_time_f.close()
            self.ssh.close()
            self.close()
        except AttributeError:
            pass
        except Exception, e:
            print e

    def forward_outbound(self):
        # 获取时间日志句柄，内容日志句柄用于后续日志回放，获取实际Log ID
        self.log_file_f, self.log_time_f, self.log = self.term.get_log()
        self.id = self.log
        logger.info("print >>>>> self.id {0}".format(self.id))
        self.termlog.setid(self.log)
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
                        # 第一次连接时，将本地生成的log_id返回前台
                    if not self.sendlog2browser:
                        data = '[log_id=%s]' % self.log
                        self.sendlog2browser = True
                    data += recv
                    if self.term.vim_flag:
                        self.term.vim_data += recv
                    try:
                        # 通过websocket返回浏览器结果
                        self.write_message(data.decode('utf-8', 'replace'))
                        # 记录termlog
                        self.termlog.write(data)
                        self.termlog.recoder = False
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


class ReplayHandler(RequestHandler):
    #@auth
    def get(self, *args, **kwargs):
        try:
            # 1获取ID
            log_id = kwargs.get('log_id')
            # 2数据库获取信息
            if log_id:
                se = get_dbsession()
                log = se.query(Log).filter_by(id=log_id).first()
                if not log:
                    raise HTTPError(404)
                    # 3根据获取数据，整理日志内容
                scriptf = log.log_path + '.log'
                timef = log.log_path + '.time'

                if os.path.isfile(scriptf) and os.path.isfile(timef):
                    content = renderJSON(scriptf, timef)
                    self.set_status(200)
                    self.finish({'content': content})
                else:
                    raise HTTPError(404)
            else:
                raise HTTPError(400)
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


class LoginfoHandler(RequestHandler):
    #@auth
    def get(self, *args, **kwargs):
        try:
            # 获取某条日志信息
            log_id = kwargs.get('log_id', None)
            se = get_dbsession()
            if log_id:
                log_info = se.query(Log).get(log_id)
                if not log_info:
                    raise HTTPError(404, "Log Not Found")

                self.set_status(200)
                self.finish({'message': 'success', 'data': log_info.to_dict()})
                return

            count = self.get_argument('count', False)
            if count:
                cnt = se.query(Log).count()
                self.set_status(200)
                self.finish({'message': 'success', 'count': cnt})
                return

            # 查询日志信息，分页
            pageno = int(self.get_argument('pageno', 1))
            pagesize = int(self.get_argument('pagesize', 10))
            # 获取数据库中信息
            log = se.query(Log).order_by(Log.id.desc()).offset((pageno - 1) * pagesize).limit(pagesize).all()
            log_list = [row.to_dict() for row in log]
            self.set_status(200)
            self.finish({'message': 'success', 'data': log_list})
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


class TtyLoginfoHandler(RequestHandler):
    #@auth
    def get(self, *args, **kwargs):
        '''
           根据指定Log的id查询所有的Ttylog信息
        '''
        try:
            log_id = self.get_argument('log_id', None)

            # 获取数据库中信息
            se = get_dbsession()
            ttylog = se.query(TtyLog)
            if log_id:
                ttylog = ttylog.filter_by(log_id=log_id)

            ttylog = ttylog.order_by(TtyLog.id.desc()).all()

            if not ttylog:
                raise HTTPError(404, 'Ttylog Not Found')

            ttylog_list = [row.to_dict() for row in ttylog]

            self.set_status(200)
            self.finish({'message': 'success', 'data': ttylog_list})
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


class TermLogRecorder(object):
    """
    TermLogRecorder
    """
    loglist = dict()

    def __init__(self, user=None, uid=None):
        self.log = {}
        self.id = 0
        self.user = user
        self.recoderStartTime = time.time()
        self.__init_screen_stream()
        self.recoder = False
        self.commands = []
        self._lists = None
        self.file = None
        self.filename = None
        self._data = None
        self.vim_pattern = re.compile(r'\W?vi[m]?\s.* | \W?fg\s.*', re.X)
        self._in_vim = False
        self.CMD = {}

    def __init_screen_stream(self):
        """
        Initializing the virtual screen and the character stream
        """
        self._stream = pyte.ByteStream()
        self._screen = pyte.Screen(80, 24)
        self._stream.attach(self._screen)

    def _command(self):
        for i in self._screen.display:
            if i.strip().__len__() > 0:
                self.commands.append(i.strip())
                if not i.strip() == '':
                    self.CMD[str(time.time())] = self.commands[-1]
        self._screen.reset()

    def setid(self, id):
        self.id = id
        TermLogRecorder.loglist[str(id)] = [self]

    def write(self, msg):
        if self.recoder and (not self._in_vim):
            if self.commands.__len__() == 0:
                self._stream.feed(msg)
            elif not self.vim_pattern.search(self.commands[-1]):
                self._stream.feed(msg)
            else:
                self._in_vim = True
                self._command()
        else:
            if self._in_vim:
                if re.compile(r'\[\?1049', re.X).search(msg.decode('utf-8', 'replace')):
                    self._in_vim = False
                    self.commands.append('')
                self._screen.reset()
            else:
                self._command()
        self.log[str(time.time() - self.recoderStartTime)] = msg.decode('utf-8', 'replace')

    def save(self, path=LOG_DIR):
        date = datetime.datetime.now().strftime('%Y%m%d')
        filename = str(uuid.uuid4())
        self.filename = filename
        filepath = os.path.join(path, 'tty', date, filename + '.zip')
        if not os.path.isdir(os.path.join(path, 'tty', date)):
            os.makedirs(os.path.join(path, 'tty', date), mode=0777)
        while os.path.isfile(filepath):
            filename = str(uuid.uuid4())
            filepath = os.path.join(path, 'tty', date, filename + '.zip')
        password = str(uuid.uuid4())
        try:
            se = get_dbsession()
            se.begin()
            try:
                zf = zipfile.ZipFile(filepath, 'w', zipfile.ZIP_DEFLATED)
                zf.setpassword(password)
                zf.writestr(filename, json.dumps(self.log))
                zf.close()
                record = TermLog(logpath=filepath, logpwd=password, filename=filename,
                                 history=json.dumps(self.CMD), timestamp=int(self.recoderStartTime), user_id=self.user)
            except:
                record = TermLog(logpath='locale', logpwd=password, log=json.dumps(self.log),
                                 filename=filename, history=json.dumps(self.CMD),
                                 timestamp=int(self.recoderStartTime), user_id=self.user)
            se.add(record)
            se.flush()
            se.commit()
        except Exception, e:
            logger.error(traceback.format_exc())
            se.rollback()
        finally:
            se.close()

        try:
            del TermLogRecorder.loglist[str(self.id)]
        except KeyError:
            pass


class ExecCommandsHandler(WebSocketHandler):
    """
    执行shell命令
    """
    clients = []
    tasks = []

    def __init__(self, *args, **kwargs):
        self.log_id = ''
        self.runner = None
        self.assets = []
        self.remote_ip = ''
        self.proxy_host = ''
        super(ExecCommandsHandler, self).__init__(*args, **kwargs)

    def check_origin(self, origin):
        return True

    def open(self):
        # 远程IP
        self.remote_ip = self.request.remote_ip
        # proxy IP
        self.proxy_host = self.request.host

        logger.info('remote ip:%s'%self.remote_ip)

    def on_message(self, message):
        data = json.loads(message)
        pattern = data.get('pattern', '')
        self.command = data.get('command', '')
        resource = data.get('resource', '')
        self.asset_name_str = ''
        if pattern and self.command:
            self.runner = MyRunner(resource)
            host_lists = [item.name for item in self.runner.inventory.list_hosts(pattern)]
            logger.info('execute commands host_lists:%s'%host_lists)
            if host_lists:
                for inv in host_lists:
                    self.asset_name_str += '%s ' % inv
                self.write_message('匹配主机: ' + self.asset_name_str)
                self.write_message('<span style="color: yellow">Ansible> %s</span>\n\n' % self.command)
                self.__class__.tasks.append(MyThread(target=self.run_cmd, args=(self.command, host_lists)))
            else:
                self.write_message('匹配不到主机')
                self.on_close()

        for t in self.__class__.tasks:
            if t.is_alive():
                continue
            try:
                t.setDaemon(True)
                t.start()
            except RuntimeError:
                pass

    def run_cmd(self, command, host_list):
        self.runner.run(host_list, 'shell', command)
        self.runner.get_result()

        # 记录日志
        Session = sessionmaker(bind=engine)
        session = Session()
        try:
            exec_log = ExecLog(host=self.asset_name_str, cmd=self.command, user='', proxy_host=self.proxy_host,
                               remote_ip=self.remote_ip, result=json.dumps(self.runner.results_raw))
            session.add(exec_log)
            session.commit()
            self.log_id = exec_log.id
        except Exception as e:
            logger.error(e)
        finally:
            session.close()

        # 将命令执行结果显示到窗口中
        logger.info('execute commands results:%s'% self.runner.results_raw)
        newline_pattern = re.compile(r'\n')
        for k, v in self.runner.results_raw.items():
            for host, info in v.items():
                if k == 'success':
                    header = "<span style='color: green'>[ %s => %s]</span>\n" % (host, 'success')
                    output = newline_pattern.sub('<br />', info['stdout'])
                else:
                    header = "<span style='color: red'>[ %s => %s]</span>\n" % (host, 'failed')
                    output = newline_pattern.sub('<br />', info)
                self.write_message(header)
                self.write_message(output)

        self.write_message('log_id:%s'%self.log_id)   # 日志ID,查询日志用
        self.write_message('\n~o~ Task finished ~o~\n')

    def on_close(self):
        logger.debug('关闭web_exec请求')


class ExecCommandsLogsHandler(RequestHandler):
    """
    批量执行命令日志查询
    """
    @auth
    def get(self, *args, **kwargs):
        try:
            log_id = kwargs.get('log_id', '')
            se = get_dbsession()
            if log_id:
                log_info = se.query(ExecLog).get(log_id)
                if not log_info:
                    raise HTTPError(404, "Log Not Found")

                self.set_status(200)
                self.finish({'messege': 'success', 'data': log_info.to_dict()})
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

