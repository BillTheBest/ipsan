# -*-coding: utf-8 -*-


import re
import os
import logging
import ipaddress
import asyncio
import subprocess
import datetime
from aiohttp import web
from coroweb import get, post
from config import grgrant_prog, configs
from errors import APIValueError


@post('/api/reboot')
def api_reboot():
    '''Reboot ipsan. Request url [POST /api/reboot]'''
    subprocess.call([grgrant_prog, '/sbin/reboot'])


@post('/api/poweroff')
def api_poweroff():
    '''Shutdown ipsan. Request url [POST /api/poweroff]'''
    subprocess.call([grgrant_prog, '/sbin/poweroff'])


@get('/api/datetime')
def api_datetime():
    '''Get current datetime. Request url[GET /api/datetime]'''
    now = datetime.datetime.today()
    str_date = '%s-%s-%s %s:%s:%s' % (now.year, now.month, now.day, now.hour, now.minute, now.second)
    return dict(retcode=0, datetime=str_date)

@post('/api/datetime')
def api_modify_datetime(*, datetime):
    '''
    Modify datetime. Request url [POST /api/datetime]

    Post data:

        datetime: format:2015-02-27 12:44:50
    '''
    try:
        dt = datetime.datetime.strptime(datetime, '%Y-%m-%d %H:%M:%S')
    except ValueError as e:
        raise APIValueError('dateime')

    return dict(retcode=0, datetime=datetime)


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
            nics.insert(0, nic)

        r = _re_mac.match(line)
        if r  and len(nics) > 0:
            nics[0]['mac'] = r.group(1)
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
    args =[grgrant_prog, 'console/network.py', '--interface', interface]
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


@get('/api/sysinfo')
def api_sysinfo():
    '''Get system information. Request url [GET /api/sysinfo]'''
    info = dict()
    info['version'] = configs.sysinfo.version
    info['SN'] = configs.sysinfo.SN
    info['model'] = configs.sysinfo.model
    info['vendor'] = configs.sysinfo.vendor
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

        The file name of upgrade package must match 'goldenrod-IPSAN*.tar.gz'
        pattern
    '''
    data = yield from request.post()
    file_name = data['file'].filename
    input_file = data['file'].file
    # content = input_file.read()
    yield from saveas(input_file, file_name)
    # return web.Response(body=content)
    return dict(retcode=0, filename=file_name)
