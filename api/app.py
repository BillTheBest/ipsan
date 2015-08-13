#!/usr/bin/env python3
# -*-coding: utf-8 -*-


import json
import os
import logging
import asyncio
from aiohttp import web
from config import configs
from coroweb import add_routes
from handlers import COOKIE_NAME, cookie2user
from orm import select, execute
from errors import APIAuthenticateError


logging.basicConfig(level=logging.INFO)

@asyncio.coroutine
def logger_factory(app, handler):
    @asyncio.coroutine
    def logger(request):
        return (yield from handler(request))
    return logger


@asyncio.coroutine
def auth_factory(app, handler):
    @asyncio.coroutine
    def auth(request):
        request.__user__ = None
        if not configs.auth:
            return (yield from handler(request))
        cookie_str = request.cookies.get(COOKIE_NAME)
        if cookie_str:
            user = yield from cookie2user(cookie_str)
            if user:
                request.__user__ = user
        if request.__user__ is None:
            if not request.path.endswith('login'):
                resp = json.dumps({"retcode": 100, "message": "Not login yet"})
                return web.Response(body=resp.encode('utf-8'))
        return (yield from handler(request))
    return auth


@asyncio.coroutine
def response_factory(app, handler):
    @asyncio.coroutine
    def response(request):
        logging.info('Response handler...')
        r = (yield from handler(request))

        if isinstance(r, web.StreamResponse):
            return r
        if isinstance(r, bytes):
            resp = web.Response(body=r)
            resp.content_type = 'application/octec-stream'
            return resp
        if isinstance(r, str):
            resp = web.Response(body=r.encode('utf-8'))
            resp.content_type = 'text/html;charset=utf-8'
            return resp
        if isinstance(r, dict):
            resp = web.Response(body=json.dumps(r).encode('utf-8'))
            resp.content_type = 'application/json;charset=utf-8'
            return resp
        resp = web.Response(body=str(r).encode('utf-8'))
        resp.content_type = 'text/plain;charset=utf-8'
        return resp

    return response


@asyncio.coroutine
def init(loop):
    app = web.Application(loop=loop, middlewares=[logger_factory,
                                                  auth_factory,
                                                  response_factory])

    add_routes(app, 'apiuser')
    add_routes(app, 'apiarray')
    add_routes(app, 'apidisk')
    add_routes(app, 'apivg')
    add_routes(app, 'apilvm')
    add_routes(app, 'apitarget')
    add_routes(app, 'apisystem')
    add_routes(app, 'apievent')
    srv = yield from loop.create_server(app.make_handler(),
                                        configs.host.address,
                                        configs.host.port)

    logging.info('server start at port %s' % configs.host.port)
    return srv

loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()
