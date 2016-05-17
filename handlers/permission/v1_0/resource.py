# -*- coding:utf-8 -*-
import logging
import shutil
import datetime
from sqlalchemy.orm import sessionmaker
from conf.settings import engine, KEY_DIR
from dbcollections.permission.models import *
from dbcollections.asset.models import Asset, AssetGroup
from paramiko import SSHException
from paramiko.rsakey import RSAKey
from uuid import uuid4

logger = logging.getLogger()


class ServerError(Exception):
    """
    self define exception
    自定义异常
    """
    pass


def chown(path, user, group=''):
    if not group:
        group = user
    try:
        uid = pwd.getpwnam(user).pw_uid
        gid = pwd.getpwnam(group).pw_gid
        os.chown(path, uid, gid)
    except KeyError:
        pass


def mkdir(dir_name, username='', mode=0755):
    """
    insure the dir exist and mode ok
    目录存在，如果不存在就建立，并且权限正确
    """
    if not os.path.isdir(dir_name):
        os.makedirs(dir_name)
        os.chmod(dir_name, mode)
    if username:
        chown(dir_name, username)


def gen_keys(key="", key_path_dir=""):
    """
    在KEY_DIR下创建一个 uuid命名的目录，
    并且在该目录下 生产一对秘钥
    :return: 返回目录名(uuid)
    """
    key_basename = "key-" + uuid4().hex
    if not key_path_dir:
        key_path_dir = os.path.join(KEY_DIR, 'role_key', key_basename)
    private_key = os.path.join(key_path_dir, 'id_rsa')
    public_key = os.path.join(key_path_dir, 'id_rsa.pub')
    mkdir(key_path_dir, mode=0755)
    if not key:
        key = RSAKey.generate(2048)
        key.write_private_key_file(private_key)
    else:
        key_file = os.path.join(key_path_dir, 'id_rsa')
        with open(key_file, 'w') as f:
            f.write(key)
            f.close()
        with open(key_file) as f:
            try:
                key = RSAKey.from_private_key(f)
            except SSHException, e:
                shutil.rmtree(key_path_dir, ignore_errors=True)
                raise SSHException(e)
    os.chmod(private_key, 0644)

    with open(public_key, 'w') as content_file:
        for data in [key.get_name(),
                     " ",
                     key.get_base64(),
                     " %s@%s" % ("magicstack", os.uname()[1])]:
            content_file.write(data)
    return key_path_dir


def get_perm_info(role_id):
    info = {}
    #建立数据库连接
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        role = session.query(PermRole).filter_by(id=int(role_id)).first()
        sudo_list = [dict(id=item.id, name=item.name, date_added=item.date_added.strftime('%Y-%m-%d  %H:%M:%S'),
                     commands=item.commands, comment=item.comment) for item in role.sudo]

        role_info = dict(id=role.id, name=role.name, password=role.password, key_path=role.key_path,
                         date_added=role.date_added,
                         comment=role.comment,
                         sudo=sudo_list)
        info['role'] = role_info
        info['assets'] = session.query(Asset).all()
        info['asset_groups'] = session.query(AssetGroup).all()
    except Exception as e:
        logger.error(e)
    finally:
        session.close()
    return info


def permrole_to_dict(role):
    """
    把role对象装换成dict
    """
    sudo_list = [dict(id=item.id, name=item.name, date_added=item.date_added.strftime('%Y-%m-%d  %H:%M:%S'),
                      commands=item.commands, comment=item.comment) for item in role.sudo]
    res = dict(id=role.id, name=role.name, password=role.password, key_path=role.key_path,
               date_added=role.date_added.strftime('%Y-%m-%d  %H:%M:%S'),
               comment=role.comment,
               sudo=sudo_list)
    return res


def permrule_to_dict(rule):
    """
    把rule对象装换成dict
    """
    assets = rule.asset
    asset_groups = rule.asset_group
    users = rule.user
    user_groups = rule.user_group
    role_list = []
    for item in rule.role:
        r = permrole_to_dict(item)
        role_list.append(r)
    res = dict(id=rule.id, date_added=rule.date_added.strftime('%Y-%m-%d  %H:%M:%S'), name=rule.name, comment=rule.comment,
               asset=assets, asset_group=asset_groups, user=users, user_group=user_groups, role=role_list)
    return res


