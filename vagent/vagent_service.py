#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import os
import datetime

import win32serviceutil
import win32service
import win32event
from functions import Handler, Server
from config import Config


PORT = 12345
log = logging.getLogger(__name__)
log_level = logging.DEBUG
log_filename = os.path.dirname(os.path.realpath(__file__)) + '/vagent.log'


log_formatter = logging.Formatter('%(asctime)s %(levelname)s '
                                  '%(module)s.%(funcName)s: %(message)s')
log_handler = logging.FileHandler(log_filename)
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

Config.filename = \
        os.path.dirname(os.path.realpath(__file__)) + '/config.xml'
Config.read_conf()
Config.write_conf()


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
        log.info("vagent start.... %s " % datetime.datetime.now()) 
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


def serve_windows():
    win32serviceutil.HandleCommandLine(HttpServerManager)


if __name__ == '__main__':
    serve_windows()
