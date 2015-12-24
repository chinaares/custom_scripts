#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import os
import platform
import signal
import sys

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
    dist = platform.dist()[0].lower()

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
    
    if os.path.exists('/etc/arch-release'):
        dist = 'arch'
    
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
            CentOSOperations.init_dns_config()
            server.register_instance(CentOSFunctions())
    elif dist == 'debian':
        from operations import DebianOperations
        from functions import DebianFunctions
        DebianOperations.apply_config()
        DebianOperations.init_dns_config()
        server.register_instance(DebianFunctions())
    elif dist == 'ubuntu':
        from operations import UbuntuOperations
        from functions import UbuntuFunctions
        UbuntuOperations.apply_config()
        UbuntuOperations.init_dns_config()
        server.register_instance(UbuntuFunctions())
    elif dist == 'suse':
        from operations import SuseOperations
        from functions import SuseFunctions
        SuseOperations.apply_config()
        SuseOperations.init_dns_config()
        server.register_instance(SuseFunctions())
    elif dist == 'arch':
        from operations import ArchOperations
        from functions import ArchFunctions
        ArchOperations.apply_config()
        ArchOperations.init_dns_config()
        server.register_instance(ArchFunctions())
    else:
        sys.stderr.write('System (%s) not supported\n' % (dist))
        sys.exit(-1)

    log.info('Agent started for (%s)' % (dist))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        os.kill(os.getpid(), signal.SIGTERM)