def permpush_to_dict(push):
    """
    push对象装换成dict
    """
    asset_list = push.asset
    role_list = []
    for item in push.role:
        r = permrole_to_dict(item)
        role_list.append(r)
    res = dict(id=push.id, asset=asset_list, role=role_list, success=push.success,
               result=push.result, is_public_key=push.is_public_key,
               is_password=push.is_password, date_added=push.date_added.strftime('%Y-%m-%d  %H:%M:%S'))
    return res


def get_all_objects(name):
    """
    获取所有的objects
    """
    res = []
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        if name == 'PermRole':
            roles = session.query(PermRole).all()
            for role in roles:
                r = permrole_to_dict(role)
                res.append(r)
        elif name == 'PermSudo':
            sudos = session.query(PermSudo).all()
            res = [dict(id=item.id, name=item.name, date_added=item.date_added.strftime('%Y-%m-%d %H:%M:%S'), commands=item.commands,
                        comment=item.comment) for item in sudos]
        elif name == 'PermRule':
            rules = session.query(PermRule).all()
            for rule in rules:
                r = permrule_to_dict(rule)
                res.append(r)
        elif name == 'PermPush':
            push_records = session.query(PermPush).all()
            for record in push_records:
                r = permpush_to_dict(record)
                res.append(r)
    except Exception as e:
        logger.error(e)
    finally:
        session.close()
    return res


def get_one_object(name, obj_id):
    """
    获取对应id的object
    """
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        if name == 'PermRole':
            role = session.query(PermRole).get(int(obj_id))
            res = permrole_to_dict(role)
        elif name == 'PermSudo':
            sudo = session.query(PermSudo).get(int(obj_id))
            res = dict(id=sudo.id, name=sudo.name, date_added=sudo.date_added.strftime('%Y-%m-%d %H:%M:%S'), commands=sudo.commands,
                       comment=sudo.comment)
        elif name == 'PermRule':
            rule = session.query(PermRule).get(int(obj_id))
            res = permrule_to_dict(rule)
        elif name == 'PermPush':
            record = session.query(PermPush).get(int(obj_id))
            res = permpush_to_dict(record)
    except Exception as e:
        logger.error(e)
    finally:
        session.close()
    return res


def save_permrole(session, param):
    now = datetime.datetime.now()
    try:
        role = PermRole(name=param['name'], password=param['password'], comment=param['comment'], date_added=now)
        logger.info('save_permrole:%s'%role)
        key_content = param['key_content']
        if key_content:
            try:
                key_path = gen_keys(key=key_content)
            except SSHException, e:
                raise ServerError(e)
        else:
            key_path = gen_keys()
        role.key_path = key_path
        sudo_ids = param['sudo_ids']
        sudo_list = [session.query(PermSudo).get(id=int(item)) for item in sudo_ids]
        role.sudo = sudo_list
        session.add(role)
        session.commit()
    except Exception as e:
        logger.error(e)


def save_permsudo(session, param):
    now = datetime.datetime.now()
    try:
        sudo = PermSudo(**param)
        sudo.date_added = now
        session.add(sudo)
        session.commit()
    except Exception as e:
        logger.error(e)


def save_object(obj_name, param):
    """
    保存数据
    """
    msg = 'success'
    Session = sessionmaker()
    Session.configure(bind=engine)
    session = Session()
    try:
        if obj_name == "PermRole":
            save_permrole(session, param)
        elif obj_name == "PermSudo":
            save_permsudo(session, param)
    except Exception as e:
        logger.error(e)
        msg = 'error'
    finally:
        session.close()
    return msg


def update_permrole(session, param):
    pass


def update_permsudo(session, obj_id, param):
    try:
        session.query(PermSudo).get(int(obj_id)).update(**param)
        session.commit()
    except Exception as e:
        logger.error(e)


def update_object(obj_name, obj_id, param):
    """
    更新数据
    """
    msg = 'success'
    Session = sessionmaker()
    Session.configure(bind=engine)
    session = Session()
    try:
        if obj_name == "PermRole":
            update_permrole(session, obj_id, param)
        elif obj_name == "PermSudo":
            update_permsudo(session, obj_id, param)
    except Exception as e:
        logger.error(e)
        msg = 'error'
    finally:
        session.close()
    return msg
