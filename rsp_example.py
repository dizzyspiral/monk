import os
import time
from time import sleep
import logging
#logging.basicConfig(level=logging.DEBUG)

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

def test_on_proc_exec():
    h = hooks.OnProcessExecute('kthreadd', cb_print_proc_name)
    control.run()

    while count < 5:
        time.sleep(5)

    h.uninstall()
    control.shutdown()

def cb_print_mm():
    global count
    count += 1
    tasks = forensics.linux.get_task_list()

    for task in tasks:
        print(f"task name: {as_string(task.comm)}")
        print(f"task.mm = {hex(task.mm)}")

def cb_print_task():
    global count
    count += 1
    
    t = forensics.linux.get_task()
    print(TaskStruct(t))

def cb_print_stuff():
    global count
    count += 1

# This works for showing that a userspace process has a saved PC at a userspace address
#    t = ThreadInfo(memreader.get_reg('r2'))
#    print(t.cpu_context)
#    user_regs = forensics.linux.get_user_regs(sp=t.cpu_context.sp)
#    print(f"uregs_pc = {hex(user_regs[UREGS_PC])}")

#    print(t)
#    print(TaskStruct(t.task))

    tasks = forensics.linux.get_task_list()

    for task in tasks:
        thread = ThreadInfo(forensics.linux.get_thread(sp=task.stack))
        print(f"name: {as_string(task.comm)}")
        print(f"addr_limit: {hex(thread.addr_limit)}")
        print(f"uregs[pc]: {hex(forensics.linux.get_user_regs(sp=thread.cpu_context.sp)[UREGS_PC])}")
#        print(f"cpu_context.pc: {hex(thread.cpu_context.pc)}")
        print()
    
#    task = TaskStruct(forensics.linux.get_task())
#    print(as_string(task.comm))
#    sp = task.stack
#    t = ThreadInfo(forensics.linux.get_thread(sp=sp))
#    print(t)
#    print(as_string(TaskStruct(t.task).comm))

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

def test_on_proc_exec():
    h1 = hooks.OnProcessScheduled(callback=cb_save_procname)
    h2 = hooks.OnProcessExecute('sh', callback=cb_on_exec)

    control.run()

    while count < 1:
        time.sleep(1)

    control.shutdown()

def run_vm():
    control.run()

    while True:
        sleep(1)

    control.shutdown()

# Turn this into a helper function somehow... wrap signal in a class w/ convenience methods?
def wait_for_signal():
    global signal

    while not signal:
        sleep(1)

    signal = False

def test_proc_tracing():
    h1 = hooks.OnProcessScheduled(callback=cb_save_procname)
    h2 = hooks.OnProcessExecute('sh', callback=cb_on_exec)

    print("_on_switch_to: %s" % hex(lookup("__switch_to")))

    control.run()
    wait_for_signal()

    print("Finished waiting for signal")

    f = open('trace.txt', 'w+')

    while proc_name == 'sh':
        f.write(f"{hex(memreader.get_reg('pc'))}\n")
        f.flush()  # In case we ctrl+c, contents will still be written out
        control.step()

    control.shutdown()

def test_step():
    print("running...")
    control.run()
    print("stopping...")
    control.stop()
    print("stepping...")
    control.step()
#    print("stopping...")
#    control.stop()
    print("getting pc...")
    print(f"{hex(memreader.get_reg('pc'))}")
    print("stopping...")
    control.shutdown()

if __name__ == '__main__':
    test_proc_tracing()
#    run_vm()
#    test_step()
