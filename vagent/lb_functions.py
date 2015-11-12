# -*- coding: utf-8 -*-

import logging
from functions import CentOSFunctions
from lb_operations import LBCentOSOperations as LBCO

log = logging.getLogger(__name__)


class LBCentOSFunctions(CentOSFunctions):

    def listener_add(self, name, ip, port, protocol, balance,
                     sstricky, cookie_info):
        if LBCO.check_listener_existance(name):
            return [False, 'Listener %s exists' % name]

        if not LBCO.config_listener(name, ip, port, protocol, balance,
                                    sstricky, cookie_info, False):
            log.error('Config listener %s (%s:%d %s %s %s)' %
                      (name, ip, port, balance, sstricky, cookie_info))
            if not LBCO.recovery_listener(name):
                log.error('Recovery listener %s config error' % name)
            return [False, 'Config listener %s error' % name]
        if not LBCO.complete_listener_config(name):
            log.error('Complete listener %s config error' % name)
            return [False, 'Complete listener %s config error' % name]
        return [True, '']

    def listener_config(self, name, ip, port, protocol, balance,
                        sstricky, cookie_info, health_chk, servers_info):
        if not LBCO.backup_listener_config(name):
            log.error('Backup listener %s config error' % name)
            return [False, 'Backup listener %s config error' % name]
        if not LBCO.config_listener(name, ip, port, protocol, balance,
                                    sstricky, cookie_info, health_chk,
                                    servers_info):
            log.error('Config listener %s (%s:%d %s %s %s)' %
                      (name, ip, port, balance, sstricky, cookie_info))
            if not LBCO.recovery_listener(name):
                log.error('Recovery listener %s config error' % name)
            return [False, 'Config listener %s error' % name]
        if not LBCO.complete_listener_config(name, servers_info):
            log.error('Complete listener %s config error' % name)
            return [False, 'Complete listener %s config error' % name]
        return [True, '']

    def listener_del(self, name):
        if not LBCO.check_listener_existance(name):
            log.error('Listener %s not exists' % name)
            return [True, '']

        if not LBCO.backup_listener_config(name):
            log.error('Backup listener %s config error' % name)
            return [False, 'Backup listener %s config error' % name]
        if not LBCO.delete_listener(name):
            log.error('Del listener %s error' % name)
            if not LBCO.recovery_listener(name):
                log.error('Recovery listener %s config error' % name)
            return [False, 'Del listener %s error' % name]
        if not LBCO.complete_listener_config(name):
            log.error('Complete listener %s config error' % name)
            return [False, 'Complete listener %s config error' % name]
        return [True, '']

    def listener_clear(self):
        if not LBCO.clear_listener():
            log.error('Clear listener error')
            return [False, 'Clear listener error']
        return [True, '']

    def server_disable(self, listener, name):
        if not LBCO.check_listener_existance(listener):
            log.error('Listener %s not exists' % listener)
            return [False, 'Listener %s not exists' % listener]
        if not LBCO.check_server_existance(listener, name):
            log.error('Server %s not exists on listener %s' %
                      (name, listener))
            return [False,
                    'Server %s not exists on listener %s' % (name, listener)]

        if not LBCO.disable_server(listener, name):
            log.error('Disable listener %s server %s error' % (listener, name))
            return [False,
                    'Disable listener %s server %s error' % (listener, name)]
        return [True, '']

    def server_enable(self, listener, name):
        if not LBCO.check_listener_existance(listener):
            log.error('Listener %s not exists' % listener)
            return [False, 'Listener %s not exists' % listener]
        if not LBCO.check_server_existance(listener, name):
            log.error('Server %s not exists on listener %s' %
                      (name, listener))
            return [False,
                    'Server %s not exists on listener %s' % (name, listener)]

        if not LBCO.enable_server(listener, name):
            log.error('Enable listener %s server %s error' % (name, listener))
            return [False,
                    'Enable listener %s server %s error' % (name, listener)]
        return [True, '']

    def servers_health_state_get(self):
        return LBCO.get_servers_health_state_info()

    def listeners_stat_info_get(self):
        return LBCO.get_listeners_stat_info()

    def upgrade(self):
        import tarfile
        import urllib

        from functions import client, stop_server
        try:
            urllib.urlretrieve('http://%s:20016/static/lb_vagent.tar.gz' %
                               client['address'], '/tmp/lb_vagent.tar.gz')
        except IOError:
            return [False, 'Retrieve lb_vagent.tar.gz failed']

        t = tarfile.open("/tmp/lb_vagent.tar.gz", "r:gz")
        t.extractall(path = '/usr/local')
        t.close()

        stop_server()

        return [True, '']
