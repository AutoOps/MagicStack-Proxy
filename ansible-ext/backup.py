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
        self.cwd(dires[0])

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
            backup_type=dict(default="file", choices=["file", "database"]),
            compression=dict(default="bz2", choices=["bz2"]),
            force=dict(default=True, type="bool"),
            src=dict(required=False),
            dest=dict(required=True),
            # database params
            db_login_user=dict(default=None),
            db_login_password=dict(default=None),
            db_login_host=dict(default="localhost"),
            db_login_port=dict(default=3306, type='int'),
            name=dict(required=True, aliases=['db']),
            config_file=dict(default="~/.my.cnf"),

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


    # 结果字典
    result = dict(changed=True)
    # upload 次数，默认为1; 强制的话，隔10s再上传，处理三次;
    times = 1
    # 上传结果标识
    upload_flag = False
    # 上传错误信息
    upload_err_msg = ""

    if backup_type == "file":
        if not os.path.exists(src):
            module.fail_json(msg="Source %s not found" % (src))
        if not os.access(src, os.R_OK):
            module.fail_json(msg="Source %s not readable" % (src))
    elif backup_type == "database":
        # 生成数据库备份文件
        if db == 'all':
            db = 'mysql'
            all_databases = True
        else:
            all_databases = False
        database = Database()
        rc, stdout, stderr = database.db_dump(module, db_login_host, db_login_user, db_login_password, db, src,
                                              all_databases, db_login_port, config_file)
        if rc != 0:
            module.fail_json(msg="%s" % stderr)

    # 拆分dest参数信息
    dest_position = dest.rfind(os.sep)
    dest_len = len(dest)
    if (dest_len - 1) == dest_position:
        # 指定目录
        dest_path = dest
        dest_filename = "{0}.tar.{1}".format(str(int(time.time())), compression)
    else:
        # 指定文件
        dest_path, dest_filename = dest[:dest_position], dest[dest_position + 1:]

    # Compress file or dir
    compress = Compress(compression)
    cmp_file = compress.compress(src, dest_filename)

    # upload
    if force:
        times = 3

    while times:
        try:
            up = Upload(type, login_host, login_port, login_user, login_password)
            up.upload(cmp_file, "/".join([dest_path, dest_filename]))
            result['dest_file'] = "/".join([dest_path, dest_filename])
            upload_flag = True
            times = 0
        except Exception, e:
            upload_err_msg = e.message
            times -= 1

    # delete tmp
    try:
        os.remove(cmp_file)
    except:
        result['delete_tmp_cmp'] = False

    if not upload_flag:
        # upload failed
        module.fail_json(msg="{0}".format(upload_err_msg))

    module.exit_json(**result)


from ansible.module_utils.basic import *

main()