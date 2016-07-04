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
import ftplib
import sys
import os

from Crypto.Cipher import AES
from binascii import b2a_hex, a2b_hex
from sqlalchemy.orm import scoped_session, sessionmaker

from conf.settings import USERS, engine, KEY


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


class MyFTP(ftplib.FTP):
    """
        自定义FTP类，实现ftp上传下载及断点续传
    """

    def __init__(self, host="", port=21, user="", passwd="", timeout=60, force=False):

        self.host = host
        self.port = port
        self.user = user
        self.passwd = passwd
        self.timeout = timeout
        self.force = force
        self._conn_login()

    def _conn_login(self):
        """
            connection and login
        """
        try:
            self.connect(self.host, self.port, self.timeout)
        except Exception, e:
            sys.stderr.write("connect failed - {0}".format(e))
            raise ftplib.Error("connect failed - {0}".format(e))

        try:
            self.login(self.user, self.passwd)
        except Exception, e:
            sys.stderr.write("login failed - {0}".format(e))
            raise ftplib.Error("login failed - {0}".format(e))

    def splitpath(self, remotepath):
        position = remotepath.rfind('/')
        return (remotepath[:position + 1], remotepath[position + 1:])

    def download(self, remote_path, local_path):
        """
            download
        """
        self.set_pasv(0)
        # get remote dir and file
        dires = self.splitpath(remote_path)
        if dires[0]:
            self.cwd(dires[0])
        remotefile = dires[1]

        # get remote file size
        rsize = self.size(remotefile)
        if rsize == 0:
            return rsize

        # check local file isn't exits and get the local file size
        lsize = 0L
        if os.path.exists(local_path):
            lsize = os.stat(local_path).st_size

        if lsize == rsize:
            return rsize

        blocksize = 1024 * 1024
        # rest marker
        cmpsize = lsize
        lwrite = open(local_path, 'ab')
        self.retrbinary('RETR ' + remotefile, lwrite.write, blocksize, cmpsize)
        lwrite.close()
        return rsize