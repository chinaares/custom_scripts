# -*- coding: utf-8 -*-

import logging
import platform

from config import Config
from operations import LinuxOperations as LO
from operations import CentOSOperations as CO
from operations import DebianOperations as DO
from operations import UbuntuOperations as UO
from operations import WindowsOperations as WO
import SimpleXMLRPCServer

import version

log = logging.getLogger(__name__)

client = {}
stop = False


def stop_server():
    global stop
    stop = True


class Server(SimpleXMLRPCServer.SimpleXMLRPCServer):
    def serve_forever(self):
        while not stop:
            self.handle_request()


class Handler(SimpleXMLRPCServer.SimpleXMLRPCRequestHandler):
    def do_POST(self):
        global client
        client['address'], client['port'] = self.client_address
        SimpleXMLRPCServer.SimpleXMLRPCRequestHandler.do_POST(self)


class Functions(object):
    DEFAULT_REPLY = ['False', 'Not implemented']

    def ip_config(self, *args, **kwargs):
        return self.__class__.DEFAULT_REPLY

    def ip_add(self, *args, **kwargs):
        return self.__class__.DEFAULT_REPLY

    def ip_del(self, *args, **kwargs):
        return self.__class__.DEFAULT_REPLY

    def route_add(self, *args, **kwargs):
        return self.__class__.DEFAULT_REPLY

    def route_del(self, *args, **kwargs):
        return self.__class__.DEFAULT_REPLY

    def ping(self):
        return [True, 'pong']

    def version(self):
        return [True, version.VERSION, version.PACKTIME, version.GITCOMMIT]

    def upgrade(self, *args, **kwargs):
        return self.__class__.DEFAULT_REPLY

    def system(self):
        return [True, platform.system().lower()]

    def azure_backup_usage_get(self):
        return self.__class__.DEFAULT_REPLY


class LinuxFunctions(Functions):
    def ip_add(self, mac, ip):
        log.info('Adding %s IP address %s' % (mac, ip))
        dev = LO.get_name_by_mac(mac)
        if dev is None:
            log.error('Device %s is invalid' % mac)
            return [False, 'Device %s is invalid' % mac]
        if not LO.validate_ip(ip):
            log.error('IP %s is invalid' % ip)
            return [False, 'IP %s is invalid' % ip]
        if not LO.check_ip_existance_on_dev(dev):
            log.error('Primary IP not exist on %s' % dev)
            return [False, 'Primary IP not exist on %s' % dev]
        if LO.check_ip_existance_on_dev(dev, ip):
            log.error('IP %s exist on %s' % (ip, dev))
            return [False, 'IP %s exist on %s' % (ip, dev)]
        if not LO.add_ip(dev, ip):
            log.error('Adding IP for %s error' % dev)
            return [False, 'Adding IP for %s error' % dev]
        Config.add_ip(mac, ip)
        return [True, '']

    def ip_del(self, mac, ip):
        log.info('Deleting %s IP address %s' % (mac, ip))
        dev = LO.get_name_by_mac(mac)
        if dev is None:
            log.error('Device %s is invalid' % mac)
            return [False, 'Device %s is invalid' % mac]
        if not LO.validate_ip(ip):
            log.error('IP %s is invalid' % ip)
            return [False, 'IP %s is invalid' % ip]
        if not LO.check_ip_existance_on_dev(dev, ip):
            log.error('IP %s not exist on %s' % (ip, dev))
            return [False, 'IP %s not exist on %s' % (ip, dev)]
        if LO.check_primary_ip_on_dev(dev, ip):
            log.error('Cannot delete primary IP on %s' % dev)
            return [False, 'Cannot delete primary IP on %s' % dev]
        if not LO.del_ip(dev, ip):
            log.error('Delete IP for %s error' % dev)
            return [False, 'Delete IP for %s error' % dev]
        Config.del_ip(mac, ip)
        return [True, '']

    def upgrade(self):
        import tarfile
        import urllib
        global client
        try:
            urllib.urlretrieve('http://%s:20016/static/vagent.tar.gz' %
                               client['address'], '/tmp/vagent.tar.gz')
        except IOError:
            return [False, 'Retrieve vagent.tar.gz failed']

        t = tarfile.open("/tmp/vagent.tar.gz", "r:gz")
        t.extractall(path='/usr/local')
        t.close()

        stop_server()

        return [True, '']


