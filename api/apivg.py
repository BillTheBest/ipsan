# -*-coding: utf-8 -*-


import os
import re
import logging
import subprocess
import asyncio
from coroweb import get, post
from config import grgrant_prog
from models import VG
from errors import APIError, APIValueError, APIAuthenticateError, APIResourceNotFoundError

_vg_status = {
    "unknow": 0,
    "resizable": 1,
    "active": 2,
    "inactive": 3
}

_vgdisplay_prog = '/sbin/vgdisplay'
_vgcreate_prog = '/sbin/vgcreate'
_vgremove_prog = '/sbin/vgremove'
_vgrename_prog = '/sbin/vgrename'
_pvcreate_prog = '/sbin/pvcreate'

_vg_seperator = '--- Volume group ---'

_re_vg_name = re.compile(r'^VG Name\s+(.+)')
_re_vg_stat = re.compile(r'^VG Status\s+(.+)')
_re_vg_size = re.compile(r'^VG Size\s+([^\s]+)\s(.+)')
_re_vg_uuid = re.compile(r'^VG UUID\s+(.+)')


@asyncio.coroutine
def _size_to_kb(size, unit):
    unit = unit.upper()
    size = float(size)
    if unit.startswith('G'):
        return (size*1024*1024)
    if unit.startswith('M'):
        return (size*1024)
    if unit.startswith('T'):
        return (size*1024*1024*1024)
    else:
        return size


@asyncio.coroutine
def _vg_parse_display(output):
    lines = output.split(os.linesep)

    vgs = []
    for line in lines:
        line = line.strip()
        if line.startswith(_vg_seperator):
            vg = VG()
            vgs.insert(0, vg)
        r_name = _re_vg_name.match(line)
        r_stat = _re_vg_stat.match(line)
        r_size = _re_vg_size.match(line)
        r_uuid = _re_vg_uuid.match(line)

        if r_name:
            vgs[0].name = r_name.group(1)
        if r_stat:
            vgs[0].state = _vg_status.get(r_stat.group(1), 0)
        if r_size:
            vgs[0].size = yield from _size_to_kb(r_size.group(1), r_size.group(2))
        if r_uuid:
            vgs[0].id = r_uuid.group(1).lower().replace('-', '')

    return vgs


@asyncio.coroutine
def _vg_display():
    try:
        output = subprocess.check_output([grgrant_prog, _vgdisplay_prog],
                                         universal_newlines = True)
        return (yield from _vg_parse_display(output))
    except subprocess.CalledProcessError as e:
        logging.exception(e)


@asyncio.coroutine
def _vg_create(name, pvs):
    args = [grgrant_prog, _vgcreate_prog, name]
    args.extend(pvs)
    try:
        for pv in pvs:
            subprocess.check_output([grgrant_prog, _pvcreate_prog, pv])
    except subprocess.CalledProcessError as e:
        logging.exception(e)
        return None
    try:
        subprocess.check_output(args, universal_newlines=True)
        return _vg_display()
    except subprocess.CalledProcessError as e:
        logging.exception(e)


@asyncio.coroutine
def _vg_delete(vg):
    args = [grgrant_prog, _vgremove_prog, vg.name, '--force']
    try:
        subprocess.check_output(args, universal_newlines=True)
        return True
    except subprocess.CalledProcessError as e:
        logging.exception(e)


@asyncio.coroutine
def _vg_rename(name, newname):
    subprocess.check_output([grgrant_prog, _vgrename_prog, name, newname])


@get('/api/vgs')
def api_vgs(request):
    '''
    Get all volume gorups. Request url [GET /api/vgs]
    '''
    vgs = yield from VG.findall()
    if vgs is None:
        vgs = []

    state_changed = False
    vgs_current = yield from _vg_display()
    vgs_dict = dict()
    for vg in vgs_current:
        vgs_dict[vg.id] = vg
    for vg in vgs:
        if vg.id not in vgs_dict:
            vg.state = _vg_status['inactive']
            state_changed = True
        else:
            vg_cur = vgs_dict[vg.id]
            if vg_cur.name != vg.name:
                state_changed = True
                vg = vg_cur
        if state_changed:
            yield from vg.update()

    vgs_id = [vg.id for vg in vgs]
    for vg in vgs_current:
        if vg.id not in vgs_id:
            #new added vg
            yield from vg.save()
            vgs.append(vg)

    return dict(retcode=0, vgs=vgs)


@post('/api/vgs')
def api_create_vg(*, name, **kw):
    '''
    Create volume group. Request url [POST /api/vgs]

    Post data:

        name: volume group name

        pv0: physical volume 1. example: /dev/md0

        pv1: physical volume 2. example: /dev/md1

        pv2: physical volume 3. example: /dev/md2

        ...
    '''
    if not name or not name.strip():
        raise APIValueError('name')
    vg = yield from VG.findall(where="name='%s'" % name)
    if vg:
        return dict(retcode=501, message='vg %s already exists' % name)

    pvs = []
    for k, v in kw.items():
        if k.startswith('pv'):
            if os.path.exists(v):
                pvs.append(v)
            else:
                return dict(retcode=502, message='Invalid pv %s' % v)

    if len(pvs) == 0:
        return dict(retcode=503, message='no pv deivces')

    vgs = yield from _vg_create(name, pvs)
    if vgs is None or len(vgs) == 0:
        return dict(retcode=504, message='create vg %s failure' % name)

    for vg in vgs:
        if vg.name != name:
            continue
        # save vg
        yield from vg.save()
        return dict(retcode=0, vg=vg)

    return dict(retcode=504, message='create vg %s failure' % name)


@post('/api/vgs/{id}/delete')
def api_delete_vg(*, id):
    '''
    Delete volume group. Request url:[POST /api/vgs/{id}/delete]
    '''
    vg = yield from VG.find(id)
    if not vg:
        raise APIResourceNotFoundError('vg %s' % id)

    r = yield from _vg_delete(vg)
    if r is None:
        return dict(retcode=505, message='delete vg failure')
    yield from vg.remove()
    return dict(retcode=0)


@post('/api/vgs/{id}')
def api_update_vg(id, request, *, name):
    '''
    Update volume group. Request url [POST /api/vgs/{id}]

    Post data:

        id: volume group id

        name: volume group name
    '''
    if not name or not name.strip():
        raise APIValueError('name:%s' % name)
    vg = yield from VG.find(id)
    if not vg:
        raise APIResourceNotFoundError('vg %s' % id)
    yield from _vg_rename(vg.name, name)
    vg.name = name
    yield from vg.update()
    return dict(retcode=0, vg=vg)
