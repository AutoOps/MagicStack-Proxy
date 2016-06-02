# -*- coding:utf-8 -*-
import sys
import os
import datetime
#将工程路径添加到sys.path中
PROJECT_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.path.pardir))
path = os.path.dirname(PROJECT_PATH)
sys.path.append(path)

from sqlalchemy import Table, Column, Integer, String, Text, Enum, DateTime, Boolean, ForeignKey, Unicode
from sqlalchemy.orm import relationship
from conf.settings import engine, Base


def to_dict(self):
    d = dict()
    for c in self.__table__.columns:
        d[c.name] = getattr(self, c.name, None)
        if isinstance(getattr(self, c.name, None), datetime.datetime):
            d[c.name] = getattr(self, c.name, None).strftime('%Y-%m-%d %H:%M:%S')
    return d


Base.to_dict = to_dict


class Task(Base):
    __tablename__ = 'task'

    id = Column(Integer, primary_key=True)
    task_name = Column(String(200))
    username = Column(String(100))
    status = Column(String(100))
    url = Column(String(200))
    result = Column(Text)

    def __repr__(self):
        return self.task_name


class Apscheduler_Task(Base):
    __tablename__ = 'apscheduler_task'

    id = Column(Integer, primary_key=True)
    job_id = Unicode(191, _warn_on_bytestring=False)
    start_time = Column(DateTime, default=datetime.datetime.now)
    end_time = Column(DateTime)
    is_finished = Column(Boolean, default=False)
    status = Column(String(100), default=0 ) # 0 初始化 1 成功 2 失败
    result = Column(Text)


Base.metadata.create_all(engine)
