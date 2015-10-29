# -*-coding: utf-8 -*-

import os
import config_defaults

# tools_dir = os.path.join(os.path.abspath(os.path.curdir), "tools")
grdisk_prog = os.path.join(os.path.curdir, "grdisk")
grgrant_prog = os.path.join(os.path.curdir, "grgrant")

class Dict(dict):
    '''
    custom dict support access x.y style
    '''
    def __init__(self, name=(), values=(), **kw):
        super(Dict, self).__init__(**kw)
        for k, v in zip(name, values):
            self[k] = v

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Dict' object has no attribute %s" % key)

    def __setattr__(self, key, val):
        self[key] = val


def merge(defaults, overrides):
    r = {}

    for k, v in defaults.items():
        if k in overrides:
            if isinstance(v, dict):
                r[k] = merge(v, overrides[k])
            else:
                r[k] = overrides[k]
        else:
            r[k] = v
    return r


def toDict(d):
    D = Dict()

    for k, v in d.items():
        D[k] = toDict(v) if isinstance(v, dict) else v

    return D


configs = config_defaults.configs
try:
    import config_override
    configs = merge(configs, config_override.configs)
except ImportError:
    pass

configs = toDict(configs)
