#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import os
import platform
import signal
import sys
import win32serviceutil
import win32service
import win32event

from config import Config
from functions import Handler, Server

PORT = 12345

log = logging.getLogger(__name__)


def daemonize(stdin='/dev/null', stdout='/dev/null', stderr='/dev/stderr'):
    """
    do the UNIX double-fork magic, see Stevens' "Advanced
    Programming in the UNIX Environment" for details (ISBN 0201563177)
    http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
    """
    try:
        pid = os.fork()
        if pid > 0:
            # exit first parent
            sys.exit(0)
    except OSError, e:
        sys.stderr.write("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
        sys.exit(1)

    # decouple from parent environment
    os.chdir("/")
    os.setsid()
    os.umask(0)

    # do second fork
    try:
        pid = os.fork()
        if pid > 0:
            # exit from second parent
            sys.exit(0)
    except OSError, e:
        sys.stderr.write("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
        sys.exit(1)

    # redirect standard file descriptors
    sys.stdout.flush()
    sys.stderr.flush()
    si = file(stdin, 'r')
    so = file(stdout, 'a+')
    se = file(stderr, 'a+', 0)
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())


def sigterm_handler(signal, frame):
    log.info('Agent stopped')
    sys.exit(0)


class HttpServerManager(win32serviceutil.ServiceFramework):
    _svc_name_ = "vagent"
    _svc_display_name_ = "vagent"
    _http_server = None

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self._http_server = Server(('', PORT), Handler, logRequests=False)
        self._http_server.register_introspection_functions()
        self._http_server.register_multicall_functions()
        from operations import WindowsOperations
        from functions import WindowsFunctions
        WindowsOperations.apply_config()
        self._http_server.register_instance(WindowsFunctions())
        print 'Service start.'

    def SvcDoRun(self):
        import servicemanager
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_, ''))
        self._http_server.serve_forever()
        return

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self._http_server.stop()
        win32event.SetEvent(self.hWaitStop)
        print 'Service stop'
        return


def serve_linux(daemon=False, do_log=False):
    server = Server(('', PORT), Handler, logRequests=False)
    server.register_introspection_functions()
    server.register_multicall_functions()

    Config.filename = \
        os.path.dirname(os.path.realpath(__file__)) + '/config.xml'
    Config.read_conf()
    Config.write_conf()

    if daemon and os.getppid() != 1:
        daemonize()
    signal.signal(signal.SIGTERM, sigterm_handler)

    dist = platform.dist()[0].lower()
    if dist in ['centos', 'redhat']:
        try:
            from lb_operations import LBCentOSOperations
            from lb_functions import LBCentOSFunctions
            LBCentOSOperations.apply_config()
            server.register_instance(LBCentOSFunctions())
            dist = 'centos-lb'
        except:
            from operations import CentOSOperations
            from functions import CentOSFunctions
            CentOSOperations.apply_config()
            server.register_instance(CentOSFunctions())
    elif dist == 'debian':
        from operations import DebianOperations
        from functions import DebianFunctions
        DebianOperations.apply_config()
        server.register_instance(DebianFunctions())
    elif dist == 'ubuntu':
        from operations import UbuntuOperations
        from functions import UbuntuFunctions
        UbuntuOperations.apply_config()
        server.register_instance(UbuntuFunctions())
    else:
        sys.stderr.write('System (%s, %s) not supported\n' % (system, dist))
        sys.exit(-1)

    log.info('Agent started for (%s, %s)' % (system, dist))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        os.kill(os.getpid(), signal.SIGTERM)


def serve_windows():
    win32serviceutil.HandleCommandLine(HttpServerManager)


if __name__ == '__main__':
    # daemonize
    daemon = True if '-d' in sys.argv else False
    do_log = True if '-l' in sys.argv else False
    log_level = logging.DEBUG if do_log else logging.CRITICAL

    log_filename = os.path.dirname(os.path.realpath(__file__)) + '/vagent.log'

    if daemon:
        log_handler = logging.FileHandler(log_filename)
    else:
        log_handler = logging.StreamHandler()
    log_formatter = logging.Formatter('%(asctime)s %(levelname)s '
                                      '%(module)s.%(funcName)s: %(message)s')
    log_handler.setFormatter(log_formatter)
    logger = logging.getLogger(__name__)
    logger.setLevel(log_level)
    logger.addHandler(log_handler)
    logger = logging.getLogger('config')
    logger.setLevel(log_level)
    logger.addHandler(log_handler)
    logger = logging.getLogger('functions')
    logger.setLevel(log_level)
    logger.addHandler(log_handler)
    logger = logging.getLogger('operations')
    logger.setLevel(log_level)
    logger.addHandler(log_handler)
    logger = logging.getLogger('lb_functions')
    logger.setLevel(log_level)
    logger.addHandler(log_handler)
    logger = logging.getLogger('lb_operations')
    logger.setLevel(log_level)
    logger.addHandler(log_handler)

    # Linux or Windows
    system = platform.system().lower()
    if system == 'linux':
        serve_linux(daemon, do_log)
    elif system == 'windows':
        serve_windows()
