# -*-coding: utf-8 -*-


import os
import re
import glob
import time
import logging
import shutil
import tempfile
import subprocess
from network import grgrant_prog
from event import log_event, event_upgrade


upgrade_file_pattern = 'goldenrod-IPSAN*.tar.gz'
uploads_dir = 'uploads'
update_dir = 'update'
ipsanapi = 'ipsanweb'
_re_status = re.compile(r'^([^\s]+)\s+([^\s]+)\s+pid\s(\d{4,5})')

logging.basicConfig(level=logging.INFO, filename='console.log')


def has_upgrade_file():
    target = os.path.join(uploads_dir, upgrade_file_pattern)
    files = glob.glob(target)
    return (files[0] if len(files) > 0 else None)


def check_upgrade():
    upgrade_file = has_upgrade_file()
    if upgrade_file is None:
        return

    exec_upgrade(upgrade_file)


def valid_upgrade(upgrade_dir):
    for root, dirs, files in os.walk(upgrade_dir):
        for dir in dirs:
            pass
        for file in files:
            pass
    return True


def stop_service(service):
    return subprocess.call([grgrant_prog, 'supervisorctl', 'stop', service])


def start_service(service):
    return subprocess.call([grgrant_prog, 'supervisorctl', 'start',  service])


def status_service(service):
    try:
        output = subprocess.check_output([grgrant_prog, 'supervisorctl', 'status', service], universal_newlines=True)
        r = _re_status.match(output)
        if r:
            return r.group(1), r.group(2), r.group(3)
    except subprocess.CalledProcessError as e:
        logging.exception(e)
    return None, None, None


def is_running(service):
    srv, status , pid = status_service(service)
    if not status or not pid:
        return False

    # assume progress started after program runing duration 5 seconds
    for i in range(5):
        time.sleep(1)
        srv2, status2, pid2 = status_service(service)
        if srv2 != srv or status2 != 'RUNNING' or pid != pid2:
            log_event(logging.ERROR, event_upgrad, 'upgrade failure:%s %s %s' % (srv2, name2, pid2))
            return False
    return True


def exec_upgrade(file):
    upgrade_dir = tempfile.mkdtemp()
    shutil.unpack_archive(file, upgrade_dir)
    if not valid_upgrade(upgrade_dir):
        return

    # stop ipsan web api
    r = stop_service(ipsanapi)
    if r != 0:
        logging.error('stop ipsan error. %s' % r)
        return
    # copy files
    upgrade_target = os.path.join(upgrade_dir, '*')
    r = subprocess.call('cp -af %s .' % upgrade_target, shell=True)
    if r != 0:
        return
    # start ipsan
    r = start_service(ipsanapi)
    if r != 0:
        log_event(logging.ERROR, event_upgrade, '%s:start service %s failure' % (os.path.basename(file), ipsanapi))
        # TODO rollback
        return

    # check upgrade success
    r = is_running(ipsanapi)
    if not r:
        # TODO rollback
        return

    # upgrade success
    log_event(logging.INFO, event_upgrade, '%s upgrade success' % os.path.basename(file))
    shutil.rmtree(upgrade_dir)
    # save this version
    if os.path.exists(update_dir):
        shutil.rmtree(update_dir)
    os.mkdir(update_dir)
    shutil.move(file, update_dir)
