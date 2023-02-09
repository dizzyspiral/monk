import os
import json

from .types import types

basic_types = ['pointer', 'base']
class_types = ['struct', 'union']
array_types = ['array']
other_types = ['enum']  # This list is't used so far, but it seemed prudent to catalog the uncategorized types

# Some types have built-in assumptions about what they map to for a base type in the C standard.
# They're mapped here.
equivalent_types = {'enum': 'int'}

# XXX The design of this module is fucked.


class Dwarf2JsonLoader:
    def __init__(self, jsonfile):
        self._json = self._load_json(jsonfile)

    def _load_json(self, jsonfile):
        with open(jsonfile) as f:
            s = f.read()
            j = json.loads(s)

        return j

    def get_endian(self):
        """
        Get the endianness of memory
        """
        return self._json['base_types']['int']['endian']

    def get_types(self):
        """
        Get the names and sizes of all basic types
        """
        types = {}

        for name, attrs in self._json['base_types'].items():
            types[name] = attrs['size']

        return types

    def find_symbol_address(self, symbol):
        try:
            s = self._json['symbols'][symbol]
            s = s['address']
        except:
            s = None

        return s

    def get_defined_struct_names(self):
        ret = []

        for t, attributes in self._json['user_types'].items():
            if attributes['kind'] in class_types:
                ret.append(t)

        return ret

    def get_struct_offset(self, struct, elem):
        try:
            off = self._json['user_types'][struct]['fields'][elem]['offset']
        except:
            print("failed to get offset for %s.%s" % (struct, elem))
            off = None

        return off

    def get_struct_fields(self, struct):
        return self._json['user_types'][struct]['fields']

    def get_base_type_size(self, base_type):
        try:
            return self._json['base_types'][base_type]['size']
        except:
            # XXX We can probably make a reasonable guess that it's an int... but maybe
            # the caller should handle that.
            exp_str = "Unable to get size for base type '{}'".format(base_type)

        raise Exception(exp_str)

    def get_field_offset(self, field_attributes):
        return field_attributes['offset']

    def get_field_type(self, field_attributes):
        return field_attributes['type']['kind']

    def get_struct_name(self, field_attributes):
        return field_attributes['type']['name']

    def get_array_type(self, field_attributes):
        k = field_attributes['type']['subtype']['kind']

        try:
            t = field_attributes['type']['subtype']['name']
        except:
            # If the array is an array of pointers to structs, then there are two subtypes, and the
            # first nested subtype doesn't have a name. It does however have a kind, and that kind
            # is (hopefully, probably, maybe?) pointer.
            t = field_attributes['type']['subtype']['kind']

        # If k is a struct, union, or (heaven forbid) an array, we assume this is an array of pointers.
        # I'm really not sure if there are ever in-place list-of-lists in the kernel. If there are, this
        # assumption will break for them. Same if there are in-place lists of structs.
        # TODO: On the whole, we really should create a better mechaism for resolving sizes.
        if k not in basic_types:
            t = 'pointer'

        return t

    def get_array_count(self, field_attributes):
        return field_attributes['type']['count']

    def get_bitfield_info(self, field_attributes):
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
        t = self.get_field_type(field_attributes)

        if t == 'pointer':
            return t
        elif t == 'base':
            t = field_attributes['type']['name']
            return t

        raise Exception("Tried to get type name for kind '%s', which is not 'pointer' or 'base'" % t)
