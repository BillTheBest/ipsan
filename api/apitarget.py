# -*-coding: utf-8 -*-


import os
import re
import uuid
import logging
import asyncio
import subprocess
from apivg import _vg_display, _size_to_kb
from coroweb import get, post
from config import grgrant_prog
from models import Target, LUN
from errors import APIError, APIValueError, APIAuthenticateError, APIResourceNotFoundError

_iqn = 'iqn.2015-08.com.ubique:%s'

_tgtadm_cmd = '/usr/sbin/tgtadm --lld iscsi'
_tgtadm_show_target = _tgtadm_cmd + ' --mode target --op show'
_tgtadm_new_target = _tgtadm_cmd + ' --mode target --op new --tid %s --targetname %s'
_tgtadm_del_target = _tgtadm_cmd + ' --mode target --op delete --force --tid %s'
_tgtadm_new_lun = _tgtadm_cmd + ' --mode logicalunit --op new --tid %s --lun %s -b %s'
_tgtadm_acl_all = _tgtadm_cmd + '--mode target --op bind --tid %s -I ALL'

_re_target_name = re.compile(r'^[a-z_A-Z0-9]{1,20}')


_re_target = re.compile('^Target\s([1-9]+):\s([^\n]+)')
_re_target_driver = re.compile(r'^Driver:\s+([^\n]+)')
_re_target_state = re.compile(r'^State:\s+([^\n]+)')
_re_lun = re.compile(r'^LUN:[^0-9]+([1-9]{1}[0-9]{0,})')
_re_lun_name = re.compile(r'Backing store path:\s+([^\n]+)')
_re_lun_type = re.compile(r'Type:\s+([^\n]+)')
_re_lun_size = re.compile(r'^Size:\s+([^\s]+)\s([^\s]+)')

_lun_unknow_state = 0
_lun_active_state = 1
_lun_inactive_state = 2

_target_state = {
    'unknow': 0,
    'ready': 1,
    'inactive': 2
}


@asyncio.coroutine
def _parse_show_target(output):
    targets = []
    lines = output.split(os.linesep)
    for line in lines:
        line = line.strip()
        if len(line) == 0:
            continue
        r_target = _re_target.match(line)
        if r_target:
            target = Target()
            target.tid = r_target.group(1)
            target.iqn = r_target.group(2)
            colon_pos = target.iqn.rfind(':')
            target.name = target.iqn[colon_pos+1:] if colon_pos != -1 else None
            target.luns = []
            targets.insert(0, target)
        r_drive = _re_target_driver.match(line)
        if r_drive:
            targets[0].driver = r_drive.group(1)
        r_state = _re_target_state.match(line)
        if r_state:
            targets[0].state = _target_state.get(r_state.group(1), 0)
        r_lun = _re_lun.match(line)
        if r_lun:
            lun = LUN()
            lun.lid = int(r_lun.group(1))
            targets[0].luns.insert(0, lun)
        if len(targets[0].luns) > 0:
            r_lun_type = _re_lun_type.match(line)
            if r_lun_type:
                targets[0].luns[0].type = r_lun_type.group(1)
            r_lun_name = _re_lun_name.match(line)
            if r_lun_name:
                targets[0].luns[0].name = r_lun_name.group(1)
            r_lun_size = _re_lun_size.match(line)
            if r_lun_size:
                targets[0].luns[0].size = yield from _size_to_kb(r_lun_size.group(1), r_lun_size.group(2))

    return targets


@asyncio.coroutine
def _get_targets():
    targets = []
    try:
        output = subprocess.check_output(_tgtadm_show_target.split(' '), universal_newlines=True)
        targets = yield from _parse_show_target(output)
    except subprocess.CalledProcessError as e:
        logging.exception(e)
    return targets


def _save_target(target):
    target_conf_file = os.path.join('/etc/tgt/conf.d', '%s.conf' % target.iqn)
    target_conf = '''
        default-driver iscsi

        <target %s>
            %s
        </target>
    '''
    backing_stroe_list = ['backing-store %s' % lun.name for lun in target.luns]
    open(target_conf_file, 'w').write(target_conf % (target.iqn, os.linesep.join(backing_stroe_list)))


@asyncio.coroutine
def _get_next_tid():
    targets = _get_targets()
    tids = [target.tid for target in targets]
    # target id start from 1
    for i in range(1, 1000):
        if i not in tids:
            target = yield from Target.findall(where='tid=%s' % i)
            if target is None or len(target) == 0:
                return i


