#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2016 MagicStack 
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

DOCUMENTATION = '''
---
module: backup
author: "mengx"
short_description: Backup files or dirs or mysql.
description:
    - Backup files or dirs or mysqldb
options:
    type:
        description:
          - 传输协议，将指定文件打包后，通过此协议上传到目标机器，默认ftp
        required: false
        choices: [ "ftp" ]
        default: "ftp"
    login_user:
        description:
          - ftp传输协议用户，支持匿名登录
        required: false
    login_password:
        description:
          - ftp传输协议密码，支持匿名登录
        required: false
    login_host:
        description:
          - ftp传输协议地址
        required: true
    login_port:
        description:
          - ftp传输协议端口，默认21
        required: false
        default: 21
    compression :
        description:
          - 压缩打包类型，将指定目标目录按此种方式打包
        required: false
        choices: [ "bz2" ]
        default: "bz2"
    dest:
        description:
          - 备份主机，目标地址，可指定备份文件名称，若不指定，系统自动根据时间戳生成
        required: true
    src:
        description:
          - 备份目标
        required: true
    force:
        description:
          - 默认C(yes)，强制备份
        required: false
        choices: [ "yes", "no" ]
        default: "yes"
    backup_type:
        description:
          - 备份类型，数据库，文件(含目录)
        required: false
        choices: [ "database", "file" ]
        default: "file"

'''

EXAMPLES = '''
# Example group command from Ansible
# backup file
ansible all -m backup -a "login_host=172.16.50.81 login_user=ftp_test login_password=ftp_test src=/home/ansible/t.txt dest=./b.tar.bz2"
# backup database
ansible all -m backup -a "backup_type=database login_host=172.16.50.81 login_user=ftp_test login_password=ftp_test src=/home/ansible/all.sql dest=./all.sql.tar.bz2 db_login_user=root db_login_password=password"
'''

import ftplib
import tarfile
import time
import sys
import os
import datetime

try:
    import MySQLdb
except ImportError:
    mysqldb_found = False
else:
    mysqldb_found = True


class Compress(object):
    def __init__(self, type='bz2'):
        self.type = type

    def compress(self, path, filename, local_path=os.getcwd()):
        '''
            param path, 要压缩的文件或目录
            param filename, 压缩到的文件
            param local_path, 指定压缩到文件的目录，默认为当前目录
        '''
        abs_filename = os.path.join(local_path, filename)
        arch = tarfile.open(abs_filename, "w:{0}".format(self.type))
        arch.add(path)
        arch.close()
        return abs_filename


class Database(object):
    def __init__(self, db_type="mysql"):
        self.db_type = db_type

    def db_dump(self, module, host, user, password, db_name, target, all_database, port, config_file, **kwargs):
        if self.db_type == 'mysql':
            return self._mysql_dump(module, host, user, password, db_name, target, all_database, port, config_file,
                                    **kwargs)

    def _mysql_dump(self, module, host, user, password, db_name, target, all_databases, port, config_file, socket=None,
                    ssl_cert=None, ssl_key=None, ssl_ca=None):
        cmd = module.get_bin_path('mysqldump', True)
        # If defined, mysqldump demands --defaults-extra-file be the first option
        if config_file:
            cmd += " --defaults-extra-file=%s" % pipes.quote(config_file)
        cmd += " --quick"
        if user is not None:
            cmd += " --user=%s" % pipes.quote(user)
        if password is not None:
            cmd += " --password=%s" % pipes.quote(password)
        if ssl_cert is not None:
            cmd += " --ssl-cert=%s" % pipes.quote(ssl_cert)
        if ssl_key is not None:
            cmd += " --ssl-key=%s" % pipes.quote(ssl_key)
        if ssl_cert is not None:
            cmd += " --ssl-ca=%s" % pipes.quote(ssl_ca)
        if socket is not None:
            cmd += " --socket=%s" % pipes.quote(socket)
        else:
            cmd += " --host=%s --port=%i" % (pipes.quote(host), port)
        if all_databases:
            cmd += " --all-databases"
        else:
            cmd += " %s" % pipes.quote(db_name)

        # 只管导出，由外部进行压缩
        cmd += " > %s" % pipes.quote(target)
        rc, stdout, stderr = module.run_command(cmd, use_unsafe_shell=True)
        return rc, stdout, stderr


