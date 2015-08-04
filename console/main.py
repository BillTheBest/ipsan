# -*-coding: utf-8 -*-


import colorinfo
import os
import re
import subprocess


tools_dir = os.path.join(os.path.abspath(os.path.curdir), "tools")
grgrant_prog = os.path.join(tools_dir, "grgrant")

prompt = colorinfo.bcolors.OKBLUE + ">> " + colorinfo.bcolors.ENDC

_re_nic_inter = re.compile(r'(^[a-zA-Z0-9]+)\s+Link encap')


def help():

    colorinfo.show_info('help      # show this message')
    colorinfo.show_info('stat      # view ipsan status')
    colorinfo.show_info('if        # show ip address')
    colorinfo.show_info('ifcfg     # config ip address')
    colorinfo.show_info('reboot    # config ip address')
    colorinfo.show_info('poweroff  # config ip address')


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
            interfaces.append(r.group(1))

    return interfaces


def stat():
    pass


def show_ip():
    r = _ifconfig()
    if r:
        colorinfo.show_info(r)


def ifcfg():
    interfaces = get_nic_interfaces()
    nic = len(interfaces)
    for i, name in enumerate(interfaces):
        colorinfo.show_info("%s: %s" % (i, name))

    r = input(colorinfo.format_input_text('Choice a interface[0..%s]:' % nic))
    if not r.isnumeric():
        colorinfo.show_fail('Input must be a number.')
        return
    n = int(r)
    if n < 0 or n >= nic:
        colorinfo.show_fail('Input must in range [0..%s].' % nic)
        return
    r = input(colorinfo.format_input_text('Config %s ip:' % interfaces[n]))
    print(r)


def reboot():
    pass


def poweroff():
    pass


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
    else:
        colorinfo.show_fail("Unrecognized command. Press 'h' to view help.")


def main():
    colorinfo.show_info("Welcome to use ubique ipsan. Press 'h' to view help")
    while True:
        try:
            r = input(prompt)
            process_input(r)
        except KeyboardInterrupt as e:
            print()
            pass
        except EOFError as e:
            print()
            pass


if __name__ == '__main__':
    main()
