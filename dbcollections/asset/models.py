# -*- coding:utf-8 -*-
import sys
import os
#将工程路径添加到sys.path中
PROJECT_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.path.pardir))
path = os.path.dirname(PROJECT_PATH)
sys.path.append(path)

from sqlalchemy import Table, Column, String, Text,Integer, DateTime, Boolean, Enum,ForeignKey
from sqlalchemy.orm import relationship
from conf.settings import engine, Base
from dbcollections.proxy.models import Proxy

class AssetGroup(Base):
    __tablename__ = 'asset_group'

    id = Column(Integer, primary_key=True)
    name = Column(String(30), unique=True)
    comment = Column(Text)

    def __repr__(self):
        return self.name


class IDC(Base):
    __tablename__ = 'idc'

    id = Column(Integer, primary_key=True)
    name = Column(String(30))
    brandwidth = Column(String(30))
    linkman = Column(String(30))
    phone = Column(String(30))
    address = Column(String(128))
    network = Column(String(90))
    date_added = Column(DateTime)
    operator = Column(String(30))
    comment = Column(Text)

    def __repr__(self):
        return self.name


class NetWorking(Base):
    __tablename__ = 'networking'

    id = Column(Integer, primary_key=True)
    net_name = Column(String(30))
    mac_address = Column(String(30))
    mtu = Column(String(30))
    ip_address = Column(String(32))
    static = Column(Boolean)
    subnet_mask = Column(String(90))
    per_gateway = Column(String(90))
    dns_name = Column(String(90))
    static_routes = Column(String(90))
    cnames = Column(String(90))

    def __repr__(self):
        return self.net_name


class NetWorkingGlobal(Base):
    __tablename__ = 'networking_g'

    id = Column(Integer, primary_key=True)
    hostname = Column(String(90))
    gateway = Column(String(90))
    name_servers = Column(String(90))

    def __repr__(self):
        return self.hostname


class PowerManage(Base):
    __tablename__ = 'power_manage'

    id = Column(Integer, primary_key=True)
    power_type = Column(Enum('drac5', 'idrac', 'ilo', 'ilo2', 'ilo3', 'ilo4', 'intelmodular', 'ipmilan'))
    power_address = Column(String(32))
    power_username = Column(String(30))
    power_password = Column(String(60))
    power_id = Column(Integer)

    def __repr__(self):
        return self.power_address


asset_assetgroup = Table('asset_assetgroup', Base.metadata,
                         Column('asset_id', ForeignKey('asset.id')),
                         Column('assetgroup_id', ForeignKey('asset_group.id'))
                         )

asset_networking = Table('asset_networking', Base.metadata,
                         Column('asset_id', ForeignKey('asset.id')),
                         Column('netwoking_id', ForeignKey('networking.id'))
                         )

class Asset(Base):
    __tablename__ = 'asset'

    id = Column(Integer, primary_key=True)
    ip = Column(String(32))
    other_ip = Column(String(255))
    name = Column(String(30))
    owerns = Column(String(90))
    profile = Column(String(90))
    status = Column(Enum('production','development','testing', 'acceptance'))
    kickstart = Column(String(90))
    netboot_enabled = Column(Boolean)
    port = Column(Integer)
    group = relationship('AssetGroup',
                         secondary=asset_assetgroup,
                         backref='asset')
    username = Column(String(30))
    password = Column(String(60))
    idc_id = Column(Integer, ForeignKey('idc.id'))
    idc = relationship('IDC')
    brand = Column(String(60))
    cpu = Column(String(20))
    memory = Column(String(20))
    disk = Column(String(20))
    system_type = Column(String(30))
    system_version = Column(String(10))
    system_arch = Column(String(20))
    cabinet = Column(String(30))
    position = Column(Integer)
    number = Column(String(30))
    machine_status = Column(Enum(u"已使用", u"未使用", u"报废"))
    asset_type = Column(Enum(u"物理机", u"虚拟机", u"交换机", u"路由器",u"防火墙", u"Docker", u"其他"))
    sn = Column(String(128))
    proxy_id = Column(Integer, ForeignKey('proxy.id'))
    proxy = relationship('Proxy')
    networking_g_id = Column(Integer, ForeignKey('networking_g.id'))
    networking_g = relationship('NetworkingGlobal')
    networking = relationship('NetWorking',
                              secondary=asset_networking,
                              backref='asset')
    power_manage_id = Column(Integer, ForeignKey('power_manage.id'))
    power_manage = relationship('PowerManage')
    date_added = Column(DateTime)
    is_active = Column(Boolean)
    comment = Column(Text)

    def __repr__(self):
        return self.name


class AssetRecord(Base):
    __tablename__ = 'asset_record'

    id = Column(Integer, primary_key=True)
    asset_id = Column(Integer, ForeignKey('asset.id'))
    asset = relationship('Asset')
    username = Column(String(30))
    alert_time = Column(DateTime)
    content = Column(Text)
    comment = Column(Text)

    def __repr__(self):
        return self.asset.name

Base.metadata.create_all(engine)



