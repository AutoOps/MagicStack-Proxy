# -*- coding:utf-8 -*-
import sys
import os
#将工程路径添加到sys.path中
PROJECT_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.path.pardir))
path = os.path.dirname(PROJECT_PATH)
sys.path.append(path)

from sqlalchemy import Table, Column, Integer, String, Text, Enum, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from conf.settings import engine, Base


class Proxy(Base):
    __tablename__ = 'proxy'

    id = Column(Integer, primary_key=True)
    proxy_name = Column(String(60), unique=True)
    username = Column(String(60))
    password = Column(String(90))
    url = Column(String(90))
    create_time = Column(DateTime)
    comment = Column(Text)

    def __repr__(self):
        return self.proxy_name

Base.metadata.create_all(engine)
