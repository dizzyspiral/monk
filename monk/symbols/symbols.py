from monk.symbols.dwarf2json_loader import Dwarf2JsonLoader
from monk.symbols.structs import Structs

class Symbols():
    def __init__(self, symbols_file, backend):
        if symbols_file:
            self._dwarf2json = Dwarf2JsonLoader(symbols_file)
            self.structs = Structs(self._dwarf2json, backend)
            self.types = self._dwarf2json.get_types()
        else:
            self.lookup = lambda x, y: None
            self.structs = None
            self.types = None

    def lookup(self, symbol):
        """
        Looks up symbol and returns its address, or None if an address isn't found

        :param str symbol: the symbol to resolve
        :rtype: int or None
        """

        addr = self._dwarf2json.find_symbol_address(symbol)

        return addr
