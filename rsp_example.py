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


_shutdown_flag = False


def do_stuff():
    control.run()
    time.sleep(1)
    control.stop()
    print(memreader.get_reg('r0'))
    print(forensics.linux.get_proc_name())

def cb_hello():
    global _shutdown_flag
    print("Hello from callback")
    _shutdown_flag = True

count = 0
def cb_print_next_proc():
    global count
    count += 1

    next_thread = memreader.get_reg('r2')
    print("current proc = %s" % forensics.linux.get_proc_name())
    next_name = forensics.linux.get_proc_name(next_thread)
    print("next proc = %s" % next_name)
    print()

def do_basic_hook():
    control.stop()
    hooks.on_execute("__switch_to", cb_hello)
    control.run()

    while not _shutdown_flag:
        time.sleep(1)

    control.shutdown()

def do_switch_to_hook():
    global count
    control.stop()
    hooks.on_execute("__switch_to", cb_print_next_proc)
    control.run()

    while count < 3:
        time.sleep(1)

    control.shutdown()

def do_task_walk():
    control.stop()
    forensics.linux.walk_tasks()
    control.run()
    control.shutdown()

if __name__ == '__main__':
    do_switch_to_hook()
