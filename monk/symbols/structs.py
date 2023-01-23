import sys

from .dwarf2json_loader import basic_types, class_types, array_types
from monk.utils.helpers import as_string  # for struct __str__ method


def generate_structs(backend, d2json):
    """ Initialize the kernel classes. Load them from JSON, return a list of them."""
    class_type_map = {}  # Bind this to all classes once every class struct has been created
    structs = []  # List of all class structs

    # 1. Generate all structs, bare-bones, no attributes
    for struct_name in d2json.get_defined_struct_names():
        obj_name = _name_to_camel(struct_name)
        c = type(obj_name, (object,), {})
        c.__init__ = _gen_struct_constructor()
        c.name = struct_name

        # Add class to lookup table, for easy resolution in kernel struct properties
        class_type_map[struct_name] = c
        structs.append((obj_name, c))

    # 3. Add attributes to the classes
    for name, struct in structs:
        _gen_attributes(struct, backend, d2json, class_type_map)

    return structs


class AttributeGenerator():
    def __init__(self, backend):
        self.backend = backend

    def _get_read_fn(self, size):
        """
        Gets the appropriate memory reading function for the size of the data to be read

        :param int size: the size in bytes of the data to be read
        :returns: The memory read function
        :rtype: function
        """
        if size == 1:
            return self.backend.read_uint8
        elif size == 2:
            return self.backend.read_uint16
        elif size == 8:
            return self.backend.read_uint64
        else:
            return self.backend.read_uint32

    def gen_uint_prop(self, offset, size):
        """
        Generates a class property getter to read memory

        :returns: The getter function
        :rtype: function
        """
        read_fn = self._get_read_fn(size)
        return lambda x: read_fn(x.base + offset)

    def gen_class_prop(self, offset, cls):
        """
        Generates a class property getter to interpret memory as a kernel data structure

        :returns: The getter function
        :rtype: function
        """
        return lambda x: cls(x.base + offset)

    def gen_list_prop(self, offset, elem_size, num_elems):
        """
        Generates a class property getter to read a list from memory

        :returns: The getter function
        :rtype: function
        """
        read_fn = self._get_read_fn(elem_size)
        return lambda x: [read_fn(a) for a in range(x.base + offset, x.base + offset + (num_elems * elem_size), elem_size)]

    def gen_bitfield_prop(self, offset, field_size, bit_position, bit_length):
        """
        Generates a class propety getter to read a bitfield from memory

        :returns: The getter function
        :rtype: function
        """
        read_fn = self._get_read_fn(field_size)

        def read_bits(x):
            bits = read_fn(x.base + offset)
            bits << bit_position
            bits >> field_size - bit_length

            return bits

        return read_bits

    def gen_null_prop(self):
        """
        Generates a function for a class property that returns None. Used for struct 
        fields that are parsed out of the JSON, but whose type is either not supported 
        or could not be discerned.

        :returns: function that always returns None
        :rtype: function
        """
        return lambda x: None


    # --- write functions ---

    def _get_write_fn(self, size):
        """
        Gets the appropriate memory reading function for the size of the data to be read

        :param int size: the size in bytes of the data to be read
        :returns: The memory read function
        :rtype: function
        """
        if size == 1:
            return self.backend.write_uint8
        elif size == 2:
            return self.backend.write_uint16
        elif size == 8:
            return self.backend.write_uint64
        else:
            return self.backend.write_uint32

    def gen_uint_setter(self, offset, size):
        """
        Generates a class property getter to read memory

        :returns: The getter function
        :rtype: function
        """
        write_fn = self._get_write_fn(size)
        return lambda x, y: write_fn(x.base + offset, y)

    def gen_class_setter(self, offset, cls):
        """
        Generates a class property setter to interpret memory as a kernel data structure

        :returns: The getter function
        :rtype: function
        """
        # This is only useful (with my limited creativity, anyway) if you want to set a
        # struct's member struct to be equal to that of a different, already-instantiated
        # struct with a different base address. E.g., copy one tasks's thread_info to 
        # another task. For this reason, we ignore the base address of newstruct and just 
        # copy its members, one by one, into memory at the correct offset.
        def write_struct(x, newstruct):
            if not type(newstruct) == cls:
                print("Cannot overwrite struct of type '%s' with type '%s'", (type(newstruct), str(cls)))
                return

            member_struct = cls(x.base + offset)

            for field in newstruct.__dir__():
                if not field.startswith('_') and not field.endswith('_offset') and field not in ('base', 'name'):
                    setattr(member_struct, field, getattr(newstruct, field))

        return write_struct

    def gen_list_setter(self, offset, elem_size, num_elems):
        """
        Generates a class property getter to read a list from memory

        :returns: The getter function
        :rtype: function
        """
        write_fn = self._get_write_fn(elem_size)

        def write_list(x, val):
            i = 0;

            for addr in range(x.base + offset, x.base + offset + (num_elems * elem_size), elem_size):
                if i < len(val):
                    write_fn(addr, val[i])

                i += 1
                
        return write_list

    def gen_bitfield_setter(self, offset, field_size, bit_position, bit_length):
        read_fn = self._get_read_fn(field_size)
        write_fn = self._get_write_fn(field_size)

        def set_bits(x, val):
            # Get the current value for the full bitfield
            bits = read_fn(x.base + offset)

            # Make the bitmask to clear the bits... this has got to be a dumb/slow way, but I don't
            # have a better idea right now.
            mask = 0
            for i in range(bit_length):
                mask += 2 ** i

            # Clear the bits we want to set
            bits = bits & mask

            # Shift val into the correct bit position
            val << bit_position

            # Set the bits with val
            bits = bits | val

            # Write the new bitfield
            write_fn(x.base + offset, bits)

        return set_bits

    def gen_null_setter(self, ):
        """
        Generates a function for a class property that returns None. Used for struct 
        fields that are parsed out of the JSON, but whose type is either not supported 
        or could not be discerned.

        :returns: None
        :rtype: None
        """
        return lambda x, y: None

