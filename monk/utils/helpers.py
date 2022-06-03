import logging

def as_string(l):
    s = ""

    for c in l:
        if c == 0:
            return s
        else:
            s += chr(c)

    return s

def as_int_list(s):
    l = []

    for c in s:
        l.append(ord(c))

    return l

def byte_order_int(val):
    """ Transforms val to the correct byte ordering """
    # The current test machine is LE, so we just assume LE for now. You can suss out 
    # the byte ordering of the machine from the JSON file by looking at the endianess
    # of the basic types.
    logging.getLogger(__name__).debug("byte_order_int(%s)" % val)
    b = bytes.fromhex(val.decode())
    i = int.from_bytes(b, "little")
    return i

def hexbyte(val):
    return hexval(val, 2)

def hexaddr(val):
    return hexval(val, 8)

def hexval(val, size):
    """
    Creates a string hex value from integer val, padded with zeroes to equal size characters, 
    if necessary. If val contains more digits than size, the returned string length will equal 
    the number of hex digits in val.

    :param int val: the value to create a hex string from
    :param size: the minimum number of digits of the return value
    """
    val = hex(val)[2:]

    while len(val) < size:
        val = '0' + val

    return val.encode('utf-8')

