#!/usr/bin/python
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

import sys
import os
import datetime
#将工程路径添加到sys.path中
PROJECT_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.path.pardir))
path = os.path.dirname(PROJECT_PATH)
sys.path.append(path)

from sqlalchemy import Column, Integer, String, Text, Boolean
from conf.settings import engine, Base


def to_dict(self):
    d = dict()
    for c in self.__table__.columns:
        d[c.name] = getattr(self, c.name, None)
        if isinstance(getattr(self, c.name, None), datetime.datetime):
            d[c.name] = getattr(self, c.name, None).strftime('%Y-%m-%d %H:%M:%S')
    return d


Base.to_dict = to_dict


class FileDownload(Base):
    __tablename__ = 'file'

    id = Column(Integer, primary_key=True)
    link = Column(Text)
    status = Column(Boolean, unique=False, default=True)

    def __repr__(self):
        return self.status


Base.metadata.create_all(engine)
