# -*-coding: utf-8 -*-


import uuid
import time
import sqlite3
import logging


database = 'ipsan.db'


event_os = 1
event_os_reboot = 1
event_os_poweroff = 2
event_os_network = 3


event_upgrade = 2


def log_event(level, category, message, type=None):
    with sqlite3.connect(database) as conn:
        c = conn.cursor()
        try:
            args = [uuid.uuid4().hex,
                    level,
                    category,
                    type,
                    message,
                    int(time.time())]
            sql = 'insert into events (id, level, category, type, message, created_at)values(?,?,?,?,?,?)'
            c.execute(sql, args)
        except Exception as e:
            logging.exception(e)
