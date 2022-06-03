import sys

# Import everything that we want the user to be able to get at from the GDB cmdl

# Allows all subsequent modules to import relative modules
sys.path.append(os.path.expanduser(os.path.dirname(__file__)))

import monk
monk.init("%s%sconfig_gdb.json" % (os.path.expanduser(os.getcwd()), os.sep))
import monk.commands.linux

if __name__ == '__main__':
#    events.core.begin_core_hooks() # Sets up hooks for tracking VM state
    pass
