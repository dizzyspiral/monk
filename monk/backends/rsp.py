import socket
import re
import xml.etree.ElementTree as ET
from queue import Queue
import threading
import selectors

from monk.backends.rsp_helpers.rsp_target import RspTarget, RspTargetError

_rsp_target = None  # After initialization, this is a GdbRsp object with a connection to the target

# === Public API ===

# Initialization

def initialize():
    global _rsp_target

    if not _rsp_target:
        _rsp_target = RspTarget('localhost', 1234)

def shutdown():
    _rsp_target.close()

# Reading memory

def get_reg(regname):
    return _rsp_target.read_register(regname)

def read_uint8(addr):
    return _rsp_target.read_memory(addr, 1)

def read_uint16(addr):
    return _rsp_target.read_memory(addr, 2)

def read_uint32(addr):
    return _rsp_target.read_memory(addr, 4)

def read_uint64(addr):
    return _rsp_target.read_memory(addr, 8)

# Writing memory

def write_reg(regname, val):
    _rsp_target.write_register(regname, val)

def write_uint8(addr, val):
    _rsp_target.write_memory(addr, val, 1)

def write_uint16(addr, val):
    _rsp_target.write_memory(addr, val, 2)

def write_uint32(addr, val_):
    _rsp_target.write_memory(addr, val, 4)

def write_uint64(addr, val):
    _rsp_target.write_memory(addr, val, 8)

# Target control

def run():
    _rsp_target.cmd_continue()

def stop():
    _rsp_target.cmd_stop()

def step():
    _rsp_target.cmd_step()

def set_read_breakpoint(addr):
    _rsp_target.set_read_watchpoint(addr)

def set_write_breakpoint(addr):
    _rsp_target.set_write_watchpoint(addr)

def set_access_breakpoint(addr):
    _rsp_target.set_access_watchpoint(addr)

def set_exec_breakpoint(addr):
    _rsp_target.set_sw_breakpoint(addr)
#    _rsp_target.set_hw_breakpoint(addr)

def del_read_breakpoint(addr):
    _rsp_target.remove_read_breakpoint(addr)

def del_write_breakpoint(addr):
    _rsp_target.remove_write_breakpoint(addr)

def del_access_breakpoint(addr):
    _rsp_target.remove_access_breakpoint(addr)

def del_exec_breakpoint(addr):
    try:
        _rsp_target.remove_sw_breakpoint(addr)
    except RspTargetError:
        # Sometimes the target returns an error even though it removed the breakpoint just fine. Ignore it.
        pass

# Stop events notification

def set_on_read_callback(callback):
    _rsp_target.on_read = callback

def set_on_write_callback(callback):
    _rsp_target.on_write = callback

def set_on_access_callback(callback):
    _rsp_target.on_access = callback

def set_on_execute_callback(callback):
    _rsp_target.on_execute = callback
