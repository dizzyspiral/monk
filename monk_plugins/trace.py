import os
import time
from time import sleep
import logging

import monk  # Import this first to initialize everything
monk.init("%s%sconfig.json" % (os.path.expanduser(os.getcwd()), os.sep))
import monk.memory.memreader as memreader
import monk.forensics as forensics
import monk.execution.control as control
import monk.execution.hooks as hooks
from monk.symbols.uregs.arm import *
from monk.symbols.structs import *
from monk.utils.helpers import as_string
from monk.symbols.lookup import lookup


_shutdown_flag = False


proc_name = None
def cb_save_procname():
    global proc_name
    next_thread = memreader.get_reg('r2')
    proc_name = forensics.linux.get_proc_name(thread=next_thread)
    print(f"cb_save_procname: {proc_name}, {hex(memreader.get_reg('pc'))}")

signal = False
def cb_on_exec():
    global signal
    print(f"on_exec: pc = {hex(memreader.get_reg('pc'))}, proc_name = {proc_name}")
    control.stop()
    signal = True

# Turn this into a helper function somehow... wrap signal in a class w/ convenience methods?
def wait_for_signal():
    """
    Blocks waiting until the global signal flag is set. This flag is set by the 
    OnProcessExecute callback for the traced process.
    """
    global signal

    while not signal:
        sleep(1)

    signal = False

def trace_process(proc_name):
    """
    Trace a process by name. Synchronous function - will block execution of the 
    caller. Must be called by main thread (because it controls execution)

    :param string proc_name: the name of the process to trace
    """
    h1 = hooks.OnProcessScheduled(callback=cb_save_procname)
    h2 = hooks.OnProcessExecute(proc_name, callback=cb_on_exec)

    control.run()
    # Do we actually need to "wait for signal" or can we just block waiting for the process
    # name to change?
    wait_for_signal()

    print("Finished waiting for signal")

    f = open('trace.txt', 'w+')

    while proc_name == proc_name:
        f.write(f"{hex(memreader.get_reg('pc'))}\n")
        f.flush()  # In case we ctrl+c, contents will still be written out
        control.step()

    control.shutdown()

if __name__ == '__main__':
    trace_process('sh')
