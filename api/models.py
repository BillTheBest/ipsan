# -*-coding: utf-8 -*-


import uuid
import time
import asyncio
from orm import Model, StringField, IntegerField, TextField, BooleanField


class User(Model):
    __table__ = 'users'

    id = StringField(primary_key=True, default=uuid.uuid4().hex)
    name = StringField()
    password = StringField()
    admin = BooleanField()
    created_at = IntegerField(default=int(time.time()))


class Array(Model):
    __table__ = 'arrays'

    id = StringField(primary_key=True, default=uuid.uuid4().hex)
    name = StringField()
    device = StringField()
    level = IntegerField()
    capacity = IntegerField()
    chunk_size = IntegerField()
    created_at = IntegerField(default=int(time.time()))
    state = StringField()


class Disk(Model):
    __table__ = 'disks'

    id = StringField(primary_key=True)
    name = StringField()
    device = StringField()
    state = IntegerField()
    array_id = IntegerField()
    slot = IntegerField()
    capacity = IntegerField()


class PV(Model):
    __table__ = 'pvs'

    id = StringField(primary_key=True)
    name = StringField()
    uuid = StringField()
    vg_name = StringField()
    state = IntegerField()


class VG(Model):
    __table__ = 'vgs'

    id = StringField(primary_key=True)
    name = StringField()
    state = IntegerField()
    size = IntegerField()


class LVM(Model):
    __table__ = 'lvms'

    id = StringField(primary_key=True)
    name = StringField()
    path = StringField()
    vg_name = StringField()
    state = IntegerField()
    size = IntegerField()


class Target(Model):
    __table__ = 'targets'

    id = StringField(primary_key=True)
    tid = IntegerField()
    iqn = StringField()
    name = StringField()
    driver = StringField()
    state = IntegerField()


class LUN(Model):
    __table__ = 'luns'

    id = StringField(primary_key=True)
    lid = IntegerField()
    name = StringField()
    type = StringField()
    size = IntegerField()
    tid = IntegerField()
    state = IntegerField()


# define event action
event_action_add = 1
event_action_del = 2
event_action_mod = 3
event_action_view = 4
event_action_login = 5
event_action_logout = 6

event_action_reboot = 7
event_action_poweroff = 8
event_action_network = 9
event_action_datetime = 10


# define api event category
event_category = 1  # evnets from api


event_os = 1
event_upgrade = 2
event_user = 3
event_array = 4
event_vg = 5
event_lvm = 6
event_target = 7


class Event(Model):
    __table__ = 'events'

    id = StringField(primary_key=True, default=uuid.uuid4().hex)
    level = IntegerField()
    category = IntegerField()
    type = IntegerField()
    action = IntegerField()
    message = TextField()
    created_at = IntegerField(default=int(time.time()))


@asyncio.coroutine
def log_event(level, type, action, message):
    event = Event()
    event.id = uuid.uuid4().hex  # avoid repeat id
    event.level = level
    event.category = event_category
    event.type = type
    event.action = action
    event.message = message
    event.created_at = int(time.time())
    yield from event.save()
