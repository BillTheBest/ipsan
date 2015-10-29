# -*-coding: utf-8 -*-


import sys
import os
import atexit
import time
import signal


class Daemon:
    """ A generic daemon class

    Usage: subclass the Daemon class and overwrite the run() method."""

    def __init__(self, pidfile):
        self.pidfile = pidfile

    def daemonize(self):
        """ Daemon class. use double fork mechanism"""

        try:
            pid = os.fork()

            if pid > 0:
                # exit first parent
                sys.exit(0)
        except OSError as e:
            sys.stderr.write("fork #1 failed: {0}\n".format(e))
            sys.exit(1)

        os.chdir('/')
        os.setsid()
        os.umask(0)

        try:
            pid = os.fork()

            if pid > 0:
                # exit second parent
                sys.exit(0)
        except OSError as e:
            sys.stderr.write("fork #2 failed: {0}\n".format(e))
            sys.exit(1)

        sys.stdout.flush()
        sys.stderr.flush()
        si = open(os.devnull, 'r')
        so = open(os.devnull, 'a+')
        se = open(os.devnull, 'a+')

        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

        atexit.register(self.delpid)

        pid = str(os.getpid())
        with open(self.pidfile, 'w+') as f:
            f.write(pid + '\n')

    def delpid(self):
        os.remove(self.pidfile)

    def start(self):
        """ Start the daemon """

        # check the pidfile
        try:
            with open(self.pidfile, 'r') as pf:
                pid = int(pf.read().strip())
        except IOError:
            pid = None

        if pid:
            sys.stderr.write("pidfile {0} already exist.\n".format(pid))
            sys.exit(1)

        # start daemon
        self.daemonize()
        self.run()

    def stop(self):
        """ Stop the daemon """

        try:
            with open(self.pidfile) as pf:
                pid = int(pf.read().strip())
        except IOError:
            pid = None

        if not pid:
            sys.stderr.write("pidfile {0} does not exist.\n")
            return

        try:
            while 1:
                os.kill(pid, signal.SIGTERM)
                time.sleep(0.1)
        except OSError as e:
            e = str(e.args)
            if e.find("No such process") > 0:
                if os.path.exists(self.pidfile):
                    os.remove(self.pidfile)
            else:
                sys.stderr.write("stop failed {0}.\n".format(e))
                sys.exit(1)

    def restart(self):
        """ Restart the daemon """
        self.stop()
        self.start()

    def run(self):
        """ You should overwrite this method when you subclass Daemon """
