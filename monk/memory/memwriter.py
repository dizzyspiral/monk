import importlib

_backend = None

def init(backend):
    global _backend
    _backend = importlib.import_module('backends.%s' % backend)
    _backend.initialize()

def write_uint8(addr, val):
    _backend.write_uint8(addr, val)

def write_uint16(addr, val):
    _backend.write_uint16(addr, val)

def write_uint32(addr, val):
    _backend.write_uint32(addr, val)

def write_uint64(addr, val):
    _backend.write_uint64(addr, val)

def write_reg(regname, val):
    _backend.write_reg(regname, val)