class CentOSFunctions(LinuxFunctions):
    def ip_config(self, mac, ip):
        log.info('Setting %s IP address to %s' % (mac, ip))
        dev = CO.get_name_by_mac(mac)
        if dev is None:
            log.error('Device %s is invalid' % mac)
            return [False, 'Device %s is invalid' % mac]
        if not CO.validate_ip(ip):
            log.error('IP %s is invalid' % ip)
            return [False, 'IP %s is invalid' % ip]
        if not CO.disable_offload(dev):
            log.error('Disable offload for %s error' % dev)
            return [False, 'Disable offload for %s error' % dev]
        if not CO.config_ip(dev, ip):
            log.error('Config IP for %s error' % dev)
            return [False, 'Config IP for %s error' % dev]
        if not CO.write_ip_config(dev, ip):
            log.error('Write IP config for %s error' % dev)
            return [True, 'Write IP config for %s error' % dev]
        Config.config_ip(mac, ip)
        CO.apply_config()
        return [True, '']

    def ip_flush(self, mac):
        log.info('Deleting all IP address on %s' % mac)
        dev = CO.get_name_by_mac(mac)
        if dev is None:
            log.info('Device %s is invalid' % mac)
            return [True, '']
        if not CO.flush_ip(dev):
            log.error('Flush IP for %s error' % dev)
            return [False, 'Flush IP for %s error' % dev]
        CO.remove_ip_config(dev)
        Config.flush_ip(mac)
        return [True, '']

    def route_add(self, node, nh, mac):
        log.info('Adding route for %s' % node)
        nh = nh if nh else None
        mac = mac if mac else None
        if nh is None and mac is None:
            log.error('No next hop or dev')
            return [False, 'No next hop or dev']
        if not node:
            log.error('Node is empty')
            return [False, 'Node is empty']
        if node == 'default':
            node = '0.0.0.0/0'
        if not CO.validate_node(node):
            log.error('Node %s is invalid' % node)
            return [False, 'Node %s is invalid' % node]
        if CO.check_node_existance(node):
            log.error('Node %s is duplicated' % node)
            return [False, 'Node %s is duplicated' % node]
        if mac is not None:
            dev = CO.get_name_by_mac(mac)
            if dev is None:
                log.error('Device %s is invalid' % mac)
                return [False, 'Device %s is invalid' % mac]
        else:
            dev = None
        if nh is not None and not CO.validate_ip(nh + '/32'):
            log.error('Next hop %s is invalid' % nh)
            return [False, 'Next hop %s is invalid' % nh]
        if not CO.add_route(node, nh, mac):
            log.error('Add route for %s error' % node)
            return [False, 'Add route for %s error' % node]
        if node == '0.0.0.0/0':
            CO.write_default_route_config(nh)
        Config.add_route(node, nh, mac)
        return [True, '']

    def route_del(self, node):
        log.info('Deleting route for %s' % node)
        if not node:
            log.error('Node is empty')
            return [False, 'Node is empty']
        if node == 'default':
            node = '0.0.0.0/0'
        if not CO.validate_node(node):
            log.error('Node %s is invalid' % node)
            return [False, 'Node %s is invalid' % node]
        if not CO.check_node_existance(node):
            log.error('Node %s not exist' % node)
            return [False, 'Node %s not exist' % node]
        if not CO.del_route(node):
            log.error('Delete route error')
            return [False, 'Delete route error']
        if node == '0.0.0.0/0':
            CO.remove_default_route_config()
        Config.del_route(node)
        return [True, '']

    def iqn_gen(self):
        log.info('Generating iscsi InitiatorName')
        if not CO.check_iscsi_service_existance():
            return [False, 'Iscsi service not exist']
        iqn = CO.generate_initiator_iqn()
        if iqn is None:
            return [False, 'Generate initiator iqn error']
        else:
            CO.write_initiator_iqn(iqn)
            return [True, iqn]

    def cloud_disk_plug(self, iqn, ip, port):
        log.info('Pluging cloud disk on target %s, ip %s:%d' %
                 (iqn, ip, port))
        if not CO.validate_iqn(iqn):
            log.error('Iqn %s is invalid' % iqn)
            return [False, 'Iqn %s is invalid' % iqn]
        if not CO.validate_ip_without_mask(ip):
            log.error('IP %s is invalid' % ip)
            return [False, 'IP %s is invalid' % ip]
        if not CO.validate_port(port):
            log.error('Port %d is invalid' % port)
            return [False, 'Port %d is invalid' % port]
        if not CO.check_iscsi_service_existance():
            return [False, 'Iscsi service not exist']
        if not CO.check_iscsi_session_existance(iqn):
            if not CO.discover_iscsi_target(ip, port):
                return [False, 'Discover target %s:%d error' % (ip, port)]
            if not CO.login_iscsi_target(iqn, ip, port):
                return [False, 'Login target %s error' % iqn]
            return [True, '']
        else:
            if not CO.update_iscsi_target(iqn, ip, port):
                return [False, 'Update target %s error' % iqn]
            return [True, '']

    def cloud_disk_unplug(self, iqn, ip, port, lun_name, last):
        log.info('Upluging cloud disk on target %s, ip %s:%d, lun_name:%s,\
                 last: %s' % (iqn, ip, port, lun_name, last))
        if not CO.validate_iqn(iqn):
            log.error('Iqn %s is invalid' % iqn)
            return [False, 'Iqn %s is invalid' % iqn]
        if not CO.validate_ip_without_mask(ip):
            log.error('IP %s is invalid' % ip)
            return [False, 'IP %s is invalid' % ip]
        if not CO.validate_port(port):
            log.error('Port %d is invalid' % port)
            return [False, 'Port %d is invalid' % port]
        if not CO.check_iscsi_service_existance():
            return [False, 'Iscsi service not exist']
        if not CO.check_iscsi_session_existance(iqn):
            log.info('Session %s not exist, do not need to logout' % iqn)
            return [True, '']
        dev_name = CO.get_iscsi_dev_name(lun_name)
        if dev_name is None:
            return [False, 'Get dev name error']
        else:
            if CO.check_dev_mounted(dev_name):
                return [False, 'Unplug failed, The device %s already mounted'
                        % dev_name]
        if last is True:
            if not CO.logout_iscsi_target(iqn, ip, port):
                return [False, 'Logout Target %s error' % iqn]
        else:
            if not CO.update_iscsi_target(iqn, ip, port):
                return [False, 'Update target %s error' % iqn]
        return [True, '']

    def block_device_unmounted(self, dev_name):
        return CO.check_block_device_unmounted(dev_name)


