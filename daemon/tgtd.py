# -*-coding: utf-8 -*-


import logging
import subprocess
from common import grgrant_prog

_tgtd_daemon = 'tgtd'


def is_tgtd_running():
    try:
        # check if tgt service started
        args = ['pidof', _tgtd_daemon]
        r = subprocess.check_output(args, universal_newlines=True)
        return (True if len(r.split(' ')) > 0 else False)
    except:
        return False


def start_tgtd():
    # start tgt service
    args = [grgrant_prog, '/usr/sbin/service', _tgtd_daemon, 'start']
    r = subprocess.call(args)
    if r != 0:
        logging.error('Start %s service error: %s' % (_tgtd_daemon, r))
    else:
        logging.info('Service %s started' % (_tgtd_daemon))


def check_tgtd():
    if not is_tgtd_running():
        logging.error('Service %s not running' % (_tgtd_daemon))
        start_tgtd()
