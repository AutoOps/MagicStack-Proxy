# -*- coding:utf-8 -*-
import logging
import crypt
import pwd
import hashlib
import shutil
import datetime
import random
from binascii import b2a_hex, a2b_hex
from Crypto.Cipher import AES
from sqlalchemy.orm import sessionmaker
from conf.settings import engine, KEY_DIR,LOG_DIR
from dbcollections.permission.models import *
from paramiko import SSHException
from paramiko.rsakey import RSAKey
from uuid import uuid4
import os
import json

handler = logging.handlers.RotatingFileHandler(os.sep.join([LOG_DIR, 'permission.log']), maxBytes=1024 * 1024,
                                               backupCount=5)
fmt = '%(asctime)s - %(filename)s:%(lineno)s - %(name)s - %(message)s'
formatter = logging.Formatter(fmt)   # 实例化formatter
handler.setFormatter(formatter)      # 为handler添加formatter
logger = logging.getLogger('permission')
logger.addHandler(handler)

KEY = '941enj9neshd1wes'


class ServerError(Exception):
    """
    self define exception
    自定义异常
    """
    pass


class PyCrypt(object):
    """
    This class used to encrypt and decrypt password.
    加密类
    """

    def __init__(self, key):
        self.key = key
        self.mode = AES.MODE_CBC

    @staticmethod
    def gen_rand_pass(length=16, especial=False):
        """
        random password
        随机生成密码
        """
        salt_key = '1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_'
        symbol = '!@$%^&*()_'
        salt_list = []
        if especial:
            for i in range(length - 4):
                salt_list.append(random.choice(salt_key))
            for i in range(4):
                salt_list.append(random.choice(symbol))
        else:
            for i in range(length):
                salt_list.append(random.choice(salt_key))
        salt = ''.join(salt_list)
        return salt

    @staticmethod
    def md5_crypt(string):
        """
        md5 encrypt method
        md5非对称加密方法
        """
        return hashlib.new("md5", string).hexdigest()

    @staticmethod
    def gen_sha512(salt, password):
        """
        generate sha512 format password
        生成sha512加密密码
        """
        return crypt.crypt(password, '$6$%s$' % salt)

    def encrypt(self, passwd=None, length=32):
        """
        encrypt gen password
        对称加密之加密生成密码
        """
        if not passwd:
            passwd = self.gen_rand_pass()

        cryptor = AES.new(self.key, self.mode, b'8122ca7d906ad5e1')
        try:
            count = len(passwd)
        except TypeError:
            raise ServerError('Encrypt password error, TYpe error.')

        add = (length - (count % length))
        passwd += ('\0' * add)
        cipher_text = cryptor.encrypt(passwd)
        return b2a_hex(cipher_text)

    def decrypt(self, text):
        """
        decrypt pass base the same key
        对称加密之解密，同一个加密随机数
        """
        cryptor = AES.new(self.key, self.mode, b'8122ca7d906ad5e1')
        try:
            plain_text = cryptor.decrypt(a2b_hex(text))
        except TypeError:
            raise ServerError('Decrypt password error, TYpe error.')
        return plain_text.rstrip('\0')

CRYPTOR = PyCrypt(KEY)

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
    key_contents = json.loads(key)
    key_basename = "key-" + uuid4().hex
    if not key_path_dir:
        key_path_dir = os.path.join(KEY_DIR, 'role_key', key_basename)
    private_key = os.path.join(key_path_dir, 'id_rsa')
    public_key = os.path.join(key_path_dir, 'id_rsa.pub')
    mkdir(key_path_dir, mode=0755)
    private_key_data = key_contents.get('private_key')
    public_key_data = key_contents.get('public_key')
    with open(private_key, 'w') as f:
        f.write(private_key_data)

    with open(public_key, 'w') as p:
        p.write(public_key_data)

    os.chmod(private_key, 0644)
    return key_path_dir


