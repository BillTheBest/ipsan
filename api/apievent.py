# -*-coding: utf-8 -*-


import asyncio
from coroweb import get, post
from models import Event


@get('/api/events')
def api_events(request, **kw):
    '''
    Get events. Request url [GET /api/events]

    Query string:

        level: event level. 10=DEBUG, 20=INFO, 30=WARNING, 40=ERROR, 50=CRITICAL

        category: event category. 1=os, 2=upgrade, 3=api

        type: event sub type below category.

        action: event action. 1=add, 2=delete, 3=modify, 4=view, 5=login, 6=logout

        begin: event begin time(UTC) such as 1439449427

        end : event end time(UTC) such as 1439450427

    Sample:

        query add user evnets:

        /api/events?level=10&category=3&type=1&action=1
    '''
    where = []
    for k, v in kw.items():
        if len(v) == 0:
            continue
        if k == 'level':
            where.extend(['level=%s' % v[0]])
        if k == 'category':
            where.extend(['category=%s' % v[0]])
        if k == 'type':
            where.extend(['type=%s' % v[0]])
        if k == 'action':
            where.extend(['action=%s' % v[0]])
        if k == 'begin':
            where.extend(['created_at >=%s' % v[0]])
        if k == 'end':
            where.extend(['created_at <= %s' % v[0]])
    events = yield from Event.findall(where=' and '.join(where), orderby='created_at')
    return dict(retcode=0, events=events)


@post('/api/events/clear')
def api_event_clear():
    '''Clear event. Request url [POST /api/events/clear]'''
    yield from Event.truncate()
    return dict(retcode=0)
