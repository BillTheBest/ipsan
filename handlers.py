# -*-coding: utf-8 -*-


import time
import logging
import asyncio
import hashlib
from config import configs
from models import User

COOKIE_NAME = "ubs-ipsan"
_COOKIE_KEY = configs.session.secret


@asyncio.coroutine
def cookie2user(cookie_str):
    if not cookie_str:
        return None

    try:
        L = cookie_str.split('-')
        user_id, expires, sha1 = L
        user = User.find(user_id)
        if user is None:
            return None

        s = '%s-%s-%s-%s' % (user_id, user.password, expires, _COOKIE_KEY)
        if (sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest()):
            return None
        user.password = '******'
        return user
    except Exception as e:
        logging.exception(e)
        return None


def user2cookie(user, maxage):
    '''
    cookie = user_id-expires-sha1(user_id-usser_passwd-expires-secretkey)
    '''
    expires = str(int(time.time()) + maxage)
    s = '%s-%s-%s-%s' % (user.id, user.password, expires, _COOKIE_KEY)
    L = [user.id, expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
    return '-'.join(L)
