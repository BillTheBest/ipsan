# -*-coding: utf-8 -*-


import os
import re
import uuid
import json
import logging
import asyncio
import subprocess
from apivg import _vg_display, _size_to_kb
from coroweb import get, post
from config import grgrant_prog
from models import *
from errors import APIError, APIValueError, APIAuthenticateError, APIResourceNotFoundError

_iqn = 'iqn.2015-08.com.ubique:%s'

_tgtadm_cmd = '%s /usr/sbin/tgtadm --lld iscsi' % grgrant_prog
_tgtadm_show_target = _tgtadm_cmd + ' --mode target --op show'
_tgtadm_new_target = _tgtadm_cmd + ' --mode target --op new --tid %s --targetname %s'
_tgtadm_del_target = _tgtadm_cmd + ' --mode target --op delete --force --tid %s'
_tgtadm_new_lun = _tgtadm_cmd + ' --mode logicalunit --op new --tid %s --lun %s -b %s'
_tgtadm_acl_all = _tgtadm_cmd + ' --mode target --op bind --tid %s -I ALL'

_re_target_name = re.compile(r'^[a-z_A-Z0-9]{1,20}')


_re_target = re.compile('^Target\s([1-9]+):\s([^\n]+)')
_re_target_driver = re.compile(r'^Driver:\s+([^\n]+)')
_re_target_state = re.compile(r'^State:\s+([^\n]+)')
_re_lun = re.compile(r'^LUN:[^0-9]+([1-9]{1}[0-9]{0,})')
_re_lun_name = re.compile(r'Backing store path:\s+([^\n]+)')
_re_lun_type = re.compile(r'Type:\s+([^\n]+)')
_re_lun_size = re.compile(r'^Size:\s+([^\s]+)\s([^\s]+)')
_re_nexus = re.compile(r'^I_T nexus:\s+([^\n]+)')
_re_initiator_name = re.compile(r'^Initiator:\s+([^\s]+)')
_re_initiator_conn = re.compile(r'^Connection:\s+([^\n]+)')
_re_initiator_addr = re.compile(r'^IP Address:\s+([^\n]+)')

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
        r = _re_target.match(line)
        if r:
            target = Target()
            target.tid = r.group(1)
            target.iqn = r.group(2)
            colon_pos = target.iqn.rfind(':')
            target.name = target.iqn[colon_pos+1:] if colon_pos != -1 else None
            target.luns = []
            target.sessions = []
            targets.insert(0, target)
        r = _re_target_driver.match(line)
        if r:
            targets[0].driver = r.group(1)
        r = _re_target_state.match(line)
        if r:
            targets[0].state = _target_state.get(r.group(1), 0)

        if len(targets) > 0:
            r = _re_nexus.match(line)
            if r:
                session = dict()
                session['sid'] = int(r.group(1))
                targets[0].sessions.insert(0, session)
        if len(targets) > 0 and len(targets[0].sessions) > 0:
            r = _re_initiator_name.match(line)
            if r:
                targets[0].sessions[0]['initiator'] = r.group(1)
            r = _re_initiator_conn.match(line)
            if r:
                targets[0].sessions[0]['cid'] = int(r.group(1))
                targets[0].sessions[0]['connections'] = []
            r = _re_initiator_addr.match(line)
            if r:
                targets[0].sessions[0]['connections'].append(r.group(1))

        r = _re_lun.match(line)
        if r:
            lun = LUN()
            lun.lid = int(r.group(1))
            targets[0].luns.insert(0, lun)
        if len(targets[0].luns) > 0:
            r = _re_lun_type.match(line)
            if r:
                targets[0].luns[0].type = r.group(1)
            r = _re_lun_name.match(line)
            if r:
                targets[0].luns[0].name = r.group(1)
            r = _re_lun_size.match(line)
            if r:
                targets[0].luns[0].size = yield from _size_to_kb(r.group(1), r.group(2))

    return targets


@asyncio.coroutine
def _get_targets():
    try:
        output = subprocess.check_output(_tgtadm_show_target.split(' '), universal_newlines=True)
        targets = yield from _parse_show_target(output)
        return targets
    except subprocess.CalledProcessError as e:
        logging.exception(e)
        return []


