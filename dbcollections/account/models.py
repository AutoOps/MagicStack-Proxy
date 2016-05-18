# -*- coding:utf-8 -*-
import sys
import os
#将工程路径添加到sys.path中
PROJECT_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.path.pardir))
path = os.path.dirname(PROJECT_PATH)
sys.path.append(path)

from sqlalchemy import Table, Column, Integer, String, Text, DateTime, Boolean,Enum, ForeignKey
from sqlalchemy.orm import relationship
from conf.settings import engine, Base


class AdminGroup(Base):
    __tablename__ = 'admin_group'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship('User')
    group_id = Column(Integer, ForeignKey('user_group.id'))
    group = relationship('UserGroup')

    def __repr__(self):
        return "{0}  {1}".format(self.user.username, self.group.name)


user_usergroup = Table('user_usergroup', Base.metadata,
    Column('user_id', Integer, ForeignKey('user.id')),
    Column('usergroup_id', Integer, ForeignKey('user_group.id'))
)


class UserGroup(Base):
    __tablename__ = 'user_group'

    id = Column(Integer, primary_key=True)
    name = Column(String(30), unique=True)
    comment = Column(String(90))

    def __repr__(self):
        return self.name


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    username = Column(String(30), unique=True)
    password = Column(String(128))
    # last_login = Column(DateTime)
    # is_superuser = Column(Boolean)
    email = Column(String(30))
    # is_staff = Column(Boolean)
    is_active = Column(Boolean)
    date_joined = Column(DateTime)
    uuid = Column(String(90))
    role = Column(Enum('SU', 'GA', 'CU'))
    ssh_key_pwd = Column(Text)
    group = relationship('UserGroup',
                         secondary=user_usergroup,
                         backref='user')

    def __repr__(self):
        return self.username


if __name__ == '__main__':
    Base.metadata.create_all(engine)