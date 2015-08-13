# -*-coding: utf-8 -*-


import os
import re
import argparse
import socket
import logging
import subprocess
import event


tools_dir = os.path.join(os.path.abspath(os.path.curdir), "tools")
grgrant_prog = os.path.join(tools_dir, "grgrant")


_re_nic_inter = re.compile(r'(^[a-zA-Z0-9]+)\s+Link encap')
net_cfg_pos = '/etc/sysconfig/network'
net_cfg_file_prefix = 'ifcfg-'
net_cfg_items = '''
STARTMODE=auto
BOOTPROTO=static
IPADDR=%s
NETMASK=%s
GATEWAY=%s
'''


def validate_ip(address):
    try:
        socket.inet_aton(address)
        return address
    except socket.error:
        return None


def ifconfig():
    args = [grgrant_prog, "/sbin/ifconfig"]
    try:
        r = subprocess.check_output(args, universal_newlines=True)
        return r
    except subprocess.CalledProcessError:
        return None


def get_nic_interfaces():
    interfaces = []
    r = ifconfig()
    if r is None:
        return interfaces

    lines = r.split(os.linesep)

    for line in lines:
        r = _re_nic_inter.match(line)
        if r:
            if r.group(1) == 'lo':  # skip loopback address
                continue
            interfaces.append(r.group(1))

    return interfaces


def config_ip(interface, ip, mask, route):
    interfaces = get_nic_interfaces()
    if interface not in interfaces:
        print('Invalid interface.Available interface:%s' % interfaces)
        exit(-1)

    if ip:
        ip = validate_ip(ip)
        if ip is None:
            exit(-1)
    if mask:
        mask = validate_ip(mask)
        if mask is None:
            exit(-1)
    if route:
        route = validate_ip(route)
        if route is None:
            exit(-1)
    save_networkcfg(interface, ip, mask, route)


def save_networkcfg(interface, address, mask, gateway):
    net_cfg_file = net_cfg_file_prefix + interface
    net_cfg_file = os.path.join(net_cfg_pos, net_cfg_file)
    if os.path.exists(net_cfg_file):
        s = open(net_cfg_file, 'r').read()
        if address:
            s = re.sub(r'(IPADDR=)([^\n]+)', r'\g<1>%s' % address, s)
        if mask:
            s = re.sub(r'(NETMASK=)([^\n]+)', r'\g<1>%s' % mask, s)
        if gateway:
            s = re.sub(r'(GATEWAY=)([^\n]+)', r'\g<1>%s' % gateway, s)
        # backup origin configuration
        if not os.path.exists(net_cfg_file+'.origin'):
            os.rename(net_cfg_file, net_cfg_file+".orgin")
        # save configuration
        open(net_cfg_file, 'w').write(s)
    else:
        open(net_cfg_file, 'w').write(net_cfg_items % (address, mask, gateway))

    event.log_event(logging.INFO, event.event_os,
                    'interface=%s address=%s mask=%s gateway=%s' % (interface, address, mask, gateway),
                    event.event_os_network)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='ipsan console')
    parser.add_argument('--interface', help='network interface')
    parser.add_argument('--ip', help='ip address')
    parser.add_argument('--route', help='ip route')
    parser.add_argument('--mask', help='network mask')
    args = parser.parse_args()
    if args.interface:
        if args.ip and args.route:
            config_ip(args.interface, args.ip, args.mask, args.route)
        elif args.ip:
            config_ip(args.interface, args.ip, args.mask, args.route)
        elif args.route:
            config_ip(args.interface, args.ip, args.mask, args.route)
        else:
            parser.print_help()
    else:
        parser.print_help()
