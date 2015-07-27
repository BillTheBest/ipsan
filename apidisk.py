# -*-coding: utf-8 -*-


import os
import asyncio
import logging
import subprocess
from coroweb import get, post
from config import grgrant_prog, grdisk_prog
from models import Disk


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
            if not fields[1].startswith('disk'):
                continue
            disk = Disk(id=fields[3], name=fields[2], slot=fields[0])
            disks.append(disk)
        print(disks)
        return disks
    except subprocess.CalledProcessError as e:
        logging.exception(e)
        pass


@get('/api/disks')
def api_disks():
    disks = yield from disk_list()
    return dict(retcode=0, disks=disks)