class DebianFunctions(LinuxFunctions):
    def ip_config(self, mac, ip):
        log.info('Setting %s IP address to %s' % (mac, ip))
        dev = DO.get_name_by_mac(mac)
        if dev is None:
            log.error('Device %s is invalid' % mac)
            return [False, 'Device %s is invalid' % mac]
        if not DO.validate_ip(ip):
            log.error('IP %s is invalid' % ip)
            return [False, 'IP %s is invalid' % ip]
        if not DO.disable_offload(dev):
            log.error('Disable offload for %s error' % dev)
            return [False, 'Disable offload for %s error' % dev]
        if not DO.config_ip(dev, ip):
            log.error('Config IP for %s error' % dev)
            return [False, 'Config IP for %s error' % dev]
        if not DO.write_ip_config(dev, ip):
            log.error('Write IP config for %s error' % dev)
            return [True, 'Write IP config for %s error' % dev]
        Config.config_ip(mac, ip)
        DO.apply_config()
        return [True, '']

    def ip_flush(self, mac):
        log.info('Deleting all IP address on %s' % mac)
        dev = DO.get_name_by_mac(mac)
        if dev is None:
            log.info('Device %s is invalid' % mac)
            return [True, '']
        if not DO.flush_ip(dev):
            log.error('Flush IP for %s error' % dev)
            return [False, 'Flush IP for %s error' % dev]
        DO.remove_ip_config(dev)
        Config.flush_ip(mac)
        return [True, '']

    def route_add(self, node, nh, mac):
        log.info('Adding route for %s' % node)
        nh = nh if nh else None
        mac = mac if mac else None
        if nh is None and mac is None:
            log.error('No next hop or dev')
            return [False, 'No next hop or dev']
        if not node:
            log.error('Node is empty')
            return [False, 'Node is empty']
        if node == 'default':
            node = '0.0.0.0/0'
        if not DO.validate_node(node):
            log.error('Node %s is invalid' % node)
            return [False, 'Node %s is invalid' % node]
        if DO.check_node_existance(node):
            log.error('Node %s is duplicated' % node)
            return [False, 'Node %s is duplicated' % node]
        if mac is not None:
            dev = DO.get_name_by_mac(mac)
            if dev is None:
                log.error('Device %s is invalid' % mac)
                return [False, 'Device %s is invalid' % mac]
        else:
            dev = None
        if nh is not None and not DO.validate_ip(nh + '/32'):
            log.error('Next hop %s is invalid' % nh)
            return [False, 'Next hop %s is invalid' % nh]
        if not DO.add_route(node, nh, mac):
            log.error('Add route for %s error' % node)
            return [False, 'Add route for %s error' % node]
        if node == '0.0.0.0/0':
            DO.write_default_route_config(nh)
        Config.add_route(node, nh, mac)
        return [True, '']

    def route_del(self, node):
        log.info('Deleting route for %s' % node)
        if not node:
            log.error('Node is empty')
            return [False, 'Node is empty']
        if node == 'default':
            node = '0.0.0.0/0'
        if not DO.validate_node(node):
            log.error('Node %s is invalid' % node)
            return [False, 'Node %s is invalid' % node]
        if not DO.check_node_existance(node):
            log.error('Node %s not exist' % node)
            return [False, 'Node %s not exist' % node]
        if not DO.del_route(node):
            log.error('Delete route error')
            return [False, 'Delete route error']
        if node == '0.0.0.0/0':
            DO.remove_default_route_config()
        Config.del_route(node)
        return [True, '']


