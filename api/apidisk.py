# -*-coding: utf-8 -*-


import os
import asyncio
import logging
import subprocess
from coroweb import get, post
from config import grgrant_prog, grdisk_prog, configs
from config_defaults import g_panel_map
from models import Disk

_exclude_slot = ['61', '62']

_disk_normal_state = 0
_disk_abnormal_state = 1

disk_slot_map = []

def get_avail_slot(count):
    for i in range(1, count):
        if i not in disk_slot_map:
            disk_slot_map.append(i)
            return i
    return None


def get_slot(slot):
    slot = int(slot)
    if configs.sysinfo.panel in g_panel_map:
        panel_map = g_panel_map[configs.sysinfo.panel]
        if slot in panel_map:
            disk_slot_map.append(panel_map[slot])
            return panel_map[slot]
        else:
            return get_avail_slot(len(panel_map)+1)


@asyncio.coroutine
def disk_list():
    try:
        output = subprocess.check_output([grgrant_prog, grdisk_prog, 'list'],
                                         universal_newlines=True)

        lines = output.split(os.linesep)
        disks = []
        for line in lines:
            fields = line.split(' ')
            if len(fields) < 8:
                return disks
            if not fields[1].startswith('disk') or fields[0] in _exclude_slot:
                continue
            slot = get_slot(fields[0])
            disk = Disk(id=fields[3], device=fields[2], name=fields[5], slot=slot)
            disk.capacity=fields[6];
            disks.append(disk)
        return disks
    except subprocess.CalledProcessError as e:
        logging.exception(e)
        pass


@get('/api/disks')
def api_disks():
    '''
    Get all disk. Request url [GET /api/disks]

    Response:

        id: disk identity

        slot: disk slot on machine

        device: disk device name

        name: disk name

        capacity: disk capacity(Bytes)

        state: 0-normal; 1-abnormal
    '''
    disks_cur = yield from disk_list()
    disk_ids = [disk.id for disk in disks_cur]
    for disk in disks_cur:
        r =  yield from Disk.find(disk.id)
        if r is None:
            if disk.capacity == 0:
                disk.state = _disk_abnormal_state
            yield from disk.save()
    disks_in_db = yield from Disk.findall()
    if disks_in_db:
        for disk in disks_in_db:
            d = [disk_cur for disk_cur in disks_cur if disk_cur.id == disk.id]
            if (len(d) != 0):
                disk_cur = d[0]
                if disk.state == _disk_abnormal_state:
                    disk.state = _disk_normal_state
                    yield from disk.update()
                    if disk.device != disk_cur.device:
                        disk.device = disk_cur.device
                        yield from disk.update()
                    else:
                        disk.state = _disk_abnormal_state
                        yield from disk.update()
                else:
                    if disk.capacity == 0:
                        disk.state = _disk_abnormal_state
                        yield from disk.update()
            else:
                # disk.state = _disk_abnormal_state;
                yield from disk.remove();
                # yield from disk.update()

    return dict(retcode=0, disks=disks_in_db)
