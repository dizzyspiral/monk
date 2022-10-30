import os
import time
import logging
#logging.basicConfig(level=logging.DEBUG)

import monk  # Import this first to initialize everything
monk.init("%s%sconfig.json" % (os.path.expanduser(os.getcwd()), os.sep))
import monk.memory.memreader as memreader
import monk.forensics as forensics
import monk.execution.control as control
import monk.execution.hooks as hooks
from monk.symbols.uregs.arm import *


_shutdown_flag = False


count = 0
def cb_print_next_proc():
    global count
    count += 1

    next_thread = memreader.get_reg('r2')
    print("current proc = %s" % forensics.linux.get_proc_name())
    next_name = forensics.linux.get_proc_name(next_thread)
    print("next proc = %s" % next_name)
    print()

def hello():
    print("Hello from callback")

def cb_print_proc_name():
    global count
    count += 1
    print(f"process = {forensics.linux.get_proc_name()}")

if __name__ == '__main__':
    h = hooks.OnProcessExecute('kthreadd', cb_print_proc_name)
    control.run()

    while count < 5:
        time.sleep(5)

    h.uninstall()
    control.shutdown()
