# -*- coding:utf-8 -*-

import sys
import os
#将工程路径添加到sys.path中
PROJECT_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.path.pardir))
path = os.path.dirname(PROJECT_PATH)
sys.path.append(path)

from sqlalchemy import Table, Column, Integer, String, Text, Enum, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
import time
from conf.settings import engine, Base
from dbcollections.account.models import User


class Log(Base):
    __tablename__ = 'log'

    id = Column(Integer, primary_key=True)
    user = Column(String(30))
    host = Column(String(200))
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
    log = relationship('Log')
    datetime = Column(DateTime)
    cmd = Column(Text)


class ExecLog(Base):
    __tablename__ = 'exec_log'

    id = Column(Integer, primary_key=True)
    user = Column(String(100))
    host = Column(String(100))
    cmd = Column(Text)
    remote_ip = Column(String(100))
    result = Column(Text)
    datetime = Column(DateTime)


class FileLog(Base):
    __tablename__ = 'file_log'

    id = Column(Integer, primary_key=True)
    user = Column(String(30))
    host = Column(Text)
    filename = Column(Text)
    type = Column(String(20))
    remote_ip = Column(String(100))
    result = Column(Text)
    datetime = Column(DateTime)


termlog_user = Table('termlog_user', Base.metadata,
    Column('termlog_id', ForeignKey('term_log.id')),
    Column('user_id', ForeignKey('user.id'))
)


class TermLog(Base):
    __tablename__ = 'term_log'

    id = Column(Integer, primary_key=True)
    user = relationship('User',
                        secondary=termlog_user,
                        backref='termlog')
    logPath = Column(Text)
    filename = Column(String(40))
    logPWD = Column(Text)
    nick = Column(Text)
    log = Column(Text)
    history = Column(Text)
    timestamp = Column(Integer, default=int(time.time()))
    datetimestamp = Column(DateTime)


class UserOperatorRecord(Base):
    __tablename__ = 'user_operator_record'

    id = Column(Integer, primary_key=True)
    username = Column(String(30))
    operator = Column(String(30))
    content = Column(Text)
    op_time = Column(DateTime)
    result = Column(String(10))

Base.metadata.create_all(engine)