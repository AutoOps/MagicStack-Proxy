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


class Task(Base):
    __tablename__ = 'task'

    id = Column(Integer, primary_key=True)
    task_name = Column(String(50))
    username = Column(String(50))
    status = Column(String(20))
    url = Column(String(60))
    content = Column(Text)
    start_time = Column(DateTime)

    def __repr__(self):
        return self.task_name


Base.metadata.create_all(engine)
