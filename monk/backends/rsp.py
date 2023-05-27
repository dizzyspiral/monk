""" RSP backend
"""
from monk.backends.rsp_helpers.rsp_target import RspTarget, RspTargetError

# This should be a subclass of an abstract class Backend, enforcing that all backends
# have the same API
class Rsp():
    """ Wrapper for all functionality of the RSP backend. Basically just exposes RspTarget
    with an API consistent with the other backends.
    """
    def __init__(self, host, port):
        self.connected = False
        self.connect(host, port)

    # Expose the underlying target's endianness. RspTarget has to do the endian translation,
    # because otherwise we're doing extra work (basically doing the conversion twice), and
    # we'd have to figure out the byte-wise length of an int after the fact, which is difficult
    # for things like registers which can sometimes be 32-bit and sometimes 64-bit. The size of
    # registers isn't defined by the symbols file, but rather by the XML that the RspTarget
    # receives from the remote target.
    @property
    def endian(self):
        """ Gets the endianess of the target
        """
        return self._rsp_target.endian

    @endian.setter
    def endian(self, val):
        """ Sets the endianess of the target. Note that this does not change the actual
        memory representation of the target, it only changes how memory is interpreted
        client-side (within Monk)

        :param str val: the endianness to set
        """
        if self._rsp_target:
            self._rsp_target.endian = val

    def connect(self, host, port):
        """ Connect to the target

        :param str host: the address of the target to connect to
        :param int port: the port number of the GDB server on the target
        """
        self._rsp_target = RspTarget(host, port)
        self.connected = True

    def shutdown(self):
        """ Shut down the connection to the target
        """
        self._rsp_target.close()
        self.connected = False

    def target_is_running(self):
        """ Get the target's running state

        :rtype: bool
        :returns: True if the target is running, False otherwise
        """
        return not self._rsp_target.target_is_stopped

    # Reading memory

    def get_reg(self, regname):
        """ Read a register's value

        :param str regname: the name of the register to read from
        """
        return self._rsp_target.read_register(regname)

    def read_uint8(self, addr):
        """ Read a uint8 from memory

        :param int addr: the address to read from
        """
        return self._rsp_target.read_memory(addr, 1)

    def read_uint16(self, addr):
        """ Read a uint16 from memory

        :param int addr: the address to read from
        """
        return self._rsp_target.read_memory(addr, 2)

    def read_uint32(self, addr):
        """ Read a uint32 from memory

        :param int addr: the address to read from
        """
        return self._rsp_target.read_memory(addr, 4)

    def read_uint64(self, addr):
        """ Read a uint64 from memory

        :param int addr: the address to read from
        """
        return self._rsp_target.read_memory(addr, 8)

    # Writing memory

    def write_reg(self, regname, val):
        """ Set a register's value
        
        :param str regname: the name of the register
        :param int val: the value to set the register to
        """
        self._rsp_target.write_register(regname, val)

    def write_uint8(self, addr, val):
        """ Write a uint8 to memory
        
        :param int addr: the address to write to
        :param int val: the value to write
        """

        self._rsp_target.write_memory(addr, val, 1)

    def write_uint16(self, addr, val):
        """ Write a uint16 to memory
        
        :param int addr: the address to write to
        :param int val: the value to write
        """
        self._rsp_target.write_memory(addr, val, 2)

    def write_uint32(self, addr, val):
        """ Write a uint32 to memory
        
        :param int addr: the address to write to
        :param int val: the value to write
        """
        self._rsp_target.write_memory(addr, val, 4)

    def write_uint64(self, addr, val):
        """ Write a uint64 to memory
        
        :param int addr: the address to write to
        :param int val: the value to write
        """
        self._rsp_target.write_memory(addr, val, 8)

    # Target control

    def run(self):
        """ Run the target
        """
        self._rsp_target.cmd_continue()

    def stop(self):
        """ Stop the target
        """
        self._rsp_target.cmd_stop()

    def step(self):
        """ Step the target
        """
        self._rsp_target.cmd_step()

    def set_read_breakpoint(self, addr):
        """ Set a read breakpoint

        :param int addr: the address to set the breakpoint at
        :raises NotImplementedError: because this functionality is not yet implemented
        """
        raise NotImplementedError("set_read_breakpoint is not yet implemented")
#        self._rsp_target.set_read_watchpoint(addr, sz)

    def set_write_breakpoint(self, addr):
        """ Set a write breakpoint

        :param int addr: the address to set the breakpoint at
        :raises NotImplementedError: because this functionality is not yet implemented
        """
        raise NotImplementedError("set_write_breakpoint is not yet implemented")
#        self._rsp_target.set_write_watchpoint(addr, sz)

    def set_access_breakpoint(self, addr):
        """ Set an access breakpoint

        :param int addr: the address to set the breakpoint at
        :raises NotImplementedError: because this functionality is not yet implemented
        """
        raise NotImplementedError("set_access_breakpoint is not yet implemented")
#        self._rsp_target.set_access_watchpoint(addr, sz)

    def set_exec_breakpoint(self, addr):
        """ Set an execution breakpoint

        :param int addr: the address to set the breakpoint at
        """
        self._rsp_target.set_sw_breakpoint(addr)
    #    self._rsp_target.set_hw_breakpoint(addr)

    def del_read_breakpoint(self, addr):
        """ Delete a read breakpoint

        :param int addr: the address of the breakpoint
        :raises NotImplementedError: because this functionality is not yet implemented
        """
        raise NotImplementedError("del_read_breakpoint is not yet implemented")
#        self._rsp_target.remove_read_watchpoint(addr, sz)

    def del_write_breakpoint(self, addr):
        """ Delete a write breakpoint

        :param int addr: the address of the breakpoint
        :raises NotImplementedError: because this functionality is not yet implemented
        """
        raise NotImplementedError("del_write_breakpoint is not yet implemented")
#        self._rsp_target.remove_write_watchpoint(addr, sz)

    def del_access_breakpoint(self, addr):
        """ Delete an access breakpoint

        :param int addr: the address of the breakpoint
        """
        raise NotImplementedError("del_access_breakpoint is not yet implemented")
#        self._rsp_target.remove_access_watchpoint(addr, sz)

    def del_exec_breakpoint(self, addr):
        """ Delete an execution breakpoint

        :param int addr: the address of the breakpoint
        """
        try:
            self._rsp_target.remove_sw_breakpoint(addr)
        except RspTargetError:
            # Sometimes the target returns an error even though it removed the
            # breakpoint just fine. Ignore it.
            pass

    # Stop events notification

    def set_on_read_callback(self, callback):
        """ Set what function gets called when an on-read event is detected
        by the target.

        :param function callback: the function to call when the event occurs
        """
        self._rsp_target.on_read = callback

    def set_on_write_callback(self, callback):
        """ Set what function gets called when an on-write event is detected
        by the target.

        :param function callback: the function to call when the event occurs
        """
        self._rsp_target.on_write = callback

    def set_on_access_callback(self, callback):
        """ Set what function gets called when an on-access event is detected
        by the target.

        :param function callback: the function to call when the event occurs
        """
        self._rsp_target.on_access = callback

    def set_on_execute_callback(self, callback):
        """ Set what function gets called when an on-execute event is detected
        by the target.

        :param function callback: the function to call when the event occurs
        """
        self._rsp_target.on_execute = callback
