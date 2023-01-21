from time import sleep
import logging
#logging.basicConfig(level=logging.DEBUG)

from monk import Monk
from monk_plugins.linux.callbacks import OnProcessScheduled, OnProcessExecute 

target = None  # Global var for Monk object
_shutdown_flag = False

# Turn this into a helper function somehow... wrap signal in a class w/ convenience methods?
def wait_for_signal():
    global signal

    while not signal:
        sleep(1)

    signal = False

proc_name = None
def cb_save_procname():
    global proc_name
    next_thread = target.get_reg('r2')
    proc_name = forensics.linux.get_proc_name(thread=next_thread)
    print(f"cb_save_procname: {proc_name}, {hex(target.get_reg('pc'))}")

signal = False
def cb_on_exec():
    global signal
    print(f"on_exec: pc = {hex(target.get_reg('pc'))}, proc_name = {proc_name}")
    control.stop()
    signal = True

def test_proc_tracing():
    h1 = OnProcessScheduled(target, callback=cb_save_procname)
    h2 = OnProcessExecute(target, 'sh', callback=cb_on_exec)

    target.run()
    wait_for_signal()

    print("Finished waiting for signal")

    f = open('trace.txt', 'w+')

    while proc_name == 'sh':
        f.write(f"{hex(target.get_reg('pc'))}\n")
        f.flush()  # In case we ctrl+c, contents will still be written out
        control.step()

    control.shutdown()

if __name__ == '__main__':
    target = Monk('localhost', 1234, symbols='/home/dizzyspiral/repos/monk/test/resources/arm-versatilepb-linux-5.10.7.json')
    test_proc_tracing()
