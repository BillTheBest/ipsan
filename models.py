# -*-coding: utf-8 -*-


import uuid
import time
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
    state = IntegerField()
    array_id = IntegerField()
    slot = IntegerField()


class PV(Model):
    __table__ = 'pvs'

    id = StringField(primary_key=True)
    name = StringField()
    uuid = StringField()
    vg_name = StringField()
    state = IntegerField()


class VG(Model):
    id = StringField(primary_key=True)
    name = StringField()
    state = IntegerField()


class LVM(Model):
    id = StringField(primary_key=True)
    name = StringField()
    path = StringField()
    vg_name = StringField()
    state = IntegerField()
