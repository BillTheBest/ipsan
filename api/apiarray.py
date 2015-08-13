# -*-coding: utf-8 -*-


import os
import re
import uuid
import logging
import subprocess
import asyncio
import errors
from config import grgrant_prog
from coroweb import get, post
from models import Array, Disk, log_event
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
            disk['name'] = r.group(6).strip()
            disk['state'] = r.group(5).strip()
            array.disks.append(disk)

    return array


@asyncio.coroutine
def _make_next_array_device():
    for i in range(128):
        devname = '/dev/md%s' % i
        if not os.path.exists(devname):
            arrays = Array.findall(where="device='%s'" % devname)
            if arrays is None:
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
    args.append(level)
    args.append('-n')
    args.append(len(disks))
    if spares and len(spares) > 0:
        args.append('-x')
        args.append(len(spares))

    args.extend(disks)
    args.append('--run') # ingore confirm

    try:
        subprocess.check_output(args, universal_newlines=True)
        return device
    except subprocess.CalledProcessError as e:
        logging.error(e.returncode, e.output, e.cmd)
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
        array = array_copy

    return array


@asyncio.coroutine
def _array_destroy(array, disks):
    try:
        # stop array
        if os.path.exists(array.device):
            subprocess.check_output([grgrant_prog, mdadm_prog, '-S', array.device],
                                universal_newlines=True)

    except subprocess.CalledProcessError as e:
        logging.error(e.returncode, e.output, e.cmd)
        logging.exception(e)
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
def api_create_array(*, name, level, chunk, **kw):
    '''
    Create array. Request url[POST /api/arrays]

    Post data:
        name: array name.

        level: array level. support RAID0, RAID1, RAID5, RAID6, RAID10.

        chunk: array chunk size. such as 64K,128K, 256K,512K. power of 2.

        disk0: disk device name.

        disk1: disk device name.

        ...

        diskN: disk devie name.

        spare0: spare disk device name.

        spare1: spare disk device name.

        ...

        spareN: spare disk device name.
    '''
    array = yield from Array.findall(where="name='%s'" % name)
    if array:
        return dict(retcode=401, message='array %s already exists' % name)

    disks = []
    spares = []
    for k, v in kw.items():
        if k.startswith('disk') or k.startswith('spare'):
            # check disk is valid
            disk = yield from Disk.findall(where="name='%s'" % v)
            if len(disk) == 0:
                raise APIResourceNotFoundError('%s' % v)
            if k.startswith('disk'):
                disks.append(disk)
            else:
                spares.append(disk)

    if len(disks) == 0:
        return dict(retcode=403, message='no raid disk choosen')

    if not level.isnumeric():
        raise APIValueError('level')
    at_least_disk = {0: 2, 1: 2, 5: 3, 6: 3, 10: 2}
    level = int(level)
    if level not in at_least_disk:
        return dict(retcode=402, message='Invalid raid level %s' % level)
    if len(disks) < at_least_disk[level]:
        return dict(retcode=404, message='Raid %s need at least %s didks' %
                    (level, at_least_disk[level]))

    disk_devices = [disk.name for disk in disks]
    spare_deivces = [spare.name for spare in spares]
    array_device = yield from _array_create(level, disk_devices, chunk, spare_devices)

    if array_device is None:
        return dict(retcode=405, message='create array failure')

    array = Array(name=name, device=array_device, level=level, chunk=chunk)
    yield from array.save()
    array = yield from _array_detail(array)
    # update array id of each array disk
    for disk in  disks:
        disk.array_id = array.id
        yield from disk.update()

    return dict(retcode=0, array=array)


@post('/api/arrays/{id}/delete')
def api_delete_array(*, id):
    '''
    Delete array. Request url:[POST /api/arrays/{id}/delete]
    '''
    array = yield from Array.find(id)
    if array is None:
        raise APIResourceNotFoundError('array %s not found' % id)
    disks = yield from Disk.findall(where="array_id='%s'" % id)
    r = yield from _array_destroy(array, disks)
    if not r:
        return dict(retcode=406, message='delete array %s failure' % id)

    yield from array.remove()
    for disk in disks:
        disk.array_id = ''
        disk.state = 0
        yield from disk.update()

    return dict(retcode=0)
