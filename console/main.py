# -*-coding: utf-8 -*-


import colorinfo
import os
import re
import subprocess
import socket


tools_dir = os.path.join(os.path.abspath(os.path.curdir), "tools")
grgrant_prog = os.path.join(tools_dir, "grgrant")

prompt = colorinfo.bcolors.OKBLUE + ">> " + colorinfo.bcolors.ENDC

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


def save_networkcfg(interface, address, mask, gateway):
    net_cfg_file = net_cfg_file_prefix + interface
    net_cfg_file = os.path.join(net_cfg_pos, net_cfg_file)
    if os.path.exists(net_cfg_file):
        s = open(net_cfg_file, 'r').read()
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


def help():
    colorinfo.show_info('help      # show this message')
    colorinfo.show_info('stat      # view ipsan status')
    colorinfo.show_info('if        # show ip address')
    colorinfo.show_info('ifcfg     # config ip address')
    colorinfo.show_info('reboot    # reboot ipsan')
    colorinfo.show_info('poweroff  # poweroff ipsan')


def confirm(prompt):
    r = input(colorinfo.format_confim_text(prompt))
    if r in ['yes', 'y', 'Y', 'YES']:
        return True
    else:
        return False


def _ifconfig():
    args = [grgrant_prog, "/sbin/ifconfig"]
    try:
        r = subprocess.check_output(args, universal_newlines=True)
        return r
    except subprocess.CalledProcessError as e:
        colorinfo.show_info(e.message)


def get_nic_interfaces():
    interfaces = []
    r = _ifconfig()
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


def validate_ip(address):
    try:
        socket.inet_aton(address)
        return address
    except socket.error:
        colorinfo.show_fail('Invalid ip address')


def stat():
    pass


def show_ip():
    r = _ifconfig()
    if r:
        colorinfo.show_info(r)


def ifcfg():
    interfaces = get_nic_interfaces()
    nic = len(interfaces) - 1
    address = None
    gateway = None
    mask = '255.255.255.0'

    for i, name in enumerate(interfaces):
        colorinfo.show_info("%s: %s" % (i, name))

    r = input(colorinfo.format_input_text('Choice a interface[0..%s]? ' % nic))
    if not r.isnumeric():
        colorinfo.show_fail('Input must be a number.')
        return
    n = int(r)
    if n < 0 or n > nic:
        colorinfo.show_fail('Input must in range [0..%s].' % nic)
        return
    r = input(colorinfo.format_input_text('%s IP ? ' % interfaces[n]))
    address = validate_ip(r)
    if address is None:
        return
    r = input(colorinfo.format_input_text('%s Mask ? ' % interfaces[n]))
    if len(r) > 0:
        r = validate_ip(r)
        if r:
            mask = r
    r = input(colorinfo.format_input_text('%s Gateway ? ' % interfaces[n]))
    if len(r) == 0:
        colorinfo.show_warning('Skip config gateway')
    else:
        r = validate_ip(r)
        if r:
            gateway = r

    colorinfo.show_info('-'*30)
    colorinfo.show_info('Interface=%s' % interfaces[n])
    colorinfo.show_info('IP=%s' % address)
    colorinfo.show_info('MASK=%s' % mask)
    if gateway:
        colorinfo.show_info('GATEWAY=%s' % gateway)
    colorinfo.show_info('-'*30)

    r = confirm('Save network configuration')

    if r:
        save_networkcfg(interfaces[n], address, mask, gateway)


def reboot():
    r = confirm('Confirm to reboot')
    if r:
        subprocess.call(['/sbin/reboot'])


def poweroff():
    r = confirm('Confirm to poweroff')
    if r:
        subprocess.call(['/sbin/poweroff'])


def xterm():
    subprocess.call(['/usr/bin/xterm'])


def process_input(input):
    input = input.lower().strip()
    if input == 'h' or input == 'help':
        help()
    elif input == 'stat':
        stat()
    elif input == 'if':
        show_ip()
    elif input == 'ifcfg':
        ifcfg()
    elif input == 'reboot':
        reboot()
    elif input == 'poweroff':
        poweroff()
    elif input == 'xterm':
        xterm()
    else:
        colorinfo.show_fail("Unrecognized command. Press 'h' to view help.")


def main():
    os.system('clear')  # clear screen
    colorinfo.show_info("Welcome to use ubique ipsan. Press 'h' to view help")
    while True:
        try:
            r = input(prompt)
            process_input(r)
        except KeyboardInterrupt:
            print()
            pass
        except EOFError:
            print()
            pass


if __name__ == '__main__':
    main()
