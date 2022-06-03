import sys
import os
import json
import logging

import monk.symbols as symbols
import monk.memory as memory

# Allows all subsequent modules to import relative modules
sys.path.append(os.path.expanduser(os.path.dirname(__file__)))

def _config_requires(config, key):
    try:
        config[key]
    except:
        print("config.json missing '%s'" % key)
        exit()

def _validate_config(config):
    _config_requires(config, 'dwarf2json')
    _config_requires(config, 'backend')

def init(config_file):
#    logging.basicConfig(level=logging.DEBUG)  # TODO: Set this from json opts

    with open(config_file) as f:
        config = json.loads(f.read())

    _validate_config(config)

    symbols.structs.init(config['dwarf2json'])
    symbols.lookup.init(config['dwarf2json'])
    memory.memreader.init(config['backend'])
    memory.memwriter.init(config['backend'])

    if config['backend'] == 'gdb':
        import monk.commands as commands
    elif config['backend'] == 'rsp':
        import monk.execution as execution
        execution.control.init(config['backend'])
