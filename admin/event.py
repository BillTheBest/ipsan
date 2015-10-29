# -*-coding: utf-8 -*-


import uuid
import time
import sqlite3
import logging


database = 'ipsan.db'

event_category = 3  # events from admin

event_os = 1
event_os_reboot = 7
event_os_poweroff = 8
event_os_network = 9


def log_event(level, type, action, message):
    with sqlite3.connect(database) as conn:
        c = conn.cursor()
        try:
            args = [uuid.uuid4().hex,
                    level,
                    event_category,
                    type,
                    action,
                    message,
                    int(time.time())]
            sql = 'insert into events (id, level, category, type, action, message, created_at)values(?,?,?,?,?,?,?)'
            c.execute(sql, args)
        except Exception as e:
            logging.exception(e)
