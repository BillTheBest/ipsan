# -*-coding: utf-8 -*-


import os
import re
import json
import uuid
import logging
import subprocess
import asyncio
import errors
from config import grgrant_prog
from coroweb import get, post
from models import *
from errors import APIError, APIValueError, APIAuthenticateError, APIResourceNotFoundError

_RE_RAID_DISK = re.compile(r'^([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([^/]+)([/a-zA-Z1-9]+)')
_RE_RAID_SIZE = re.compile(r'^[0-9]+')


mdadm_prog = "/sbin/mdadm"


@asyncio.coroutine
def _array_parse_output(output):
    if output is None:
        return None

    array = Array()
    array.disks = []

    lines = output.split(os.linesep)
    for line in lines:
        line = line.strip()
        pair = line.split(':')
        if len(pair) == 2:
            k = pair[0].strip()
            v = pair[1].strip()
            if k.startswith('Raid Level'):
                array.level = int(v[4:]);
            elif k.startswith('Raid Devices'):
                array.raid_devices = int(v)
            elif k.startswith('Total Devices'):
                array.total_devices = int(v)
            elif k.startswith('Active Devices'):
                array.active_devices = int(v)
            elif k.startswith('Working Devices'):
                array.working_devices = int(v)
            elif k.startswith('Failed Devices'):
                array.failed_devices = int(v)
            elif k.startswith('Spare Devices'):
                array.spare_devices = int(v)
            elif k.startswith('State'):
                array.state = v.strip()
            elif k.startswith('Array Size'):
                r = _RE_RAID_SIZE.match(v)
                if r:
                    array.capacity = int(r.group(0))
            elif k.startswith('Chunk Size'):
                if v.endswith('K'):
                    array.chunk_size = int(v[:-1])
            else:
                pass
        elif line.startswith('UUID'):
            array.id = line[6:].strip().replace(':', '')
            print(array.id)
        else:
            r = _RE_RAID_DISK.match(line)
            if not r:
                continue
            disk = dict()

            disk['state'] = r.group(5).strip()
            disk['device'] = r.group(6).strip()
            # handle disk removed. (device will not shown)
            if not disk['device'].startswith('/'):
                disk['state'] += disk['device']
                disk['device'] = ""

            d = yield from Disk.findall(where="device='%s'" % disk['device'])
            if d and len(d) > 0:
                disk['name'] = d[0].name
                disk['capacity'] = d[0].capacity
            array.disks.append(disk)

    return array


@asyncio.coroutine
def _make_next_array_device():
    for i in range(128):
        devname = '/dev/md%s' % i
        if not os.path.exists(devname):
            arrays = yield from Array.findall(where="device='%s'" % devname)
            if arrays is None or len(arrays) == 0:
                return devname


@asyncio.coroutine
def _array_create(level, disks, chunk=512, spares=None):
    args = [grgrant_prog, mdadm_prog, '-C']
    device = yield from _make_next_array_device()
    if device is None:
        logging.error('create array failre. no more device name')
        return None
    args.append(device)
    args.append('-l')
    args.append(str(level))
    args.append('-n')
    args.append(str(len(disks)))
    if spares and len(spares) > 0:
        args.append('-x')
        args.append(str(len(spares)))

    args.extend(disks)
    args.append('--run') # ingore confirm

    try:
        subprocess.check_output(args, universal_newlines=True)
        return device
    except subprocess.CalledProcessError as e:
        logging.exception(e)


@asyncio.coroutine
def _array_detail(array):
    output = None
    try:
        output = subprocess.check_output([grgrant_prog, mdadm_prog, '-D',
                                          array.device],
                                         universal_newlines=True)
    except subprocess.CalledProcessError as e:
        logging.error(e.returncode, e.output)
        logging.exception(e)
        output = None

    if output:
        array_copy = yield from _array_parse_output(output)
        array_copy.name = array.name
        array_copy.device = array.device
        array_copy.created_at = array.created_at
        array = array_copy
    else:
        array.state = "Missing"
        array.raid_devices = 0
        array.active_devices = 0
        array.total_devices = 0
        array.working_devices = 0
        array.failed_devices = 0
        array.spare_devices = 0
        array.disks = []

    return array


@asyncio.coroutine
def _array_destroy(array, disks):
    retry_times = 3
    while os.path.exists(array.device) and retry_times > 0:
        try:
            # stop array
            subprocess.check_output([grgrant_prog, mdadm_prog, '-S', array.device],
                                        universal_newlines=True)

        except subprocess.CalledProcessError as e:
            logging.error(e.returncode, e.output, e.cmd)
            logging.exception(e)
        finally:
            retry_times -= 1

    if os.path.exists(array.device):
        return False

    try:
        # destroy array
        devices = [disk.name for disk in disks]
        args = [grgrant_prog, mdadm_prog, '--zero-superblock']
        args.extend(devices)
        subprocess.check_output(args, universal_newlines=True)
    except:
        pass
    return True