class UbuntuFunctions(LinuxFunctions):
    def ip_config(self, mac, ip):
        log.info('Setting %s IP address to %s' % (mac, ip))
        dev = UO.get_name_by_mac(mac)
        if dev is None:
            log.error('Device %s is invalid' % mac)
            return [False, 'Device %s is invalid' % mac]
        if not UO.validate_ip(ip):
            log.error('IP %s is invalid' % ip)
            return [False, 'IP %s is invalid' % ip]
        if not UO.disable_offload(dev):
            log.error('Disable offload for %s error' % dev)
            return [False, 'Disable offload for %s error' % dev]
        if not UO.config_ip(dev, ip):
            log.error('Config IP for %s error' % dev)
            return [False, 'Config IP for %s error' % dev]
        if not UO.write_ip_config(dev, ip):
            log.error('Write IP config for %s error' % dev)
            return [True, 'Write IP config for %s error' % dev]
        Config.config_ip(mac, ip)
        UO.apply_config()
        return [True, '']

    def ip_flush(self, mac):
        log.info('Deleting all IP address on %s' % mac)
        dev = UO.get_name_by_mac(mac)
        if dev is None:
            log.info('Device %s is invalid' % mac)
            return [True, '']
        if not UO.flush_ip(dev):
            log.error('Flush IP for %s error' % dev)
            return [False, 'Flush IP for %s error' % dev]
        UO.remove_ip_config(dev)
        Config.flush_ip(mac)
        return [True, '']

    def route_add(self, node, nh, mac):
        log.info('Adding route for %s' % node)
        nh = nh if nh else None
        mac = mac if mac else None
        if nh is None and mac is None:
            log.error('No next hop or dev')
            return [False, 'No next hop or dev']
        if not node:
            log.error('Node is empty')
            return [False, 'Node is empty']
        if node == 'default':
            node = '0.0.0.0/0'
        if not UO.validate_node(node):
            log.error('Node %s is invalid' % node)
            return [False, 'Node %s is invalid' % node]
        if UO.check_node_existance(node):
            log.error('Node %s is duplicated' % node)
            return [False, 'Node %s is duplicated' % node]
        if mac is not None:
            dev = UO.get_name_by_mac(mac)
            if dev is None:
                log.error('Device %s is invalid' % mac)
                return [False, 'Device %s is invalid' % mac]
        else:
            dev = None
        if nh is not None and not UO.validate_ip(nh + '/32'):
            log.error('Next hop %s is invalid' % nh)
            return [False, 'Next hop %s is invalid' % nh]
        if not UO.add_route(node, nh, mac):
            log.error('Add route for %s error' % node)
            return [False, 'Add route for %s error' % node]
        if node == '0.0.0.0/0':
            UO.write_default_route_config(nh)
        Config.add_route(node, nh, mac)
        return [True, '']

    def route_del(self, node):
        log.info('Deleting route for %s' % node)
        if not node:
            log.error('Node is empty')
            return [False, 'Node is empty']
        if node == 'default':
            node = '0.0.0.0/0'
        if not UO.validate_node(node):
            log.error('Node %s is invalid' % node)
            return [False, 'Node %s is invalid' % node]
        if not UO.check_node_existance(node):
            log.error('Node %s not exist' % node)
            return [False, 'Node %s not exist' % node]
        if not UO.del_route(node):
            log.error('Delete route error')
            return [False, 'Delete route error']
        if node == '0.0.0.0/0':
            UO.remove_default_route_config()
        Config.del_route(node)
        return [True, '']

    def iqn_gen(self):
        log.info('Generating iscsi InitiatorName')
        if not UO.check_iscsi_service_existance():
            return [False, 'Iscsi service not exist']
        iqn = UO.generate_initiator_iqn()
        if iqn is None:
            return [False, 'Generate initiator iqn error']
        else:
            UO.write_initiator_iqn(iqn)
            return [True, iqn]

    def cloud_disk_plug(self, iqn, ip, port):
        log.info('Pluging cloud disk on target %s, ip %s:%d' %
                 (iqn, ip, port))
        if not UO.validate_iqn(iqn):
            log.error('Iqn %s is invalid' % iqn)
            return [False, 'Iqn %s is invalid' % iqn]
        if not UO.validate_ip_without_mask(ip):
            log.error('IP %s is invalid' % ip)
            return [False, 'IP %s is invalid' % ip]
        if not UO.validate_port(port):
            log.error('Port %d is invalid' % port)
            return [False, 'Port %d is invalid' % port]
        if not UO.check_iscsi_service_existance():
            return [False, 'Iscsi service not exist']
        if not UO.check_iscsi_session_existance(iqn):
            if not UO.discover_iscsi_target(ip, port):
                return [False, 'Discover target %s:%d error' % (ip, port)]
            if not UO.login_iscsi_target(iqn, ip, port):
                return [False, 'Login target %s error' % iqn]
            return [True, '']
        else:
            if not UO.update_iscsi_target(iqn, ip, port):
                return [False, 'Update target %s error' % iqn]
            return [True, '']

    def cloud_disk_unplug(self, iqn, ip, port, last):
        log.info('Upluging cloud disk on target %s, ip %s:%d, last: %s' %
                 (iqn, ip, port, last))
        if not UO.validate_iqn(iqn):
            log.error('Iqn %s is invalid' % iqn)
            return [False, 'Iqn %s is invalid' % iqn]
        if not UO.validate_ip_without_mask(ip):
            log.error('IP %s is invalid' % ip)
            return [False, 'IP %s is invalid' % ip]
        if not UO.validate_port(port):
            log.error('Port %d is invalid' % port)
            return [False, 'Port %d is invalid' % port]
        if not UO.check_iscsi_service_existance():
            return [False, 'Iscsi service not exist']
        if not UO.check_iscsi_session_existance(iqn):
            log.info('Session %s not exist, do not need to logout' % iqn)
            return [True, '']
        if last is True:
            if not UO.logout_iscsi_target(iqn, ip, port):
                return [False, 'Logout Target %s error' % iqn]
        else:
            if not UO.update_iscsi_target(iqn, ip, port):
                return [False, 'Update target %s error' % iqn]
        return [True, '']

    def block_device_unmounted(self, dev_name):
        return UO.check_block_device_unmounted(dev_name)


