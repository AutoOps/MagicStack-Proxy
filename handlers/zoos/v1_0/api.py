#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Name    : api.py
# @Date    : 2016-04-13 11:25
# @Author  : AutoOps
# @Link    : http://www.magicstack.cn/
# @Version :

import logging
try:
    import simplejson as json
except ImportError:
    import json

from tornado.web import RequestHandler
from tornado.web import asynchronous
from tornado.gen import coroutine
from tornado.concurrent import run_on_executor
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger()

class ZooHandler(RequestHandler):
    """
        示例接口
    """
    executor = ThreadPoolExecutor(2)
    def get(self, *args, **kwargs):
        """
            查询
        """
        self.write({
            'zoo1':{
                'address':'beijing.**.1',
                'name':'zoo1'
            },
            'zoo2':{
                'address':'beijing.**.2',
                'name':'zoo2'
            },
            'zoon':{
                'address':'beijing.**.n',
                'name':'zoon'
            }

        })

    def put(self, *args, **kwargs):
        """
          修改
        """
        pass

    def delete(self, *args, **kwargs):
        """
            删除
        """
        pass

    @asynchronous
    @coroutine
    def post(self, *args, **kwargs):
        """
            新增
        """
        #print self.request.body           # json方式
        #name = self.get_argument('name')  # form-data
        #address =  self.get_argument('address') #form-data
        #name = self.get_body_argument('name')    # x-www-form-urlencoded
        #address = self.get_body_argument('address') # x-www-form-urlencoded
        # print self.request.body, type(self.request.body)
        params = json.loads(self.request.body) # json方式
        name = params.get( 'name' )
        address = params.get( 'address' )
        self.add_zoos(*args, **kwargs)
        print '22222222222222222'
        self.write({
            'zoo1':{
                'address': address,
                'name':name
            },
            'status':'creating'
        })
        self.finish()

    @run_on_executor
    def add_zoos(self, *args, **kwargs):
        print 'add_zoos --> start'
        import time
        time.sleep( 20 )
        print 'add_zoos --> end'
        return


class CaseServerHandler(RequestHandler):

    def post(self, *args, **kwargs):
        pass

