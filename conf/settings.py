#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Name    : settings.py
# @Date    : 2016-04-13 11:19
# @Author  : AutoOps
# @Link    : http://www.magicstack.cn/
# @Version :

import logging
import os
import ConfigParser

from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base

logging.basicConfig(
                    level = logging.DEBUG,
                    format='%(filename)s[line:%(lineno)d] %(levelname)s (%(asctime)s) %(message)s',
                    datefmt='%H:%M:%S',
)

config = ConfigParser.ConfigParser()

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

UPLOAD_PATH = os.path.join(os.path.dirname(__file__),'..', 'upload_files')

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
LOG_DIR = os.path.join(BASE_DIR, 'logs')
KEY_DIR = os.path.join(BASE_DIR, 'keys')

# log
KEY = ""
# SSH_KEY_DIR = os.path.join(BASE_DIR, 'keys/role_keys')
# KEY = config.get('base', 'key')
# URL = config.get('base', 'url')
# LOG_LEVEL = config.get('base', 'log')
# IP = config.get('base', 'ip')
# PORT = config.get('base', 'port')

#database
engine = create_engine('sqlite:///{0}/magicstack.db'.format(BASE_DIR))
Base = declarative_base()
metadata = MetaData(engine)

