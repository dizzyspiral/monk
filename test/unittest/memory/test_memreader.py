import unittest
from unittest.mock import MagicMock

import monk.backends
from monk.target import Monk

test_backend = MagicMock()
test_backend.read_uint8.return_value = 8
test_backend.read_uint16.return_value = 16
test_backend.read_uint32.return_value = 32
test_backend.read_uint64.return_value = 64
test_backend.get_reg.return_value = "reg"

monk.backends.backend_map = {'test_backend': MagicMock()}


class TestMemreader(unittest.TestCase):
    def test_memreader_configures_read_functions_based_on_backend(self):
        m = Monk('host', 'port', backend='test_backend')
        m._backend = test_backend
        self.assertEqual(m._backend, test_backend)

        self.assertEqual(m.read_uint8(1), 8)
        test_backend.read_uint8.assert_called_with(1)

        self.assertEqual(m.read_uint16(2), 16)
        test_backend.read_uint16.assert_called_with(2)

        self.assertEqual(m.read_uint32(3), 32)
        test_backend.read_uint32.assert_called_with(3)

        self.assertEqual(m.read_uint64(4), 64)
        test_backend.read_uint64.assert_called_with(4)

        self.assertEqual(m.get_reg('reg1'), 'reg')
        test_backend.get_reg.assert_called_with('reg1')