def _gen_str_method(attr_list):
    """
    Generates the __str__ method for the kernel structure, to pretty-print each of
    its members according to their types.
    """

    def to_str(self):
        s = f"{self.name}: base:{hex(self.base)}\n"
        s += "=====\n"
        for attr, attr_type in attr_list:
            if attr_type in basic_types:
                s += f"{attr}: {hex(getattr(self, attr))}\n"
            elif attr_type in class_types:
                cls = getattr(self, attr)
                s += f"{attr} ({cls.name}): {hex(cls.base)}\n"
            elif attr_type in array_types:
                arr = getattr(self, attr)
                s += f"{attr}: {arr}"
                try:
                    s += f", as string: {as_string(arr)}\n"
                except OverflowError:
                    s += "\n"
            elif attr_type == 'bitfield':
                s += f"{attr}: {hex(getattr(self, attr))}\n"
            else:
                s += f"{attr}: null\n"

        return s

    return to_str


def _gen_struct_constructor():
    """
    Binds a name to a constructor for a kernel struct, and returns that constructor

    :returns: The class constructor
    :rtype: function
    """
    def struct_constructor(self, base):
        self.base = base

    return struct_constructor

def _gen_attributes(cls, backend, d2json, class_type_map):
    """
    Generates all of the member attributes for a kernel struct class. Each attribute
    has a getter and setter that reads/writes memory of the target.
    """
    attribute_generator = AttributeGenerator(backend)
    # Logically speaking, the attributes for a struct's class could/should be created
    # prior to invoking its constructor. But, doing it here lets us defer creation of
    # them until instantiation, which is useful because attributes which are
    # themselves other structs need to have those other structs defined before the
    # attribute can be created. This isn't the best way to solve that problem - we
    # should just do a define pass on the structs, and then an attribute assignment
    # pass, but whatever, this is how it turned out for now.

    attr_list = []

    # For every field defined for this struct
    for field, attributes in d2json.get_struct_fields(cls.name).items():
        field_type = d2json.get_field_type(attributes)
        offset = d2json.get_field_offset(attributes)

        attr_list.append((field, field_type))

        # Generate the appropriate getter for the data type. If the type is a union 
        # or a struct, this will create an instance of the class for the kernel data
        # structure by looking up the class from the class map generated by the class 
        # auto-generation process. Otherwise, the getter will invoke GDB to read 
        # memory and return the value read in the format most intuitive for the data 
        # type. Note that memory is read each time the attribute is accessed. Further 
        # note that arrays are represented as lists, regardless of whether they are 
        # char arrays (because char does not always *really* represent a character). 
        # If you want to interpret an array of characters as a string, you will need 
        # to convert it. A helper function for this is provided in state.helpers.
        if field_type in basic_types:
            size = d2json.get_base_type_size(d2json.get_base_type_name(attributes))
            setattr(cls, field, 
                    property(attribute_generator.gen_uint_prop(offset, size),
                             attribute_generator.gen_uint_setter(offset, size)))
        elif field_type in class_types:
            c = class_type_map[d2json.get_struct_name(attributes)]
            setattr(cls, field,
                    property(attribute_generator.gen_class_prop(offset, c),
                             attribute_generator.gen_class_setter(offset, c)))
        elif field_type in array_types:
            num_elems = d2json.get_array_count(attributes)
            elem_size = d2json.get_base_type_size(d2json.get_array_type(attributes))
            setattr(cls, field, 
                    property(attribute_generator.gen_list_prop(offset, elem_size, num_elems),
                             attribute_generator.gen_list_setter(offset, elem_size, num_elems)))
        elif field_type == 'bitfield':
            # XXX IN PROGRESS
            base_type, bit_position, bit_length = d2json.get_bitfield_info(attributes)
            field_size = d2json.get_base_type_size(base_type)
            setattr(cls, field, 
                    property(attribute_generator.gen_bitfield_prop(offset, field_size, bit_position, bit_length),
                             attribute_generator.gen_bitfield_setter(offset, field_size, bit_position, bit_length)))
        else:
            setattr(cls, field,
                    property(attribute_generator.gen_null_prop(),
                             attribute_generator.gen_null_setter()))

        setattr(cls, "{}_offset".format(field), offset)
        setattr(cls, "__str__", _gen_str_method(attr_list))

def _name_to_camel(name):
    """
    Converts name to camel case with the first letter capitalized, 
    e.g. 'thread_info' -> 'ThreadInfo'

    :returns: The camel-case name
    :rtype: string
    """
    return ''.join(x for x in name.replace('_', ' ').title() if not x.isspace() or x == '_')


# Auto-generate the kernel struct classes. The way this works is that for each struct 
# or union encountered in the volatility JSON file (parsed by config.kernel), we create
# a class. That class auto-populates itself with attributes according to the fields
# that the JSON file specifies the struct as having. See _gen_struct_constructor and
# struct_constructor, above. This has the effect of populating the API classes with
# .-accessible attributes that are identical to those specified in the JSON file. The
# JSON file, in turn, corresponds to the actual symbols in the kernel code. So we get
# some nicely intuitive classes that handle reading data out of memory for us, without
# having to tediously define them all

class Structs():
    """
    A class to bind all of the parsed kernel class objects to. Hopefully this works.
    """
    def __init__(self, d2json, backend):
        # Generate all of the kernel struct classes
        kernel_structs = generate_structs(backend, d2json)

        # Bind them to this class as subclasses
        for name, struct in kernel_structs:
            setattr(self, name, struct)
