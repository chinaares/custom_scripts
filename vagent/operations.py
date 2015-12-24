# -*- coding: utf-8 -*-

import logging
import os
import re
import subprocess
import tempfile
import json

from config import Config

log = logging.getLogger(__name__)

DNS = '114.114.114.114'


def call_system_check(args):
    assert isinstance(args, list)
    try:
        with open(os.devnull, 'w') as devnull:
            subprocess.check_call(args, stdout=devnull, stderr=devnull)
        return True
    except subprocess.CalledProcessError as e:
        log.debug('[%s] failed (%d)' % (e.cmd, e.returncode))
        return False
    except Exception as e:
        log.debug('[%s] failed (%r)' % (args, e))
        return False


def call_windows_system_check(args):
    assert isinstance(args, list)
    try:
        tmp = tempfile.mktemp('.bat')
        with open(tmp, 'w') as f:
            f.write(' '.join(args))
        with open(os.devnull, 'w') as devnull:
            subprocess.check_call([tmp], stdout=devnull, stderr=devnull)
        return True
    except subprocess.CalledProcessError as e:
        log.debug('[%s] failed (%d)' % (args, e.returncode))
        return False


def call_system_sh_check(args):
    assert isinstance(args, list)
    cmd = ' '.join(args)
    log.debug(cmd)
    (_, err) = subprocess.Popen(cmd,
                                shell=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE).communicate()
    if err:
        log.debug('[%s] failed: %s' % (cmd, err))
        return False
    return True


def call_system_output(args):
    assert isinstance(args, list)
    (out, err) = subprocess.Popen(args,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE).communicate()
    if err:
        log.debug('[%s] failed: %s' % (args, err))
    return out


def call_system_sh_output(args):
    assert isinstance(args, list)
    cmd = ' '.join(args)
    (out, err) = subprocess.Popen(cmd,
                                  shell=True,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE).communicate()
    if err:
        log.debug('[%s] failed: %s' % (args, err))
    return out


def call_system_output_no_log(args):
    assert isinstance(args, list)
    (out, err) = subprocess.Popen(args,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE).communicate()
    if err:
        return (False, err)
    return (True, out)


def string_enum(*sequential, **named):
    enums = dict(zip(sequential, sequential), **named)
    return type('StringEnum', (), enums)


class Operations(object):
    IP_REGEX = re.compile(r'^(?:(?:25[0-5]|2[0-4]\d|[01]?\d{1,2})\.){3}'
                          '(?:25[0-5]|2[0-4]\d|[01]?\d{1,2})'
                          '/(?:3[0-2]|[0-2]?\d)$')
    IP_WITHOUT_MASK_REGEX = \
        re.compile(r'^(?:(?:25[0-5]|2[0-4]\d|[01]?\d{1,2})\.){3}'
                   '(?:25[0-5]|2[0-4]\d|[01]?\d{1,2})')
    MAC_REGEX = re.compile(r'^(?:[0-9A-Fa-f]{2}([-:]))'
                           '(?:[0-9A-Fa-f]{2}\\1){4}[0-9A-Fa-f]{2}$')
    IQN_REGEX = re.compile(r'^iqn.[0-9]{4}-[0-9]{2}')

    @classmethod
    def validate_ip(cls, ip):
        if re.match(cls.IP_REGEX, ip) is None:
            return False
        else:
            return True

    @classmethod
    def validate_ip_without_mask(cls, ip):
        if re.match(cls.IP_WITHOUT_MASK_REGEX, ip) is None:
            return False
        else:
            return True

    @classmethod
    def validate_node(cls, ip):
        if re.match(cls.IP_REGEX, ip) is None:
            return False
        (ipaddr, masklen) = ip.split('/')
        (a, b, c, d) = [int(_str) for _str in ipaddr.split('.')]
        ip_bin = (a << 24) + (b << 16) + (c << 8) + d
        if ip_bin & (0xFFFFFFFF >> int(masklen)):
            return False
        return True

    @classmethod
    def in_same_subnet(cls, ip1, ip2, netmask):
        (a, b, c, d) = [int(_str) for _str in ip1.split('.')]
        ip1_bin = (a << 24) + (b << 16) + (c << 8) + d
        (a, b, c, d) = [int(_str) for _str in ip2.split('.')]
        ip2_bin = (a << 24) + (b << 16) + (c << 8) + d
        (a, b, c, d) = [int(_str) for _str in netmask.split('.')]
        netmask_bin = (a << 24) + (b << 16) + (c << 8) + d
        if (ip1_bin & netmask_bin) == (ip2_bin & netmask_bin):
            return True
        else:
            return False

    @classmethod
    def validate_mac(cls, mac):
        if re.match(cls.MAC_REGEX, mac) is None:
            return False
        else:
            return True

    @classmethod
    def validate_port(cls, port):
        if port > 0 and port < 65535:
            return True
        else:
            return False

    @classmethod
    def masklen2netmask(cls, masklen):
        if masklen < 0 or masklen > 32:
            return None
        mask = (0xFFFFFFFF >> masklen) ^ 0xFFFFFFFF
        return '%d.%d.%d.%d' % (mask >> 24,
                                (mask & 0x00FFFFFF) >> 16,
                                (mask & 0x0000FFFF) >> 8,
                                mask & 0x000000FF)

    @classmethod
    def apply_config(cls):
        cls.self_init_script()
        with Config.lock:
            for interface in Config.interfaces:
                device = cls.get_name_by_mac(interface.dev)
                if device is None:
                    continue
                cls.flush_ip(device)
                cls.disable_offload(device)
                cls.config_ip(device, interface.primary_ip)
                cls.write_ip_config(device, interface.primary_ip)
                for ip in interface.secondary_ips:
                    cls.add_ip(device, ip)
            for route in Config.routes:
                cls.del_route(route.node)
                cls.add_route(route.node, route.nh, route.dev)
                if route.node == '0.0.0.0/0':
                    cls.write_default_route_config(route.nh)

    @classmethod
    def write_ip_config(cls, dev, ip):
        pass

    @classmethod
    def remove_ip_config(cls, dev):
        pass

    @classmethod
    def validate_iqn(cls, iqn):
        if re.match(cls.IQN_REGEX, iqn) is None:
            return False
        else:
            return True


