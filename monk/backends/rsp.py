from monk.backends.rsp_helpers.rsp_target import RspTarget, RspTargetError

# This should be a subclass of an abstract class Backend, enforcing that all backends
# have the same API
class Rsp():
    def __init__(self, host, port):
        self._rsp_target = RspTarget(host, port)

    def shutdown(self):
        self._rsp_target.close()

    # Reading memory

    def get_reg(self, regname):
        return self._rsp_target.read_register(regname)

    def read_uint8(self, addr):
        return self._rsp_target.read_memory(addr, 1)

    def read_uint16(self, addr):
        return self._rsp_target.read_memory(addr, 2)

    def read_uint32(self, addr):
        return self._rsp_target.read_memory(addr, 4)

    def read_uint64(self, addr):
        return self._rsp_target.read_memory(addr, 8)

    # Writing memory

    def write_reg(self, regname, val):
        self._rsp_target.write_register(regname, val)

    def write_uint8(self, addr, val):
        self._rsp_target.write_memory(addr, val, 1)

    def write_uint16(self, addr, val):
        self._rsp_target.write_memory(addr, val, 2)

    def write_uint32(self, addr, val_):
        self._rsp_target.write_memory(addr, val, 4)

    def write_uint64(self, addr, val):
        self._rsp_target.write_memory(addr, val, 8)

    # Target control

    def run(self):
        self._rsp_target.cmd_continue()

    def stop(self):
        self._rsp_target.cmd_stop()

    def step(self):
        self._rsp_target.cmd_step()

    def set_read_breakpoint(self, addr):
        self._rsp_target.set_read_watchpoint(addr)

    def set_write_breakpoint(self, addr):
        self._rsp_target.set_write_watchpoint(addr)

    def set_access_breakpoint(self, addr):
        self._rsp_target.set_access_watchpoint(addr)

    def set_exec_breakpoint(self, addr):
        self._rsp_target.set_sw_breakpoint(addr)
    #    self._rsp_target.set_hw_breakpoint(addr)

    def del_read_breakpoint(self, addr):
        self._rsp_target.remove_read_breakpoint(addr)

    def del_write_breakpoint(self, addr):
        self._rsp_target.remove_write_breakpoint(addr)

    def del_access_breakpoint(self, addr):
        self._rsp_target.remove_access_breakpoint(addr)

    def del_exec_breakpoint(self, addr):
        try:
            self._rsp_target.remove_sw_breakpoint(addr)
        except RspTargetError:
            # Sometimes the target returns an error even though it removed the breakpoint just fine. Ignore it.
            pass

    # Stop events notification

    def set_on_read_callback(self, callback):
        self._rsp_target.on_read = callback

    def set_on_write_callback(self, callback):
        self._rsp_target.on_write = callback

    def set_on_access_callback(self, callback):
        self._rsp_target.on_access = callback

    def set_on_execute_callback(self, callback):
        self._rsp_target.on_execute = callback
