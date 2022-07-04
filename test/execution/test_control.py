import unittest
from unittest.mock import MagicMock

import monk.execution.control as control
import monk.backends

test_backend = MagicMock()
test_backend.initialize.return_value = None

monk.backends.test_backend = test_backend

# This is only necessary because the test_backend mock isn't getting added
# to monk.backends as expected
control._backend = test_backend
control._backend.set_on_read_callback(control._on_read_dispatcher)
control._backend.set_on_write_callback(control._on_write_dispatcher)
control._backend.set_on_access_callback(control._on_access_dispatcher)
control._backend.set_on_execute_callback(control._on_execute_dispatcher)


class TestControl(unittest.TestCase):
    def setUp(self):
        control._on_read_callbacks.clear()
        control._on_write_callbacks.clear()
        control._on_access_callbacks.clear()
        control._on_execute_callbacks.clear()

    def test_memreader_initializes_backend(self):
        self.skipTest("mock not working")
        memreader.init('test_backend')
        test_backend.initialize.assert_called_with()

    def test_run(self):
        control.run()
        test_backend.run.assert_called_with()

    def test_stop(self):
        control.stop()
        test_backend.stop.assert_called_with()

    def test_shutdown(self):
        control.shutdown()
        test_backend.shutdown.assert_called_with()

    def test_set_breakpoint(self):
        control._set_breakpoint(control.EVENT_READ, 0)
        test_backend.set_read_breakpoint.assert_called_with(0)

        control._set_breakpoint(control.EVENT_WRITE, 1)
        test_backend.set_write_breakpoint.assert_called_with(1)

        control._set_breakpoint(control.EVENT_ACCESS, 2)
        test_backend.set_access_breakpoint.assert_called_with(2)

        control._set_breakpoint(control.EVENT_EXECUTE, 3)
        test_backend.set_exec_breakpoint.assert_called_with(3)

        with self.assertRaises(control.MonkControlError):
            control._set_breakpoint(12345, 4)

    def test_del_breakpoint(self):
        control._del_breakpoint(control.EVENT_READ, 0)
        test_backend.del_read_breakpoint.assert_called_with(0)

        control._del_breakpoint(control.EVENT_WRITE, 1)
        test_backend.del_write_breakpoint.assert_called_with(1)

        control._del_breakpoint(control.EVENT_ACCESS, 2)
        test_backend.del_access_breakpoint.assert_called_with(2)

        control._del_breakpoint(control.EVENT_EXECUTE, 3)
        test_backend.del_exec_breakpoint.assert_called_with(3)

    def test_break_on_event(self):
        cb1 = MagicMock()
        cb2 = MagicMock()

        # Read events
        result = control._break_on_event(control.EVENT_READ, 0, cb1)
        self.assertEqual(control._on_read_callbacks[0], [cb1])
        self.assertEqual(result, (control.EVENT_READ, 0, cb1))

        result = control._break_on_event(control.EVENT_READ, 0, cb2)
        self.assertEqual(control._on_read_callbacks[0], [cb1, cb2])
        self.assertEqual(result, (control.EVENT_READ, 0, cb2))

        result = control._break_on_event(control.EVENT_READ, 1, cb2)
        self.assertEqual(control._on_read_callbacks[1], [cb2])
        self.assertEqual(result, (control.EVENT_READ, 1, cb2))

        result = control._break_on_event(control.EVENT_READ, 2, None)
        self.assertEqual(control._on_read_callbacks[2], [None])
        self.assertEqual(result, (control.EVENT_READ, 2, None))

        # Write events
        result = control._break_on_event(control.EVENT_WRITE, 0, cb1)
        self.assertEqual(control._on_write_callbacks[0], [cb1])
        self.assertEqual(result, (control.EVENT_WRITE, 0, cb1))

        result = control._break_on_event(control.EVENT_WRITE, 0, cb2)
        self.assertEqual(control._on_write_callbacks[0], [cb1, cb2])
        self.assertEqual(result, (control.EVENT_WRITE, 0, cb2))

        result = control._break_on_event(control.EVENT_WRITE, 1, cb2)
        self.assertEqual(control._on_write_callbacks[1], [cb2])
        self.assertEqual(result, (control.EVENT_WRITE, 1, cb2))

        result = control._break_on_event(control.EVENT_WRITE, 2, None)
        self.assertEqual(control._on_write_callbacks[2], [None])
        self.assertEqual(result, (control.EVENT_WRITE, 2, None))

        # Access events
        result = control._break_on_event(control.EVENT_ACCESS, 0, cb1)
        self.assertEqual(control._on_access_callbacks[0], [cb1])
        self.assertEqual(result, (control.EVENT_ACCESS, 0, cb1))

        result = control._break_on_event(control.EVENT_ACCESS, 0, cb2)
        self.assertEqual(control._on_access_callbacks[0], [cb1, cb2])
        self.assertEqual(result, (control.EVENT_ACCESS, 0, cb2))

        result = control._break_on_event(control.EVENT_ACCESS, 1, cb2)
        self.assertEqual(control._on_access_callbacks[1], [cb2])
        self.assertEqual(result, (control.EVENT_ACCESS, 1, cb2))

        result = control._break_on_event(control.EVENT_ACCESS, 2, None)
        self.assertEqual(control._on_access_callbacks[2], [None])
        self.assertEqual(result, (control.EVENT_ACCESS, 2, None))

        # Execute events
        result = control._break_on_event(control.EVENT_EXECUTE, 0, cb1)
        self.assertEqual(control._on_execute_callbacks[0], [cb1])
        self.assertEqual(result, (control.EVENT_EXECUTE, 0, cb1))

        result = control._break_on_event(control.EVENT_EXECUTE, 0, cb2)
        self.assertEqual(control._on_execute_callbacks[0], [cb1, cb2])
        self.assertEqual(result, (control.EVENT_EXECUTE, 0, cb2))

        result = control._break_on_event(control.EVENT_EXECUTE, 1, cb2)
        self.assertEqual(control._on_execute_callbacks[1], [cb2])
        self.assertEqual(result, (control.EVENT_EXECUTE, 1, cb2))

        result = control._break_on_event(control.EVENT_EXECUTE, 2, None)
        self.assertEqual(control._on_execute_callbacks[2], [None])
        self.assertEqual(result, (control.EVENT_EXECUTE, 2, None))

        # Error
        with self.assertRaises(control.MonkControlError):
            control._break_on_event(12345, cb1)

    def test_break_on_read(self):
        cb1 = MagicMock()
        cb2 = MagicMock()

        result = control.break_on_read(0, cb1)
        self.assertEqual(result, (control.EVENT_READ, 0, cb1))
        self.assertEqual(control._on_read_callbacks[0], [cb1])
        test_backend.set_read_breakpoint.assert_called_with(0)

        result = control.break_on_read(0, cb2)
        self.assertEqual(result, (control.EVENT_READ, 0, cb2))
        self.assertEqual(control._on_read_callbacks[0], [cb1, cb2])

        result = control.break_on_read(1, cb2)
        self.assertEqual(result, (control.EVENT_READ, 1, cb2))
        self.assertEqual(control._on_read_callbacks[1], [cb2])
        test_backend.set_read_breakpoint.assert_called_with(1)

    def test_break_on_write(self):
        cb1 = MagicMock()
        cb2 = MagicMock()

        result = control.break_on_write(0, cb1)
        self.assertEqual(result, (control.EVENT_WRITE, 0, cb1))
        self.assertEqual(control._on_write_callbacks[0], [cb1])
        test_backend.set_write_breakpoint.assert_called_with(0)

        result = control.break_on_write(0, cb2)
        self.assertEqual(result, (control.EVENT_WRITE, 0, cb2))
        self.assertEqual(control._on_write_callbacks[0], [cb1, cb2])

        result = control.break_on_write(1, cb2)
        self.assertEqual(result, (control.EVENT_WRITE, 1, cb2))
        self.assertEqual(control._on_write_callbacks[1], [cb2])
        test_backend.set_write_breakpoint.assert_called_with(1)

    def test_break_on_access(self):
        cb1 = MagicMock()
        cb2 = MagicMock()

        result = control.break_on_access(0, cb1)
        self.assertEqual(result, (control.EVENT_ACCESS, 0, cb1))
        self.assertEqual(control._on_access_callbacks[0], [cb1])
        test_backend.set_access_breakpoint.assert_called_with(0)

        result = control.break_on_access(0, cb2)
        self.assertEqual(result, (control.EVENT_ACCESS, 0, cb2))
        self.assertEqual(control._on_access_callbacks[0], [cb1, cb2])

        result = control.break_on_access(1, cb2)
        self.assertEqual(result, (control.EVENT_ACCESS, 1, cb2))
        self.assertEqual(control._on_access_callbacks[1], [cb2])
        test_backend.set_access_breakpoint.assert_called_with(1)

    def test_break_on_execute(self):
        cb1 = MagicMock()
        cb2 = MagicMock()

        result = control.break_on_execute(0, cb1)
        self.assertEqual(result, (control.EVENT_EXECUTE, 0, cb1))
        self.assertEqual(control._on_execute_callbacks[0], [cb1])
        test_backend.set_exec_breakpoint.assert_called_with(0)

        result = control.break_on_execute(0, cb2)
        self.assertEqual(result, (control.EVENT_EXECUTE, 0, cb2))
        self.assertEqual(control._on_execute_callbacks[0], [cb1, cb2])

        result = control.break_on_execute(1, cb2)
        self.assertEqual(result, (control.EVENT_EXECUTE, 1, cb2))
        self.assertEqual(control._on_execute_callbacks[1], [cb2])
        test_backend.set_exec_breakpoint.assert_called_with(1)

    def test_remove_callback(self):
        cb1 = MagicMock()
        cb2 = MagicMock()

        # Read
        r1 = control.break_on_read(0, cb1)
        self.assertEqual(control._on_read_callbacks[0], [cb1])
        control.remove_callback(r1)
        self.assertEqual(control._on_read_callbacks[0], [])
        test_backend.del_exec_breakpoint.called_with(0)

        r1 = control.break_on_read(0, cb1)
        self.assertEqual(control._on_read_callbacks[0], [cb1])
        r2 = control.break_on_read(0, cb2)
        self.assertEqual(control._on_read_callbacks[0], [cb1, cb2])
        control.remove_callback(r1)
        self.assertEqual(control._on_read_callbacks[0], [cb2])
        control.remove_callback(r2)
        self.assertEqual(control._on_read_callbacks[0], [])
        test_backend.del_exec_breakpoint.called_with(0)

        r1 = control.break_on_read(0, cb1)
        self.assertEqual(control._on_read_callbacks[0], [cb1])
        r2 = control.break_on_read(0, cb2)
        self.assertEqual(control._on_read_callbacks[0], [cb1, cb2])
        control.remove_callback(r2)
        self.assertEqual(control._on_read_callbacks[0], [cb1])
        control.remove_callback(r1)
        self.assertEqual(control._on_read_callbacks[0], [])
        test_backend.del_exec_breakpoint.called_with(0)

        # Write
        r1 = control.break_on_write(0, cb1)
        self.assertEqual(control._on_write_callbacks[0], [cb1])
        control.remove_callback(r1)
        self.assertEqual(control._on_write_callbacks[0], [])
        test_backend.del_exec_breakpoint.called_with(0)

        r1 = control.break_on_write(0, cb1)
        self.assertEqual(control._on_write_callbacks[0], [cb1])
        r2 = control.break_on_write(0, cb2)
        self.assertEqual(control._on_write_callbacks[0], [cb1, cb2])
        control.remove_callback(r1)
        self.assertEqual(control._on_write_callbacks[0], [cb2])
        control.remove_callback(r2)
        self.assertEqual(control._on_write_callbacks[0], [])
        test_backend.del_exec_breakpoint.called_with(0)

        r1 = control.break_on_write(0, cb1)
        self.assertEqual(control._on_write_callbacks[0], [cb1])
        r2 = control.break_on_write(0, cb2)
        self.assertEqual(control._on_write_callbacks[0], [cb1, cb2])
        control.remove_callback(r2)
        self.assertEqual(control._on_write_callbacks[0], [cb1])
        control.remove_callback(r1)
        self.assertEqual(control._on_write_callbacks[0], [])
        test_backend.del_exec_breakpoint.called_with(0)

        # Access
        r1 = control.break_on_access(0, cb1)
        self.assertEqual(control._on_access_callbacks[0], [cb1])
        control.remove_callback(r1)
        self.assertEqual(control._on_access_callbacks[0], [])
        test_backend.del_exec_breakpoint.called_with(0)

        r1 = control.break_on_access(0, cb1)
        self.assertEqual(control._on_access_callbacks[0], [cb1])
        r2 = control.break_on_access(0, cb2)
        self.assertEqual(control._on_access_callbacks[0], [cb1, cb2])
        control.remove_callback(r1)
        self.assertEqual(control._on_access_callbacks[0], [cb2])
        control.remove_callback(r2)
        self.assertEqual(control._on_access_callbacks[0], [])
        test_backend.del_exec_breakpoint.called_with(0)

        r1 = control.break_on_access(0, cb1)
        self.assertEqual(control._on_access_callbacks[0], [cb1])
        r2 = control.break_on_access(0, cb2)
        self.assertEqual(control._on_access_callbacks[0], [cb1, cb2])
        control.remove_callback(r2)
        self.assertEqual(control._on_access_callbacks[0], [cb1])
        control.remove_callback(r1)
        self.assertEqual(control._on_access_callbacks[0], [])
        test_backend.del_exec_breakpoint.called_with(0)

        # Execute
        r1 = control.break_on_execute(0, cb1)
        self.assertEqual(control._on_execute_callbacks[0], [cb1])
        control.remove_callback(r1)
        self.assertEqual(control._on_execute_callbacks[0], [])
        test_backend.del_exec_breakpoint.called_with(0)

        r1 = control.break_on_execute(0, cb1)
        self.assertEqual(control._on_execute_callbacks[0], [cb1])
        r2 = control.break_on_execute(0, cb2)
        self.assertEqual(control._on_execute_callbacks[0], [cb1, cb2])
        control.remove_callback(r1)
        self.assertEqual(control._on_execute_callbacks[0], [cb2])
        control.remove_callback(r2)
        self.assertEqual(control._on_execute_callbacks[0], [])
        test_backend.del_exec_breakpoint.called_with(0)

        r1 = control.break_on_execute(0, cb1)
        self.assertEqual(control._on_execute_callbacks[0], [cb1])
        r2 = control.break_on_execute(0, cb2)
        self.assertEqual(control._on_execute_callbacks[0], [cb1, cb2])
        control.remove_callback(r2)
        self.assertEqual(control._on_execute_callbacks[0], [cb1])
        control.remove_callback(r1)
        self.assertEqual(control._on_execute_callbacks[0], [])
        test_backend.del_exec_breakpoint.called_with(0)

    def test_del_breakpoint(self):
        pass

    def test_on_read_dispatcher(self):
        pass

    def test_on_write_dispatcher(self):
        pass

    def test_on_access_dispatcher(self):
        pass

    def test_on_execute_dispatcher(self):
        pass

    def test_callback_handler(self):
        pass
