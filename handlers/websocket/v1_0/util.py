#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Name    : utils.py
# @Date    : 2016-05-12 11:12
# @Author  : AutoOps
# @Link    : http://www.magicstack.cn/
# @Version :
import threading

from json import dumps
from io import open as ioopen
from contextlib import closing
from math import ceil

from tornado.websocket import WebSocketClosedError

from common.connect import Tty


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


def getTiming(timef):
    timing = None
    with closing(timef):
        timing = [l.strip().split(' ') for l in timef]
        timing = [(int(ceil(float(r[0]) * 1000)), int(r[1])) for r in timing]
    return timing


def renderJSON(script_path, time_file_path):
    # 使用io.open打开命令文件
    with ioopen(script_path, encoding='utf-8', errors='replace', newline='\r\n') as scriptf:
        # 打开时间记录文件
        with open(time_file_path) as timef:
            timing = getTiming(timef)
            ret = {}
            with closing(scriptf):
                scriptf.readline()  # ignore first header line from script file
                offset = 0
                for t in timing:
                    dt = scriptf.read(t[1])
                    offset += t[0]
                    ret[str(offset / float(1000))] = dt.decode('utf-8', 'replace')
    return dumps(ret)