def _save_target(target):
    target_conf_file = os.path.join('/etc/tgt/conf.d', '%s.conf' % target.iqn)
    with open(target_conf_file, 'w') as f:
        f.write('<target %s>\n' % target.iqn)
        for lun in target.luns:
            f.write('    backing-store %s\n' % lun.name)
        f.write('    controller_tid %s\n' % target.tid)
        f.write('</target>')


@asyncio.coroutine
def _get_next_tid():
    targets = yield from _get_targets()
    if targets is None:
        return None
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

    Response data:

        target state: 0-unknow; 1-ready; 2-inactive;

        lun state: 0-unknow; 1-active; 2-inactive;
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
            target.sessions = []
            yield from target.update()
            for lun in luns:
                lun.state = _lun_inactive_state
                yield from lun.update()
        else:
            target_cur = targets_dict[target.iqn]
            target.sessions = target_cur.sessions

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
def api_create_target(*, name, tid, type,  lun):
    '''
    Create target. Request url:[POST /api/targets]

    Post data:

        name: target name

        tid: target id in numeric. ensure the tid is unique when exists multiple ipsan server

        type: 1-lvm; 2-disk;

        lun: lun device array. example: [/dev/vg0/lv0,...]
        ...
    '''
    if name is None or not name.strip():
        raise APIValueError('name')
    if not _re_target_name.match(name):
        raise APIValueError('name')

    if not type.isnumeric():
        raise APIValueError("type")

    if not tid.isnumeric():
        raise APIValueError("target id")

    tid = int(tid)

    if tid <= 0 or tid > 1000:  # assume max tid is 1000
        raise APIValueError("target id(number)")

    ct = int(type)

    # valid lun
    luns = json.loads(lun)
    if not luns or len(luns) == 0:
        raise APIValueError("lun")

    for lun in luns:
        if not os.path.exists(lun):
            raise APIValueError('Lun %s not exists' % lun)

    target = yield from Target.findall(where="tid=%s" % tid)
    if target and len(target) > 0:
        return dict(retcode=701, message='target id %s already exists' % tid)

    target = yield from Target.findall(where="name='%s'" % name)
    if target and len(target) > 0:
        return dict(retcode=700, message='target %s already exists' % name)

    # get tid from user input
    # tid = yield from _get_next_tid()
    # if tid is None:
    #    return dict(retcode=703, message='too many targets in this server')

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
        return dict(retcode=701, message='enable target ACL to all failure')


    # add lun
    lid = 0  #lun id start from 1
    for lun in luns:
        lid += 1
        cmd = _tgtadm_new_lun % (str(tid), str(lid), lun)
        r = subprocess.call(cmd.split(' '))
        if r != 0:
            return dict(retcode=702, message='add lun %s to target error' % lun)

    targets = yield from _get_targets()
    for target in targets:
        if target.iqn == name:
            target.id = uuid.uuid4().hex
            yield from target.save()
            for lun in target.luns:
                lun.id = uuid.uuid4().hex
                lun.tid = target.id
                yield from lun.save()
                if ct == 2:
                    r = yield from Disk.findall(where="device='%s'" % lun.name)
                    if r and len(r) > 0:
                        disk = r[0]
                        disk.used_by = target.id
                        disk.used_for = 2 # used for target
                        yield from disk.update()

            # save target
            _save_target(target)
            yield from log_event(logging.INFO, event_target, event_action_add,
                         'Create target %s.' % (target.iqn))
            return dict(retcode=0, target=target)

    # create target error
    return dict(retcode=701, target='create target error')


@post('/api/targets/{id}/delete')
def api_delete_target(*, id):
    '''
    Delete target. Request url[POST /api/targets/{id}/delete]
    '''
    target = yield from Target.find(id)
    if target is None:
        raise APIResourceNotFoundError('target %s' % id)

    targets = yield from _get_targets()
    target_names = [target.name for target in targets]

    if target.name in target_names:
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
    yield from log_event(logging.INFO, event_target, event_action_del,
                         'Delete target %s.' % (target.iqn))

    # reset disk user information
    disks = yield from Disk.findall(where="used_by='%s'" % id)
    if disks and len(disks) > 0:
        for disk in disks:
            disk.used_by = ''
            disk.used_for = 0
            yield from disk.update()

    target_conf_file = os.path.join('/etc/tgt/conf.d', '%s.conf' % target.iqn)
    if os.path.exists(target_conf_file):
        os.remove(target_conf_file)

    return dict(retcode=0, id=id)