@get('/api/arrays')
def api_arrays(request):
    '''
    Get all arrays. Request url:[GET /api/arrays]

    Response:

        state: 0-unknow;

        device: array device name

        name: array name

        level: array level

        chunk_size: array chunk size(KB)

        capacity: array capacity(KB)

        created_at: array created time(seconds)
    '''
    arrays = yield from Array.findall()
    if arrays is None:
        return dict(retcode=0, message='no arrays')
    array_copy = []
    for array in arrays:
        array = yield from _array_detail(array)
        array_copy.append(array)
    arrays = array_copy
    return dict(retcode=0, arrays=arrays)


@get('/api/arrays/{id}')
def api_get_array(*, id):
    '''
    Get array by id. Request url[GET /api/arrays/{id}]
    '''
    array = yield from Array.find(id)
    if array is None:
        raise APIResourceNotFoundError('array %s not found' % id)

    array = yield from _array_detail(array)
    return dict(retcode=0, array=array)


@post('/api/arrays')
def api_create_array(*, name, level, chunk, disk, spare):
    '''
    Create array. Request url[POST /api/arrays]

    Post data:
        name: array name.

        level: array level. support RAID0, RAID1, RAID5, RAID6, RAID10.

        chunk: array chunk size. such as 64K,128K, 256K,512K. power of 2.

        disks: disk device array in json format. such as [/dev/sdb, /dev/sdc, /dev/sdd...]

        spares: spare disk device array in json format.
    '''

    if not re.match(r'^[a-z_A-Z0-9]{1,20}', name):
        raise APIValueError("name")
    array = yield from Array.findall(where="name='%s'" % name)
    if array:
        return dict(retcode=401, message='Array %s already exists' % name)

    data_devname= json.loads(disk)
    spare_devname = json.loads(spare)

    disks = []
    spares = []

    # valid disk
    for dev in data_devname:
        r = yield from Disk.findall(where="device='%s'" % dev)
        if not r or len(r) == 0:
            raise APIResourceNotFoundError('%s' % dev)
        disks.append(r[0])

    for dev in spares:
        r = yield from Disk.findall(where="device='%s'" % dev)
        if not r or len(r) == 0:
            raise APIResourceNotFoundError('%s' % dev)
        spares.append(r[0])

    if len(disks) == 0:
        return dict(retcode=403, message='No available data disk')

    if not level.isnumeric():
        raise APIValueError('level')
    at_least_disk = {0: 2, 1: 2, 5: 3, 6: 3, 10: 2}
    level = int(level)
    if level not in at_least_disk:
        return dict(retcode=402, message='Invalid raid level %s' % level)
    if len(disks) < at_least_disk[level]:
        return dict(retcode=404, message='Raid %s need at least %s disks' %
                    (level, at_least_disk[level]))

    array_device = yield from _array_create(level, data_devname, chunk, spare_devname)

    if array_device is None:
        return dict(retcode=405, message='Create array failure.No available device')

    array = Array(name=name, device=array_device, level=level, chunk_size=chunk, created_at=int(time.time()))
    array = yield from _array_detail(array)
    yield from array.save()

    # update array id of each array disk
    for disk in  disks:
        disk.used_by = array.id
        disk.used_for = 1 # 1 for raid
        yield from disk.update()

    yield from log_event(logging.INFO, event_array, event_action_add,
                         'Create array %s.level:%s,data disk:%s,spare:%s' % (name, level, ','.join(data_devname), ','.join(spare_devname)))
    return dict(retcode=0, array=array)


@post('/api/arrays/{id}/delete')
def api_delete_array(*, id):
    '''
    Delete array. Request url:[POST /api/arrays/{id}/delete]
    '''
    array = yield from Array.find(id)
    if array is None:
        raise APIResourceNotFoundError('array %s' % id)
    disks = yield from Disk.findall(where="used_by='%s'" % id)
    r = yield from _array_destroy(array, disks)
    if not r:
        return dict(retcode=406, message='delete array %s failure' % id)

    yield from array.remove()
    for disk in disks:
        disk.used_by = ''
        disk.used_for = 0
        disk.state = 0
        yield from disk.update()

    yield from log_event(logging.INFO, event_array, event_action_del,
                         "Delete array %s" % array.name)
    return dict(retcode=0, id=id)
