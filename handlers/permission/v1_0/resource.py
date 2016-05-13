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
        role = session.query(PermRole).filter_by(id=int(role_id)).first()
        sudo_list = [dict(id=item.id, name=item.name, date_added=item.date_added, commands=item.commands, comment=item.comment)
                     for item in role.sudo]

        role_info = dict(id=role.id, name=role.name, password=role.password, key_path=role.key_path,
                         date_added=role.date_added,
                         comment=role.comment,
                         sudo=sudo_list
        )
        info['role'] = role_info
        info['assets'] = session.query(Asset).all()
        info['asset_groups'] = session.query(AssetGroup).all()
    except Exception as e:
        logger.error(e)
    finally:
        session.close()
    return info



