"""Loader for dwarf2json
"""
import json

basic_types = ['pointer', 'base']
class_types = ['struct', 'union']
array_types = ['array']
other_types = ['enum']  # This list is't used so far

# Some types have built-in assumptions about what they map to for a base type in the C standard.
# They're mapped here.
equivalent_types = {'enum': 'int'}


class Dwarf2JsonError(Exception):
    """Error raised by Dwarf2JsonLoader for JSON element access errors
    """

# XXX The design of this module is fucked.


class Dwarf2JsonLoader:
    """Loads JSON produced by volatility's dwarf2json utility to provide target symbols

    Exposes methods for getting a target's symbols, types, and other information provided
    by the JSON file.
    """
    def __init__(self, jsonfile):
        self._json = self._load_json(jsonfile)

    def _load_json(self, jsonfile):
        """Load the JSON

        :param str jsonfile: the path to the JSON file
        :rtype: map
        :returns: the JSON loaded into a map
        """
        with open(jsonfile) as f:
            s = f.read()
            j = json.loads(s)

        return j

    def get_endian(self):
        """
        Get the endianness of memory
        """
        return self._json['base_types']['int']['endian']

    def get_addr_size(self):
        """Get the number of bytes in an address
        """
        return self._json['base_types']['pointer']['size']

    def get_types(self):
        """
        Get the names and sizes of all basic types
        """
        types = {}

        for name, attrs in self._json['base_types'].items():
            types[name] = attrs['size']

        return types

    def find_symbol_address(self, symbol):
        """Translate a symbol into its address

        :param str symbol: the symbol to translate
        :rtype: int or None
        :returns: the address, or None if translation failed
        """
        try:
            s = self._json['symbols'][symbol]
            s = s['address']
        except KeyError:
            s = None

        return s

    def get_defined_struct_names(self):
        """Get a list of all kernel struct names
        """
        ret = []

        for t, attributes in self._json['user_types'].items():
            if attributes['kind'] in class_types:
                ret.append(t)

        return ret

    def get_struct_offset(self, struct, elem):
        """Get the offset of an element within a struct

        :param str struct: the name of the struct
        :param str elem: the element to get the offset of
        :rtype: int or None
        :returns: the offset of the element within the struct, or None if the element 
        was not found
        """
        try:
            off = self._json['user_types'][struct]['fields'][elem]['offset']
        except (KeyError, TypeError):
            print(f"failed to get offset for {struct}.{elem}")
            off = None

        return off

    def get_struct_fields(self, struct):
        """Get a struct's fields

        :param str struct: the name of the struct
        :rtype: map
        :returns: the JSON map object for the struct's fields
        """
        return self._json['user_types'][struct]['fields']

    def get_base_type_size(self, base_type):
        """Get a base type's size

        :param str base_type: the name of the base type
        :raises Exception: if unable to find the base type
        :rtype: int
        :returns: the size of the base type
        """
        try:
            return self._json['base_types'][base_type]['size']
        except KeyError:
            # XXX We can probably make a reasonable guess that it's an int... but maybe
            # the caller should handle that.
            exp_str = f"Unable to get size for base type '{base_type}'"

        raise Dwarf2JsonError(exp_str)

    def get_field_offset(self, field_attributes):
        """Get the offset attribute from the field attributes

        :param map field_attributes: the JSON map object of field attributes
        :rtype: int
        :returns: the offset
        """
        return field_attributes['offset']

    def get_field_type(self, field_attributes):
        """Get the field type from the field attributes

        :param map field_attributes: the field attributes
        :rtype: str
        :returns: the name of the field's type
        """
        return field_attributes['type']['kind']

    def get_struct_name(self, field_attributes):
        """Get the struct name out of the field attributes

        :param map field_attributes: the field attributes
        :rtype: str
        :returns: the name of the struct
        """
        return field_attributes['type']['name']

    def get_array_type(self, field_attributes):
        """Get an array's type from its field attributes

        :param map field_attributes: the field attributes
        :rtype: str
        :returns: the array type
        """
        k = field_attributes['type']['subtype']['kind']

        try:
            t = field_attributes['type']['subtype']['name']
        except KeyError:
            # If the array is an array of pointers to structs, then there are two subtypes, and the
            # first nested subtype doesn't have a name. It does however have a kind, and that kind
            # is (hopefully, probably, maybe?) pointer.
            t = field_attributes['type']['subtype']['kind']

        # If k is a struct, union, or (heaven forbid) an array, we assume this is an array of
        # pointers. I'm really not sure if there are ever in-place list-of-lists in the kernel.
        # If there are, this assumption will break for them. Same if there are in-place lists
        # of structs.
        # TODO: On the whole, we really should create a better mechaism for resolving sizes.
        if k not in basic_types:
            t = 'pointer'

        return t

    def get_array_count(self, field_attributes):
        """Get the count attribute for an array

        :param map field_attributes: the field attributes
        :rtype: int
        :returns: the count
        """
        return field_attributes['type']['count']

    def get_bitfield_info(self, field_attributes):
        """Get a bitfield's base type, bit position, and bit length

        :param map field_attributes: the bitfield's field attributes
        :rtype: tuple
        :returns: the base type, bit position, and bit length
        """
        field_type = field_attributes['type']['type']['kind']
        base_type = field_attributes['type']['type']['name']

        # If our base type is actually not a base type, we map it to a base type. E.g. I've
        # seen bitfields with a type of enum, which is really an int.
        if field_type not in basic_types:
            base_type = equivalent_types[field_type]

        bit_position = field_attributes['type']['bit_position']
        bit_length = field_attributes['type']['bit_length']

        return base_type, bit_position, bit_length

    def get_base_type_name(self, field_attributes):
        """Get the base type name

        :param map field_attributes: the field attributes
        :rtype: str
        :returns: the base type name
        """
        t = self.get_field_type(field_attributes)

        if t not in ['pointer', 'base']:
            raise Dwarf2JsonError(f"Tried to get type name for kind '{t}', which is not"
                                 " 'pointer' or 'base'")           

        if t == 'base':
            t = field_attributes['type']['name']

        return t
