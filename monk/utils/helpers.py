"""Helper functions for data formatting
"""

import logging

def as_string(l):
    """Transforms a list into a string. Useful for turning memory reads of array types into
    strings when you know the underlying struct member should be interpreted as a string.

    :param list l: the list to transform into a string
    :rtype: str
    :returns: the string representation of the list
    """
    s = ""

    for c in l:
        if c == 0:
            return s

        s += chr(c)

    return s

def as_int_list(s):
    """Transforms a string into a list of integers. Useful for writing a string to memory
    as an array.

    :param s: the string to transform into a list of integers
    :rtype: list
    :returns: the integer list representation of the string
    """
    l = []

    for c in s:
        l.append(ord(c))

    return l

def byte_order_int(val, order):
    """Transforms a value to the indicated byte ordering. This is used by rsp_target to take
    byte strings returned by the RSP memory reads and turn them into integers.

    :param str val: the value to transform, as a binary string
    :param str order: the byte ordering (big or little)
    :raises ValueError: if unable to decode the value
    :rtype: int
    :returns: the value in the specified byte ordering
    """
    logging.getLogger(__name__).debug(f"byte_order_int({val})")

    try:
        b = bytes.fromhex(val.decode())
    except ValueError as e:
        print(f"Unable to decode '{val}'")
        raise e

    i = int.from_bytes(b, order)

    return i

def hexbyte(val):
    """Creates a one-byte string hex value from integer val

    :param int val:
    :rtype: str
    :returns: hex string representation of val
    """
    return hexval(val, 2)

def hexaddr(val, num_bytes):
    """Creates a string hex value from integer val

    :param int val: The value to translate into a hex string of bytes
    :param int num_bytes: The number of bytes in the target's addressing
    :rtype: str
    :returns: hex string representation of val
    """

    return hexval(val, num_bytes * 2)

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
