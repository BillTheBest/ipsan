# -*-coding: utf-8 -*-


import os
import re
import json
import logging
import subprocess
import asyncio
from coroweb import get, post
from config import grgrant_prog
from models import *
from errors import APIError, APIValueError, APIAuthenticateError, APIResourceNotFoundError

_vg_status = {
    "unknow": 0,
    "resizable": 1,
    "active": 2,
    "inactive": 3
}

_vgscan_prog = '/sbin/vgscan'
_vgchange_prog = '/sbin/vgchange'
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
    subprocess.call([grgrant_prog, _vgscan_prog]);
    subprocess.call([grgrant_prog, _vgchange_prog, '-a', 'y']);
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

    Response:

        id: volume group guid

        name: volume group name

        state: volume group state. 0-unknow; 1-resizeable; 2-active; 3-inactive;

        size: volume group size(KB)
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
def api_create_vg(*, name, pv):
    '''
    Create volume group. Request url [POST /api/vgs]

    Post data:

        name: volume group name

        pv: physical volume array in json format. example: [/dev/md0, /dev/md1...]
    '''
    if not name or not name.strip():
        raise APIValueError('name')
    if not re.match(r'^[a-z_A-Z0-9]{1,20}', name):
        raise APIValueError("name")

    vg = yield from VG.findall(where="name='%s'" % name)
    if vg:
        return dict(retcode=501, message='Volume group %s already exists' % name)

    pvs_name = json.loads(pv)
    for pv_name in pvs_name:
            if not os.path.exists(pv_name):
                return dict(retcode=502, message='Invalid pv %s' % pv_name)

    if len(pvs_name) == 0:
        return dict(retcode=503, message='No physical volume')

    vgs = yield from _vg_create(name, pvs_name)
    if vgs is None or len(vgs) == 0:
        return dict(retcode=504, message='Create volume group %s failure' % name)

    for vg in vgs:
        if vg.name != name:
            continue
        # save vg
        yield from vg.save()
        yield from log_event(logging.INFO, event_vg, event_action_add,
                         'Create volume group %s.' % (vg.name))
        return dict(retcode=0, vg=vg)

    return dict(retcode=504, message='Create volume group %s failure' % name)


@post('/api/vgs/{id}/delete')
def api_delete_vg(*, id):
    '''
    Delete volume group. Request url:[POST /api/vgs/{id}/delete]
    '''
    vg = yield from VG.find(id)
    if not vg:
        raise APIResourceNotFoundError('vg %s' % id)

    vgs_current = yield from _vg_display()
    vg_id = None
    for v in vgs_current:
        if v.id == id:
            r = yield from _vg_delete(vg)
            if r is None:
                return dict(retcode=505, message='delete vg failure')
            break

    yield from vg.remove()
    yield from log_event(logging.INFO, event_vg, event_action_del,
                         'Delete volume group %s.' % (vg.name))
    return dict(retcode=0, id=id)


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

    if not re.match(r'^[a-z_A-Z0-9]{1,20}', name):
        raise APIValueError("name")

    vg = yield from VG.find(id)
    if not vg:
        raise APIResourceNotFoundError('vg %s' % id)
    yield from _vg_rename(vg.name, name)
    vg.name = name
    yield from vg.update()
    yield from log_event(logging.INFO, event_vg, event_action_mod,
                         'Update volume group name to %s.' % (vg.name))
    return dict(retcode=0, vg=vg)
