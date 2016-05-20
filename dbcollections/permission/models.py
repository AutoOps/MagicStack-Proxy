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
from dbcollections.account.models import User, UserGroup
from dbcollections.asset.models import Asset, AssetGroup


permrole_sudo = Table('permrole_sudo', Base.metadata,
    Column('permrole_id', Integer, ForeignKey('perm_role.id')),
    Column('permsudo_id', Integer, ForeignKey('perm_sudo.id'))
)


class PermRole(Base):
    __tablename__ = 'perm_role'

    id = Column(Integer, primary_key=True)
    name = Column(String(100))
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

    id = Column(Integer, primary_key=True)
    name = Column(String(30))
    date_added = Column(DateTime)
    commands = Column(Text)
    comment = Column(Text)

    def __repr__(self):
        return self.name


permrule_asset = Table('permrule_asset', Base.metadata,
    Column('permrule_id', Integer, ForeignKey('perm_rule.id')),
    Column('asset_id', Integer, ForeignKey('asset.id'))
)

permrule_asset_group = Table('permrule_asset_group', Base.metadata,
    Column('permrule_id', Integer, ForeignKey('perm_rule.id')),
    Column('assetgroup_id', Integer, ForeignKey('asset_group.id'))
)

permrule_user = Table('permrule_user', Base.metadata,
    Column('permrule_id', Integer, ForeignKey('perm_rule.id')),
    Column('user_id', Integer, ForeignKey('user.id'))
)

permrule_user_group = Table('permrule_user_group', Base.metadata,
    Column('permrule_id', Integer, ForeignKey('perm_rule.id')),
    Column('usergroup_id', Integer, ForeignKey('user_group.id'))

)


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