#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Name    : server.py
# @Date    : 2016-04-13 11:17
# @Author  : AutoOps
# @Link    : http://www.magicstack.cn/
# @Version :

import os
import sys
import socket

import tornado.web
import tornado.options
import tornado.ioloop
import tornado.httpserver
from tornado.options import define, options

define("address", default='0.0.0.0', help="run on the given address", type=str)
define("port", default=8100, help=u"设置cobbler-api端口")


conf = {
    "debug": True,
}

if __name__ == "__main__":

    sys.path.append(os.path.join(os.path.dirname(__file__), "handlers"))

    from conf import urls

    conf["handlers"] = urls.urls
    conf['cookie_secret'] = "bZJc2sWbQLKos6GkHn/VB9oXwQt8S0R0kRvJ5/xJ89E="

    tornado.options.parse_command_line()

    app = tornado.web.Application(**conf)
    server = tornado.httpserver.HTTPServer(app)
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    else:
        port = options.port

    server.listen(port)

    if options.address:
        hostname = options.address
    else:
        hostname = socket.gethostbyname(socket.gethostname())

    print "-" * 20
    print "      tornado运行地址:%s:%s" % (hostname, port)
    print "      等待连接......"
    print "-" * 20

    tornado.ioloop.IOLoop.instance().start()