class Upload(object):
    def __init__(self, type, host="", port=21, user="", passwd="", timeout=60):
        self.type = type
        self.host = host
        self.port = port
        self.user = user
        self.passwd = passwd
        self.timeout = timeout

    def upload(self, src, desc):
        if self.type == "ftp":
            self._ftp(src, desc)


    def _ftp(self, src, desc):
        ftp = MyFTP(self.host, self.port, self.user, self.passwd, self.timeout, True)
        ftp.upload(src, desc)
        ftp.quit()


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
            return

        # check local file isn't exits and get the local file size
        lsize = 0L
        if os.path.exists(local_path):
            lsize = os.stat(local_path).st_size

        if lsize == rsize:
            return

        blocksize = 1024 * 1024
        # rest marker
        cmpsize = lsize
        lwrite = open(local_path, 'ab')
        self.retrbinary('RETR ' + remotefile, lwrite.write, blocksize, cmpsize)
        lwrite.close()


    def upload(self, local_path, remote_path):
        """
            上传
        """
        # check local file exists
        if not os.path.exists(local_path):
            raise ftplib.Error("local file doesn't exists")

        # self.set_debuglevel(0)
        dires = self.splitpath(remote_path)
        remotefile = dires[1]
        # 多层级目录
        for dir in dires[0].split('/'):
            if self.force:
                try:
                    self.cwd(dir)
                except:
                    self.mkd(dir)
                    self.cwd(dir)
            else:
                self.cwd(dir)
            # get remote file info
        rsize = 0L
        try:
            rsize = self.size(remotefile)
        except:
            pass
        if (rsize == None):
            rsize = 0L

        # get local file info
        lsize = os.stat(local_path).st_size
        if lsize == rsize:
            return

        if rsize < lsize:
            # 断点续传
            localf = open(local_path, 'rb')
            localf.seek(rsize)
            self.storbinary("STOR " + remotefile, localf, blocksize=1024 * 1024, rest=rsize)
            localf.close()


    def splitpath(self, remotepath):
        position = remotepath.rfind('/')
        return (remotepath[:position + 1], remotepath[position + 1:])


