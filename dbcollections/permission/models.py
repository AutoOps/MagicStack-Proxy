# -*- coding:utf-8 -*-
import sys
import os
#将工程路径添加到sys.path中
PROJECT_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.path.pardir))
path = os.path.dirname(PROJECT_PATH)
sys.path.append(path)

from sqlalchemy import Table, Column, Integer, String, Text, DateTime,Boolean, ForeignKey
from sqlalchemy.orm import relationship
from conf.settings import engine, Base

permrole_sudo = Table('permrole_sudo', Base.metadata,
    Column('permrole_id', Integer, ForeignKey('perm_role.id')),
    Column('permsudo_id', Integer, ForeignKey('perm_sudo.id'))
)


class PermRole(Base):
    __tablename__ = 'perm_role'

    id = Column(Integer)
    uuid_id = Column(String(200), primary_key=True)
    name = Column(String(100), unique=True)
    password = Column(String(200))
    key_path = Column(String(200))
    date_added = Column(DateTime)
    comment = Column(Text)
    sudo = relationship("PermSudo",
                        secondary=permrole_sudo,
                        backref="perm_role")

    def __repr__(self):
        return self.name


class PermSudo(Base):
    __tablename__ = 'perm_sudo'

    id = Column(Integer)
    uuid_id = Column(String(200), primary_key=True)
    name = Column(String(30), unique=True)
    date_added = Column(DateTime)
    commands = Column(Text)
    comment = Column(Text)

    def __repr__(self):
        return self.name


class PermPush(Base):
    __tablename__ = 'perm_push'

    id = Column(Integer, primary_key=True)
    assets = Column(Text)
    role_name = Column(String(200))
    is_public_key = Column(Boolean)
    is_password = Column(Boolean)
    success_assets = Column(Text)
    result = Column(Text)
    date_added = Column(DateTime)

Base.metadata.create_all(engine)