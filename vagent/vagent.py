#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import os
import platform
import sys


PORT = 12345

log = logging.getLogger(__name__)


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
        from op_linux import serve_linux
        serve_linux(daemon, do_log)
    elif system == 'windows':
        from op_windows import serve_windows
        serve_windows()
