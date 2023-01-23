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
        # Use the monk instance supplied. If not supplied, use the global instance.
        #if monk:
        #    self.monk = monk
        #else:
        #    self.monk = monk.g_monk

        # XXX Fix internal self.monk naming to be self.target, to match naming convention
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

    def _on_execute(self, symbol, callback):
        logging.getLogger(__name__).debug("on_execute")

        if isinstance(symbol, str):
            logging.getLogger(__name__).debug("looking up symbol '%s'" % symbol)
            addr = self.target.symbols.lookup(symbol)

            if not addr:
                raise MonkHookError("Unable to set hook for symbol '%s', cannot resolve address" % symbol)
        else:
            logging.getLogger(__name__).debug("setting hook for address %d" % symbol)
            addr = symbol

        logging.getLogger(__name__).debug("Adding callback")
        bp = self.target.on_execute(addr, callback)

        return bp
