import monk.backends as backends
from monk.callback_manager import CallbackManager
from monk.symbols import Symbols

class Monk():
    def __init__(self, host='localhost', port=1234, symbols=None, backend='rsp'):
        """
        Creates a new Monk instance connected to the target specified by host and port.

        :param string host: the host of the target
        :param int port: the port the GDB stub is hosted on
        :param string symbols: the path to the symbols file generated by dwarf2json
        :param class backend: the backend to use (rsp or gdb)
        """
        # Should prob do some error checking that backend is actually a class, and if not,
        # search the "backends" directory for a module matching the supplied value
        self._backend = backends.backend_map[backend](host, port)
        self._callback_manager = CallbackManager(self._backend)
        self.symbols = Symbols(symbols, self._backend)
        self.structs = self.symbols.structs
        self.types = self.symbols.types

    # == Target status ==
    def is_running(self):
        return self._backend.target_is_running()

    # === Memory ===
    # Read
    def read_uint8(self, addr):
        return self._backend.read_uint8(addr)

    def read_uint16(self, addr):
        return self._backend.read_uint16(addr)

    def read_uint32(self, addr):
        return self._backend.read_uint32(addr)

    def read_uint64(self, addr):
        return self._backend.read_uint64(addr)

    def get_reg(self, regname):
        return self._backend.get_reg(regname)

    # Write
    def write_uint8(self, addr, val):
        self._backend.write_uint8(addr, val)

    def write_uint16(self, addr, val):
        self._backend.write_uint16(addr, val)

    def write_uint32(self, addr, val):
        self._backend.write_uint32(addr, val)

    def write_uint64(self, addr, val):
        self._backend.write_uint64(addr, val)

    def write_reg(self, regname, val):
        self._backend.write_reg(regname, val)

    # === Execution ===
    # Control
    def run(self):
        self._backend.run()

    def stop(self):
        self._backend.stop()

    def step(self):
        self._backend.step()

    def shutdown(self):
        self._backend.shutdown()

    # Hooks
    # This isn't really a user-facing API, but it can be used safely by a user if they
    # want to. callbacks.py defines the various callback classes, which have a nicer
    # user interface and can be subclassed to do complex tasks more cleanly.
    def on_execute(self, addr, callback):
        return self._callback_manager.on_execute(addr, callback)

    def on_read(self, addr, callback):
        return self._callback_manager.on_read(addr, callback)

    def on_write(self, addr, callback):
        return self._callback_manager.on_write(addr, callback)

    def on_access(self, addr, callback):
        return self._callback_manager.on_access(addr, callback)

    def remove_hook(self, callback):
        self._callback_manager.remove_callback(callback)

    # === Symbols ===
    # Convenience functions to access the symbols object attributes more directly
    def lookup(self, symbol):
        return self.symbols.lookup(symbol)
