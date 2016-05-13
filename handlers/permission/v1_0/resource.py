# -*- coding:utf-8 -*-

from sqlalchemy.orm import sessionmaker
from conf.settings import engine
from dbcollections.permission.models import PermRole
from dbcollections.asset.models import Asset, AssetGroup
import logging

logger = logging.getLogger()


def get_perm_info(role_id):
    info = {}

    #建立数据库连接
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        info['role'] = session.query(PermRole).filter_by(id=int(role_id)).first()
        info['assets'] = session.query(Asset).all()
        info['asset_groups'] = session.query(AssetGroup).all()
    except Exception as e:
        logger.error(e)
    finally:
        session.close()
    return info



