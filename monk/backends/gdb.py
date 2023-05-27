""" GDB Python backend
"""
import re
import gdb  # pylint:disable=import-error


# pylint: disable=consider-using-f-string
class Gdb():
    """ Wrapper for all functionality of the GDB backend. Exposes GDBPython methods
    in an API consistent with other backends (as much as possible).
    """
    # pylint:disable=unused-argument
    def __init__(self, host=None, port=None):
        # No initialization is really necessary - if we're using the GDB backend,
        # we're running inside of GDB via GDBPython.
        self.connected = True

    @property
    def endian(self):
        """ Get the endianess of the target
        """
        # TODO: fix to actually get the endianess
        return 'little'

    @endian.setter
    def endian(self, val):
        """ Sets the endianess of the target.
        """
        # TODO: Implement

    def connect(self, host=None, port=None):
        """ Connect to the target. Dummy function, GDB backend is always connected
        when in use.

        :param str host: not used
        :param int port: not used
        """
        # Unnecessary, the GDB backend is always already connected

    def shutdown(self):
        """ Shutdown the connection to the target. Dummy function, GDB backend cannot
        be shut down.
        """

    def target_is_running(self):
        """ Get the target's running state

        :rtype: bool
        :returns: True if the target is running, False otherwise
        :raises NotImplementedError: because this function is not yet implemented
        """
        raise NotImplementedError("GDB backend target_is_running is not implemented yet")

    def get_reg(self, regname):
        """ Read a register's value

        :param str regname: the name of the register to read from
        """
        try:
            # Read the register, and convert the returned gdb.Value to an int
            reg = int(gdb.selected_frame().read_register(regname))
        except:  # pylint:disable=bare-except
            print("Unable to find regname '%s' in GDB symbol table for current frame" % regname)
            reg = None

        # TODO: Get the size of the register from GDB
        return _sanitize_int(reg, 4 * 8)

    def read_uint8(self, addr):
        """ Read a uint8 from memory

        :param int addr: the address to read from
        """
        return _exec_read_uint_cmd("x/1xb 0x%x" % addr)

    def read_uint16(self, addr):
        """ Read a uint16 from memory

        :param int addr: the address to read from
        """
        return _exec_read_uint_cmd("x/1xh 0x%x" % addr)

    def read_uint32(self, addr):
        """ Read a uint32 from memory

        :param int addr: the address to read from
        """
        return _exec_read_uint_cmd("x/1xw 0x%x" % addr)

    def read_uint64(self, addr):
        """ Read a uint64 from memory

        :param int addr: the address to read from
        """
        return _exec_read_uint_cmd("x/1xg 0x%x" % addr)

    def write_reg(self, regname, val):
        """ Set a register's value

        :param str regname: the name of the register
        :param int val: the value to set the register to
        :raises NotImplementedError: because this function is not implemented yet
        """
        raise NotImplementedError("write_reg is not implemented yet")

    def write_uint8(self, addr, val):
        """ Write a uint8 to memory

        :param int addr: the address to write to
        :paranm int val: the value to write
        """
        _exec_write_uint_cmd("set {char}0x%x = 0x%x" % (addr, val))

    def write_uint16(self, addr, val):
        """ Write a uint16 to memory

        :param int addr: the address to write to
        :paranm int val: the value to write
        """
        _exec_write_uint_cmd("set {short}0x%x = 0x%x" % (addr, val))

    def write_uint32(self, addr, val):
        """ Write a uint32 to memory

        :param int addr: the address to write to
        :paranm int val: the value to write
        """
        _exec_write_uint_cmd("set {int}0x%x = 0x%x" % (addr, val))

    def write_uint64(self, addr, val):
        """ Write a uint64 to memory

        :param int addr: the address to write to
        :paranm int val: the value to write
        """
        _exec_write_uint_cmd("set {long}0x%x = 0x%x" % (addr, val))

    def run(self):
        """ Run the target

        :raises NotImplementedError: because it's not yet implemented
        """
        raise NotImplementedError("run() is not yet implemented for the GDB backend")

    def stop(self):
        """ Stop the target

        :raises NotImplementedError: because it's not yet implemented
        """
        raise NotImplementedError("run() is not yet implemented for the GDB backend")

    def step(self):
        """ Step the target

        :raises NotImplementedError: because it's not yet implemented
        """
        raise NotImplementedError("run() is not yet implemented for the GDB backend")

    def set_read_breakpoint(self):
        """ Set a read breakpoint

        :param int addr: the address to se the breakpoint at
        :raises NotImplementedError: because this functionality is not yet implemented
        """
        raise NotImplementedError("set_read_breakpoint is not yet implemented")

    def set_write_breakpoint(self):
        """ Set a write breakpoint

        :param int addr: the address to set the breakpoint at
        :raises NotImplementedError: because this functionality is not yet implemented
        """
        raise NotImplementedError("set_write_breakpoint is not yet implemented")

    def set_access_breakpoint(self):
        """ Set an access breakpoint

        :param int addr: the address to set the breakpoint at
        :raises NotImplementedError: because this functionality is not yet implemented
        """
        raise NotImplementedError("set_access_breakpoint is not yet implemented")

    def set_exec_breakpoint(self):
        """ Set an execution breakpoint

        :param int addr: the address to seit the breakpoint at
        :raises NotImplementedError: because this functionality is not yet implemented
        """
        raise NotImplementedError("set_exec_breakpoint is not yet implemented")

    def del_read_breakpoint(self, addr):
        """ Delete a read breakpoint

        :param int addr: the address of the breakpoint
        :raises NotImplementedError: because this functionality is not yet implemented
        """
        raise NotImplementedError("del_read_breakpoint is not yet implemented")

    def del_write_breakpoint(self, addr):
        """ Delete a write breakpoint

        :param int addr: the address of the breakpoint
        :raises NotImplementedError: because this functionality is not yet implemented
        """
        raise NotImplementedError("del_write_breakpoint is not yet implemented")

    def del_access_breakpoint(self, addr):
        """ Delete an access breakpoint

        :param int addr: the address of the breakpoint
        :raises NotImplementedError: because this functionality is not yet implemented
        """
        raise NotImplementedError("del_access_breakpoint is not yet implemented")

    def del_exec_breakpoint(self, addr):
        """ Delete an execution breakpoint

        :param int addr: the address of the breakpoint
        :raises NotImplementedError: because this functionality is not yet implemented
        """
        raise NotImplementedError("del_exec_breakpoint is not yet implemented")


def _exec_read_uint_cmd(cmd):
    result = gdb.execute(cmd, to_string=True)
    mem = re.findall("0x[abcdef0123456789]+", result)
    # TODO: Error checking that mem[1] actually exists. GDB could have failed to read
    # mem at the address.
    return int(mem[1], 16)

def _exec_write_uint_cmd(cmd):
    # TODO: Check for success?
    gdb.execute(cmd, to_string=True)

def _sanitize_int(val, nbits):
    # Python ints are arbitrarily large, so we'll get negative hex values
    # sometimes from reading memory. Subsequent functions don't know what
    # to do with negative hex values. So we sanitize them into the correct
    # bit width 2's complement representation.
    return int(hex((val + (1 << nbits)) % (1 << nbits)), 16)
