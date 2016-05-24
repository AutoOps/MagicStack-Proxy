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

PROJECT_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.path.pardir))
path = os.path.dirname(PROJECT_PATH)
sys.path.append(path)

from sqlalchemy import Column, Integer, String, Text, DateTime, Enum
import time
from conf.settings import engine, Base


class Node(Base):
    __tablename__ = 'node'

    id = Column(String(200), primary_key=True, doc=u'ID，由业务系统上送')
    ip = Column(String(32), doc=u'节点管理地址')
    port = Column(Integer, doc=u'节点ssh管理端口', default=22)

Base.metadata.create_all(engine)