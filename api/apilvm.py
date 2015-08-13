# -*-coding: utf-8 -*-


import os
import re
import logging
import asyncio
import subprocess
from apivg import _vg_display, _size_to_kb
from coroweb import get, post
from config import grgrant_prog
from models import LVM
from errors import APIError, APIValueError, APIAuthenticateError, APIResourceNotFoundError


_lvm_status = {
    "unknow": 0,
    'available': 1,
    'inactive': 2
}

_lvdisplay_prog = '/sbin/lvdisplay'
_lvcreate_prog = '/sbin/lvcreate'
_lvremove_prog = '/sbin/lvremove'
_lvrename_prog = '/sbin/lvrename'

_lv_seperator = '--- Logical volume ---'

_re_lv_name = re.compile(r'^LV Name\s+(.+)')
_re_lv_path = re.compile(r'^LV Path\s+(.+)')
_re_vg_name = re.compile(r'^VG Name\s+(.+)')
_re_lv_uuid = re.compile(r'^LV UUID\s+(.+)')
_re_lv_size = re.compile(r'^LV Size\s+([^\s]+)\s(.+)')
_re_lv_stat = re.compile(r'^LV Status\s+(.+)')


@asyncio.coroutine
def _lvm_parse_display(output):
    lvms = []
    lines = output.split(os.linesep)
    for line in lines:
        line = line.strip()
        if line.startswith(_lv_seperator):
            lvm = LVM()
            lvms.insert(0, lvm)

        r_name = _re_lv_name.match(line)
        r_path = _re_lv_path.match(line)
        r_vgname = _re_vg_name.match(line)
        r_stat = _re_lv_stat.match(line)
        r_size = _re_lv_size.match(line)
        r_uuid = _re_lv_uuid.match(line)

        if r_name:
            lvms[0].name = r_name.group(1)
        if r_path:
            lvms[0].path = r_path.group(1)
        if r_vgname:
            lvms[0].vg_name = r_vgname.group(1)
        if r_stat:
            lvms[0].state = _lvm_status.get(r_stat.group(1), 0)
        if r_size:
            lvms[0].size = yield from _size_to_kb(r_size.group(1), r_size.group(2))
        if r_uuid:
            lvms[0].id = r_uuid.group(1).lower().replace('-', '')

    print(lvms)
    return lvms


@asyncio.coroutine
def _lvm_display():
    args = [grgrant_prog, _lvdisplay_prog]
    output = subprocess.check_output(args, universal_newlines=True)
    return (yield from _lvm_parse_display(output))


@asyncio.coroutine
def _lvm_create(name, vgname, size):
    args = [grgrant_prog, _lvcreate_prog, '-L', size, '-n', name, vgname]
    try:
        subprocess.check_output(args)
        return _lvm_display()
    except subprocess.CalledProcessError as e:
        logging.exception(e)


@asyncio.coroutine
def _lvm_delete(lvm):
    args = [grgrant_prog, _lvremove_prog, lvm.path, '--force']
    try:
        subprocess.check_output(args)
        return True
    except subprocess.CalledProcessError as e:
        logging.exception(e)


@asyncio.coroutine
def _lvm_rename(path, newname):
    subprocess.check_output([grgrant_prog, _lvrename_prog, path, newname])


@get('/api/lvms')
def api_lvms(request):
    '''
    Get all lvms. Request url:[GET /api/lvms]
    '''
    lvms = yield from LVM.findall()
    if lvms is None:
        lvms = []

    state_changed = False
    lvms_current = yield from _lvm_display()
    lvms_dict = dict()
    for lvm in lvms_current:
        lvms_dict[lvm.id] = lvm
    for lvm in lvms:
        if lvm.id not in lvms_dict:
            lvm.state = _lvm_status['inactive']
            state_changed = True
        else:
            lvm_cur = lvms_dict[lvm.id]
            if lvm_cur.name != lvm.name or lvm_cur.path != lvm.path:
                state_changed = True
                lvm = lvm_cur
        # keep lvm in database is latest
        if state_changed:
            yield from lvm.update()

    lvms_id= [lvm.id for lvm in lvms]
    for lvm in lvms_current:
        if lvm.id not in lvms_id:
            # save new added lvm to db
            yield from lvm.save()
            lvms.append(lvm)

    return dict(retcode=0, lvms=lvms)


@post('/api/lvms')
def api_lvm_create(*, name, vgname, size, unit):
    '''
    Create lvm. Request url:[POST /api/lvms]

    Post data:

        name: lvm name

        vgname: volume group name. reference:/api/vgs

        size: lvm size

        unit: lvm size unit. [K, M, G, T, P]
    '''
    if not name or not name.strip():
        raise APIValueError('name')
    if not size.isnumeric():
        raise APIValueError('size')
    if unit.upper() not in ['K','M','G','T','P']:
        raise APIValueError('unit value should be [K,M,G,T,P]')

    # validate vg
    vgs = yield from _vg_display()
    vgs_name = [vg.name for vg in vgs]
    if vgname not in vgs_name:
        raise APIResourceNotFoundError("vg '%s' not found" % vgname)

    lvm_size_str = '%s%s' % (size, unit)
    print(name, vgname, lvm_size_str)
    lvms = yield from _lvm_create(name, vgname, lvm_size_str)

    if lvms is None or len(lvms) == 0:
        return dict(retcode=604, message='create lvm failure')

    for lvm in lvms:
        if lvm.name != name:
            continue
        # save lvm
        yield from lvm.save()
        return dict(retcode=0, lvm=lvm)
    return dict(retcode=604, message='create lvm failure')


@post('/api/lvms/{id}/delete')
def api_delete_lvm(*, id):
    '''
    Delete lvm. Request url:[POST /api/lvms/{id}/delete]
    '''
    lvm = yield from LVM.find(id)
    if not lvm:
        raise APIResourceNotFoundError('lvm %s' % id)

    r = yield from _lvm_delete(lvm)
    if r is None:
        return dict(retcode=605, message='delete lvm failure')
    yield from lvm.remove()
    return dict(retcode=0)


@post('/api/lvms/{id}')
def api_update_lvm(id, request, *, name):
    '''
    Update lvm. Request url [POST /api/lvms/{id}]

    Post data:

        id: lvm id

        name: lvm name
    '''
    if not name or not name.strip():
        raise APIValueError('name:%s' % name)
    lvm = yield from LVM.find(id)
    if not lvm:
        raise APIResourceNotFoundError('vg %s' % id)
    yield from _lvm_rename(lvm.path, name)
    lvm.name = name
    yield from lvm.update()
    return dict(retcode=0, lvm=lvm)
