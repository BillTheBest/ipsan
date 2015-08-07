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

_tgtadm_args = ['/usr/sbin/tgtadm', '--lld', 'iscsi']
_re_target = re.compile('^Target\s([1-9]+):\s([^\n]+)')
_re_target_driver = re.compile(r'^Driver:([^\n]+)')
_re_target_state = re.compile(r'^State:([^\n]+)')
_re_lun = re.compile(r'^LUN:[^0-9]+([1-9]{1}[0-9]{0,})')
_re_lun_name = re.compile(r'Backing store path:([^\n]+)')
_re_lun_type = re.compile(r'Type:([^\n]+)')
_re_lun_size = re.compile(r'^Size:\s+([^\s]+)\s([^\s]+)')


@asyncio.coroutine
def _parse_show_target(output):
    targets = []
    lines = output.split(os.linesep)
    for line in lines:
        line = line.strip()
        r_target = _re_target.match(line)
        if r_target:
            target = Target()
            target.id = uuid.uuid4().hex
            target.tid = r_target.group(1)
            target.iqn = r_target.group(2)
            colon_pos = target.iqn.rfind(':')
            target.name = target.iqn[colon_pos+1:] if colon_pos != -1 else None
            target.luns = []
            targets.insert(0, target)
        r_drive = _re_target_driver.match(line)
        if r_drive:
            targets[0].drive = r_drive.group(1)
        r_state = _re_target_state.match(line)
        if r_state:
            targets[0].state = r_state.group(1)
        r_lun = _re_lun.match(line)
        if r_lun:
            lun = LUN()
            lun.id = uuid.uuid4().hex
            lun.lid = r_lun.group(1)
            lun.tid = targets[0].id
            targets[0].luns.insert(0, lun)
            print('add lun')
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

    print(targets)
    return targets


@asyncio.coroutine
def _get_targets():
    targets = []
    args = _tgtadm_args
    args.extend(['--mode', 'target', '--op', 'show'])
    try:
        output = subprocess.check_output(args, universal_newlines=True)
        targets = yield from _parse_show_target(output)
    except subprocess.CalledProcessError as e:
        logging.exception(e)
    return targets


@get('/api/targets')
def api_targets(request):
    '''
    Get all targets. Request url:[GET /api/targets]
    '''
    targets = yield from Target.findall()
    if targets is None:
        targets = []

    state_changed = False
    targets_current = yield from _get_targets()
    targets_dict = dict()
    for target in targets_current:
        targets_dict[target.id] = target

    for target in targets:
        if target.id not in targets_dict:
            target.state = 'inactive'
            yield from target.update()

    target_id = [target.id for target in targets]
    for target in targets_current:
        if target.id not in target_id:
            yield from target.save()
            for lun in target.luns:
                yield from lun.save()
            targets.append(target)

    return dict(retcode=0, targets=targets)