class WindowsFunctions(Functions):
    def ip_add(self, mac, ip):
        log.info('Adding %s IP address %s' % (mac, ip))
        if not WO.validate_ip(ip):
            log.error('IP %s is invalid' % ip)
            return [False, 'IP %s is invalid' % ip]
        if WO.check_ip_existance(ip):
            log.error('IP %s exist' % ip)
            return [False, 'IP %s exist' % ip]
        dev = WO.get_name_by_mac(mac)
        if dev is None:
            log.error('Device %s is invalid' % mac)
            return [False, 'Device %s is invalid' % mac]
        if not WO.add_ip(dev, ip):
            log.error('Adding IP for %s error' % mac)
            return [False, 'Adding IP for %s error' % mac]
        Config.add_ip(mac, ip)
        return [True, '']

    def ip_del(self, mac, ip):
        log.info('Deleting %s IP address %s' % (mac, ip))
        if not WO.validate_ip(ip):
            log.error('IP %s is invalid' % ip)
            return [False, 'IP %s is invalid' % ip]
        dev = WO.get_name_by_mac(mac)
        if dev is None:
            log.error('Device %s is invalid' % mac)
            return [False, 'Device %s is invalid' % mac]
        if not WO.del_ip(dev, ip):
            log.error('Delete IP for %s error' % mac)
            return [False, 'Delete IP for %s error' % mac]
        Config.del_ip(mac, ip)
        return [True, '']

    def ip_config(self, mac, ip):
        log.info('Setting %s IP address %s' % (mac, ip))
        if not WO.validate_ip(ip):
            log.error('IP %s is invalid' % ip)
            return [False, 'IP %s is invalid' % ip]
        if WO.check_ip_existance(ip):
            log.error('IP %s exist' % ip)
            return [False, 'IP %s exist' % ip]
        dev = WO.get_name_by_mac(mac)
        if dev is None:
            log.error('Device %s is invalid' % mac)
            return [False, 'Device %s is invalid' % mac]
        if not WO.disable_offload(dev):
            log.error('Disable offload for %s error' % dev)
            return [False, 'Disable offload for %s error' % dev]
        if not WO.config_ip(dev, ip):
            log.error('Setting IP for %s error' % mac)
            return [False, 'Setting IP for %s error' % mac]
        Config.config_ip(mac, ip)
        return [True, '']

    def ip_flush(self, mac):
        log.info('Deleting all IP address on %s' % mac)
        dev = WO.get_name_by_mac(mac)
        if dev is None:
            log.info('Device %s is invalid' % mac)
            return [True, '']
        if not WO.flush_ip(dev):
            log.error('Flush IP for %s error' % mac)
            return [False, 'Flush IP for %s error' % mac]
        Config.flush_ip(mac)
        return [True, '']

    def route_add(self, node, nh, mac):
        log.info('Adding route for %s' % node)
        mac = mac if mac else None
        if not node:
            log.error('Node is empty')
            return [False, 'Node is empty']
        if node == 'default':
            node = '0.0.0.0/0'
        if not WO.validate_node(node):
            log.error('Node %s is invalid' % node)
            return [False, 'Node %s is invalid' % node]
        if WO.check_node_existance(node):
            log.error('Node %s is duplicated' % node)
            return [False, 'Node %s is duplicated' % node]
        if not WO.validate_ip(nh + '/32'):
            log.error('Next hop %s is invalid' % nh)
            return [False, 'Next hop %s is invalid' % nh]
        if not WO.add_route(node, nh, mac):
            log.error('Add route for %s error' % node)
            return [False, 'Add route for %s error' % node]
        Config.add_route(node, nh, mac)
        return [True, '']

    def route_del(self, node):
        log.info('Deleting route for %s' % node)
        if not node:
            log.error('Node is empty')
            return [False, 'Node is empty']
        if node == 'default':
            node = '0.0.0.0/0'
        if not WO.validate_node(node):
            log.error('Node %s is invalid' % node)
            return [False, 'Node %s is invalid' % node]
        if not WO.check_node_existance(node):
            log.error('Node %s not exist' % node)
            return [False, 'Node %s not exist' % node]
        if not WO.del_route(node):
            log.error('Delete route error')
            return [False, 'Delete route error']
        Config.del_route(node)
        return [True, '']

    def iqn_gen(self):
        log.info('Generating iscsi InitiatorName')
        return [True, 'xxx']

    def cloud_disk_plug(self, iqn, ip, port):
        log.info('Pluging cloud disk on target %s, ip %s:%d' %
                 (iqn, ip, port))
        if not UO.validate_iqn(iqn):
            log.error('Iqn %s is invalid' % iqn)
            return [False, 'Iqn %s is invalid' % iqn]
        if not UO.validate_ip_without_mask(ip):
            log.error('IP %s is invalid' % ip)
            return [False, 'IP %s is invalid' % ip]
        if not UO.validate_port(port):
            log.error('Port %d is invalid' % port)
            return [False, 'Port %d is invalid' % port]
        return [True, '']

    def cloud_disk_unplug(self, iqn, ip, port, last):
        log.info('Upluging cloud disk on target %s, ip %s:%d, last: %s' %
                 (iqn, ip, port, last))
        if not UO.validate_iqn(iqn):
            log.error('Iqn %s is invalid' % iqn)
            return [False, 'Iqn %s is invalid' % iqn]
        if not UO.validate_ip_without_mask(ip):
            log.error('IP %s is invalid' % ip)
            return [False, 'IP %s is invalid' % ip]
        if not UO.validate_port(port):
            log.error('Port %d is invalid' % port)
            return [False, 'Port %d is invalid' % port]
        return [True, '']

    def block_device_unmounted(self, dev_name):
        return WO.check_block_device_unmounted(dev_name)

    def azure_backup_usage_get(self):
        usage = WO.get_azure_backup_usage()
        return [True, usage]
