# -*-coding: utf-8 -*-


import os
import re
import json
import argparse
import socket
import logging
import subprocess
import event


grgrant_prog = os.path.join(os.path.curdir, "grgrant")

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
    args = [grgrant_prog, '/sbin/ifconfig', interface, ip, 'netmask', mask, 'UP']
    subprocess.call(args)


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

    # chnage api server address for web
    store_ip(address)
    event.log_event(logging.INFO, event.event_os, event.event_os_network,
                    'Network setting:interface=%s address=%s mask=%s gateway=%s' % (interface, address, mask, gateway))


def get_ip():
    args = ['curl', '-ql', 'http://127.0.0.1:8000/api/network']
    try:
        r = subprocess.check_output(args, universal_newlines=True)
        s = json.loads(r)
        if s['retcode'] != 0:
            return None

        for interface in s['interfaces']:
            if interface['state'] == 'UP':
                return interface['ip']
        return None
    except subprocess.CalledProcessError as e:
        logging.exception(e)
        return None


def init_ip():
    ip = get_ip()
    if ip is None:
        return

    store_ip(ip)


def store_ip(ip):

    if ip is None or not ip.strip():
        return

    js_file = 'web/js/js.js'
    new_js_file = 'web/js/js.js~'
    if not os.path.exists(js_file):
        return

    with open(js_file, 'r') as r:
        with open(new_js_file, 'w') as w:
            for line in r:
                if line.strip().startswith('var api_server'):
                    api_server = '    var api_server = "%s";%s' % (ip, os.linesep)
                    w.write(api_server)
                else:
                    w.write(line)
    os.rename(new_js_file, js_file)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='IPSan admin tool')
    parser.add_argument('--interface', help='Network interface')
    parser.add_argument('--ip', help='IP address')
    parser.add_argument('--route', help='IP route')
    parser.add_argument('--mask', help='Network mask')
    parser.add_argument('--init', help='Init api server ip', action='store_true')
    parser.add_argument('--store', help='store ip')
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
    elif args.init:
        init_ip()
    elif args.store:
        store_ip(args.store)
    else:
        parser.print_help()
