# -*- coding:utf-8 -*-
import sys
import os
import datetime
#将工程路径添加到sys.path中
PROJECT_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.path.pardir))
path = os.path.dirname(PROJECT_PATH)
sys.path.append(path)

from sqlalchemy import Table, Column, Integer, String, Text, Enum, DateTime, Boolean, ForeignKey, Unicode
from conf.settings import engine, Base


def to_dict(self):
    d = dict()
    for c in self.__table__.columns:
        d[c.name] = getattr(self, c.name, None)
        if isinstance(getattr(self, c.name, None), datetime.datetime):
            d[c.name] = getattr(self, c.name, None).strftime('%Y-%m-%d %H:%M:%S')
    return d


Base.to_dict = to_dict


class App(Base):
    __tablename__ = 'app'

    uuid = Column(Unicode(191, _warn_on_bytestring=False), primary_key=True)
    type = Column(String(200))
    basedir = Column(String(100))
    playbooks = Column(Text)
    desc = Column(Text)

    def __repr__(self):
        return self.desc


Base.metadata.create_all(engine)