class LinuxOperations(Operations):
    name_table = {}

    @classmethod
    def get_name_by_mac(cls, mac):
        if mac in cls.name_table:
            return cls.name_table[mac]
        args = ['/sbin/ip', '-oneline', 'link']
        out = call_system_output(args)
        if out:
            regex = re.compile(mac)
            info_list = out.split('\n')
            for info in info_list:
                if not info:
                    continue
                ma = re.search(regex, info)
                if ma is not None:
                    cls.name_table[mac] = info.split(':')[1].strip()
                    return cls.name_table[mac]
        return None

    @classmethod
    def check_ip_existance_on_dev(cls, dev, ip=None):
        args = ['/sbin/ip', '-f', 'inet', '-oneline', 'addr', 'show',
                'dev', dev]
        out = call_system_output(args)
        if out:
            if ip is not None:
                regex = ip.replace('.', '\.')
                if re.search(regex, out) is None:
                    return False
            log.debug('IP exists on %s' % dev)
            return True
        return False

    @classmethod
    def check_primary_ip_on_dev(cls, dev, ip):
        args = ['/sbin/ip', '-f', 'inet', '-oneline', 'addr', 'show',
                'dev', dev]
        out = call_system_output(args)
        if out:
            regex = ip.replace('.', '\.')
            if re.search(regex, out.split('\n')[0]) is None:
                return False
            log.debug('Primary IP exists on %s' % dev)
            return True
        return False

    @classmethod
    def check_node_existance(cls, node):
        out = call_system_output(
            ['/sbin/ip', '-oneline', 'route', 'list', 'exact', node])
        if out:
            log.debug('Route for %s exists' % node)
            return True
        return False

    @classmethod
    def disable_offload(cls, dev):
        # only disable offload in xenserver vms
        if not call_system_sh_check(
                ['ps', 'ax', '|', 'grep', '-w', 'qemu-ga', '|',
                 'grep', '-v', 'grep']):
            if not call_system_check(
                    ['/sbin/ethtool', '-K', dev, 'tso', 'off', 'gso', 'off',
                     'tx', 'off', 'sg', 'off']):
                log.debug('Disable offload for %s error' % dev)
                return False
        return True

    @classmethod
    def config_ip(cls, dev, ip):
        (ipaddr, masklen) = ip.split('/')
        netmask = cls.masklen2netmask(int(masklen))
        if not call_system_check(
                ['/sbin/ifconfig', dev, ipaddr, 'netmask', netmask, 'up']):
            log.debug('Config IP for %s error' % dev)
            return False
        return True

    @classmethod
    def add_ip(cls, dev, ip):
        if not call_system_check(
                ['/sbin/ip', 'addr', 'add', ip,
                 'brd', '+', 'dev', dev]):
            log.debug('Add IP for %s error' % dev)
            return False
        return True

    @classmethod
    def del_ip(cls, dev, ip):
        if not call_system_check(
                ['/sbin/ip', 'addr', 'del', ip, 'dev', dev]):
            log.debug('Delete IP for %s error' % dev)
            return False
        return True

    @classmethod
    def flush_ip(cls, dev):
        if not call_system_check(
                ['/sbin/ip', 'addr', 'flush', 'dev', dev]):
            log.debug('Flush IP for %s error' % dev)
            if not call_system_check(
                    ['/sbin/ip', 'addr', 'flush', 'dev', dev]):
                log.debug('Flush IP for %s error' % dev)
                return False
        return True

    @classmethod
    def add_route(cls, node, nh, mac):
        assert nh is not None or mac is not None
        args = ['/sbin/ip', 'route', 'add', node]
        if nh is not None:
            args.extend(['via', nh])
        if mac is not None:
            dev = cls.get_name_by_mac(mac)
            args.extend(['dev', dev])
        if not call_system_check(args):
            log.debug('Add route for %s error' % node)
            return False
        return True

    @classmethod
    def del_route(cls, node):
        args = ['/sbin/ip', 'route', 'del', node]
        if not call_system_check(args):
            log.debug('Delete route for %s error' % node)
            return False
        return True

    @classmethod
    def self_init_script(cls):
        init_script = \
            os.path.dirname(os.path.realpath(__file__)) + '/script/init.sh'
        if not call_system_check([init_script]):
            log.debug('Self init error')
            return False
        return True


