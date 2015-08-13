# -*-coding: utf-8 -*-


import uuid
import logging
import json
import asyncio
import errors
from handlers import user2cookie, COOKIE_NAME
from coroweb import get, post
from models import *
from errors import APIError, APIValueError, APIAuthenticateError
from aiohttp import web


login_html = b'''
<html>
    <head>
        <title>Login</title>
    </head
    <body>
        <form method="post" action="/api/login">
            User:<input type="text" name="user"/><br/>
            Password: <input type="password" name="password"/><br/>
            <div>
                <p><input type="submit" value="Login"/></p>
            </div>
        </form>
    </body>
</html>
'''

logout_html = b'''
<html>
    <head>
        <title>Logout</title>
    </head
    <body>
        You already logined.
        <form method="post" action="/api/logout">
           <p><input type="submit" value="Logout"/></p>
        </form>
    </body>
</html>
'''

@get('/login')
def login(request):
    '''Test page for login and logout. Request url [GET /login]'''
    user = request.__user__
    if user is None:
        return web.Response(body=login_html)
    else:
        return web.Response(body=logout_html)


@post('/api/login')
def api_login(*, user, password):
    '''
    Do login. Request url: [POST /api/login]

    Post data:

        user: user name

        password: password
    '''
    users = yield from User.findall(where="name='%s'" % user)
    if not users or len(users) == 0:
        return dict(retcode=0, message='user %s not eixsts' % user)

    user = users[0]
    if user.password != password:
        return dict(retcode=0, message='incorrect password')
    # set cookie
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    r.content_type = 'application/json;charset=utf8'
    d = dict(retcode=0, user=user)
    r.body = json.dumps(d, ensure_ascii=True).encode('utf-8')
    yield from log_event(logging.INFO, event_api_user, event_action_login,
                         'user %s login' % user.name)
    return r


@post('/api/logout')
def api_logout():
    '''
    Do logout. Request url: [POST /api/logout']
    '''
    # set cookie
    r = web.Response()
    r.set_cookie(COOKIE_NAME, "deleted", httponly=True)
    r.content_type = 'application/json;charset=utf8'
    d = dict(retcode=0)
    r.body = json.dumps(d, ensure_ascii=True).encode('utf-8')
    yield from log_event(logging.INFO, event_api_user, event_action_login,
                         'user %s logout' % user.name)
    return r


@get('/api/users')
def api_users(request):
    '''
    List all users. Request url: [GET /api/users]
    '''
    users = yield from User.findall(orderby='created_at desc')
    return dict(retcode=0, users=users)


@get('/api/users/{id}')
def api_get_user(*, id):
    '''
    Get user by id. Request url: [GET /api/users/{id}]
    '''
    user = yield from User.find(id)
    return dict(retcode=0, user=user)


@post('/api/users')
def api_ceate_user(*, name, password):
    '''
    Create user. Request url: [POST /api/users]

    Post data:

        name: user name

        password: user password
    '''
    if not name or not name.strip():
        raise APIValueError('name')
    if not password or not password.strip():
        raise APIValueError('password')

    users = yield from User.findall(where="name='%s'" % name)
    if len(users) > 0:
        raise APIError(errors.EUSER_ALREADY_EXISTS, 'User %s already exist' % name)

    user = User(name=name, password=password)
    yield from user.save()
    yield from log_event(logging.INFO, event_api_user, event_action_add,
                         'add user %s' % name)
    return dict(retcode=0, user=user)


@post('/api/users/{id}/delete')
def api_delete_user(*, id):
    '''
    Delete user by id. Request url [POST /api/users/{id}/delete
    '''
    user = yield from User.find(id)
    if user is None:
        raise APIResourceNotFoundError('user %s not found', id)

    yield from user.remove()
    yield from log_event(logging.INFO, event_api_user, event_action_del,
                         'delete user %s' % user.name)
    return dict(retcode=0)


@post('/api/users/{id}')
def api_update_user(id, request, *, password):
    '''
    Update user. Request url: [POST /api/users/{id}]

    Post data:

        password: user new password
    '''
    user = yield from User.find(id)

    if user is None:
        raise APIResourceNotFoundError('user %s not exist' % id)
    if not password or not password.strip():
        raise APIValueError('password can not be empty')

    user.password = password
    yield from user.update()
    yield from log_event(logging.INFO, event_api_user, event_action_del,
                         'update user %s password' % user.name)
    return dict(retcode=0, user=user)
