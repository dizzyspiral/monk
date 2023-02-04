from monk.callback_manager import MonkControlError

import logging
import threading


class MonkHookError(Exception):
    pass


class MonkCallbackError(Exception):
    pass


class Callback:
    def __init__(self, target, callback=None):
        """
        Create a new callback.

        :param function callback: callback function
        :param Monk target: instance of monk
        """
        self.target = target

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
        h = self._on_execute(symbol, cb)
        self._hooks.append(h)
        self._hook_lock.release()

        return h  # So that hooks can be tracked and later removed individually

    def remove_hook(self, hook):
        self._hook_lock.acquire()
        
        try:
            self.target.remove_hook(hook)
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
        self.target.stop()

    def install(self):
        """
        Install the callback. This function is defined by the subclass, often hooking execution
        of a particular address or symbol. That hook may not directly call run(), though it is
        expected that run() will eventually be called when the event of interest occurs, in order
        to invoke the user-defined callback for the event.

        Note that this function does not have to be implemented, but by convention the subclass
        should implement install() to allow the user to install and uninstall the callback without
        re-creating the callback object.
        """
        raise MonkCallbackError("Callback install() not initialized")

    def uninstall(self):
        for hook in self._hooks:
            self.remove_hook(hook)

        self._hook_lock.acquire()
        self._hooks = []
        self._hook_lock.release()

    def _symbol_to_address(self, symbol):
        # If string, try looking up symbol (e.g. function name)
        if isinstance(symbol, str):
            addr = self.target.symbols.lookup(symbol)

            # If lookup failed, maybe it's a hex string
            if not addr:
                try:
                    addr = int(symbol, 16)
                except:
                    addr = None
        else:
            # If not string, try casting to int directly
            try:
                addr = int(symbol)
            except:
                addr = None

        return addr

    def _on_execute(self, symbol, callback):
        logging.getLogger(__name__).debug("on_execute")
        addr = self._symbol_to_address(symbol)

        if not symbol:
            raise MonkHookError("Unable to set hook for symbol '%s', cannot resolve address" % symbol)

        logging.getLogger(__name__).debug("Adding callback")
        bp = self.target.on_execute(addr, callback)

        return bp
