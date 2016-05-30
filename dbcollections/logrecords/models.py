#!/usr/bin/env python
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

__author__ = 'mengx'

import sys
import os
import datetime

PROJECT_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.path.pardir))
path = os.path.dirname(PROJECT_PATH)
sys.path.append(path)

from sqlalchemy import Table, Column, Integer, String, Text, Enum, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
import time
from conf.settings import engine, Base


def to_dict(self):
    d = dict()
    for c in self.__table__.columns:
        d[c.name] = getattr(self, c.name, None)
        if isinstance(getattr(self, c.name, None), datetime.datetime):
            d[c.name] = getattr(self, c.name, None).strftime('%Y-%m-%d %H:%M:%S')
    return d


Base.to_dict = to_dict


class TermLog(Base):
    __tablename__ = 'term_log'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    logpath = Column(Text)
    filename = Column(String(40))
    logpwd = Column(Text)
    log = Column(Text)
    history = Column(Text)
    timestamp = Column(Integer, default=int(time.time()))
    datetimestamp = Column(DateTime)


class Log(Base):
    __tablename__ = 'log'

    id = Column(Integer, primary_key=True)
    user_id = Column(String(30))
    node_id = Column(String(200))
    remote_ip = Column(String(100))
    login_type = Column(String(100))
    log_path = Column(String(100))
    start_time = Column(DateTime)
    pid = Column(Integer)
    is_finished = Column(Boolean)
    end_time = Column(DateTime)
    filename = Column(String(40))

    def __repr__(self):
        return self.log_path


class TtyLog(Base):
    __tablename__ = 'tty_log'

    id = Column(Integer, primary_key=True)
    log_id = Column(Integer, ForeignKey('log.id'))
    datetime = Column(DateTime, default=datetime.datetime.now)
    cmd = Column(Text)


Base.metadata.create_all(engine)