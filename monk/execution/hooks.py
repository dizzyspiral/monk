import logging

from monk.forensics.linux import get_user_regs, get_proc_name
from monk.memory.memreader import get_reg
from monk.execution.control import break_on_execute, remove_callback
from monk.symbols.lookup import lookup
from monk.symbols.uregs.arm import *

#UREGS_SP = None  # TODO: fix this to be the right number.
#UREGS_PC = None


class GdbeastHookError(Exception):
    pass


def on_process_execute(proc_name, callback):

    def _on_switch_cb():

        # There's gotta be a better way to make callable objects with bound vars on the fly...
        def _on_proc_exec_wrapper():
            callback()
            remove_callback(bp)    

        next_thread = get_reg('r2')

        if get_proc_name(thread=next_thread) == proc_name:
            # Dunno if getting the kregs is necessary, or if we're already running in the 
            # correct kernel thread context by the time __switch_to executes
            kernel_regs = PtRegs(get_kernel_regs(thread=next_thread))
            user_regs = PtRegs(get_user_regs(sp=kregs.uregs[UREGS_SP]))
            bp = break_on_execute(user_regs.uregs[UREGS_PC], _on_proc_exec_wrapper)

    return on_execute("__switch_to", _on_switch_cb)

def on_execute(symbol, callback):
    logging.getLogger(__name__).debug("on_execute")
    if isinstance(symbol, str):
        logging.getLogger(__name__).debug("looking up symbol '%s'" % symbol)
        addr = lookup(symbol)

        if not addr:
            raise GdbeastHookError("Unable to set hook for symbol '%s', cannot resolve address" % symbol)
    else:
        logging.getLogger(__name__).debug("setting hook for address %d" % symbol)
        addr = symbol

    logging.getLogger(__name__).debug("Adding callback")
    bp = break_on_execute(addr, callback)
