import monk.backends.rsp as rsp
# need to address this later, can't import gdb backend because it depends on GDBPython, 
# which only exists in a running GDB session context.
#import monk.backends.gdb as gdb

# All available backends must be listed here so that Monk can accept them as strings in its
# constructor and map those strings to the correct backend constructor
backend_map = {
    'rsp': rsp.Rsp
    # 'gdb': gdb.Gdb
}