class CentOSOperations(LinuxOperations):
    IFCFG_STR = """DEVICE=%s
HWADDR=%s
NM_CONTROLLED=yes
ONBOOT=yes
IPADDR=%s
NETMASK=%s
BOOTPROTO=static
"""
    INITIATORNAME_STR = """InitiatorName=%s
"""
    INITIATORNAME_FILE = '/etc/iscsi/initiatorname.iscsi'
    NETWORK_FILE = '/etc/sysconfig/network'

    @classmethod
    def write_ip_config(cls, dev, ip):
        items = call_system_output(
            ['/sbin/ip', '-oneline', 'link', 'show', dev]).split()
        mac = None
        for item in items:
            if cls.validate_mac(item):
                mac = item
                break
        if mac is None:
            log.debug('Get MAC for %s error' % dev)
            return False
        (ipaddr, masklen) = ip.split('/')
        netmask = cls.masklen2netmask(int(masklen))
        f = open('/etc/sysconfig/network-scripts/ifcfg-%s' % dev, 'w')
        f.write(cls.IFCFG_STR % (dev, mac, ipaddr, netmask))
        f.close()
        return True

    @classmethod
    def remove_ip_config(cls, dev):
        filename = '/etc/sysconfig/network-scripts/ifcfg-%s' % dev
        if os.path.isfile(filename):
            os.remove(filename)

    @classmethod
    def write_default_route_config(cls, ip):
        cls.remove_default_route_config()
        try:
            with open(cls.NETWORK_FILE, 'a') as f:
                f.write('GATEWAY=%s\n' % ip)
        except Exception as e:
            log.debug('write default route config error: %r' % e)
            return False
        return True

    @classmethod
    def remove_default_route_config(cls):
        args = ['/bin/sed', '-i', r'/GATEWAY=.*/d', cls.NETWORK_FILE]
        if not call_system_check(args):
            log.debug('remove default route config error')
            return False
        return True

    @classmethod
    def init_dns_config(cls):
        try:
            if not os.path.isfile('/etc/resolv.conf'):
                with open('/etc/resolv.conf', 'w') as f:
                    f.write('nameserver %s' % DNS)
        except Exception as e:
            log.debug('init dns error (%s)' % e)
            return False
        return True

    @classmethod
    def check_iscsi_service_existance(cls):
        args = ['/sbin/chkconfig', '--list', 'iscsi']
        if not call_system_check(args):
            log.error('Service iscsi does not exist')
            return False
        return True

    @classmethod
    def generate_initiator_iqn(cls):
        initiator_iqn = call_system_output(['/sbin/iscsi-iname'])
        if not cls.validate_iqn(initiator_iqn):
            log.error('Generate iqn %s error' % initiator_iqn)
            return None
        else:
            return initiator_iqn

    @classmethod
    def write_initiator_iqn(cls, initiator_iqn):
        try:
            with open(cls.INITIATORNAME_FILE, 'w') as f:
                f.write(cls.INITIATORNAME_STR % initiator_iqn)
                f.close()
            return True
        except Exception as e:
            log.debug('Write [%s] failed (%r)' % (cls.INITIATORNAME_FILE, e))
            return False

    @classmethod
    def discover_iscsi_target(cls, ip, port):
        args = ['/sbin/iscsiadm', '-m', 'discovery', '-t', 'sendtargets', '-p',
                '%s:%d' % (ip, port)]
        if not call_system_check(args):
            log.error('Target %s does not exist' % ip)
            return False
        return True

    @classmethod
    def login_iscsi_target(cls, iqn, ip, port):
        args = ['/sbin/iscsiadm', '-m', 'node', '-T', iqn, '-p',
                '%s:%d' % (ip, port), '-l']
        if not call_system_check(args):
            log.error('Login Target %s error' % iqn)
            return False
        return True

    @classmethod
    def logout_iscsi_target(cls, iqn, ip, port):
        args = ['/sbin/iscsiadm', '-m', 'node', '-T', iqn, '-p',
                '%s:%d' % (ip, port), '-u']
        if not call_system_check(args):
            log.error('Logout Target %s error' % iqn)
            return False
        return True

    @classmethod
    def update_iscsi_target(cls, iqn, ip, port):
        args = ['/sbin/iscsiadm', '-m', 'node', '-T', iqn, '-p',
                '%s:%d' % (ip, port), '-R']
        if not call_system_check(args):
            log.error('Update Target %s error' % iqn)
            return False
        return True

    @classmethod
    def check_iscsi_session_existance(cls, iqn):
        args = ['/sbin/iscsiadm', '-m', 'session', '|', 'grep', iqn]
        if not call_system_check(args):
            log.error('Session %s not active' % iqn)
            return False
        return True

    @classmethod
    def get_iscsi_dev_name(cls, lun_name):
        path = '/dev/disk/by-path/' + lun_name
        dev_name = call_system_output(['/usr/bin/readlink', '-f',
                                       path]).strip('\n')
        if not dev_name:
            log.error('Get dev name error')
            return None
        else:
            log.info('Get dev name %s success' % dev_name)
            return dev_name

    @classmethod
    def check_dev_mounted(cls, dev_name):
        args = ['/sbin/blkid', '-o', 'list', '|', 'grep', '-w', dev_name]
        if not call_system_sh_output(args):
            return False
        args = ['/sbin/blkid', '-o', 'list', '|', 'grep', '-w', dev_name,
                '|', 'grep', '-w', '"not mounted"']
        if not call_system_sh_output(args):
            log.error('Device %s already mounted' % dev_name)
            return True
        else:
            return False

    @classmethod
    def check_block_device_unmounted(cls, dev_name):
        args = ['/bin/mount', '-l', '|', 'grep', dev_name]
        if not call_system_sh_output(args):
            log.debug('Device %s is unmounted' % dev_name)
            return True
        else:
            log.debug('Device %s is mounted' % dev_name)
            return False


