# -*-coding: utf-8 -*-


import logging
import functools
import inspect
import asyncio
from aiohttp import web
from urllib import parse
import errors
from errors import APIError


def get(path):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*arg, **kw):
            return func(*arg, **kw)
        wrapper.__method__ = 'GET'
        wrapper.__route__ = path
        return wrapper
    return decorator


def post(path):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*arg, **kw):
            return func(*arg, **kw)
        wrapper.__method__ = 'POST'
        wrapper.__route__ = path
        return wrapper
    return decorator


def get_required_kw_args(fn):
    args = []
    params = inspect.signature(fn).parameters

    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY and param.default == inspect.Parameter.empty:
            args.append(name)
    return tuple(args)


def get_named_kw_args(fn):
    args = []
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            args.append(name)
    return tuple(args)


def has_named_kw_args(fn):
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            return True


def has_var_kw_args(fn):
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            return True


def has_request_arg(fn):
    sig = inspect.signature(fn)
    params = sig.parameters
    found = False

    for name, param in params.items():
        if name == 'request':
            found = True
            continue

        if found and (param.kind != inspect.Parameter.VAR_KEYWORD and
                      param.kind != inspect.Parameter.VAR_POSITIONAL and
                      param.kind != inspect.Parameter.KEYWORD_ONLY):
            raise ValueError('request parameter must be the last named param'
                             'in function %s%s' % fn.__name, str(sig))
    return found


class RequestHandler(object):

    def __init__(self, app, fn):
        self._app = app
        self._fn = fn
        self._has_request_arg = has_request_arg(fn)
        self._has_var_kw_arg = has_var_kw_args(fn)
        self._has_named_kw_arg = has_named_kw_args(fn)
        self._named_kw_args = get_named_kw_args(fn)
        self._required_kw_args = get_required_kw_args(fn)

    def __call__(self, request):
        kw = None
        print('-------------')
        if self._has_var_kw_arg or self._has_named_kw_arg or self._required_kw_args:
            if request.method == 'POST':
                if not request.content_type:
                    return dict(retcode=errors.EHTTP_NO_CONTENT_TYPE,
                                message='Missing content type')
                ct = request.content_type.lower()
                if ct.startswith('application/json'):
                    params = yield from request.json()
                    if not isinstance(params, dict):
                        return dict(retcode=errors.EHTTP_INVALID_JSON_DATA,
                                    message='Json body must be a dict')
                    kw = params
                elif ct.startswith('application/x-www-form-urlencoded') or ct.startswith('multipart/form-data'):
                    params = yield from request.post()
                    kw = dict(**params)
                else:
                    return dict(retcode=errors.EHTTP_UNSUPPORT_CONTENT_TYPE,
                                message='Unsupport content type %s' % ct)

            if request.method == 'GET':
                qs = request.query_string
                if qs:
                    kw = dict()
                    for k, v in parse.parse_qs(qs, True).items():
                        kw[k] = v

        if kw is None:
            kw = dict(**request.match_info)
        else:
            if not self._has_var_kw_arg and self._named_kw_args:
                copy = dict()
                for k in self._named_kw_args:
                    if k in kw:
                        copy[k] = kw[k]

                kw = copy
            for k, v in request.match_info.items():
                if k in kw:
                    logging.warning('duplicate arg %s in named kw arg kw' % k)
                kw[k] = v

        if self._has_request_arg:
            kw['request'] = request

        if self._required_kw_args:
            for name in self._required_kw_args:
                if not name in kw:
                    return dict(retcode=101, message='Missing argument %s'%name)

        logging.info('calling %s with arg %s' % (request.path, str(kw)))
        try:
            r = yield from self._fn(**kw)
            return r
        except APIError as e:
            return dict(retcode=e.retcode, message=e.message)


def add_route(app, fn):
    method = getattr(fn, '__method__', None)
    route = getattr(fn, '__route__', None)
    if method is None or route is None:
        raise ValueError('@get or @post not defined in %s' % str(fn))

    if not asyncio.iscoroutinefunction(fn) or not inspect.isgeneratorfunction(fn):
        fn = asyncio.coroutine(fn)

    logging.info('add route %s:%s=>%s(%s)'% (method, route, str(fn.__name__),
                 ','.join(inspect.signature(fn).parameters.keys())))

    app.router.add_route(method, route, RequestHandler(app, fn))


def add_routes(app, module_name):
    mod = __import__(module_name, globals(), locals())

    for attr in dir(mod):
        if attr.startswith('_'):
            continue

        fn = getattr(mod, attr)
        if callable(fn):
            method = getattr(fn, '__method__', None)
            route = getattr(fn, '__route__', None)
            if method and route:
                add_route(app, fn)