@get('/api/targets')
def api_targets(request):
    '''
    Get all targets. Request url:[GET /api/targets]
    '''
    targets = yield from Target.findall()
    if targets is None:
        targets = []

    targets_current = yield from _get_targets()
    targets_dict = dict()
    for target in targets_current:
        targets_dict[target.iqn] = target

    for target in targets:
        luns = yield from LUN.findall(where="tid='%s'" % target.id)
        if luns is None:
            luns = []
        target.luns=luns
        if target.iqn not in targets_dict:
            # inactive target and luns
            target.state = _target_state['inactive']
            yield from target.update()
            for lun in luns:
                lun.state = _lun_inactive_state
                yield from lun.update()
        else:
            target_cur = targets_dict[target.iqn]

            for lun in luns:
                exist = False
                for lun_cur in target_cur.luns:
                    if lun.lid == lun_cur.lid and lun.name == lun_cur.name and lun.type == lun_cur.type:
                        exist = True
                        break
                if not exist:
                    lun.state = _lun_inactive_state
                else:
                    lun.state = _lun_active_state
                yield from lun.update()
            for lun_cur in target_cur.luns:
                exist = False
                for lun in target.luns:
                    if lun.lid == lun_cur.lid and lun.name == lun_cur.name and lun.type == lun_cur.type:
                        exist = True
                        break
                if not exist:
                    # new added lun
                    lun_cur.id = uuid.uuid4().hex
                    lun_cur.tid = target.id
                    yield from lun_cur.save()

    iqns = [target.iqn for target in targets]
    for target in targets_current:
        if target.iqn not in iqns:
            target.id = uuid.uuid4().hex
            yield from target.save()
            for lun in target.luns:
                lun.id = uuid.uuid4().hex
                lun.tid = target.id
                yield from lun.save()
            targets.append(target)

    return dict(retcode=0, targets=targets)


@get('/api/targets/{id}')
def api_get_target(*, id):
    '''
    Get target by id. Request url[GET /api/targets/{id}]
    '''
    target = yield from Target.find(id)
    if target is None:
        raise APIResourceNotFoundError('target %s' % id)

    targets = yield from _get_targets()
    for target_cur in targets:
        if target_cur.iqn == target.iqn:
            target_cur.id = target.id
            return dict(retcode=0, target=target_cur)

    target.state = _target_state['inactive']
    yield from target.update()
    return dict(retcode=0, target=target)


@post('/api/targets')
def api_create_target(*, name, **kw):
    '''
    Create target. Request url:[POST /api/targets]

    Post data:

        name: target name

        lun0: lun_device0. example: /dev/vg0/lv0

        lun1: lun_device1. example: /dev/vg0/lv1

        ...
    '''
    if name is None or not name.strip():
        raise APIValueError('name')
    r = _re_target_name.match(name)
    print(r, r is None)
    if not _re_target_name.match(name):
        raise APIValueError('name')

    # valid lun
    luns = []
    for k, v in kw.items():
        if not k.startswith('lun'):
            continue
        if not os.path.exists(v):
            raise APIValueError('block %s not exists' % v)
        luns.append(v)

    target = yield from Target.findall(where="name='%s'" % name)
    if target and len(target) > 0:
        return dict(retcode=700, message='target %s already exists' % name)

    tid = yield from _get_next_tid()
    if tid is None:
        return dict(retcode=703, message='too many targets in this server')

    name = _iqn % name
    cmd = _tgtadm_new_target % (str(tid), name)
    # create target
    r = subprocess.call(cmd.split(' '))
    if r != 0:
        return dict(retcode=701, message='create target error')
    # enable all client to access target
    cmd = _tgtadm_acl_all % str(tid)
    r = subprocess.call(cmd.split(' '))
    if r != 0:
        return dict(retcode=701, message='enable target ACL to all fialure')


    # add lun
    lid = 0  #lun id start from 1
    for lun in luns:
        lid += 1
        cmd = _tgtadm_new_lun % (str(tid), str(lid), v)
        r = subprocess.call(cmd.split(' '))
        if r != 0:
            return dict(retcode=702, message='add lun %s to target error' % v)

    targets = yield from _get_targets()
    for target in targets:
        if target.iqn == name:
            target.id = uuid.uuid4().hex
            yield from target.save()
            for lun in target.luns:
                lun.id = uuid.uuid4().hex
                lun.tid = target.id
                yield from lun.save()

            return dict(retcode=0, target=target)

    # save target
    _save_target(target)
    return dict(retcode=701, target='create target error')


@post('/api/targets/{id}/delete')
def api_delete_target(*, id):
    '''
    Delete target. Request url[POST /api/targets/{id}/delete]
    '''
    target = yield from Target.find(id)
    if target is None:
        raise APIResourceNotFoundError('target %s' % id)

    cmd = _tgtadm_del_target % (target.tid)
    try:
        subprocess.check_output(cmd.split(' '))
    except subprocess.CalledProcessError as e:
        logging.exception(e)
        return dict(retcode=704, message='delete target error')

    # delete from db
    luns = yield from LUN.findall(where="tid='%s'" % target.id)
    for lun in luns:
        yield from lun.remove()
    yield from target.remove()
    return dict(retcode=0)
