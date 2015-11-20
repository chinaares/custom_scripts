#!/usr/bin/python
# -*- coding: utf-8 -*-

import win32serviceutil
import win32service
import win32event
from functions import Handler, Server


PORT = 12345


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


def serve_windows():
    win32serviceutil.HandleCommandLine(HttpServerManager)
