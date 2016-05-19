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
from conf.settings import engine, KEY_DIR
from dbcollections.permission.models import *
from dbcollections.asset.models import Asset, AssetGroup
from paramiko import SSHException
from paramiko.rsakey import RSAKey
from uuid import uuid4

KEY = '941enj9neshd1wes'
logger = logging.getLogger()


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
    # push_list = []
    # for item in role.perm_push:
    #     asset_list = {}
    #     push_list.append(dict(id=item.id, asset=asset_list, success=item.success,
    #            result=item.result, is_public_key=item.is_public_key,
    #            is_password=item.is_password, date_added=item.date_added.strftime('%Y-%m-%d  %H:%M:%S')))
    res = dict(id=role.id, name=role.name, password=role.password, key_path=role.key_path,
               date_added=role.date_added.strftime('%Y-%m-%d  %H:%M:%S'),
               comment=role.comment, sudo=sudo_list)
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
    res = {}
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
        sudo_list = [session.query(PermSudo).get(int(item)) for item in sudo_ids]
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


def update_permrole(session,obj_id, param):
    try:
        role = session.query(PermRole).filter_by(id=int(obj_id))
        key_content = param['key_content']
        # 生成随机密码，生成秘钥对
        if key_content:
            try:
                key_path = gen_keys(key=key_content, key_path_dir=role.key_path)
            except SSHException:
                raise ServerError('输入的密钥不合法')
            logger.info('Recreate role key: %s' % role.key_path)
        sudo_list = []
        for item in param['sudo_ids']:
            sudo_list.append(session.query(PermSudo).get(int(item)))
        role.name = param['name']
        if param['password']:
            encrypt_pass = CRYPTOR.encrypt(param['password'])
            role.password = param['password']
        if key_content:
            role.key_path = key_path
        role.sudo = sudo_list
        session.commit()
    except Exception as e:
        logger.error(e)


def update_permsudo(session, obj_id, param):
    try:
        session.query(PermSudo).filter_by(id=int(obj_id)).update(param)
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


def delete_permrole(session, obj_id):
    try:
        role = session.query(PermRole).get(obj_id)
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
        logger.error(e)


def delete_permsudo(session, obj_id):
    try:
        sudo = session.query(PermSudo).get(obj_id)
        session.delete(sudo)
        session.commit()
    except Exception as e:
          logger.error(e)


def delete_permrule(session, obj_id):
    try:
        rule = session.query(PermRule).get(obj_id)
        session.delete(rule)
        session.commit()
    except Exception as e:
        logger.error(e)


def delete_object(obj_name, obj_id):
    """
    删除数据
    """
    msg = 'success'
    Session = sessionmaker()
    Session.configure(bind=engine)
    session = Session()
    try:
        if obj_name == "PermRole":
            delete_permrole(session, obj_id)
        elif obj_name == "PermSudo":
            delete_permsudo(session, obj_id)
        elif obj_name == "PermRule":
            delete_permrule(session, obj_id)
    except Exception as e:
        logger.error(e)
        msg = 'error'
    finally:
        session.close()
    return msg
