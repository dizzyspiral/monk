import importlib

_backend = None

def init(backend):
    global _backend
    _backend = importlib.import_module('backends.%s' % backend)
    _backend.initialize()

def read_uint8(addr):
    return _backend.read_uint8(addr)

def read_uint16(addr):
    return _backend.read_uint16(addr)

def read_uint32(addr):
    return _backend.read_uint32(addr)

def read_uint64(addr):
    return _backend.read_uint64(addr)

def get_reg(regname):
    return _backend.get_reg(regname)