class SuseOperations(LinuxOperations):
    IFCFG_STR = """BOOTPROTO='static'
BROADCAST=''
ETHTOOL_OPTIONS=''
IPADDR='%s'
NETMASK='%s'
MTU=''
NAME='%s'
NETWORK=''
REMOTE_IPADDR=''
STARTMODE='auto'
USERCONTROL='no'
"""
    NETWORK_FILE = '/etc/sysconfig/network/routes'

    @classmethod
    def write_ip_config(cls, dev, ip):
        (ipaddr, masklen) = ip.split('/')
        netmask = cls.masklen2netmask(int(masklen))
        f = open('/etc/sysconfig/network/ifcfg-%s' % dev, 'w')
        f.write(cls.IFCFG_STR % (ipaddr, netmask, dev))
        f.close()
        return True

    @classmethod
    def remove_ip_config(cls, dev):
        filename = '/etc/sysconfig/network/ifcfg-%s' % dev
        if os.path.isfile(filename):
            os.remove(filename)

    @classmethod
    def write_default_route_config(cls, ip):
        cls.remove_default_route_config()
        try:
            with open(cls.NETWORK_FILE, 'a') as f:
                f.write('default %s - - \n' % ip)
        except Exception as e:
            log.debug('write default route config error: %r' % e)
            return False
        return True

    @classmethod
    def remove_default_route_config(cls):
        args = ['/bin/sed', '-i', r'/default.*/d', cls.NETWORK_FILE]
        if not call_system_check(args):
            log.debug('remove default route config error')
            return False
        return True

    @classmethod
    def init_dns_config(cls):
        try:
            if not os.path.isfile('/etc/resolv.conf'):
                with open('/etc/resolv.conf', 'w') as f:
                    f.write('nameserver %s' % DNS)
        except Exception as e:
            log.debug('init dns error (%s)' % e)
            return False
        return True


