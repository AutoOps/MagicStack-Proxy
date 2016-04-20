#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Name    : cobbler_api
# @Date    : 2016-04-18 16:10
# @Author  : AutoOps
# @Link    : http://www.magicstack.cn/
# @Version :

import xmlrpclib
import traceback
import logging
import functools
import uuid

import conf.settings as settings

logger = logging.getLogger()

class Cobbler(object):

    def __init__(self, username=settings.COBBLER_USERNAME, password=settings.COBBLER_PASSWORD):
        self.username = username
        self.password = password
        self.api_url  = settings.COBBLER_RPC_URL

    def get_remote(self):
        remote = xmlrpclib.Server(self.api_url)
        return remote

    def get_token(self):
        remote = self.get_remote()
        try:
            token = remote.login( self.username, self.password )
        except:
            logging.error(traceback.format_exc())
            raise RuntimeError( 'get cobbler token error' )
        return token

    def get_fileds(self):
        """
            获取需要参数值
        """
        pass

class System(Cobbler):

    def get_fileds(self):

        return {
            'name':None,
            'uid':None,

        }

    def power(self, params):
        remote = self.get_remote()
        token = self.get_token()
        logger.debug('systems[{0}] power{1}'.format(params.get('systems'), params.get('power')))
        result = remote.background_power_system(params,token)

    def create(self, params):
        remote = self.get_remote()
        token = self.get_token()
        logger.debug('create system params:{0}'.format(params))
        name = params.get('name')


    def modify(self, params):
        remote = self.get_remote()
        token = self.get_token()
        logger.debug('modify system params:{0}'.format(params))

    def delete(self, params):
        remote = self.get_remote()
        token = self.get_token()

class Distros(Cobbler):

    def _check_iso(self):

        return False

    def get_fileds(self):

        return {}

    def upload(self, params):
        """
            1. mount  dvd
            2. import dvd
            3. umount dvd
        """
        path = params.get('path')
        osname = params.get('name')
        dvd = '/'.join(path, osname)
        self._check_iso(dvd)
        mnt_sub = "/mnt/{0}".format(uuid.uuid1())
        mnt_sub_cmd = "mkdir {0}".format(mnt_sub)
        mount_cmd = "mount -o loop {0} {1}".format(dvd, mnt_sub)
        umount_cmd = "umount {0}".format(mnt_sub)
        




def cobbler_token(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        cobbler = Cobbler()
        token = cobbler.get_token()
        while token is None:
            token = cobbler.get_token()
        return func(token=token, *args, **kwargs)
    return wrapper


if __name__ == "__main__":
    cobbler = Cobbler()
    print cobbler.get_token()


