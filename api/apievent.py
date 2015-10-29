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

        category: event source. 1=api, 2=daemon, 3=admin

        type: event sub type below category. 1=OS, 2=upgrade, 3=user, 4=array, 5=volume group, 6=lvm, 7=target

        action: event action. 1=add, 2=delete, 3=modify, 4=view, 5=login, 6=logout, 7=reboot, 8=poweroff, 9=network

        begin: event begin time(UTC) such as 1439449427

        end : event end time(UTC) such as 1439450427

        page : page number. like 1, 2, 3, 4....

        pagesize : how many record in each page. default is 10

    Sample:

        query add user evnets:

        /api/events?page=1&pagesize=20&level=10&category=3&type=1&action=1
    '''
    where = []
    page = None
    page_size = None
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
        if k == 'page':
            if v[0].isdigit():
                page = int(v[0])
            else:
                return dict(retcode=0, total=0, events=[])
        if k == 'pagesize':
            if v[0].isdigit():
                page_size = int(v[0])
            else:
                return dict(retcode=0, total=0, events=[])

    total = yield from Event.findNumber('count(id)', where)
    events = []
    if not page_size:
        page_size = 10
    total_page = total // page_size + (1 if total % page_size > 0 else 0)
    if page:
        if page >= 1 and page <= total_page:
            offset = (page-1) * page_size
            events = yield from Event.findall(where=' and '.join(where), orderby='created_at desc', limit=(offset, page_size))
        else:
            total = 0
    else:
        events = yield from Event.findall(where=' and '.join(where), orderby='created_at desc')

    return dict(retcode=0, total=total, events=events)


@post('/api/events/clear')
def api_event_clear():
    '''Clear event. Request url [POST /api/events/clear]'''
    yield from Event.truncate()
    return dict(retcode=0)
