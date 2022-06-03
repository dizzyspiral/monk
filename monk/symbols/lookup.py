from .dwarf2json_loader import Dwarf2JsonLoader

d2json = None

class GdbeastLookupError(Exception):
    pass

def init(vol_sym_file):
    global d2json

    d2json = Dwarf2JsonLoader(vol_sym_file)

def lookup(symbol):
    """
    Looks up symbol and returns it address, or None if an address isn't found

    :param str symbol: the symbol to resolve
    :rtype: int or None
    """

    addr = d2json.find_symbol_address(symbol)

    return addr
