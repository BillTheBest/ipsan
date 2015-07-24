# -*-coding: utf-8 -*-


import os
import re
import uuid
import logging
import subprocess
import asyncio
import errors
from coroweb import get, post
from models import Array, Disk
from errors import APIError, APIValueError, APIAuthenticateError

_RE_RAID_DISK = re.compile(r'^([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([^/]+)([/a-zA-Z1-9]+)')
_RE_RAID_SIZE = re.compile(r'^[0-9]+')

grgrant_prog = os.path.join(os.path.dirname(os.path.abspath(__file__)), "grgrant")
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
                array.level = int(v[-1]);
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
            elif k.startswith('UUID'):
                array.id = v.strip()
            elif k.startswith('State'):
                array.state = v.strip()
            elif k.startswith('Array Size'):
                r = _RE_RAID_SIZE.match(v)
                if r:
                    array.capacity = int(r.group(0))
                    print(array.capacity, "KB")
            else:
                pass
        else:
            r = _RE_RAID_DISK.match(line)
            if not r:
                continue
            disk = dict()
            disk['name'] = r.group(6).strip()
            disk['state'] = r.group(5).strip()
            array.disks.append(disk)

    return array


def _array_create(level, disks, chunk=512, spares=None):
    pass


@asyncio.coroutine
def query_array(array):
    print("query array")
    print(grgrant_prog, mdadm_prog)
    with subprocess.Popen([grgrant_prog, mdadm_prog, "-D", array.device],
                          stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE) as p:

        output = p.stdout.read().decode('utf-8')
        # TODO: returncode will None when child process not terminated
        if p.returncode != 0:
            logging.error('%s=>%s' % (p.args, output))
        array_copy = yield from _array_parse_output(output)
        array_copy.name = array.name
        array = array_copy

    return array


@get('/api/arrays')
def api_arrays(request):
    arrays = yield from Array.findall()
    if arrays is None:
        return dict(retcode=0, message='no arrays')
    array_copy = []
    for array in arrays:
        array = yield from query_array(array)
        array_copy.append(array)
    arrays = array_copy
    return dict(retcode=0, arrays=arrays)


@post('/api/arrays')
def api_create_array(*, name, level, chunk_size, **kw):
    array = yield from Array.findall(where="name='%s'" % name)
    if array:
        return dict(retcode=401, message='array %s already exists' % name)

    disks = []
    spares = []
    for k, v in kw.items():
        if k.startswith('disk') or k.startswith('spare'):
            # check disk is valid
            disk = Disk.findall(where="name='%s'" % v)
            if disk is None:
                raise APIResourceNotFoundError('%s' % v)
            if k.startswith('disk'):
                disks.append(disk)
            else:
                spares.append(disk)

        print(k, "=", v)

    if disks is None:
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

    array = Array(name=name, device="/dev/md126", level=level,
                  chunk_size = chunk_size)
    yield from array.save()

    return dict(retcode=0, array=array)
