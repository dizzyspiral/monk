import unittest

import monk.utils.helpers as helpers

class TestHelpers(unittest.TestCase):
    def test_hexval(self):
        self.assertEqual(helpers.hexval(0xaaaa, 1), b'aaaa')
        self.assertEqual(helpers.hexval(0xa, 1), b'a')
        self.assertEqual(helpers.hexval(0xaa, 2), b'aa')
        self.assertEqual(helpers.hexval(0xaa, 4), b'00aa')
        self.assertEqual(helpers.hexval(0xaa, 8), b'000000aa')

    def test_hexaddr(self):
        self.assertEqual(helpers.hexaddr(0xa), b'0000000a')

    def test_hexbyte(self):
        self.assertEqual(helpers.hexbyte(0xa), b'0a')
        self.assertEqual(helpers.hexbyte(0xaaa), b'aaa')

    def test_byte_order_int(self):
        self.assertEqual(helpers.byte_order_int(b'12345678', 'little'), 0x78563412)
        self.assertEqual(helpers.byte_order_int(b'12345678', 'big'), 0x12345678)

    def test_as_string(self):
        l = [ord('h'), ord('e'), ord('l'), ord('l'), ord('o'), 0]
        self.assertEqual(helpers.as_string(l), 'hello')

    def test_as_int_list(self):
        s = 'hello'
        self.assertEqual(helpers.as_int_list(s), [ord('h'), ord('e'), ord('l'), ord('l'), ord('o')])

