#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Name    : settings.py
# @Date    : 2016-04-13 11:19
# @Author  : AutoOps
# @Link    : http://www.magicstack.cn/
# @Version :

import logging
logging.basicConfig(
                    level = logging.DEBUG,
                    format='%(filename)s[line:%(lineno)d] %(levelname)s (%(asctime)s) %(message)s',
                    datefmt='%H:%M:%S',
)

debug = True

API_HOST = 'localhost'
API_PORT = 8100

COBBLER_RPC_HOST = '172.16.30.69'
COBBLER_RPC_PORT = 80
COBBLER_RPC_PROC = 'http'
COBBLER_RPC_URL  = '{0}://{1}:{2}/cobbler_api'.format( COBBLER_RPC_PROC, COBBLER_RPC_HOST, COBBLER_RPC_PORT )
COBBLER_USERNAME = 'cobbler'
COBBLER_PASSWORD = 'cobbler'

# 用户定义，可放入到数据库中
USERS = {
    'test':'123456'
}

# timestamp available
TIMESTAMP_AVAI = 15*60 # seconds