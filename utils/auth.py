#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Name    : auth.py
# @Date    : 2016-04-15 16:18
# @Author  : AutoOps
# @Link    : http://www.magicstack.cn/
# @Version :

import hmac
import time
import datetime
import urllib
import functools

from utils import get_users
from conf.settings import TIMESTAMP_AVAI

def _auth(username, timestamp, hexdigest):
    """
        身份验证
        @username:  用户名
        @timestamp: 时间戳
        @hexdigest: 摘要
    """
    timestamp2date = datetime.datetime.fromtimestamp(int(timestamp))
    now_date = datetime.datetime.now()
    interval = now_date - timestamp2date
    # 校验时间戳
    if abs(interval.seconds)>TIMESTAMP_AVAI:
        return False
    # 校验用户
    users = get_users()
    if not users.has_key(username):
        return False
    password = users.get(username)
    data = {
        'X-Timestamp':int(timestamp),
        'X-Username':username
    }
    message = urllib.urlencode(data)
    vhmac = hmac.new(password)
    vhmac.update(message)
    vhexdigest = vhmac.hexdigest()
    if vhexdigest != hexdigest:
        return False
    return True

def auth(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        username = self.request.headers.get('X-Username', '')
        timestamp = self.request.headers.get('X-Timestamp', '')
        hexdigest = self.request.headers.get('X-Hexdigest', '')
        try:
            if _auth(username, timestamp, hexdigest):
                return func(self, *args, **kwargs)
            else:
                self.write_error(401)
        except:
            import traceback
            traceback.print_exc()
            self.write_error(401)

    return wrapper

if __name__ == "__main__":
    times = time.time()
    data = {
        'X-Username':'test',
        'X-Timestamp': int(times)
    }
    message = urllib.urlencode(data)
    print message, '1'
    vhamc = hmac.new('123456')
    vhamc.update(message)
    vv = vhamc.hexdigest()
    print auth('test', times, vv)