class ArchOperations(LinuxOperations):
    IFCFG_STR = """[Match]
Name=%s

[Network]
Address=%s
"""
    NETWORK_FILE = '/etc/systemd/network/%s.network'

    @classmethod
    def write_ip_config(cls, dev, ip):
        f = open('/etc/systemd/network/%s.network' % dev, 'w')
        f.write(cls.IFCFG_STR % (dev, ip))
        f.close()
        return True

    @classmethod
    def remove_ip_config(cls, dev):
        filename = '/etc/systemd/network/%s.network' % dev
        if os.path.isfile(filename):
            os.remove(filename)

    @classmethod
    def write_default_route_config(cls, dev, ip):
        cls.remove_default_route_config(dev)
        try:
            with open(cls.NETWORK_FILE % dev, 'a') as f:
                f.write('Gateway=%s' % ip)
        except Exception as e:
            log.debug('write default route config error: %r' % e)
            return False
        return True

    @classmethod
    def remove_default_route_config(cls, dev):
        args = ['/bin/sed', '-i', r'/Gateway=.*/d', cls.NETWORK_FILE % dev]
        if not call_system_check(args):
            log.debug('remove default route config error')
            return False
        return True

    @classmethod
    def init_dns_config(cls):
        try:
            if not os.path.isfile('/etc/resolv.conf'):
                with open('/etc/resolv.conf', 'w') as f:
                    f.write('nameserver %s' % DNS)
        except Exception as e:
            log.debug('init dns error (%s)' % e)
            return False
        return True


