# -*-coding: utf-8 -*-


import os
import re
import glob
import time
import logging
import shutil
import tempfile
import subprocess
from common import log_event, event_upgrade, event_upd_upgrade, grgrant_prog, work_dir

# uploads and upgrade dir
uploads_dir = os.path.join(work_dir, 'uploads')
update_dir = os.path.join(work_dir, 'update')


upgrade_file_pattern = 'goldenrod.IPSAN*.tar.gz'
ipsanapi = 'ipsanapi'
_re_status = re.compile(r'^([^\s]+)\s+([^\s]+)\s+pid\s(\d{4,5})')


def valid_upgrade(target):
    # TODO
    return True

def has_upgrade_file():
    target = os.path.join(uploads_dir, upgrade_file_pattern)
    files = glob.glob(target)
    return (files[0] if len(files) > 0 else None)


def check_upgrade():
    upgrade_file = has_upgrade_file()
    if upgrade_file is None:
        return

    exec_upgrade(upgrade_file)


def restart_service(service):
    return subprocess.call([grgrant_prog, 'supervisorctl', 'restart',  service])


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
            log_event(logging.ERROR, event_upgrade, 0, 'upgrade failure:%s %s %s' % (srv2, name2, pid2))
            return False
    return True


def exec_upgrade(file):
    logging.info("Ready to upgrade: %s." % os.path.basename(file))
    upgrade_dir = tempfile.mkdtemp()
    try:
        shutil.unpack_archive(file, upgrade_dir)
    except ValueError as e:
        logging.exception(e)
        os.remove(file)
        return
    except shutil.ReadError as e:
        logging.exception(e)
        os.remove(file)
        shutil.rmtree(upgrade_dir)
        return

    if not valid_upgrade(upgrade_dir):
        logging.error("Valid upgrade file %s failure." % os.path.basename(file))
        os.remove(file)
        shutil.rmtree(upgrade_dir)
        return

    # execute scrpit before upgrade
    r = subprocess.call('scripts/pre_upgrade.sh')
    logging.info("Execute pre update shell return %s" % r)

    # copy files
    upgrade_target = os.path.join(upgrade_dir, '*')
    r = subprocess.call('cp -af %s %s' % (upgrade_target, work_dir), shell=True)
    if r != 0:
        logging.error("Copy %s to %s warn: %s" % (upgrade_target, work_dir, r))

    # execute scrpit after upgrade
    r = subprocess.call('scripts/post_upgrade.sh')
    logging.info("Execute post update shell return %s" % r)

    # start ipsan
    r = restart_service(ipsanapi)
    if r != 0:
        # TODO rollback
        logging.error("Start Service %s failure." % ipsanapi)
        shutil.rmtree(upgrade_dir)
        os.remove(file)
        return

    # check upgrade success
    r = is_running(ipsanapi)
    if not r:
        logging.error("Service %s is not running." % ipsanapi)
        shutil.rmtree(upgrade_dir)
        os.remove(file)
        return

    logging.info("Service %s started,Upgrade success." % ipsanapi)
    # upgrade success
    log_event(logging.INFO, event_upgrade, event_upd_upgrade, '%s upgrade success' % os.path.basename(file))
    shutil.rmtree(upgrade_dir)
    # save this version
    if os.path.exists(update_dir):
        shutil.rmtree(update_dir)
    os.mkdir(update_dir)
    shutil.move(file, update_dir)
