#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Name    : api.py
# @Date    : 2016-04-14 10:48
# @Author  : AutoOps
# @Link    : http://www.magicstack.cn/
# @Version :

try:
    import simplejson as json
except ImportError:
    import json
from tornado.web import RequestHandler

from conf.settings import API_HOST, API_PORT

class VersionHandler(RequestHandler):
    """
        Version Info
    """

    def get(self, *args, **kwargs):

        versions = {
            "versions": [
                {
                    "id": "v1.0",
                    "links": [
                        {
                            "href": "http://{0}:{1}/v1.0/".format(API_HOST, API_PORT),
                            "rel": "self"
                        }
                    ],
                    "status": "CURRENT",
                    "version": "v1.0",
                    "updated": "2016-04-14T11:33:21Z"
                }
            ]
        }
        self.write( versions )
        self.finish()


class Version1Handler(RequestHandler):
    """
        API 1.0 Version Info
    """

    def get(self, *args, **kwargs):
        version = {
            "version": {
                "id": "v1.0",
                "links": [
                    {
                        "href": "http://{0}:{1}/v1.0/".format(API_HOST, API_PORT),
                        "rel": "self"
                    },
                    {
                        "href": "http://{0}:{1}/v1.0/docs".format(API_HOST, API_PORT),
                        "rel": "describedby",
                        "type": "text/html"
                    }
                ],
                "status": "CURRENT",
                "version": "1.0",
                "min_version": "1.0",
                "updated": "2016-04-14T11:33:21Z"
            }
        }
        self.write(version)
        self.finish()

class Version1Handler(RequestHandler):
    """
        API 1.0 Version Info
    """

    def get(self, *args, **kwargs):
        version = {
            "version": {
                "id": "v1.0",
                "links": [
                    {
                        "href": "http://{0}:{1}/v1.0/".format(API_HOST, API_PORT),
                        "rel": "self"
                    },
                    {
                        "href": "http://{0}:{1}/v1.0/docs".format(API_HOST, API_PORT),
                        "rel": "describedby",
                        "type": "text/html"
                    }
                ],
                "status": "CURRENT",
                "version": "1.0",
                "min_version": "1.0",
                "updated": "2016-04-14T11:33:21Z"
            }
        }
        self.write(version)
        self.finish()

class VersionDocsHandler(RequestHandler):
    """

    """
    def get(self, *args, **kwargs):
        self.write('<H1>waitting...</H1>')
        self.finish()