class DebianOperations(LinuxOperations):
    LOCFG_STR = """auto lo
iface lo inet loopback
    address %s
    netmask %s
"""
    IFCFG_STR = """auto %s
iface %s inet static
    address %s
    netmask %s
"""
    IFCFG_FILE = '/etc/network/interfaces'

    @classmethod
    def write_ip_config(cls, dev, ip):
        if not cls.remove_ip_config(dev):
            return False

        (ipaddr, masklen) = ip.split('/')
        netmask = cls.masklen2netmask(int(masklen))
        with open(cls.IFCFG_FILE, 'a') as f:
            f.write('\n')
            if dev == 'lo':
                f.write(cls.LOCFG_STR % (ipaddr, netmask))
            else:
                f.write(cls.IFCFG_STR % (dev, dev, ipaddr, netmask))
        return True

    @classmethod
    def remove_ip_config(cls, dev):
        if not os.path.isfile(cls.IFCFG_FILE):
            log.debug('Configuration file %s not found' % cls.IFCFG_FILE)
            return False

        start = re.compile(r'^auto\s+\b%s\b' % dev)
        end = re.compile(r'^auto')
        removing = False
        modified = False
        lines = []
        try:
            with open(cls.IFCFG_FILE, 'r') as f:
                for line in f:
                    if not removing:
                        if start.search(line):
                            removing = True
                            modified = True
                        else:
                            lines.append(line)
                    else:
                        if end.search(line) and not start.search(line):
                            removing = False
                            lines.append(line)
            if not modified:
                return True
        except Exception as e:
            log.debug('read interface config error: %r' % e)
            return False

        # remove trailing blank lines
        non_blank_line = re.compile(r'\w')
        while len(lines) > 0 and not non_blank_line.search(lines[-1]):
            lines.pop()
        try:
            with open(cls.IFCFG_FILE, 'w') as f:
                for line in lines:
                    f.write(line)
        except Exception as e:
            log.debug('write interface config error: %r' % e)
            return False
        return True

    @classmethod
    def write_default_route_config(cls, ip):
        cls.remove_default_route_config()
        if not os.path.isfile(cls.IFCFG_FILE):
            log.debug('Configuration file %s not found' % cls.IFCFG_FILE)
            return False

        regex_start = re.compile(r'^iface\s+\w+')
        address = None
        regex_address = re.compile(r'address\s+(\S+)')
        netmask = None
        regex_netmask = re.compile(r'netmask\s+(\S+)')
        lines = []
        try:
            with open(cls.IFCFG_FILE, 'r') as f:
                for line in f:
                    lines.append(line)
                    if regex_start.search(line) is not None:
                        address = None
                        netmask = None
                        continue
                    m = regex_address.search(line)
                    if m is not None:
                        address = m.group(1)
                        if cls.validate_ip_without_mask(address) is False:
                            log.debug('Configuration file %s corrupted' %
                                      cls.IFCFG_FILE)
                            return False
                    m = regex_netmask.search(line)
                    if m is not None:
                        netmask = m.group(1)
                        if cls.validate_ip_without_mask(netmask) is False:
                            log.debug('Configuration file %s corrupted' %
                                      cls.IFCFG_FILE)
                            return False
                    if address is not None and netmask is not None and \
                            cls.in_same_subnet(ip, address, netmask):
                        lines.append('    gateway %s\n' % ip)
                        address = None
                        netmask = None
        except Exception as e:
            log.debug('read interface config error: %r' % e)
            return False

        # remove trailing blank lines
        non_blank_line = re.compile(r'\w')
        while len(lines) > 0 and not non_blank_line.search(lines[-1]):
            lines.pop()
        try:
            with open(cls.IFCFG_FILE, 'w') as f:
                for line in lines:
                    f.write(line)
        except Exception as e:
            log.debug('write interface config error: %r' % e)
            return False

        return True

    @classmethod
    def remove_default_route_config(cls):
        args = ['/bin/sed', '-i', r'/gateway.*/d', cls.IFCFG_FILE]
        if not call_system_check(args):
            log.debug('remove default route config error')
            return False
        return True

    @classmethod
    def init_dns_config(cls):
        try:
            if not os.path.isfile('/etc/resolv.conf'):
                with open('/etc/resolv.conf', 'w') as f:
                    f.write('nameserver %s' % DNS)
        except Exception as e:
            log.debug('init dns error (%s)' % e)
            return False
        return True


