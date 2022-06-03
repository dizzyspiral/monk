import unittest
from unittest.mock import MagicMock
import sys

gdb_mock = MagicMock()
gdb_mock.execute.return_value = "0x0 0x12345678"
gdb_mock.selected_frame = MagicMock()
gdb_mock.selected_frame.read_register.return_value = 0x00000001
sys.modules['gdb'] = gdb_mock

import monk.backends.gdb
from monk.backends.gdb import _sanitize_int, _exec_read_uint_cmd, read_uint8, read_uint16, read_uint32, read_uint64, get_reg

monk.backends.gdb.types = {'int' : 4}

class TestMemreader(unittest.TestCase):
    def test_exec_read_uint_cmd(self):
        self.assertEqual(_exec_read_uint_cmd("cmd"), 0x12345678)

    def test_read_uint8(self):
        self.assertEqual(read_uint8(0x0), 0x12345678)

    def test_read_uint16(self):
        self.assertEqual(read_uint16(0x0), 0x12345678)

    def test_read_uint32(self):
        self.assertEqual(read_uint32(0x0), 0x12345678)

    def test_read_uint64(self):
        self.assertEqual(read_uint64(0x0), 0x12345678)

    def test_sanitize_int(self):
        # TODO: Improve this test to actually cover the "negative hex" values that are problematic
        self.assertEqual(_sanitize_int(1, 32), 1)

    def test_get_reg(self):
        self.assertEqual(get_reg('regname'), 0x1)
