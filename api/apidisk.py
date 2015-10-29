# -*-coding: utf-8 -*-


import os
import asyncio
import logging
import subprocess
from coroweb import get, post
from config import grgrant_prog, grdisk_prog, configs
from models import Disk

_exclude_slot = ['61', '62']

_disk_normal_state = 0
_disk_missing_state = 1


_panel_map = {
    2 : {3: 1, 2: 2, 4: 3, 5: 4, 9: 5, 6: 6},
    3 : {3: 1, 2: 2, 4: 3, 5: 4, 9: 5, 6: 6, 8: 7, 7: 8},
    4 : {3: 1, 2: 2, 4: 3, 5: 4, 9: 5, 6: 6, 8: 7, 7: 8},
    5 : {3: 1, 2: 2, 4: 3, 5: 4, 9: 5, 6: 6, 8: 7, 7: 8, 10: 9},
    6 : {3: 1, 2: 2, 4: 3, 5: 4, 9: 5, 6: 6, 8: 7, 7: 8},
    7 : {3: 1, 2: 2, 4: 3, 5: 4, 9: 5, 6: 6, 8: 7, 7: 8, 9: 9, 10: 10, 11: 11, 12: 12, 13: 13, 14: 14, 15: 15, 16: 16},
    8 : {3: 1, 2: 2, 4: 3, 5: 4, 9: 5, 6: 6, 8: 7, 7: 8, 9: 9, 10: 10, 11: 11, 12: 12, 13: 13, 14: 14, 15: 15, 16: 16}
}


def get_slot(slot):
    slot = int(slot)
    if configs.sysinfo.panel in _panel_map:
        panel_map = _panel_map[configs.sysinfo.panel]
        if slot in panel_map:
            return panel_map[slot]
        else:
            return slot % configs.sysinfo.panel


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

        state: 0-normal; 1-missing
    '''
    disks_cur = yield from disk_list()
    disk_ids = [disk.id for disk in disks_cur]
    for disk in disks_cur:
        r =  yield from Disk.find(disk.id)
        if r is None:
            yield from disk.save()
    disks_in_db = yield from Disk.findall()
    for disk in disks_in_db:
        d = [disk_cur for disk_cur in disks_cur if disk_cur.id == disk.id]
        if (len(d) != 0):
            disk_cur = d[0]
            if disk.state == _disk_missing_state:
                disk.state = _disk_normal_state
                yield from disk.update()
            if disk.device != disk_cur.device:
                disk.device = disk_cur.device
                yield from disk.update()
        else:
            disk.state = _disk_missing_state
            yield from disk.update()

    return dict(retcode=0, disks=disks_in_db)