def main():
    module = AnsibleModule(
        argument_spec=dict(
            # upload params
            type=dict(default="ftp", choices=["ftp"]),
            login_user=dict(default=None),
            login_password=dict(default=None),
            login_host=dict(default="localhost"),
            login_port=dict(default=21, type='int'),
            # backup params
            backup_type=dict(default="file", choices=["file", "database", "path"]),
            compression=dict(default="bz2", choices=["bz2"]),
            force=dict(default=True, type="bool"),
            src=dict(required=False),
            dest=dict(required=True),
            # database params
            db_login_user=dict(default=None),
            db_login_password=dict(default=None),
            db_login_host=dict(default="localhost"),
            db_login_port=dict(default=3306, type='int'),
            name=dict(aliases=['db']), # 指定多个数据库时，备份多个文件
            config_file=dict(default="/etc/my.cnf"),
        )
    )
    # 上传参数
    type = module.params['type']
    login_user = module.params['login_user']
    login_password = module.params['login_password']
    login_host = module.params['login_host']
    login_port = module.params['login_port']
    # 备份参数
    backup_type = module.params['backup_type']
    compression = module.params['compression']
    force = module.params['force']
    src = module.params.get('src')
    dest = module.params['dest']
    # 数据库参数
    db_login_user = module.params['db_login_user']
    db_login_password = module.params['db_login_password']
    db_login_host = module.params['db_login_host']
    db_login_port = module.params['db_login_port']
    db = module.params['name']
    config_file = module.params['config_file']

    # 获取localhost地址赋值backnode
    backnode = 'localhost'
    ip_path = module.get_bin_path('ip')
    if ip_path:
        v4_cmd = [ip_path, '-4', 'route', 'get', '8.8.8.8']
        rc, out, err = module.run_command(v4_cmd)
        if out:
            words = out.split('\n')[0].split()
            for i in range(len(words) - 1):
                if words[i] == 'src':
                    backnode = words[i+1]

    # 结果字典
    result = dict(changed=True)
    # upload 次数，默认为1; 强制的话，隔60s再上传，处理三次;
    times = 1
    # 上传结果标识
    upload_flag = False
    # 上传错误信息
    upload_err_msg = {}
    remove_err_msg = {}

    # 压缩文件/目录参数 >> (待压缩文件/目录?， 压缩成文件?, 上传目标目录)
    compress_filenames = []
    remove_filenames = []

    if backup_type in ( "file", "path"):
        if not os.path.exists(src):
            module.fail_json(msg="Source %s not found" % (src))
        if not os.access(src, os.R_OK):
            module.fail_json(msg="Source %s not readable" % (src))

        # 拆分dest参数信息，用于压缩文件及目录
        dest_position = dest.rfind(os.sep)
        dest_len = len(dest)
        if (dest_len - 1) == dest_position:
            # 指定目录，只指定目录时自动赋值一个名字
            dest_path, dest_filename = dest, "{0}.tar.{1}".format(str(int(time.time())), compression)
        else:
            # 指定压缩到文件名  dest 参数中指定
            dest_path, dest_filename = dest[:dest_position], '{0}-{1}.{2}'.format(dest[dest_position + 1:],
                                                                                  str(int(time.time())), compression)

        # 统一被压缩的文件或者目录
        compress_filenames.append((src, dest_filename, dest_path))

    elif backup_type == "database":
        # 判断目录是否存在
        if not os.path.exists(src):
            module.fail_json(msg="Source %s not found" % (src))

        src = src.rstrip(os.sep)
        if not os.path.isdir(src):
            src = src[:src.rfind(os.sep)]

        # 构造dest的参数
        dest_position = dest.rfind(os.sep)
        if dest_position != len(dest):
            # 构造dest中，末位不是符号时，将后面内容舍弃
            dest = dest[:dest_position]

        # 生成数据库备份文件
        if db == 'all':
            db = 'mysql'
            all_databases = True
        else:
            all_databases = False
            # 拆分name列表
            if db.find(',') > -1:
                db = db.strip(',').split(',')

        database = Database()
        if isinstance(db, list):
            # 备份多个数据库，指定src只需要目录即可，文件全部由系统生成，名字格式db_name.sql.compression
            success_db = {}
            fail_db = {}
            for d in db:
                f_name = '{0}.sql-{1}'.format(d, str(int(time.time())))
                backup_name = os.sep.join([src, f_name])
                rc, stdout, stderr = database.db_dump(module, db_login_host, db_login_user, db_login_password, d,
                                                      backup_name,
                                                      all_databases, db_login_port, config_file)
                if rc != 0:
                    fail_db[d] = stderr
                else:
                    success_db[d] = backup_name
                    remove_filenames.append(backup_name)

            if len(success_db) == 0:
                # 全部备份失败
                module.fail_json(msg=fail_db)

            # 整理压缩信息待使用
            for dbname, filename in success_db.items():
                compress_filenames.append((filename, '{0}.{1}'.format(filename.split(os.sep)[-1], compression), dest))

            if fail_db:
                result['dbback_err_msg'] = fail_db
        else:
            f_name = '{0}.sql-{1}'.format(db, str(int(time.time())))
            backup_name = os.sep.join([src, f_name])
            rc, stdout, stderr = database.db_dump(module, db_login_host, db_login_user, db_login_password, db,
                                                  backup_name,
                                                  all_databases, db_login_port, config_file)
            if rc != 0:
                module.fail_json(msg="%s" % stderr)

            remove_filenames.append(backup_name)
            compress_filenames.append((backup_name, '{0}.{1}'.format(f_name, compression), dest))


    # Compress file or dir
    upload_filenames = [] # ( 源文件, 文件名, 目标目录)
    for src_filename, compress_filename, dest in compress_filenames:
        compress = Compress(compression)
        cmp_file = compress.compress(src_filename, compress_filename)
        upload_filenames.append((cmp_file, compress_filename, dest))

    remove_filenames.extend(map(lambda x: x[0], upload_filenames))

    for u_file, dest_filename, dest_path in upload_filenames:
        # upload
        if force:
            times = 3
        while times:
            try:
                up = Upload(type, login_host, login_port, login_user, login_password)
                #
                up.upload(u_file, "/".join(
                    [dest_path, backnode, datetime.datetime.now().strftime('%Y-%m-%d'), backup_type, dest_filename]))
                upload_flag = True
                times = 0
            except Exception, e:
                upload_err_msg[u_file] = e.message
                times -= 1
                # 休息60秒再次进行ftp进行上传
                time.sleep(5)

    # delete tmp
    for r_file in remove_filenames:
        try:
            os.remove(r_file)
        except:
            remove_err_msg[r_file] = False

    if remove_err_msg:
        result['remove_file_err_msg'] = remove_err_msg
    if upload_err_msg:
        result['upload_file_err_msg'] = upload_err_msg
    module.exit_json(**result)


from ansible.module_utils.basic import *

main()