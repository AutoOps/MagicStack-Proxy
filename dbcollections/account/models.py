# -*- coding:utf-8 -*-
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
    last_login = Column(DateTime)
    is_superuser = Column(Boolean)
    email = Column(String(30))
    is_staff = Column(Boolean)
    is_active = Column(Boolean)
    date_joined = Column(DateTime)
    name = Column(String(30))
    uuid = Column(String(90))
    role = Column(Enum('SU', 'GA', 'CU'))
    ssh_key_pwd = Column(Text)
    group = relationship('UserGroup',
                         secondary=user_usergroup,
                         backref='user')

    def __repr__(self):
        return self.username


Base.metadata.create_all(engine)