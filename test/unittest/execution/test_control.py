import unittest
from unittest.mock import MagicMock

from monk.callback_manager import CallbackManager, MonkControlError, EVENT_READ, EVENT_WRITE, EVENT_ACCESS, EVENT_EXECUTE


# TODO: Split this file according to the classes it tests, currently it tests both
# Monk and CallbackManager
class TestControl(unittest.TestCase):
    def setUp(self):
        self.test_backend = MagicMock()
        self.callback_manager = CallbackManager(self.test_backend)

    def test_callback_manager_constructor_initializes_callbacks(self):
        self.test_backend.set_on_read_callback.assert_called_with(self.callback_manager._on_read_dispatcher)
        self.test_backend.set_on_write_callback.assert_called_with(self.callback_manager._on_write_dispatcher)
        self.test_backend.set_on_access_callback.assert_called_with(self.callback_manager._on_access_dispatcher)

    def test_run(self):
        self.skipTest("move to test_monk")
        self.callback_manager.run()
        self.test_backend.run.assert_called_with()

    def test_stop(self):
        self.skipTest("move to test_monk")
        self.callback_manager.stop()
        self.test_backend.stop.assert_called_with()

    def test_shutdown(self):
        self.skipTest("move to test_monk")
        self.callback_manager.shutdown()
        self.test_backend.shutdown.assert_called_with()

    def test_set_breakpoint(self):
        self.callback_manager._set_breakpoint(EVENT_READ, 0)
        self.test_backend.set_read_breakpoint.assert_called_with(0)

        self.callback_manager._set_breakpoint(EVENT_WRITE, 1)
        self.test_backend.set_write_breakpoint.assert_called_with(1)

        self.callback_manager._set_breakpoint(EVENT_ACCESS, 2)
        self.test_backend.set_access_breakpoint.assert_called_with(2)

        self.callback_manager._set_breakpoint(EVENT_EXECUTE, 3)
        self.test_backend.set_exec_breakpoint.assert_called_with(3)

        with self.assertRaises(MonkControlError):
            self.callback_manager._set_breakpoint(12345, 4)

    def test_del_breakpoint(self):
        self.callback_manager._del_breakpoint(EVENT_READ, 0)
        self.test_backend.del_read_breakpoint.assert_called_with(0)

        self.callback_manager._del_breakpoint(EVENT_WRITE, 1)
        self.test_backend.del_write_breakpoint.assert_called_with(1)

        self.callback_manager._del_breakpoint(EVENT_ACCESS, 2)
        self.test_backend.del_access_breakpoint.assert_called_with(2)

        self.callback_manager._del_breakpoint(EVENT_EXECUTE, 3)
        self.test_backend.del_exec_breakpoint.assert_called_with(3)

    def test_break_on_event(self):
        cb1 = MagicMock()
        cb2 = MagicMock()

        # Read events
        result = self.callback_manager._break_on_event(EVENT_READ, 0, cb1)
        self.assertEqual(self.callback_manager._on_read_callbacks[0], [cb1])
        self.assertEqual(result, (EVENT_READ, 0, cb1))

        result = self.callback_manager._break_on_event(EVENT_READ, 0, cb2)
        self.assertEqual(self.callback_manager._on_read_callbacks[0], [cb1, cb2])
        self.assertEqual(result, (EVENT_READ, 0, cb2))

        result = self.callback_manager._break_on_event(EVENT_READ, 1, cb2)
        self.assertEqual(self.callback_manager._on_read_callbacks[1], [cb2])
        self.assertEqual(result, (EVENT_READ, 1, cb2))

        result = self.callback_manager._break_on_event(EVENT_READ, 2, None)
        self.assertEqual(self.callback_manager._on_read_callbacks[2], [None])
        self.assertEqual(result, (EVENT_READ, 2, None))

        # Write events
        result = self.callback_manager._break_on_event(EVENT_WRITE, 0, cb1)
        self.assertEqual(self.callback_manager._on_write_callbacks[0], [cb1])
        self.assertEqual(result, (EVENT_WRITE, 0, cb1))

        result = self.callback_manager._break_on_event(EVENT_WRITE, 0, cb2)
        self.assertEqual(self.callback_manager._on_write_callbacks[0], [cb1, cb2])
        self.assertEqual(result, (EVENT_WRITE, 0, cb2))

        result = self.callback_manager._break_on_event(EVENT_WRITE, 1, cb2)
        self.assertEqual(self.callback_manager._on_write_callbacks[1], [cb2])
        self.assertEqual(result, (EVENT_WRITE, 1, cb2))

        result = self.callback_manager._break_on_event(EVENT_WRITE, 2, None)
        self.assertEqual(self.callback_manager._on_write_callbacks[2], [None])
        self.assertEqual(result, (EVENT_WRITE, 2, None))

        # Access events
        result = self.callback_manager._break_on_event(EVENT_ACCESS, 0, cb1)
        self.assertEqual(self.callback_manager._on_access_callbacks[0], [cb1])
        self.assertEqual(result, (EVENT_ACCESS, 0, cb1))

        result = self.callback_manager._break_on_event(EVENT_ACCESS, 0, cb2)
        self.assertEqual(self.callback_manager._on_access_callbacks[0], [cb1, cb2])
        self.assertEqual(result, (EVENT_ACCESS, 0, cb2))

        result = self.callback_manager._break_on_event(EVENT_ACCESS, 1, cb2)
        self.assertEqual(self.callback_manager._on_access_callbacks[1], [cb2])
        self.assertEqual(result, (EVENT_ACCESS, 1, cb2))

        result = self.callback_manager._break_on_event(EVENT_ACCESS, 2, None)
        self.assertEqual(self.callback_manager._on_access_callbacks[2], [None])
        self.assertEqual(result, (EVENT_ACCESS, 2, None))

        # Execute events
        result = self.callback_manager._break_on_event(EVENT_EXECUTE, 0, cb1)
        self.assertEqual(self.callback_manager._on_execute_callbacks[0], [cb1])
        self.assertEqual(result, (EVENT_EXECUTE, 0, cb1))

        result = self.callback_manager._break_on_event(EVENT_EXECUTE, 0, cb2)
        self.assertEqual(self.callback_manager._on_execute_callbacks[0], [cb1, cb2])
        self.assertEqual(result, (EVENT_EXECUTE, 0, cb2))

        result = self.callback_manager._break_on_event(EVENT_EXECUTE, 1, cb2)
        self.assertEqual(self.callback_manager._on_execute_callbacks[1], [cb2])
        self.assertEqual(result, (EVENT_EXECUTE, 1, cb2))

        result = self.callback_manager._break_on_event(EVENT_EXECUTE, 2, None)
        self.assertEqual(self.callback_manager._on_execute_callbacks[2], [None])
        self.assertEqual(result, (EVENT_EXECUTE, 2, None))

        # Error
        with self.assertRaises(MonkControlError):
            self.callback_manager._break_on_event(12345, cb1)

    def test_on_read(self):
        cb1 = MagicMock()
        cb2 = MagicMock()

        result = self.callback_manager.on_read(0, cb1)
        self.assertEqual(result, (EVENT_READ, 0, cb1))
        self.assertEqual(self.callback_manager._on_read_callbacks[0], [cb1])
        self.test_backend.set_read_breakpoint.assert_called_with(0)

        result = self.callback_manager.on_read(0, cb2)
        self.assertEqual(result, (EVENT_READ, 0, cb2))
        self.assertEqual(self.callback_manager._on_read_callbacks[0], [cb1, cb2])

        result = self.callback_manager.on_read(1, cb2)
        self.assertEqual(result, (EVENT_READ, 1, cb2))
        self.assertEqual(self.callback_manager._on_read_callbacks[1], [cb2])
        self.test_backend.set_read_breakpoint.assert_called_with(1)

    def test_on_write(self):
        cb1 = MagicMock()
        cb2 = MagicMock()

        result = self.callback_manager.on_write(0, cb1)
        self.assertEqual(result, (EVENT_WRITE, 0, cb1))
        self.assertEqual(self.callback_manager._on_write_callbacks[0], [cb1])
        self.test_backend.set_write_breakpoint.assert_called_with(0)

        result = self.callback_manager.on_write(0, cb2)
        self.assertEqual(result, (EVENT_WRITE, 0, cb2))
        self.assertEqual(self.callback_manager._on_write_callbacks[0], [cb1, cb2])

        result = self.callback_manager.on_write(1, cb2)
        self.assertEqual(result, (EVENT_WRITE, 1, cb2))
        self.assertEqual(self.callback_manager._on_write_callbacks[1], [cb2])
        self.test_backend.set_write_breakpoint.assert_called_with(1)

    def test_on_access(self):
        cb1 = MagicMock()
        cb2 = MagicMock()

        result = self.callback_manager.on_access(0, cb1)
        self.assertEqual(result, (EVENT_ACCESS, 0, cb1))
        self.assertEqual(self.callback_manager._on_access_callbacks[0], [cb1])
        self.test_backend.set_access_breakpoint.assert_called_with(0)

        result = self.callback_manager.on_access(0, cb2)
        self.assertEqual(result, (EVENT_ACCESS, 0, cb2))
        self.assertEqual(self.callback_manager._on_access_callbacks[0], [cb1, cb2])

        result = self.callback_manager.on_access(1, cb2)
        self.assertEqual(result, (EVENT_ACCESS, 1, cb2))
        self.assertEqual(self.callback_manager._on_access_callbacks[1], [cb2])
        self.test_backend.set_access_breakpoint.assert_called_with(1)

    def test_on_execute(self):
        cb1 = MagicMock()
        cb2 = MagicMock()

        result = self.callback_manager.on_execute(0, cb1)
        self.assertEqual(result, (EVENT_EXECUTE, 0, cb1))
        self.assertEqual(self.callback_manager._on_execute_callbacks[0], [cb1])
        self.test_backend.set_exec_breakpoint.assert_called_with(0)

        result = self.callback_manager.on_execute(0, cb2)
        self.assertEqual(result, (EVENT_EXECUTE, 0, cb2))
        self.assertEqual(self.callback_manager._on_execute_callbacks[0], [cb1, cb2])

        result = self.callback_manager.on_execute(1, cb2)
        self.assertEqual(result, (EVENT_EXECUTE, 1, cb2))
        self.assertEqual(self.callback_manager._on_execute_callbacks[1], [cb2])
        self.test_backend.set_exec_breakpoint.assert_called_with(1)

    def test_remove_callback(self):
        cb1 = MagicMock()
        cb2 = MagicMock()

        # Read
        r1 = self.callback_manager.on_read(0, cb1)
        self.assertEqual(self.callback_manager._on_read_callbacks[0], [cb1])
        self.callback_manager.remove_callback(r1)
        self.assertEqual(self.callback_manager._on_read_callbacks[0], [])
        self.test_backend.del_exec_breakpoint.called_with(0)

        r1 = self.callback_manager.on_read(0, cb1)
        self.assertEqual(self.callback_manager._on_read_callbacks[0], [cb1])
        r2 = self.callback_manager.on_read(0, cb2)
        self.assertEqual(self.callback_manager._on_read_callbacks[0], [cb1, cb2])
        self.callback_manager.remove_callback(r1)
        self.assertEqual(self.callback_manager._on_read_callbacks[0], [cb2])
        self.callback_manager.remove_callback(r2)
        self.assertEqual(self.callback_manager._on_read_callbacks[0], [])
        self.test_backend.del_exec_breakpoint.called_with(0)

        r1 = self.callback_manager.on_read(0, cb1)
        self.assertEqual(self.callback_manager._on_read_callbacks[0], [cb1])
        r2 = self.callback_manager.on_read(0, cb2)
        self.assertEqual(self.callback_manager._on_read_callbacks[0], [cb1, cb2])
        self.callback_manager.remove_callback(r2)
        self.assertEqual(self.callback_manager._on_read_callbacks[0], [cb1])
        self.callback_manager.remove_callback(r1)
        self.assertEqual(self.callback_manager._on_read_callbacks[0], [])
        self.test_backend.del_exec_breakpoint.called_with(0)

        # Write
        r1 = self.callback_manager.on_write(0, cb1)
        self.assertEqual(self.callback_manager._on_write_callbacks[0], [cb1])
        self.callback_manager.remove_callback(r1)
        self.assertEqual(self.callback_manager._on_write_callbacks[0], [])
        self.test_backend.del_exec_breakpoint.called_with(0)

        r1 = self.callback_manager.on_write(0, cb1)
        self.assertEqual(self.callback_manager._on_write_callbacks[0], [cb1])
        r2 = self.callback_manager.on_write(0, cb2)
        self.assertEqual(self.callback_manager._on_write_callbacks[0], [cb1, cb2])
        self.callback_manager.remove_callback(r1)
        self.assertEqual(self.callback_manager._on_write_callbacks[0], [cb2])
        self.callback_manager.remove_callback(r2)
        self.assertEqual(self.callback_manager._on_write_callbacks[0], [])
        self.test_backend.del_exec_breakpoint.called_with(0)

        r1 = self.callback_manager.on_write(0, cb1)
        self.assertEqual(self.callback_manager._on_write_callbacks[0], [cb1])
        r2 = self.callback_manager.on_write(0, cb2)
        self.assertEqual(self.callback_manager._on_write_callbacks[0], [cb1, cb2])
        self.callback_manager.remove_callback(r2)
        self.assertEqual(self.callback_manager._on_write_callbacks[0], [cb1])
        self.callback_manager.remove_callback(r1)
        self.assertEqual(self.callback_manager._on_write_callbacks[0], [])
        self.test_backend.del_exec_breakpoint.called_with(0)

        # Access
        r1 = self.callback_manager.on_access(0, cb1)
        self.assertEqual(self.callback_manager._on_access_callbacks[0], [cb1])
        self.callback_manager.remove_callback(r1)
        self.assertEqual(self.callback_manager._on_access_callbacks[0], [])
        self.test_backend.del_exec_breakpoint.called_with(0)

        r1 = self.callback_manager.on_access(0, cb1)
        self.assertEqual(self.callback_manager._on_access_callbacks[0], [cb1])
        r2 = self.callback_manager.on_access(0, cb2)
        self.assertEqual(self.callback_manager._on_access_callbacks[0], [cb1, cb2])
        self.callback_manager.remove_callback(r1)
        self.assertEqual(self.callback_manager._on_access_callbacks[0], [cb2])
        self.callback_manager.remove_callback(r2)
        self.assertEqual(self.callback_manager._on_access_callbacks[0], [])
        self.test_backend.del_exec_breakpoint.called_with(0)

        r1 = self.callback_manager.on_access(0, cb1)
        self.assertEqual(self.callback_manager._on_access_callbacks[0], [cb1])
        r2 = self.callback_manager.on_access(0, cb2)
        self.assertEqual(self.callback_manager._on_access_callbacks[0], [cb1, cb2])
        self.callback_manager.remove_callback(r2)
        self.assertEqual(self.callback_manager._on_access_callbacks[0], [cb1])
        self.callback_manager.remove_callback(r1)
        self.assertEqual(self.callback_manager._on_access_callbacks[0], [])
        self.test_backend.del_exec_breakpoint.called_with(0)

        # Execute
        r1 = self.callback_manager.on_execute(0, cb1)
        self.assertEqual(self.callback_manager._on_execute_callbacks[0], [cb1])
        self.callback_manager.remove_callback(r1)
        self.assertEqual(self.callback_manager._on_execute_callbacks[0], [])
        self.test_backend.del_exec_breakpoint.called_with(0)

        r1 = self.callback_manager.on_execute(0, cb1)
        self.assertEqual(self.callback_manager._on_execute_callbacks[0], [cb1])
        r2 = self.callback_manager.on_execute(0, cb2)
        self.assertEqual(self.callback_manager._on_execute_callbacks[0], [cb1, cb2])
        self.callback_manager.remove_callback(r1)
        self.assertEqual(self.callback_manager._on_execute_callbacks[0], [cb2])
        self.callback_manager.remove_callback(r2)
        self.assertEqual(self.callback_manager._on_execute_callbacks[0], [])
        self.test_backend.del_exec_breakpoint.called_with(0)

        r1 = self.callback_manager.on_execute(0, cb1)
        self.assertEqual(self.callback_manager._on_execute_callbacks[0], [cb1])
        r2 = self.callback_manager.on_execute(0, cb2)
        self.assertEqual(self.callback_manager._on_execute_callbacks[0], [cb1, cb2])
        self.callback_manager.remove_callback(r2)
        self.assertEqual(self.callback_manager._on_execute_callbacks[0], [cb1])
        self.callback_manager.remove_callback(r1)
        self.assertEqual(self.callback_manager._on_execute_callbacks[0], [])
        self.test_backend.del_exec_breakpoint.called_with(0)

        # Remove callback that doesn't exist
        with self.assertRaises(MonkControlError):
            self.callback_manager.remove_callback(r1)

        # Use unsupported kind
        with self.assertRaises(MonkControlError):
            self.callback_manager.remove_callback(('nope', 0, None))

    def test_del_breakpoint(self):
        self.callback_manager._del_breakpoint(EVENT_WRITE, 0)
        self.test_backend.del_write_breakpoint.assert_called_with(0)

        self.callback_manager._del_breakpoint(EVENT_READ, 1)
        self.test_backend.del_read_breakpoint.assert_called_with(1)

        self.callback_manager._del_breakpoint(EVENT_ACCESS, 2)
        self.test_backend.del_access_breakpoint.assert_called_with(2)

        self.callback_manager._del_breakpoint(EVENT_EXECUTE, 3)
        self.test_backend.del_exec_breakpoint.assert_called_with(3)

        with self.assertRaises(MonkControlError):
            self.callback_manager._del_breakpoint('nope', 4)

    def test_on_read_dispatcher(self):
        test_callback = MagicMock()
        test_callback2 = MagicMock()
        self.callback_manager.on_read(0x0, test_callback)
        self.callback_manager.on_read(0x1, test_callback2)
        self.callback_manager._on_read_dispatcher(0x0)
        test_callback.assert_called()
        test_callback2.assert_not_called()

    def test_on_write_dispatcher(self):
        test_callback = MagicMock()
        test_callback2 = MagicMock()
        self.callback_manager.on_write(0x0, test_callback)
        self.callback_manager.on_write(0x1, test_callback2)
        self.callback_manager._on_write_dispatcher(0x0)
        test_callback.assert_called()
        test_callback2.assert_not_called()

    def test_on_access_dispatcher(self):
        test_callback = MagicMock()
        test_callback2 = MagicMock()
        self.callback_manager.on_access(0x0, test_callback)
        self.callback_manager.on_access(0x1, test_callback2)
        self.callback_manager._on_access_dispatcher(0x0)
        test_callback.assert_called()
        test_callback2.assert_not_called()

    def test_on_execute_dispatcher(self):
        test_callback = MagicMock()
        test_callback2 = MagicMock()
        self.callback_manager.on_execute(0x0, test_callback)
        self.callback_manager.on_execute(0x1, test_callback2)
        self.callback_manager._on_execute_dispatcher(0x0)
        test_callback.assert_called()
        test_callback2.assert_not_called()

    def test_callback_handler(self):
        test_callback = MagicMock()
        self.callback_manager._set_breakpoint(EVENT_EXECUTE, 0x0)
        self.callback_manager._callback_handler([test_callback])
        test_callback.assert_called()
        # This is supposed to test that breakpoints are re-set on target stop, but atm it's not
        # an effective test...
        self.test_backend.set_exec_breakpoint.assert_called_with(0x0)
