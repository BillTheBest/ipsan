# -*-coding: utf-8 -*-


import os
import time
import logging
import subprocess


last_mtime = None


def check_network():
    if not os.path.exists("grnet.cfg"):
        return

    global last_mtime
    mtime = os.stat("grnet.cfg").st_mtime

    if mtime != last_mtime:
        logging.info("Detect machine ip changed")
        last_mtime = mtime
        time.sleep(15)  # ensure ip setting effected
        subprocess.call("scripts/init_network.sh")