class UbuntuOperations(LinuxOperations):
    INITIATORNAME_STR = """InitiatorName=%s
"""
    INITIATORNAME_FILE = '/etc/iscsi/initiatorname.iscsi'

    @classmethod
    def write_ip_config(cls, dev, ip):
        return DebianOperations.write_ip_config(dev, ip)

    @classmethod
    def remove_ip_config(cls, dev):
        return DebianOperations.remove_ip_config(dev)

    @classmethod
    def write_default_route_config(cls, ip):
        return DebianOperations.write_default_route_config(ip)

    @classmethod
    def remove_default_route_config(cls):
        return DebianOperations.remove_default_route_config()

    @classmethod
    def init_dns_config(cls):
        try:
            with open('/etc/resolvconf/resolv.conf.d/base', 'a+') as f:
                content = f.read()
                if content.find('nameserver') == -1:
                    f.write('nameserver %s' % DNS)
        except Exception as e:
            log.debug('init dns conf error (%s)' % e)
            return False
        if not call_system_check(['resolvconf', '-u']):
            log.error('init dns failed')
            return False
        return True

    @classmethod
    def check_iscsi_service_existance(cls):
        args = ['/etc/init.d/open-iscsi', 'status']
        if not call_system_check(args):
            log.error('Service iscsi does not exist')
            return False
        return True

    @classmethod
    def generate_initiator_iqn(cls):
        initiator_iqn = call_system_output(['/usr/sbin/iscsi-iname'])
        if not cls.validate_iqn(initiator_iqn):
            log.error('Generate iqn %s error' % initiator_iqn)
            return None
        else:
            return initiator_iqn

    @classmethod
    def write_initiator_iqn(cls, initiator_iqn):
        try:
            with open(cls.INITIATORNAME_FILE, 'w') as f:
                f.write(cls.INITIATORNAME_STR % initiator_iqn)
                f.close()
            return True
        except Exception as e:
            log.debug('Write [%s] failed (%r)' % (cls.INITIATORNAME_FILE, e))
            return False

    @classmethod
    def discover_iscsi_target(cls, ip, port):
        args = ['/usr/bin/iscsiadm', '-m', 'discovery', '-t', 'sendtargets',
                '-p', '%s:%d' % (ip, port)]
        if not call_system_check(args):
            log.error('Target %s does not exist' % ip)
            return False
        return True

    @classmethod
    def login_iscsi_target(cls, iqn, ip, port):
        args = ['/usr/bin/iscsiadm', '-m', 'node', '-T', iqn, '-p',
                '%s:%d' % (ip, port), '-l']
        if not call_system_check(args):
            log.error('Login Target %s error' % iqn)
            return False
        return True

    @classmethod
    def logout_iscsi_target(cls, iqn, ip, port):
        args = ['/usr/bin/iscsiadm', '-m', 'node', '-T', iqn, '-p',
                '%s:%d' % (ip, port), '-u']
        if not call_system_check(args):
            log.error('Logout Target %s error' % iqn)
            return False
        return True

    @classmethod
    def update_iscsi_target(cls, iqn, ip, port):
        args = ['/usr/bin/iscsiadm', '-m', 'node', '-T', iqn, '-p',
                '%s:%d' % (ip, port), '-R']
        if not call_system_check(args):
            log.error('Update Target %s error' % iqn)
            return False
        return True

    @classmethod
    def check_iscsi_session_existance(cls, iqn):
        args = ['/usr/bin/iscsiadm', '-m', 'session', '|', 'grep', iqn]
        if not call_system_check(args):
            log.error('Session %s not active' % iqn)
            return False
        return True

    @classmethod
    def check_block_device_unmounted(cls, dev_name):
        args = ['/bin/mount', '-l', '|', 'grep', dev_name]
        if not call_system_sh_output(args):
            log.debug('Device %s is unmounted' % dev_name)
            return True
        else:
            log.debug('Device %s is mounted' % dev_name)
            return False


