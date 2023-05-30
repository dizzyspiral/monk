import os
import time
from time import sleep
import logging

from monk_plugins.linux.callbacks import OnProcessScheduled, OnProcessExecute
from monk_plugins.linux.forensics import get_proc_name


class SaveProcNameOnSched(OnProcessScheduled):
    def __init__(self, target):
        self.cur_proc_name = None
        super().__init__(target)

    def run(self):
        self.cur_proc_name = get_proc_name(self.target, thread=self.target.get_reg('r2'))


class SignalOnProcExec(OnProcessExecute):
    def __init__(self, target, proc_name):
        self.signal = False
        super().__init__(target, proc_name)

    def run(self):
        self.target.stop()
        self.signal = True


def trace_process(target, proc_name):
    """
    Trace a process by name. Synchronous function - will block execution of the 
    caller. Must be called by main thread (because it controls execution)

    :param Monk target: the target to trace the process on
    :param string proc_name: the name of the process to trace
    """
    cb_proc_name = SaveProcNameOnSched(target)
    cb_signal_exec = SignalOnProcExec(target, proc_name)

    target.run()

    while not cb_signal_exec.signal:
        sleep(0.001)

    print("Finished waiting for signal")

    with open('trace.txt', 'w+') as f:
        while cb_proc_name.cur_proc_name == proc_name:
            f.write(f"{hex(target.get_reg('pc'))}\n")
            f.flush()  # In case we ctrl+c, contents will still be written out
            target.step()

    target.shutdown()
