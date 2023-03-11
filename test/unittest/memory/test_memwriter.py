import unittest
from unittest.mock import MagicMock

import monk.backends
from monk.target import Monk

test_backend = MagicMock()
test_backend.write_uint8.return_value = None
test_backend.write_uint16.return_value = None
test_backend.write_uint32.return_value = None
test_backend.write_uint64.return_value = None
test_backend.write_reg.return_value = None
test_backend.initialize.return_value = None

monk.backends.backend_map = {'test_backend': MagicMock()}


class TestMemwriter(unittest.TestCase):
    def test_memwriter_configures_write_functions_based_on_backend(self):
        m = Monk(backend='test_backend')
        m._backend = test_backend
        m.write_uint8(1, 1)
        test_backend.write_uint8.assert_called_with(1, 1)

        m.write_uint16(2, 2)
        test_backend.write_uint16.assert_called_with(2, 2)

        m.write_uint32(3, 3)
        test_backend.write_uint32.assert_called_with(3, 3)

        m.write_uint64(4, 4)
        test_backend.write_uint64.assert_called_with(4, 4)

        m.write_reg('reg1', 5)
        test_backend.write_reg.assert_called_with('reg1', 5)
