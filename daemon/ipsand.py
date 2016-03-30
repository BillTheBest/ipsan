# -*-coding: utf-8 -*-


import os
import time
import logging
import subprocess
from upgrade import check_upgrade
from network import check_network
from tgtd import check_tgtd
from lvm import check_lvm



# class IPSanDaemon(Daemon): use supervisor instead
class IPSanDaemon():
    def run(self):
        logging.info("Service ipsand started.")
        # can not get network info imediately after reboot
        # so, I put initial network script here
        init_script = "scripts/init_network.sh"
        if os.path.exists(init_script):
            subprocess.call(init_script)
        while True:
            check_tgtd()
            check_lvm()
            check_upgrade()
            check_network()
            time.sleep(5)
        logging.info("Service ipsand stopped.")


# usage = "Usage: {0} start | stop | restart\n".format(sys.argv[0])

if __name__ == '__main__':
    """daemon = IPSanDaemon('/tmp/ipsand.pid')

    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        else:
            sys.stderr.write(usage)
            sys.exit(2)
        sys.exit(0)
    else:
        sys.stderr.write(usage)
        sys.exit(1)"""
    # cretea log directory if not exist
    log_dir = "log"
    if not os.path.exists(log_dir):
        os.mkdir(log_dir)

    logging.basicConfig(level=logging.INFO,
                        filename=os.path.join(log_dir, "daemon.log"),
                        format='%(asctime)s %(levelname)s:%(message)s')

    # start ipsand
    daemon = IPSanDaemon()
    daemon.run()
