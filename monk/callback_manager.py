import importlib
from collections import defaultdict
import threading
import logging

EVENT_READ = "read"
EVENT_WRITE = "write"
EVENT_ACCESS = "access"
EVENT_EXECUTE = "execute"

class MonkControlError(Exception):
    pass

class CallbackManager():
    def __init__(self, backend):
        # Callback registries are dictionaries of addresses with associated lists of callbacks 
        # registered for that address
        self._on_read_callbacks = defaultdict(lambda: [])
        self._on_write_callbacks = defaultdict(lambda: [])
        self._on_access_callbacks = defaultdict(lambda: [])
        self._on_execute_callbacks = defaultdict(lambda: [])
        self._callback_registries = {
            EVENT_READ: self._on_read_callbacks,
            EVENT_WRITE: self._on_write_callbacks,
            EVENT_ACCESS: self._on_access_callbacks,
            EVENT_EXECUTE: self._on_execute_callbacks
        }

        # Tell the backend to call CallbackManager's dispatchers when breakpoints are hit
        self._backend = backend
        self._backend.set_on_read_callback(self._on_read_dispatcher)
        self._backend.set_on_write_callback(self._on_write_dispatcher)
        self._backend.set_on_access_callback(self._on_access_dispatcher)
        self._backend.set_on_execute_callback(self._on_execute_dispatcher)

    def on_read(self, addr, callback):
        return self._break_on_event(EVENT_READ, addr, callback)

    def on_write(self, addr, callback):
        return self._break_on_event(EVENT_WRITE, addr, callback)

    def on_access(self, addr, callback):
        return self._break_on_event(EVENT_ACCESS, addr, callback)

    def on_execute(self, addr, callback):
        return self._break_on_event(EVENT_EXECUTE, addr, callback)

    def remove_callback(self, cb):
        """
        Removes a previously set callback from the callback registry

        :param tuple cb: A tuple of (kind, addr, callback) representing the callback to remove.
        This is the same type of tuple returned by any of the break_on_* functions.
        """
        kind, addr, callback = cb
        logging.getLogger(__name__).debug("Removing callback '{}: {}'".format(kind, hex(addr)))
        fail = False

        try:
            cb_registry = self._callback_registries[kind]
        except KeyError:
            fail = True

        if fail:
            raise MonkControlError("callback kind '{}' not recognized".format(kind))

        try:
            cb_registry[addr].remove(callback)
        except ValueError:
            fail = True

        if fail:
            raise MonkControlError("no '{}' callback found for address '{}'".format(kind, hex(addr)))
       
        # If there are no more callbacks registered for this address, we need to remove the breakpoint
        if len(cb_registry[addr]) < 1:
            self._del_breakpoint(kind, addr)

    def _break_on_event(self, kind, addr, callback=None):
        """
        Sets a callback for an address, adding a breakpoint if one does not already exist.
        """
        # What happens when callback=None with the RSP backend? Presumably in this case, the target 
        # should just stop, instead of executing a callback...? The main thread has no good way to 
        # detect this. Maybe we can make the add hook code block until the target stops if no callback
        # is given?

        # XXX possible silent fail of global var write?
        logging.getLogger(__name__).debug("_break_on_event(%s, %s)" % (kind, hex(addr)))

        fail = False
        
        try:
            cb_registry = self._callback_registries[kind]
        except:
            fail = True

        # We raise outside of the try-except above so that we don't end up with "exception while
        # handling other exception" if this is uncaught by the caller. In practice, this should
        # never happen because it's an internal function and we're only ever calling it with a
        # "kind" that should be defined, but code changes, and assumptions don't always hold.
        if fail:
            raise MonkControlError("breakpoint kind '{}' not recognized".format(kind))

        cb_registry[addr].append(callback)

        # If this is the first callback added for this address, we need to add the breakpoint to the target
        if len(cb_registry[addr]) < 2:
            logging.getLogger(__name__).debug("Adding breakpoint")
            self._set_breakpoint(kind, addr)

        logging.getLogger(__name__).debug("_break_on_event() new callback registry kind:%s addr:%s = %s" % (kind, addr, cb_registry[addr]))

        return (kind, addr, callback)

    def _set_breakpoint(self, kind, addr):
        if kind == EVENT_READ:
            self._backend.set_read_breakpoint(addr)
        elif kind == EVENT_WRITE:
            self._backend.set_write_breakpoint(addr)
        elif kind == EVENT_ACCESS:
            self._backend.set_access_breakpoint(addr)
        elif kind == EVENT_EXECUTE:
            self._backend.set_exec_breakpoint(addr)
        else:
            raise MonkControlError("breakpoint kind '{}' not recognized".format(kind))

    def _del_breakpoint(self, kind, addr):
        if kind == EVENT_READ:
            self._backend.del_read_breakpoint(addr)
        elif kind == EVENT_WRITE:
            self._backend.del_write_breakpoint(addr)
        elif kind == EVENT_ACCESS:
            self._backend.del_access_breakpoint(addr)
        elif kind == EVENT_EXECUTE:
            self._backend.del_exec_breakpoint(addr)
        else:
            raise MonkControlError("breakpoint kind '{}' not recognized".format(kind))

    # Signal handlers hooked into the backend signals notification functions
    def _on_read_dispatcher(self, addr):
        self._callback_handler(self._on_read_callbacks[addr])

    def _on_write_dispatcher(self, addr):
        self._callback_handler(self._on_write_callbacks[addr])

    def _on_access_dispatcher(self, addr):
        self._callback_handler(self._on_access_callbacks[addr])

    def _on_execute_dispatcher(self, addr):
        logging.getLogger(__name__).debug("_on_execute_dispatcher(%s)" % hex(addr))
        self._callback_handler(self._on_execute_callbacks[addr])

    def _callback_handler(self, callbacks):
        logging.getLogger(__name__).debug("_callback_handler")
        logging.getLogger(__name__).debug(callbacks)
        for callback in callbacks:
            logging.getLogger(__name__).debug("invoking callback...")
            # We kick off another thread here because new threads do not have permission to call
            # target execution functions (run, stop, etc) and the callbacks must not execute the
            # target. It also gives us agency to terminate the callback if it's hung.
            t = threading.Thread(target=callback)
            t.start()
            t.join()

        logging.getLogger(__name__).debug("callbacks done.")

        # This is an implementation detail of the RSP backend... All sw breakpoints get cleared by the gdbstub
        # when the target stops. This makes it so that reading memory won't result in accidentally reading some
        # breakpoint opcodes instead of the actual memory at that address. However, we have to set the 
        # breakpoints that got cleared again before re-starting the target, otherwise they're just gone, and 
        # all of our hooks are broken.
        for addr in self._on_execute_callbacks.keys():
            if len(self._on_execute_callbacks[addr]) > 0:
                self._set_breakpoint(EVENT_EXECUTE, addr)
