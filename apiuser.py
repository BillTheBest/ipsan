# -*-coding: utf-8 -*-


import uuid
import asyncio
import errors
from coroweb import get, post
from models import User
from errors import APIError, APIValueError, APIAuthenticateError


@get('/api/users')
def api_users(request):
    users = yield from User.findall(orderby='created_at desc')
    return dict(retcode=0, users=users)


@get('/api/users/{id}')
def api_get_user(*, id):
    user = yield from User.find(id)
    return dict(retcode=0, user=user)


@post('/api/users')
def api_ceate_user(*, name, password):
    if not name or not name.strip():
        raise APIValueError('name')
    if not password or not password.strip():
        raise APIValueError('password')

    users = yield from User.findall(where="name='%s'" % name)
    if len(users) > 0:
        raise APIError(errors.EUSER_ALREADY_EXISTS, 'User %s already exist' % name)

    user = User(name=name, password=password)
    yield from user.save()
    return dict(retcode=0, user=user)


@post('/api/users/{id}/delete')
def api_delete_user(*, id):
      user = yield from User.find(id)
      if user is None:
          raise APIResourceNotFoundError('user %s not found', id)

      yield from user.remove()
      return dict(retcode=0)


@post('/api/users/{id}')
def api_update_user(id, request, *, password):
    user = yield from User.find(id)

    if user is None:
        raise APIResourceNotFoundError('user %s not exist' % id)
    if not password or not password.strip():
        raise APIValueError('password can not be empty')

    user.password = password
    yield from user.update()
    return dict(retcode=0, user=user)
