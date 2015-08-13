# -*-coding: utf-8 -*-


import logging
import sqlite3
import asyncio
from config import configs


@asyncio.coroutine
def select(sql, args=(), size=None):
    with sqlite3.connect(configs.database.name) as conn:
        c = conn.cursor()
        try:
            print(sql)
            c.execute(sql, args)
            if size:
                r = c.fetchmany(size)
            else:
                r = c.fetchall()
            return r
        except Exception as e:
            logging.exception(e)
            return None


@asyncio.coroutine
def execute(sql, args=()):
    with sqlite3.connect(configs.database.name) as conn:
        c = conn.cursor()
        try:
            c.execute(sql, args)
            return c.rowcount
        except Exception as e:
            logging.exception(e)
            return None


class Field(object):
    def __init__(self, name, column_type, primary_key, default):
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        self.default = default

    def str(self):
        return '<%s,%s:%s>' % (self.__class__.__name__,
                               self.name, self.column_type)

    __repr__ = str


class StringField(Field):

    def __init__(self, name=None, primary_key=False, default=None,
                 ddl='varchar(50)'):
        super().__init__(name, ddl, primary_key, default)


class IntegerField(Field):

    def __init__(self, name=None, primary_key=False, default=0):
        super().__init__(name, 'bigint', primary_key, default)


class BooleanField(Field):

    def __init__(self, name=None, default=False):
        super().__init__(name, 'integer', False, default)


class TextField(Field):

    def __init__(self, name=None, default=None):
        super().__init__(name, 'text', False, default)


class ModelMetaclass(type):

    def __new__(cls, name, bases, attrs):
        if name == 'Model':
            return type.__new__(cls, name, bases, attrs)
        table_name = attrs.get('__table__', None) or name
        primary_key = None
        mappings = dict()
        fields = []

        for k, v in attrs.items():
            if isinstance(v, Field):
                mappings[k] = v

                if v.primary_key:
                    if primary_key:
                        raise Exception('duplicate primary key %s' % k)
                    primary_key = k
                else:
                    fields.append(k)

        if not primary_key:
            raise Exception('primary key not found in %s' % name)

        for k in mappings.keys():
            if k in attrs:
                attrs.pop(k)

        attrs['__mappings__'] = mappings
        attrs['__table__'] = table_name
        attrs['__primary_key__'] = primary_key
        attrs['__fields__'] = fields
        attrs['__select__'] = 'select %s,%s from %s' % (
            primary_key, ','.join(fields), table_name)
        attrs['__update__'] = 'update %s set %s where %s=?' % (
            table_name, ','.join(map(lambda n: '%s=?' % n, fields)),
            primary_key)
        attrs['__insert__'] = 'insert into %s(%s,%s)values(%s)' % (
            table_name, ','.join(fields), primary_key, ('?,'*(len(fields)+1))[0:-1])
        attrs['__delete__'] = 'delete from %s where %s=?' % (
            table_name, primary_key)
        attrs['__truncate__'] = 'delete from %s' % table_name
        return type.__new__(cls, name, bases, attrs)


class Model(dict, metaclass=ModelMetaclass):
    def __init__(self, **kw):
        super(Model, self).__init__(**kw)


    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError as e:
            raise AttributeError('Model has no attribute %s ' % key)

    def __setattr__(self, key, val):
        self[key] = val

    def getValue(self, key):
        return getattr(self, key, None)

    def getValueOrDefault(self, key):
        v = self.getValue(key)
        if v is None:
            field = self.__mappings__[key]
            if field.default is not None:
                v= field.default() if callable(field.default) else field.default
                logging.info('%s setting default value' % key)
                setattr(self, key, v)
        return v


    @classmethod
    @asyncio.coroutine
    def findall(cls, where=None, args=None, **kw):
        sql = [cls.__select__]
        if where:
            sql.append('where')
            sql.append(where)

        orderby = kw.get('orderby', None)
        if orderby:
            sql.append('order by %s' % orderby)

        if args is None:
            args = []

        rs = yield from select(' '.join(sql), args)
        if rs is None:
            return rs
        rs_dict = []
        for r in rs:
            d = dict()
            d[cls.__primary_key__] = r[0]
            for k, v in zip(cls.__fields__, r[1:]):
                d[k] = v
            rs_dict.append(d)

        return [cls(**r) for r in rs_dict]


    @classmethod
    @asyncio.coroutine
    def find(cls, pk):
        '''
        find by primary key
        '''
        sql = [cls.__select__]
        sql.append("where %s='%s'" % (cls.__primary_key__, pk))
        rs = yield from select(' '.join(sql))
        if len(rs) == 0:
            return None
        d = dict()
        r = rs[0]
        d[cls.__primary_key__] = r[0]
        for k, v in zip(cls.__fields__, r[1:]):
            d[k] = v
        return cls(**d)


    @asyncio.coroutine
    def save(self):
        args = list(map(self.getValueOrDefault, self.__fields__))
        args.append(self.getValueOrDefault(self.__primary_key__))
        rows = yield from execute(self.__insert__, args)
        if rows != 1:
            logging.warning("failure to save data. affected:%s" % rows)
        return rows


    @asyncio.coroutine
    def update(self):
        args = list(map(self.getValue, self.__fields__))
        args.append(self.getValueOrDefault(self.__primary_key__))
        rows = yield from execute(self.__update__, args)
        if rows != 1:
            logging.warning('failure to update data. affected:%s' % rows)
        return rows


    @asyncio.coroutine
    def remove(self):
        args = [self.getValue(self.__primary_key__)]
        rows = yield from execute(self.__delete__, args)
        if rows != 1:
            logging.warning('failure to delete.affected:%s' % rows)
        return rows


    @classmethod
    @asyncio.coroutine
    def truncate(self):
        yield from execute(self.__truncate__)
