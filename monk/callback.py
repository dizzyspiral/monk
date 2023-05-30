"""Callback class and associated exceptions

Exposes a callback class to either use directly, or subclass for custom callbacks.
"""
import logging
import threading

from monk.callback_manager import MonkControlError


class MonkCallbackError(Exception):
    """Exception for errors raised by Callback"""
    #pass


class Callback:
    """Register a callback hook with the target

    Class for registering an execution callback with the target. It's designed to be
    subclassed to create more complex hooks. E.g. the OnExecute callback defined in
    monk_plugins is a more user-friendly way of creating an execution callback. This
    Callback class manages the lifecycle of the callback and provides safe methods for 
    adding and removing hooks, so that logic does not have to be duplicated throughout
    every subclassed callback.

    This class can also be used to simply register a breakpoint, with no associated
    callback function. If no callback is supplied, this class will stop the target's
    execution when the callback condition is met.
    """
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
        """
        Add a hook to the target

        :param string|int symbol: the symbol for which to register the hook. Can be a function
        name or address.
        :param function cb: the callback function to execute when the hook is triggered
        :rtype: tuple
        :returns: the hook
        """
        with self._hook_lock:
            h = self._on_execute(symbol, cb)
            self._hooks.append(h)

        return h  # So that hooks can be tracked and later removed individually

    def remove_hook(self, hook):
        """
        Remove a hook from the target

        :param tuple hook: the hook to remove
        :raises MonkControlError: if the hook did not exist in the target
        """
        with self._hook_lock:
            try:
                self.target.remove_hook(hook)
            except MonkControlError as e:
                raise MonkCallbackError("Unable to remove hook, hook did not exist") from e

            try:
                self._hooks.remove(hook)
            except ValueError:
                # hook wasn't in list, probably not a big deal if removing it from the system
                # succeeded
                pass

    # pylint:disable=method-hidden
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
        """
        Uninstall the callback.

        This removes all of the hooks added by add_hook.
        """
        for hook in self._hooks:
            self.remove_hook(hook)

        with self._hook_lock:
            self._hooks = []

    def _symbol_to_address(self, symbol):
        # If string, try looking up symbol (e.g. function name)
        if isinstance(symbol, str):
            addr = self.target.symbols.lookup(symbol)

            # If lookup failed, maybe it's a hex string
            if not addr:
                try:
                    addr = int(symbol, 16)
                except ValueError:
                    addr = None
        else:
            # If not string, try casting to int directly
            try:
                addr = int(symbol)
            except ValueError:
                addr = None

        return addr

    def _on_execute(self, symbol, callback):
        logging.getLogger(__name__).debug("on_execute")
        addr = self._symbol_to_address(symbol)

        if not symbol:
            raise MonkCallbackError(f"Unable to set hook for symbol '{symbol}',"
                                    f" cannot resolve address ({self.__class__})")

        logging.getLogger(__name__).debug("Adding callback")
        bp = self.target.on_execute(addr, callback)

        return bp
