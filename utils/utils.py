#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Name    : utils.py
# @Date    : 2016-04-15 17:11
# @Author  : AutoOps
# @Link    : http://www.magicstack.cn/
# @Version :
import hashlib
import random
import crypt

from Crypto.Cipher import AES
from binascii import b2a_hex, a2b_hex
from sqlalchemy.orm import scoped_session, sessionmaker

from conf.settings import USERS, engine, KEY

from dbcollections.permission.models import *
from dbcollections.asset.models import *


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
            raise RuntimeError('Encrypt password error, TYpe error.')

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
            raise RuntimeError('Decrypt password error, TYpe error.')
        return plain_text.rstrip('\0')


CRYPTOR = PyCrypt(KEY)


def get_users():
    """
        获取用户信息
    """
    return USERS


def get_dbsession():
    """
        基于sqlalchemy获取数据库session
    """
    session = scoped_session(sessionmaker(bind=engine, autoflush=True, autocommit=True))
    return session


def get_group_user_perm(se, ob):
    """
    se为session
    ob为用户或用户组
    获取用户、用户组授权的资产、资产组
    return:
    {’asset_group': {
            asset_group1: {'asset': [], 'role': [role1, role2], 'rule': [rule1, rule2]},
            asset_group2: {'asset: [], 'role': [role1, role2], 'rule': [rule1, rule2]},
            }
    'asset':{
            asset1: {'role': [role1, role2], 'rule': [rule1, rule2]},
            asset2: {'role': [role1, role2], 'rule': [rule1, rule2]},
            }
        ]},
    'rule':[rule1, rule2,]
    'role': {role1: {'asset': []}, 'asset_group': []}, role2: {}},
    }
    """
    perm = {}
    if isinstance(ob, User):
        rule_all = set(se.query(PermRule).filter_by(user=ob).all())
        for user_group in ob.group.all():
            rule_all = rule_all.union(set(se.query(PermRule).filter_by(user_group=user_group).all()))

    elif isinstance(ob, UserGroup):
        rule_all = se.query(PermRule).filter_by(user=ob).all()
    else:
        rule_all = []

    perm['rule'] = rule_all
    perm_asset_group = perm['asset_group'] = {}
    perm_asset = perm['asset'] = {}
    perm_role = perm['role'] = {}
    for rule in rule_all:
        asset_groups = rule.asset_group.all()
        assets = rule.asset.all()
        perm_roles = rule.role.all()
        group_assets = []
        for asset_group in asset_groups:
            group_assets.extend(asset_group.asset_set.all())
            # 获取一个规则授权的角色和对应主机
        for role in perm_roles:
            if perm_role.get(role):
                perm_role[role]['asset'] = perm_role[role].get('asset', set()).union(
                    set(assets).union(set(group_assets)))
                perm_role[role]['asset_group'] = perm_role[role].get('asset_group', set()).union(set(asset_groups))
            else:
                perm_role[role] = {'asset': set(assets).union(set(group_assets)), 'asset_group': set(asset_groups)}

        # 获取一个规则用户授权的资产
        for asset in assets:
            if perm_asset.get(asset):
                perm_asset[asset].get('role', set()).update(set(rule.role.all()))
                perm_asset[asset].get('rule', set()).add(rule)
            else:
                perm_asset[asset] = {'role': set(rule.role.all()), 'rule': set([rule])}

        # 获取一个规则用户授权的资产组
        for asset_group in asset_groups:
            asset_group_assets = asset_group.asset_set.all()
            if perm_asset_group.get(asset_group):
                perm_asset_group[asset_group].get('role', set()).update(set(rule.role.all()))
                perm_asset_group[asset_group].get('rule', set()).add(rule)
            else:
                perm_asset_group[asset_group] = {'role': set(rule.role.all()), 'rule': set([rule]),
                                                 'asset': asset_group_assets}

            # 将资产组中的资产添加到资产授权中
            for asset in asset_group_assets:
                if perm_asset.get(asset):
                    perm_asset[asset].get('role', set()).update(perm_asset_group[asset_group].get('role', set()))
                    perm_asset[asset].get('rule', set()).update(perm_asset_group[asset_group].get('rule', set()))
                else:
                    perm_asset[asset] = {'role': perm_asset_group[asset_group].get('role', set()),
                                         'rule': perm_asset_group[asset_group].get('rule', set())}
    return perm


def gen_resource(se, ob, perm=None):
    """
    ob为用户或资产列表或资产queryset, 如果同时输入用户和{'role': role1, 'asset': []}，则获取用户在这些资产上的信息
    生成MyInventory需要的 resource文件
    """
    res = []
    if isinstance(ob, dict):
        role = ob.get('role')
        asset_r = ob.get('asset')
        user = ob.get('user')
        if not perm:
            perm = get_group_user_perm(se, user)

        if role:
            roles = perm.get('role', {}).keys()  # 获取用户所有授权角色
            if role not in roles:
                return {}

            role_assets_all = perm.get('role').get(role).get('asset')  # 获取用户该角色所有授权主机
            assets = set(role_assets_all) & set(asset_r)  # 获取用户提交中合法的主机

            for asset in assets:
                asset_info = get_asset_info(asset)
                role_key = get_role_key(user, role)
                info = {'hostname': asset.hostname,
                        'ip': asset.ip,
                        'port': asset_info.get('port', 22),
                        'ansible_ssh_private_key_file': role_key,
                        'username': role.name,
                }

                if os.path.isfile(role_key):
                    info['ssh_key'] = role_key

                res.append(info)
        else:
            for asset, asset_info in perm.get('asset').items():
                if asset not in asset_r:
                    continue
                asset_info = get_asset_info(asset)
                try:
                    role = sorted(list(perm.get('asset').get(asset).get('role')))[0]
                except IndexError:
                    continue

                role_key = get_role_key(user, role)
                info = {'hostname': asset.hostname,
                        'ip': asset.ip,
                        'port': asset_info.get('port', 22),
                        'username': role.name,
                        'password': CRYPTOR.decrypt(role.password),
                }
                if os.path.isfile(role_key):
                    info['ssh_key'] = role_key

                res.append(info)

    elif isinstance(ob, User):
        if not perm:
            perm = get_group_user_perm(ob)

        for asset, asset_info in perm.get('asset').items():
            asset_info = get_asset_info(asset)
            info = {'hostname': asset.hostname, 'ip': asset.ip, 'port': asset_info.get('port', 22)}
            try:
                role = sorted(list(perm.get('asset').get(asset).get('role')))[0]
            except IndexError:
                continue
            info['username'] = role.name
            info['password'] = CRYPTOR.decrypt(role.password)

            role_key = get_role_key(ob, role)
            if os.path.isfile(role_key):
                info['ssh_key'] = role_key
            res.append(info)

    elif isinstance(ob, list):
        for asset in ob:
            info = get_asset_info(asset)
            res.append(info)
    return res


def get_asset_info():
    pass


def get_role_key():
    pass


def user_have_perm():
    pass