def permrole_to_dict(role):
    """
    把role对象装换成dict
    """
    sudo_list = [dict(id=item.id, name=item.name, date_added=item.date_added.strftime('%Y-%m-%d  %H:%M:%S'),
                      commands=item.commands, comment=item.comment) for item in role.sudo]
    res = dict(id=role.id, name=role.name, password=role.password, key_path=role.key_path,
               date_added=role.date_added.strftime('%Y-%m-%d  %H:%M:%S'),
               comment=role.comment, sudo=sudo_list, system_groups=role.system_groups, uuid_id=role.uuid_id)
    return res


def permrule_to_dict(rule):
    """
    把rule对象装换成dict
    """
    assets = {}
    asset_groups = {}
    users = {}
    user_groups = {}
    role_list = []
    for item in rule.role:
        r = permrole_to_dict(item)
        role_list.append(r)
    res = dict(id=rule.id, date_added=rule.date_added.strftime('%Y-%m-%d  %H:%M:%S'), name=rule.name, comment=rule.comment,
               asset=assets, asset_group=asset_groups, user=users, user_group=user_groups, role=role_list)
    return res


def permpush_to_dict(push):
    """
    push对象转换成dict
    """
    # asset_list = push.asset
    asset_list = {}
    role = push.role
    role = permrole_to_dict(role)
    res = dict(id=push.id, asset=asset_list, role=role, success=push.success,
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


def get_one_object(name, obj_uuid):
    """
    获取对应id的object
    """
    res = {}
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        if name == 'PermRole':
            role = session.query(PermRole).get(obj_uuid)
            res = permrole_to_dict(role)
        elif name == 'PermSudo':
            sudo = session.query(PermSudo).get(obj_uuid)
            res = dict(id=sudo.id, name=sudo.name, date_added=sudo.date_added.strftime('%Y-%m-%d %H:%M:%S'), commands=sudo.commands,
                       comment=sudo.comment)
        elif name == 'PermPush':
            record = session.query(PermPush).get(int(obj_uuid))
            res = permpush_to_dict(record)
    except Exception as e:
        logger.error(e)
    finally:
        session.close()
    logger.info("get_one_object:%s  %s"%(name, res))
    return res


def save_permrole(session, param):
    """
       保存 PermRole
    """
    now = datetime.datetime.now()
    msg_info = 'success'
    try:
        if not param['name']:
            raise ServerError(u'名字不能为空')

        role = PermRole(name=param['name'], password=param['password'], comment=param['comment'],
                        date_added=now, uuid_id=param['uuid_id'], id=param['id'], system_groups=param['sys_groups'])
        key_content = param['key_content']
        if not key_content:
            raise ValueError(u'系统用户的秘钥为空,请重新生成公钥和私钥')

        try:
            key_path = gen_keys(key=key_content)
        except SSHException, e:
            raise ServerError(e)

        role.key_path = key_path
        sudo_uuids = param['sudo_uuids']
        sudo_list = [session.query(PermSudo).filter_by(uuid_id=item).first() for item in sudo_uuids]
        logger.info('sudo_list:%s'%sudo_list)
        role.sudo = sudo_list
        session.add(role)
        session.commit()
    except Exception as e:
        msg_info = 'error'
        logger.error(e)
    logger.info('svae perm_role:%s'%msg_info)
    return msg_info


def save_permsudo(session, param):
    """
       保存 sudo
    """
    msg_info = 'success'
    now = datetime.datetime.now()
    try:
        if not param['name']:
            raise ServerError(u'名字不能为空')

        sudo = PermSudo(**param)
        sudo.date_added = now
        session.add(sudo)
        session.commit()
    except Exception as e:
        msg_info = 'error'
        logger.error(e)
    logger.info('save perm_sudo:%s'%msg_info)
    return msg_info


def save_object(obj_name, param):
    """
    保存数据
    """
    msg = ' '
    Session = sessionmaker()
    Session.configure(bind=engine)
    session = Session()
    try:
        if obj_name == "PermRole":
            msg = save_permrole(session, param)
        elif obj_name == "PermSudo":
            msg = save_permsudo(session, param)
    except Exception as e:
        logger.error(e)
        msg = 'error'
    finally:
        session.close()
    return msg


def update_permrole(session,obj_uuid, param):
    msg_info = 'success'
    try:
        if not param['name']:
            raise ServerError(u'名字不能为空')
        logger.info("uuid_id:%s"%obj_uuid)
        role = session.query(PermRole).get(obj_uuid)
        key_content = param['key_content']
        # 如果key_content不为空,就更新秘钥对;如果为空，就保持不变
        if key_content:
            try:
                key_path = gen_keys(key_content, role.key_path)
                role.key_path = key_path
            except SSHException:
                raise ServerError('输入的密钥不合法')
            logger.info('Recreate role key: %s' % role.key_path)
        sudo_list = [session.query(PermSudo).get(item) for item in param['sudo_uuids']]
        logger.info("[permrole update] sudo_list:%s"%sudo_list)
        role.name = param['name']
        if param['password']:
            encrypt_pass = CRYPTOR.encrypt(param['password'])
            role.password = encrypt_pass
        role.system_groups = param['sys_groups']
        role.sudo = sudo_list
        role.comment = param['comment']
        session.add(role)
        session.commit()
    except Exception as e:
        msg_info = 'error'
        logger.error(e)
    return msg_info


def update_permsudo(session, obj_uuid, param):
    msg_info = 'success'
    try:
        session.query(PermSudo).filter_by(uuid_id=obj_uuid).update(param)
        session.commit()
    except Exception as e:
        msg_info = 'error'
        logger.error(e)
    return msg_info


def update_object(obj_name, obj_uuid, param):
    """
    更新数据
    """
    msg = ''
    Session = sessionmaker()
    Session.configure(bind=engine)
    session = Session()
    try:
        if obj_name == "PermRole":
            msg = update_permrole(session, obj_uuid, param)
            logger.info("update permrole:%s"%msg)
        elif obj_name == "PermSudo":
            msg = update_permsudo(session, obj_uuid, param)
            logger.info("update permsudo:%s"%msg)
    except Exception as e:
        logger.error(e)
        msg = 'error'
    finally:
        session.close()
    return msg


def delete_permrole(session, obj_uuid):
    msg_info = 'success'
    try:
        role = session.query(PermRole).get(obj_uuid)
        role_key = role.key_path
        #删除存储的秘钥，以及目录
        try:
            key_files = os.listdir(role_key)
            for key_file in key_files:
                os.remove(os.path.join(role_key, key_file))
            os.rmdir(role_key)
        except OSError, e:
            logger.warning(u"Delete Role: delete key error, %s" % e)
        logger.info(u"delete role %s - delete role key directory: %s" % (role.name, role_key))
        session.delete(role)
        session.commit()
    except Exception as e:
        msg_info = 'error'
        logger.error(e)
    return msg_info


def delete_permsudo(session, obj_uuid):
    msg_info = 'success'
    try:
        sudo = session.query(PermSudo).get(obj_uuid)
        session.delete(sudo)
        session.commit()
    except Exception as e:
        msg_info = 'error'
        logger.error(e)
    return msg_info


def delete_object(obj_name, obj_uuid):
    """
    删除数据
    """
    msg = ''
    Session = sessionmaker()
    Session.configure(bind=engine)
    session = Session()
    try:
        if obj_name == "PermRole":
            msg = delete_permrole(session, obj_uuid)
            logger.info('delete permrole:%s'%msg)
        elif obj_name == "PermSudo":
            msg = delete_permsudo(session, obj_uuid)
            logger.info('delete permsudo:%s'%msg)
    except Exception as e:
        logger.error(e)
        msg = 'error'
    finally:
        session.close()
    return msg