class WindowsOperations(Operations):
    name_table = {}
    PS_CMD = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"

    @classmethod
    def get_name_by_mac(cls, mac):
        if mac in cls.name_table:
            return cls.name_table[mac]
        args = ['getmac', '/FO', 'csv', '/NH', '/V']
        out = call_system_output(args)
        if out:
            info_list = out.split('\n')
            for i in info_list:
                if not i:
                    continue
                tmp = i.split(',')
                if len(tmp) < 4:
                    continue
                name, _, device_mac, _ = tmp
                device_mac = \
                    device_mac.strip().strip('"').replace('-', ':').lower()
                if mac == device_mac:
                    cls.name_table[mac] = name
                    return name
        return None

    @classmethod
    def check_ip_existance(cls, ip):
        args = ['netsh', 'interface', 'ip', 'dump']
        out = call_system_output(args)
        if out:
            (ipaddr, _) = ip.split('/')
            regex = 'add address.*%s' % ipaddr.replace('.', '\.')
            if re.search(regex, out) is None:
                return False
            log.debug('IP exists')
            return True
        return False

    @classmethod
    def check_node_existance(cls, node):
        out = call_system_output(['route', 'print'])
        if out:
            (ipaddr, masklen) = node.split('/')
            netmask = cls.masklen2netmask(int(masklen))
            regex = '%s\s+%s' % (ipaddr.replace('.', '\.'),
                                 netmask.replace('.', '\.'))
            if re.search(regex, out) is None:
                return False
            log.debug('Route for %s exists' % node)
            return True
        return False

    @classmethod
    def get_ifid_from_mac(cls, mac):
        out = call_system_output(['route', 'print'])
        if out:
            regex = '(\d+)...%s' % mac.replace(':', ' ')
            ma = re.search(regex, out)
            if ma is None:
                return None
            return ma.group(1)
        return None

    @classmethod
    def disable_offload(cls, dev):
        # only disable offload in xenserver vms
        if not call_windows_system_check(
                ['tasklist', '|', 'findstr', 'qemu-ga.exe']):
            if not call_windows_system_check(
                    ['netsh', 'interface', 'ipv4', 'set', 'global',
                     'taskoffload=disabled']):
                log.debug('Disable ipv4 offload for %s error' % dev)
                return False
            if not call_windows_system_check(
                    ['netsh', 'interface', 'tcp', 'set', 'global',
                     'rss=disabled', 'chimney=disabled', 'netdma=disabled']):
                log.debug('Disable tcp offload for %s error' % dev)
                return False
        return True

    @classmethod
    def config_ip(cls, dev, ip):
        (ipaddr, masklen) = ip.split('/')
        netmask = cls.masklen2netmask(int(masklen))
        if not call_windows_system_check(
                ['netsh', 'interface', 'ip', 'set', 'address',
                 dev, 'static', ipaddr, netmask]):
            log.debug('Config IP for %s error' % dev)
            return False
        if not call_windows_system_check(
                ['netsh', 'interface', 'ip', 'set', 'dns',
                 dev, 'static', DNS]):
            log.debug('Config DNS for %s error' % dev)
            return False
        return True

    @classmethod
    def add_ip(cls, dev, ip):
        (ipaddr, masklen) = ip.split('/')
        netmask = cls.masklen2netmask(int(masklen))
        if not call_windows_system_check(
                ['netsh', 'interface', 'ip', 'add', 'address',
                 dev, ipaddr, netmask]):
            log.debug('Add IP for %s error' % dev)
            return False
        return True

    @classmethod
    def del_ip(cls, dev, ip):
        (ipaddr, _) = ip.split('/')
        if not call_windows_system_check(
                ['netsh', 'interface', 'ip', 'delete', 'address',
                 dev, ipaddr]):
            log.debug('Delete IP for %s error' % dev)
            return False
        return True

    @classmethod
    def flush_ip(cls, dev):
        if not call_windows_system_check(
                ['netsh', 'interface', 'ip', 'set', 'address', dev, 'dhcp']):
            log.debug('Flush IP for %s failed, may already be clean' % dev)
        return True

    @classmethod
    def add_route(cls, node, nh, mac):
        assert nh is not None
        (ipaddr, masklen) = node.split('/')
        netmask = cls.masklen2netmask(int(masklen))
        args = ['route', '-p', 'add', ipaddr, 'mask', netmask, nh]
        if mac is not None:
            ifid = cls.get_ifid_from_mac(mac)
            if ifid is None:
                log.debug('Device %s is invalid' % mac)
                return False
            args.extend(['if', ifid])
        if not call_system_check(args):
            log.debug('Add route for %s error' % node)
            return False
        return True

    @classmethod
    def del_route(cls, node):
        (ipaddr, masklen) = node.split('/')
        netmask = cls.masklen2netmask(int(masklen))
        args = ['route', 'delete', ipaddr, 'mask', netmask]
        if not call_system_check(args):
            log.debug('Delete route for %s error' % node)
            return False
        return True

    @classmethod
    def write_default_route_config(cls, ip):
        return True

    @classmethod
    def remove_default_route_config(cls):
        return True

    @classmethod
    def self_init_script(cls):
        init_script = \
            os.path.dirname(os.path.realpath(__file__)) + '/script/init.bat'
        if not call_windows_system_check([init_script]):
            log.debug('Self init error')
            return False
        return True

    @classmethod
    def check_block_device_unmounted(cls, dev_name):
            return True

    @classmethod
    def get_azure_backup_usage(cls):
        args = [cls.PS_CMD, "-ExecutionPolicy", "Unrestricted",
                "Import-Module", "MSOnlineBackup"]
        ret, _ = call_system_output_no_log(args)
        if not ret:
            return 0

        args = [cls.PS_CMD, "-ExecutionPolicy", "Unrestricted",
                "Get-OBMachineUsage", "|", "ConvertTo-Json"]
        ret, out = call_system_output_no_log(args)
        if ret:
            usage_info = json.loads(out)
            if 'StorageUsedByMachineInBytes' in usage_info:
                return usage_info['StorageUsedByMachineInBytes']
        return 0
