# -*-coding: utf-8 -*-


import re
import os
import sys
import logging
import ipaddress
import asyncio
import subprocess
import datetime
from aiohttp import web
from coroweb import get, post
from models import *
from config import grgrant_prog, configs
from errors import APIValueError


@post('/api/reboot')
def api_reboot():
    '''Reboot ipsan. Request url [POST /api/reboot]'''
    yield from log_event(logging.INFO, event_os, event_action_reboot,'Reboot')
    subprocess.call([grgrant_prog, '/sbin/reboot'])


@post('/api/poweroff')
def api_poweroff():
    '''Shutdown ipsan. Request url [POST /api/poweroff]'''
    yield from log_event(logging.INFO, event_os, event_action_poweroff,'Shutdown')
    subprocess.call([grgrant_prog, '/sbin/poweroff'])


@get('/api/datetime')
def api_datetime():
    '''Get current datetime. Request url[GET /api/datetime]'''
    now = datetime.datetime.today()
    str_date = '%s/%02d/%02d %02d:%02d:%02d' % (now.year, now.month, now.day, now.hour, now.minute, now.second)
    return dict(retcode=0, datetime=str_date)

@post('/api/datetime')
def api_modify_datetime(*, now):
    '''
    Modify datetime. Request url [POST /api/datetime]

    Post data:

        now:2015/02/27 12:44:50
    '''
    try:
        dt = datetime.datetime.strptime(now, '%Y/%m/%d %H:%M:%S')
    except ValueError as e:
        raise APIValueError('Invalid datetime format(yyyy/mm/dd HH:MM:SS)')

    args = [grgrant_prog, 'date', '-s', now]
    r = subprocess.call(args)
    if r == 0:
        log_event(logging.INFO, event_os, event_action_datetime, 'Change system datetime:%s' % dt)
    return dict(retcode=0, datetime=now)


_re_nic = re.compile(r'^[^:]+:([^:]+):.+state\s([^\s]+)')
_re_mac = re.compile(r'^link/ether\s([^\s]+)')
_re_ip = re.compile(r'^inet\s([^\s]+)')


@asyncio.coroutine
def _parse_ipaddr(output):
    nics = []
    lines = output.split(os.linesep)
    for line in lines:
        line = line.strip()
        r = _re_nic.match(line)
        if r:
            interface = r.group(1).strip()
            if interface == 'lo':
                continue
            nic = dict()
            nic['interface'] = interface
            nic['state'] = r.group(2)
            nic['ip'] = ''
            nic['mask'] = ''
            nics.insert(0, nic)

        r = _re_mac.match(line)
        if r  and len(nics) > 0:
            nics[0]['mac'] = r.group(1).upper()
        r = _re_ip.match(line)
        if r and len(nics) > 0:
            ip = ipaddress.ip_interface(r.group(1))
            nics[0]['ip'] = str(ip.ip)
            nics[0]['mask'] = str(ip.netmask)
    return nics


@get('/api/network')
def api_network():
    '''Get network address. Request url [GET /api/network]'''
    args = ['ip', 'addr']
    try:
        r = subprocess.check_output(args, universal_newlines=True)
        interfaces = yield from _parse_ipaddr(r)
        return dict(retcode=0, interfaces=interfaces)
    except subprocess.CalledProcessError as e:
        logging.exception(e)
        return dict(retcode=800, message=e.output)


@post('/api/network')
def api_networksetting(*, interface, **kw):
    '''
    Networking setting. Request url [POST /api/network]

    Post data:

        ip: ip address. [optional]

        mask: network mask. [optional]

        route: network route. [optional]
    '''
    if not interface or not interface.strip():
        raise APIValueError('interface')
    ip = None
    mask = None
    route = None
    for k, v in kw.items():
        if k == 'ip':
            if not v or not v.strip():
                raise APIValueError('mask')
            ip = v
        elif k == 'mask':
            if not v or not v.strip():
                raise APIValueError('mask')
            mask = v
        elif k == 'route':
            if not v or not v.strip():
                raise APIValueError('route')
            route = v
    args =[grgrant_prog, sys.executable, 'admin/network.py', '--interface', interface]
    if ip is None and mask is None and route is None:
        raise APIValueError('need at least one.[ip, mask, route]')
    if ip:
        args.extend(['--ip', ip])
    if mask:
        args.extend(['--mask', mask])
    if route:
        args.extend(['--route', route])
    try:
        r = subprocess.check_output(args, universal_newlines=True)
    except subprocess.CalledProcessError as e:
        logging.exception(e)
        return dict(retcode=801, message='configuration network failure')
    yield from log_event(logging.INFO, event_os, event_action_network,
                         'Networing setting ip:%s mask:%s route:%s' % (ip, mask, route))


@get('/api/sysinfo')
def api_sysinfo():
    '''
    Get system information. Request url [GET /api/sysinfo]

    Response:

        panel: 0-unknow; 1-L6; 2-L6(3x2); 3-L8; 4-L8(4x2); 5-L9; 6-L9(3x3);

        7-L16; 8-L16(4x4); 9-L12(4x3); 10-L24(4x6), 11-L4(4x1)
    '''
    info = dict()
    info['version'] = configs.sysinfo.version
    info['SN'] = configs.sysinfo.SN
    info['model'] = configs.sysinfo.model
    info['vendor'] = configs.sysinfo.vendor
    info['panel'] = configs.sysinfo.panel
    return dict(retcode=0, sysinfo=info)



upload_html = b'''
<form action="/api/upload" method="post" accept-charset="utf-8" enctype="multipart/form-data">
    <label for="file">File</label>
    <input id="file" name="file" type="file" value="" />
    <input type="submit" value="submit" />
</form>
'''
@get('/api/upload')
def upload():
    '''Upload test page. Request url [/api/upload]'''
    return web.Response(body=upload_html)

@asyncio.coroutine
def saveas(fd, filename):
    uploads_dir = 'uploads'
    if not os.path.exists(uploads_dir):
        os.mkdir(uploads_dir)
    savefile = os.path.join(uploads_dir, filename)
    tempfile = '%s.filepart' % savefile
    with open(tempfile, 'wb') as w:
        while True:
            c = fd.read(4096)
            if len(c) == 0:
                break
            w.write(c)
    os.rename(tempfile, savefile)


@post('/api/upload')
def api_upgrade(request):
    '''
    Do upgrade. Request url [POST /api/upload]

    Post data:

        The file name of upgrade package must match 'goldenrod.IPSAN*.tar.gz'
        pattern
    '''
    pattern = re.compile('goldenrod.IPSAN[^\s]*.tar.gz')
    data = yield from request.post()
    file_name = data['file'].filename
    if not pattern.match(file_name):
        return dict(retcode=102, message="Package file name must match 'goldenrod.IPSAN*.tar.gz'")
    input_file = data['file'].file
    # content = input_file.read()
    yield from saveas(input_file, file_name)
    # return web.Response(body=content)
    return dict(retcode=0, filename=file_name)


@get('/api/sysstat')
def api_sysstat():
    '''
    Get system current status information. Reqeust url [GET /api/sysstat]
    '''


@get('/api/diagnosis')
def api_diagnosis():
    '''
    Collect diagnosis information. Request url [GET /api/diagnosis]

    Response:

        filename: diagnosis file name.

    '''
    r = subprocess.call(['./collect_diagnosis.sh'])
    if r == 0:
        logging.info("Collect diagnosis.")

    return dict(retcode=0, filename="diagnosis.tar.gz")
