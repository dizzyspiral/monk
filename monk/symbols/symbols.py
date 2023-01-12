class Symbols():
    def __init__(self, symbols_file, backend):
        _dwarf2json = Dwarf2JsonLoader(symbols_file)
        self.structs = Structs(_dwarf2json, backend)
        self.types = _dwarf2json.get_types()
