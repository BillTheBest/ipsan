#!/usr/bin/env python
# -*-coding: utf-8 -*-


import colorinfo
import os
import time
import subprocess
import event
from network import get_nic_interfaces, grgrant_prog, ifconfig, validate_ip, config_ip


prompt = colorinfo.bcolors.OKBLUE + ">> " + colorinfo.bcolors.ENDC


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


def stat():
    pass


def show_ip():
    r = ifconfig()
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
        colorinfo.show_fail('Invalid ip')
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
        config_ip(interfaces[n], address, mask, gateway)


def reboot():
    r = confirm('Confirm to reboot')
    if r:
        event.log_event(logging.INFO, event.event_os, event_os_reboot, 'Reboot')
        subprocess.call([grgrant_prog, '/sbin/reboot'])


def poweroff():
    r = confirm('Confirm to poweroff')
    if r:
        event.log_event(logging.INFO, event.event_os, event_os_poweroff, 'poweroff')
        subprocess.call([grgrant_prog, '/sbin/poweroff'])


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


def loop():
    # start a thread to watch upgrade file
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
    loop()
