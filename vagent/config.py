# -*- coding: utf-8 -*-

import logging
import xml.etree.ElementTree as ET
from os.path import isfile
from threading import RLock

log = logging.getLogger(__name__)


class Interface(object):
    def __init__(self, dev, primary_ip, secondary_ips=None):
        self.dev = dev
        self.primary_ip = primary_ip
        if secondary_ips is None:
            secondary_ips = []
        self.secondary_ips = secondary_ips


class Route(object):
    def __init__(self, node, nh=None, dev=None):
        self.node = node
        self.nh = nh
        self.dev = dev


class Config(object):
    filename = None
    interfaces = []
    routes = []
    lock = RLock()

    @classmethod
    def read_conf(cls):
        with cls.lock:
            assert cls.filename is not None
            filename = cls.filename
            cls.interfaces = []
            cls.routes = []
            if not isfile(filename):
                cls.write_conf()
            else:
                try:
                    tree = ET.parse(filename)
                    root = tree.getroot()
                    interfaces = root.find('interfaces')
                    assert interfaces is not None
                    routes = root.find('routes')
                    assert routes is not None
                except:
                    log.error('Invalid config file %s' % filename)
                    return

                for intf in interfaces.findall('interface'):
                    name = intf.find('name')
                    if name is None:
                        log.error('No name for device')
                        continue
                    dev = name.text
                    if dev in [i.dev for i in cls.interfaces]:
                        log.error('Duplicate device %s' % dev)
                        continue
                    primary_ip = None
                    secondary_ips = []
                    for ip in intf.findall('ip'):
                        if ip.get('type') == 'primary':
                            primary_ip = ip.text
                            break
                    if primary_ip is None:
                        log.error('No primary IP for %s' % dev)
                        continue
                    for ip in intf.findall('ip'):
                        if ip.get('type') == 'secondary':
                            if ip.text == primary_ip or \
                                    ip.text in secondary_ips:
                                log.error('Duplicate IP %s' % ip.text)
                                continue
                            secondary_ips.append(ip.text)
                        elif ip.get('type') == 'primary':
                            continue
                        else:
                            log.error("Unknown type '%s' in config" %
                                      ip.get('type'))
                            continue
                    cls.interfaces.append(Interface(dev, primary_ip,
                                                    secondary_ips))

                for route in routes.findall('route'):
                    e_node = route.find('node')
                    if e_node is None:
                        log.error('No node for route')
                        continue
                    node = e_node.text
                    if node in [i.node for i in cls.routes]:
                        log.error('Duplicate node %s' % node)
                        continue
                    e_nh = route.find('nh')
                    e_dev = route.find('dev')
                    if e_nh is None and e_dev is None:
                        log.error('No next hop or dev for route')
                        continue
                    nh = e_nh.text if e_nh is not None else None
                    dev = e_dev.text if e_dev is not None else None
                    cls.routes.append(Route(node, nh, dev))

    @classmethod
    def _indent(cls, elem, level=0):
        i = '\n' + level * '  '
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + '  '
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                cls._indent(elem, level + 1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i

    @classmethod
    def write_conf(cls):
        with cls.lock:
            assert cls.filename is not None
            filename = cls.filename
            root = ET.Element('config')

            ifs = ET.SubElement(root, 'interfaces')
            for interface in cls.interfaces:
                intf = ET.Element('interface')
                name = ET.Element('name')
                name.text = interface.dev
                intf.append(name)
                ip = ET.Element('ip', {'type': 'primary'})
                ip.text = interface.primary_ip
                intf.append(ip)
                for s_ip in interface.secondary_ips:
                    ip = ET.Element('ip', {'type': 'secondary'})
                    ip.text = s_ip
                    intf.append(ip)
                ifs.append(intf)

            routes = ET.SubElement(root, 'routes')
            for r in cls.routes:
                route = ET.Element('route')
                node = ET.Element('node')
                node.text = r.node
                route.append(node)
                if r.nh is not None:
                    nh = ET.Element('nh')
                    nh.text = r.nh
                    route.append(nh)
                if r.dev is not None:
                    dev = ET.Element('dev')
                    dev.text = r.dev
                    route.append(dev)
                routes.append(route)

            cls._indent(root)
            tree = ET.ElementTree(root)
            tree.write(filename, encoding='utf-8')

    @classmethod
    def config_ip(cls, dev, ip):
        with cls.lock:
            cls.read_conf()
            interface = None
            for intf in cls.interfaces:
                if intf.dev == dev:
                    interface = intf
                    break
            if interface is None:
                interface = Interface(dev, ip)
                cls.interfaces.append(interface)
            else:
                interface.primary_ip = ip
            cls.write_conf()

    @classmethod
    def add_ip(cls, dev, ip):
        with cls.lock:
            cls.read_conf()
            interface = None
            for intf in cls.interfaces:
                if intf.dev == dev:
                    interface = intf
                    break
            if interface is not None:
                interface.secondary_ips.append(ip)
            else:
                interface = Interface(dev, ip)
                cls.interfaces.append(interface)
            cls.write_conf()

    @classmethod
    def del_ip(cls, dev, ip):
        with cls.lock:
            cls.read_conf()
            interface = None
            for intf in cls.interfaces:
                if intf.dev == dev:
                    interface = intf
                    break
            if interface is not None:
                interface.secondary_ips.remove(ip)
                cls.write_conf()

    @classmethod
    def flush_ip(cls, dev):
        with cls.lock:
            cls.read_conf()
            interface = None
            for intf in cls.interfaces:
                if intf.dev == dev:
                    interface = intf
                    break
            if interface is not None:
                cls.interfaces.remove(interface)
                cls.write_conf()

    @classmethod
    def add_route(cls, node, nh, dev):
        with cls.lock:
            cls.read_conf()
            route = None
            for r in cls.routes:
                if r.node == node:
                    route = r
                    break
            if route is None:
                route = Route(node, nh, dev)
                cls.routes.append(route)
            else:
                if nh is not None:
                    route.nh = nh
                if dev is not None:
                    route.dev = dev
            cls.write_conf()

    @classmethod
    def del_route(cls, node):
        with cls.lock:
            cls.read_conf()
            route = None
            for r in cls.routes:
                if r.node == node:
                    route = r
                    break
            if route is not None:
                cls.routes.remove(route)
                cls.write_conf()
