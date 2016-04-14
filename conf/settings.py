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

RPC_HOST = '172.16.20.200'
RPC_PORT = 80
RPC_PROC = 'http'
RPC_URL  = '{0}://{1}:{2}/cobbler_api'.format( RPC_PROC, RPC_HOST, RPC_PORT )

