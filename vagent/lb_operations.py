# -*- coding: utf-8 -*-

import logging
import os
import re
from operations import CentOSOperations
from operations import \
    call_system_check, call_system_sh_check, call_system_sh_output, \
    string_enum

log = logging.getLogger(__name__)


class LBCentOSOperations(CentOSOperations):
    CONF_DIR = '/etc/haproxy/'
    CONF_FILE = '/etc/haproxy/lc_%s.cfg'
    GLOBAL_CONF = '/etc/haproxy/haproxy.cfg'
    CONF_FILE_BAK = '/etc/haproxy/lc_%s.cfg.bak'
    BASIC_CONFIG_STR = """listen %s %s:%d
       mode %s
       balance %s
       %s
       %s
"""
    INSERT_COOKIE_STR = \
        'cookie SESSION_COOKIE insert indirect nocache maxidle %s'
    REWRITE_COOKIE_STR = 'cookie %s prefix'
    SERVER_STR = 'server %s %s:%s cookie %s weight %s'
    DOMAIN_RULE_CONFIG_STR = """acl %s hdr_reg(host) %s
       use_backend %s if %s
"""
    URL_RULE_CONFIG_STR = """acl %s path_reg %s
       use_backend %s if %s
"""
    BACKEND_CONFIG_STR = """\nbackend %s
       balance %s
       %s %s
"""
    DEFAULT_BACKEND_STR = 'default_backend %s'
    DEFAULT_BACKEND_NAME = '%s-default'
    BACKEND_NAME = '%s-%s'
    INDENTATION = '\n       '
    _protocols = ['http', 'tcp']
    protocols = string_enum(*_protocols)
    _server_states = ['ENABLE', 'DISABLE']
    server_states = string_enum(*_server_states)
    _session_strickys = ['NONE', 'INSERT', 'REWRITE']
    session_strickys = string_enum(*_session_strickys)
    _rule_types = ['URL', 'DOMAIN']
    rule_types = string_enum(*_rule_types)

    @classmethod
    def get_stats_socket_list(cls):
        sockets = []
        try:
            with open(cls.GLOBAL_CONF) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('stats socket'):
                        sockets.append(line.split()[2])
        except:
            pass

        return sockets

    @classmethod
    def check_listener_existance(cls, name):
        stat_files = cls.get_stats_socket_list()
        args = ['echo', 'show stat -1 1 -1', '|', 'nc', '-U', stat_files[0],
                '|', 'grep', '-v', '"#"', '|', 'awk', "-F','", "'{print $1}'"]
        out = call_system_sh_output(args)
        if out:
            if re.search(name, ''.join(out.split('\\n'))) is None:
                return False
            log.debug('Listener %s exists' % name)
            return True
        return False

    @classmethod
    def check_server_existance(cls, listener, name):
        stat_files = cls.get_stats_socket_list()
        args = ['echo', 'show stat -1 4 -1', '|', 'nc', '-U', stat_files[0],
                '|', 'grep', listener, '|', 'awk', "-F','", "'{print $2}'"]
        out = call_system_sh_output(args)
        if out:
            if re.search(name, ''.join(out.split('\\n'))) is None:
                return False
            log.debug('Server %s exists on %s' % (name, listener))
            return True
        return False

    @classmethod
    def backup_listener_config(cls, name):
        conf_file = (cls.CONF_FILE % name)
        conf_file_bak = (cls.CONF_FILE_BAK % name)
        if os.path.isfile(conf_file):
            args = ['/bin/cp', '-f', conf_file, conf_file_bak]
            if not call_system_check(args):
                return False
        return True

    @classmethod
    def recovery_listener(cls, name):
        conf_file = (cls.CONF_FILE % name)
        if os.path.isfile(conf_file):
            os.remove(conf_file)

        conf_file_bak = (cls.CONF_FILE_BAK % name)
        if os.path.isfile(conf_file_bak):
            args = ['/bin/mv', '-f', conf_file_bak, conf_file]
            if not call_system_check(args):
                return False

        args = ['service', 'haproxy', 'reload']
        if not call_system_check(args):
            return False
        return True

    @classmethod
    def complete_listener_config(cls, name, servers_info=[]):
        args = ['service', 'haproxy', 'reload']
        if not call_system_check(args):
            cls.recovery_listener(name)
            return False

        for server in servers_info:
            (sname, sip, sport, sweight, sstate, srule) = server.split('/', 5)
            if sstate == cls.server_states.DISABLE and \
                    (not cls.disable_server(name, sname)):
                log.error('Disable listener %s server %s error' %
                          (name, sname))
                cls.recovery_listener(name)
                return False

        conf_file_bak = (cls.CONF_FILE_BAK % name)
        if os.path.isfile(conf_file_bak):
            os.remove(conf_file_bak)
        return True

    @classmethod
    def config_listener(cls, name, ip, port, protocol, balance,
                        sstricky, cookie_info, health_chk, servers_info=[]):
        assert isinstance(servers_info, list)
        cookie_str = ''
        if sstricky == cls.session_strickys.INSERT:
            cookie_str += (cls.INSERT_COOKIE_STR % cookie_info)
        elif sstricky == cls.session_strickys.REWRITE:
            cookie_str += (cls.REWRITE_COOKIE_STR % cookie_info)
        elif sstricky != cls.session_strickys.NONE:
            log.error('Not support session stricky(%s)' % sstricky)
            return False
        default_backend_name = (cls.DEFAULT_BACKEND_NAME % name)

        forward_rules = {}
        servers_config_str = ''
        rule_config_strs = ''
        backend_config_strs = ''
        # default backend servers
        for server in servers_info:
            (sname, sip, sport, sweight, sstate, srule) = server.split('/', 5)
            server_config_str = cls.INDENTATION
            server_config_str += (cls.SERVER_STR %
                                  (sname, sip, sport, sname, sweight))
            if health_chk:
                server_config_str += ' check'
            servers_config_str += server_config_str
            # construct dict {forward_rule, server_config_str)
            if len(srule):
                if srule not in forward_rules:
                    forward_rules[srule] = []
                forward_rules[srule].append(server_config_str)
        backend_config_strs += (cls.BACKEND_CONFIG_STR %
                                (default_backend_name,
                                 balance,
                                 cookie_str,
                                 servers_config_str))

        # forward_rules config and servers
        for rule, servers_info in forward_rules.items():
            (rule_name, rule_type, rule_content) = rule.split('#')
            rule_config_str = cls.INDENTATION
            if rule_type == cls.rule_types.URL:
                rule_config_str += (cls.URL_RULE_CONFIG_STR %
                                    (rule_name, rule_content,
                                     (cls.BACKEND_NAME % (name, rule_name)),
                                     rule_name))
            elif rule_type == cls.rule_types.DOMAIN:
                rule_config_str += (cls.DOMAIN_RULE_CONFIG_STR %
                                    (rule_name, rule_content,
                                     (cls.BACKEND_NAME % (name, rule_name)),
                                     rule_name))
            else:
                log.error('Not support rule_type(%s)' % rule_type)
                return False
            rule_config_strs += rule_config_str

            servers_config_str = ''
            for server_config_str in servers_info:
                servers_config_str += server_config_str
            backend_config_str = (cls.BACKEND_CONFIG_STR %
                                  ((cls.BACKEND_NAME % (name, rule_name)),
                                   balance,
                                   cookie_str,
                                   servers_config_str))
            backend_config_strs += backend_config_str

        # complete config_str
        if protocol == cls.protocols.http:
            default_backend_str = (cls.DEFAULT_BACKEND_STR %
                                   default_backend_name)
            config_str = (cls.BASIC_CONFIG_STR % (name, ip, port, protocol,
                                                  balance, cookie_str,
                                                  default_backend_str))
            config_str += rule_config_strs
            config_str += backend_config_strs
        elif protocol == cls.protocols.tcp:
            config_str = (cls.BASIC_CONFIG_STR % (name, ip, port, protocol,
                                                  balance, cookie_str,
                                                  servers_config_str))
        else:
            log.error('Not support protocol(%s)' % protocol)
            return False

        try:
            conf_file = (cls.CONF_FILE % name)
            with open(conf_file, 'w') as f:
                f.write(config_str)
        except Exception as e:
            log.error('Config listener [%s] failed (%r)' % (config_str, e))
            return False
        return True

    @classmethod
    def delete_listener(cls, name):
        conf_file = (cls.CONF_FILE % name)
        if os.path.isfile(conf_file):
            os.remove(conf_file)
        return True

    @classmethod
    def clear_listener(cls):
        for file in os.listdir(cls.CONF_DIR):
            filename = os.path.splitext(file)
            # Only keep haproxy.cfg file
            if filename[0] != 'haproxy':
                os.remove(cls.CONF_DIR + file)

        args = ['service', 'haproxy', 'reload']
        if not call_system_check(args):
            return False
        return True

    @classmethod
    def disable_server(cls, listener, name):
        stat_files = cls.get_stats_socket_list()
        args = ['echo show stat -1 4 -1', '|', 'nc', '-U', stat_files[0],
                '|', 'grep', listener, '|', "awk -F',' '{print $1}'"]
        out = call_system_sh_output(args)
        if not out:
            backends = []
        else:
            backends = out.split('\n')
        for backend in backends:
            server = backend + '/' + name
            args = []
            for file in stat_files:
                args += ['echo', 'disable server', server,
                         '|', 'nc', '-U', file, '&&']
            del(args[-1])
            if not call_system_sh_check(args):
                log.error('disable %s failed' % server)
                return False
        return True

    @classmethod
    def enable_server(cls, listener, name):
        stat_files = cls.get_stats_socket_list()
        args = ['echo show stat -1 4 -1', '|', 'nc', '-U', stat_files[0],
                '|', 'grep', listener, '|', "awk -F',' '{print $1}'"]
        out = call_system_sh_output(args)
        if not out:
            backends = []
        else:
            backends = out.split('\n')
        for backend in backends:
            server = backend + '/' + name
            args = []
            for file in stat_files:
                args += ['echo', 'enable server', server,
                         '|', 'nc', '-U', file, '&&']
            del(args[-1])
            if not call_system_sh_check(args):
                log.error('enable %s failed' % server)
                return False
        return True

    @classmethod
    def get_servers_health_state_info(cls):
        stat_files = cls.get_stats_socket_list()
        args = ['echo show stat -1 1 -1', '|', 'nc', '-U', stat_files[0],
                '|', "grep -vE  '(^#.*)|(^$)'", '|', "awk -F',' '{print $1}'"]
        out = call_system_sh_output(args)
        if not out:
            listeners_servers_health_state = []
        else:
            listeners = out.split('\n')[:-1]
            listeners_servers_health_state = []
            for listener in listeners:
                listener_servers_health_state = [listener]
                args = ['echo show stat -1 4 -1',
                        '|', 'nc', '-U', stat_files[0],
                        '|', 'grep', listener,
                        '|', "awk -F',| ' '{print $2, $18}'"
                        '|', 'sort -u']
                out = call_system_sh_output(args)
                servers_info = []
                servers_health_state = []
                if out:
                    servers_info = out.split('\n')[:-1]
                for server_info in servers_info:
                    (server, health_state) = server_info.split(' ')
                    servers_health_state.append([server, health_state])
                listener_servers_health_state.append(servers_health_state)
                listeners_servers_health_state.\
                    append(listener_servers_health_state)
        return listeners_servers_health_state

    @classmethod
    def get_listeners_stat_info(cls):
        stat_files = cls.get_stats_socket_list()
        stat_args = []
        for file in stat_files:
            stat_args += ['echo show stat -1 1 -1',
                          '|', 'nc', '-U', file, '&&']
        del(stat_args[-1])
        args = ['echo', '\"`', '('] + stat_args + [')',
                '|', 'grep', '-vE', "'(^#.*)|(^$)'",
                '|', "awk -F',' '{print $1, $34}'", '`\"', '|', 'sort',
                '|', "awk '{a[$1]+=$2}END{for(i in a)print i, a[i]}'"]
        out = call_system_sh_output(args)
        if not out:
            listeners_stat = []
        else:
            listeners_info = out.split('\n')[:-1]
            listeners_stat = []
            for listener_info in listeners_info:
                (listener, conn_num) = listener_info.split(' ')
                listener_stat = [listener, conn_num]
                stat_args = []
                for file in stat_files:
                    stat_args += ['echo show stat -1 4 -1',
                                  '|', 'nc', '-U', file, '&&']
                del(stat_args[-1])
                args = ['echo', '\"`', '('] + stat_args + [')',
                        '|', 'grep', listener, '|', 'grep', '-v', "'^$'",
                        '|', "awk -F',' '{print $2,$34}'", '`\"', '|', 'sort',
                        '|', "awk '{a[$1]+=$2}END{for(i in a)print i,a[i]}'"]
                out = call_system_sh_output(args)
                servers_info = []
                servers_stat = []
                if out:
                    servers_info = out.split('\n')[:-1]
                for server_info in servers_info:
                    (server, conn_num) = server_info.split(' ')
                    servers_stat.append([server, conn_num])
                listener_stat.append(servers_stat)
                listeners_stat.append(listener_stat)
        return listeners_stat
