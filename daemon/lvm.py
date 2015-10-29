# -*-coding: utf-8 -*-


import os
import sqlite3
import logging
import subprocess
from common import grgrant_prog
from common import database


def fetch_all_lvm():
    with sqlite3.connect(database) as conn:
        c = conn.cursor()
        try:
            c.execute('select name, path from lvms')
            r = c.fetchall()
            return r
        except Exception as e:
            logging.exception(e)
            return None


def active_lvm(name, path):
    args = [grgrant_prog, '/sbin/vgchange', '-a', 'y']
    try:
        r = subprocess.check_output(args, universal_newlines=True)
        logging.info("Active lvm:%s path:%s success." % (name, path))
    except subprocess.CalledProcessError as e:
        logging.info("Active lvm:%s path:%s failure:" % (name, path))
        logging.exception(e)


def check_lvm():
    rs = fetch_all_lvm()
    if rs is None:
        return
    for r in rs:
        name = r[0]
        path = r[1]
        if not os.path.exists(path):
            active_lvm(name, path)


# if __name__ == '__main__':
    # check_lvm()
