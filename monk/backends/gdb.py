import gdb
import re

# TODO: Needs to be refactored into a class


def initialize():
    pass

def read_uint8(addr):
    return _exec_read_uint_cmd("x/1xb 0x%x" % addr)

def read_uint16(addr):
    return _exec_read_uint_cmd("x/1xh 0x%x" % addr)

def read_uint32(addr):
    return _exec_read_uint_cmd("x/1xw 0x%x" % addr)

def read_uint64(addr):
    return _exec_read_uint_cmd("x/1xg 0x%x" % addr)

def get_reg(regname):
    try:
        # Read the register, and convert the returned gdb.Value to an int
        reg = int(gdb.selected_frame().read_register(regname))
    except:
        print("Unable to find regname '%s' in GDB symbol table for current frame" % regname)
        reg = None

    return _sanitize_int(reg, types['int'] * 8)

def write_uint8(addr, val):
    _exec_write_uint_cmd("set {char}0x%x = 0x%x" % (addr, val))

def write_uint16(addr, val):
    _exec_write_uint_cmd("set {short}0x%x = 0x%x" % (addr, val))

def write_uint32(addr, val):
    _exec_write_uint_cmd("set {int}0x%x = 0x%x" % (addr, val))

def write_uint64(addr, val):
    _exec_write_uint_cmd("set {long}0x%x = 0x%x" % (addr, val))

def write_reg(regname, val):
    try:
        # Read the register, and convert the returned gdb.Value to an int
        reg = int(gdb.selected_frame().read_register(regname))
    except:
        print("Unable to find regname '%s' in GDB symbol table for current frame")
        reg = None

    return _sanitize_int(reg, types['int'] * 8)

def _exec_read_uint_cmd(cmd):
    result = gdb.execute(cmd, to_string=True)
    mem = re.findall("0x[abcdef0123456789]+", result)
    # TODO: Error checking that mem[1] actually exists. GDB could have failed to read mem at the address.
    return int(mem[1], 16)

def _exec_write_uint_cmd(cmd):
    result = gdb.execute(cmd, to_string=True)

def _sanitize_int(val, nbits):
    # Python ints are arbitrarily large, so we'll get negative hex values 
    # sometimes from reading memory. Subsequent functions don't know what
    # to do with negative hex values. So we sanitize them into the correct 
    # bit width 2's complement representation.
    return int(hex((val + (1 << nbits)) % (1 << nbits)), 16)

def _sanitize_int(val, nbits):
    # Python ints are arbitrarily large, so we'll get negative hex values 
    # sometimes from reading memory. Subsequent functions don't know what
    # to do with negative hex values. So we sanitize them into the correct 
    # bit width 2's complement representation.
    return int(hex((val + (1 << nbits)) % (1 << nbits)), 16)
