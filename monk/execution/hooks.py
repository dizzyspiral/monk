import logging
import threading

from monk.forensics.linux import get_user_regs, get_kernel_regs, get_proc_name
from monk.memory.memreader import get_reg
from monk.execution.control import break_on_execute, remove_callback, MonkControlError
from monk.symbols.structs import ThreadInfo
from monk.symbols.lookup import lookup
from monk.symbols.uregs.arm import *

#UREGS_SP = None  # TODO: fix this to be the right number.
#UREGS_PC = None


class MonkHookError(Exception):
    pass


class MonkCallbackError(Exception):
    pass


class Callback:
    def __init__(self, callback=None):
        """
        Create a new callback.

        :param function cb_func: callback function
        :param dict bind: dictionary of bound values
        """
        # Hooks can be installed/uninstalled by any thread. It's conceivable that they'll be
        # manipulated both by the main thread and callback threads. So, we provide a lock.
        # This lock _should not_ be used by the subclasses, in order to ensure that nobody
        # does anything stupid - i.e. none of the locked operations depend on something
        # happening in a particular thread other than the current one.
        self._hook_lock = threading.Lock()
        self._hooks = []

        if callback:
            self.run = callback

    def add_hook(self, symbol, cb):
        self._hook_lock.acquire()
        h = _on_execute(symbol, cb)
        self._hooks.append(h)
        self._hook_lock.release()

        return h  # So that hooks can be tracked and later removed individually

    def remove_hook(self, hook):
        self._hook_lock.acquire()
        
        try:
            remove_callback(hook)
        except MonkControlError as e:
            raise MonkCallbackError("Unable to remove hook, hook did not exist") from e

        try:
            self._hooks.remove(hook)
        except ValueError:
            pass  # hook wasn't in list, probably not a big deal if removing it from the system succeeded

        self._hook_lock.release()

    def run(self):
        """
        Run the callback. This function is overriden in the constructor by the
        user-defined cb_func, or defined by a subclass
        """
        raise MonkCallbackError("Callback not initialized")

    def install(self):
        """
        Install the callback. This function is defined by the subclass, often hooking execution
        of a particular address or symbol. That hook may not directly call run(), though it is
        expected that run() will eventually be called when the event of interest occurs, in order
        to invoke the user-defined callback for the event.
        """
        raise MonkCallbackError("Callback install() not initialized")

    def uninstall(self):
        for hook in self._hooks:
            self.remove_hook(hook)

        self._hook_lock.acquire()
        self._hooks = []
        self._hook_lock.release()


class OnExecute(Callback):
    def __init__(self, symbol, callback=None):
        super().__init__(callback)
        self._symbol = symbol
        self.install()

    def install(self):
        self.add_hook(self._symbol, self.run)


class OnProcessScheduled(Callback):
    def __init__(self, proc_name=None, callback=None):
        super().__init__(callback)
        self._proc_name = proc_name
        self.install()

    def install(self):
        self.add_hook("__switch_to", self._on_switch_to)

    def _on_switch_to(self):
        print("_on_switch_to")
        if not self._proc_name:
            self.run()
        else:
            next_thread = get_reg('r2')

            if get_proc_name(next_thread) == self._proc_name:
                self.run()


class OnProcessExecute(Callback):
    def __init__(self, proc_name, callback=None):
        super().__init__(callback)
        self._proc_name = proc_name
        self.install()

    def _on_switch_to(self):
        next_thread = get_reg('r2')

        if get_proc_name(next_thread) == self._proc_name:
            t = ThreadInfo(next_thread)
            
            # addr_limit is the highest userspace address a process can access; if it's 0,
            # then this is a kernel process. If not, then it's a userspace process.
            if t.addr_limit > 0x0:
                saved_pc = get_user_regs(sp=t.cpu_context.sp)[UREGS_PC]
                self._cb_proc_exec = self.add_hook(saved_pc, self._on_proc_exec)
            else:
                saved_regs = get_kernel_regs()
                self._cb_proc_exec = self.add_hook(saved_regs.pc, self._on_proc_exec)

    def _on_proc_exec(self):
        self.remove_hook(self._cb_proc_exec)
        self.run()

    def install(self):
        self._cb_switch_to = self.add_hook("__switch_to", self._on_switch_to)


def _on_execute(symbol, callback):
    logging.getLogger(__name__).debug("on_execute")
    if isinstance(symbol, str):
        logging.getLogger(__name__).debug("looking up symbol '%s'" % symbol)
        addr = lookup(symbol)

        if not addr:
            raise MonkHookError("Unable to set hook for symbol '%s', cannot resolve address" % symbol)
    else:
        logging.getLogger(__name__).debug("setting hook for address %d" % symbol)
        addr = symbol

    logging.getLogger(__name__).debug("Adding callback")
    bp = break_on_execute(addr, callback)

    return bp
