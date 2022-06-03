import unittest
from unittest.mock import MagicMock
import sys
import socket
import threading
from queue import Queue
import time
import logging

gdb_mock = MagicMock()
gdb_mock.execute.return_value = "0x0 0x12345678"
gdb_mock.selected_frame = MagicMock()
gdb_mock.selected_frame.read_register.return_value = 0x00000001
sys.modules['gdb'] = gdb_mock

import monk.backends.rsp_helpers.rsp_target as rsp_target
import monk.execution.signals as signals

recvbuf = ""


def _sock_listen(sock, _):
    """ Listens for a connection and immediately quits """
    sock.listen()
    conn, addr = sock.accept()
    conn.close()

def _sock_send(sock, args):
    """
    Listens for a connection and sends all packets in a queue, receiving the + ack from the 
    connection for each packet
    """
    sock.listen()
    conn, addr = sock.accept()

    send_queue = args[0]

    while not send_queue.empty():
        conn.send(send_queue.get())
        gdbrsp = conn.recv(1)  # Get the '+' acknowledgement

    conn.close()

def _sock_recv(sock, _):
    """ Listens for a connection and receives one packet from the connection """
    global recvbuf
    sock.listen()
    conn, addr = sock.accept()
    recvbuf = conn.recv(1024)
    conn.close()

debug_print_recv = False
debug_print_send = False
def _sock_read_and_send(sock, args):
    """
    Listens for a connection, and alternates receiving and sending packets until the send 
    queue is empty
    """
    global recvbuf
    try:
        sock.listen()
        conn, addr = sock.accept()

        send_queue = args[0]

        while not send_queue.empty():
            recvbuf = conn.recv(1024)

            if debug_print_recv:
                print(recvbuf)

            conn.send(b'+')
            packet = send_queue.get()

            if debug_print_send:
                print(packet)

            conn.send(packet)
            gdbrsp = conn.recv(1)  # Get the '+' acknowledgement

        # Wait for the other end to be done with the socket before closing it
        time.sleep(1)
    except Exception as e:
        raise e
    finally:
        conn.close()


def _start_sock_thread(sock, sock_fn, *args):
    sock_thread = threading.Thread(target=sock_fn, args=[sock, args])
    sock_thread.start()
    time.sleep(.1)  # Wait briefly for socket to start listening

    return sock_thread

def _make_test_socket(portnum=0):
    sock = socket.socket()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('localhost', portnum))

    return sock


class TestRspTarget(unittest.TestCase):
    def test_decode_stop_reason(self):
        self.assertEqual(rsp_target._decode_stop_reason(signals.SIGTRAP), rsp_target.StopReasons.swbreak)

    def test_get_register_info(self):
        reg_layout, reg_map = rsp_target._get_register_info([
            arm_core_xml[2:-3],
            arm_vfp_xml[2:-3],
            system_registers_xml[2:-3]
        ])

        expected_reg_layout = [('r0', 4), ('r1', 4), ('r2', 4), ('r3', 4), ('r4', 4), ('r5', 4), ('r6', 4), ('r7', 4), ('r8', 4), ('r9', 4), ('r10', 4), ('r11', 4), ('r12', 4), ('sp', 4), ('lr', 4), ('pc', 4), ('cpsr', 4), ('d0', 8), ('d1', 8), ('d2', 8), ('d3', 8), ('d4', 8), ('d5', 8), ('d6', 8), ('d7', 8), ('d8', 8), ('d9', 8), ('d10', 8), ('d11', 8), ('d12', 8), ('d13', 8), ('d14', 8), ('d15', 8), ('fpsid', 4), ('fpscr', 4), ('fpexc', 4), ('DUMMY', 4), ('DBGDIDR', 4), ('MIDR', 4), ('CTR', 4), ('TCMTR', 4), ('TLBTR', 4), ('DUMMY', 4), ('DUMMY', 4), ('DACR', 4), ('TTBR0_EL1', 4), ('DFAR', 4), ('TTBR1_EL1', 4), ('TTBCR', 4), ('DUMMY', 4), ('DUMMY', 4), ('SCTLR', 4), ('DFSR', 4), ('DLOCKDOWN', 4), ('IFSR', 4), ('FCSEIDR', 4), ('ILOCKDOWN', 4), ('CONTEXTIDR_EL1', 4)]
        expected_reg_map = {'r0': 0, 'r1': 1, 'r2': 2, 'r3': 3, 'r4': 4, 'r5': 5, 'r6': 6, 'r7': 7, 'r8': 8, 'r9': 9, 'r10': 10, 'r11': 11, 'r12': 12, 'sp': 13, 'lr': 14, 'pc': 15, 'cpsr': 16, 'd0': 17, 'd1': 18, 'd2': 19, 'd3': 20, 'd4': 21, 'd5': 22, 'd6': 23, 'd7': 24, 'd8': 25, 'd9': 26, 'd10': 27, 'd11': 28, 'd12': 29, 'd13': 30, 'd14': 31, 'd15': 32, 'fpsid': 33, 'fpscr': 34, 'fpexc': 35, 'DUMMY': 50, 'DBGDIDR': 37, 'MIDR': 38, 'CTR': 39, 'TCMTR': 40, 'TLBTR': 41, 'DACR': 44, 'TTBR0_EL1': 45, 'DFAR': 46, 'TTBR1_EL1': 47, 'TTBCR': 48, 'SCTLR': 51, 'DFSR': 52, 'DLOCKDOWN': 53, 'IFSR': 54, 'FCSEIDR': 55, 'ILOCKDOWN': 56, 'CONTEXTIDR_EL1': 57}

        self.assertEqual(reg_layout, expected_reg_layout)
        self.assertEqual(reg_map, expected_reg_map)

    def test_get_xml_file_names(self):
        self.assertEqual(rsp_target._get_xml_file_names(target_xml[1:-3]), ['arm-core.xml', 'arm-vfp.xml', 'system-registers.xml'])

    def test_rsp_target_init(self):
        send_queue = Queue()
        send_queue.put(target_xml)
        send_queue.put(arm_core_xml)
        send_queue.put(arm_vfp_xml)
        send_queue.put(system_registers_xml)

        sock = _make_test_socket()
        _start_sock_thread(sock, _sock_read_and_send, send_queue)

        t = rsp_target.RspTarget('localhost', sock.getsockname()[1])
        t.close()
        sock.close()

    def test_get_reg_layout(self):
        expected_reg_layout = [('r0', 4), ('r1', 4), ('r2', 4), ('r3', 4), ('r4', 4), ('r5', 4), ('r6', 4), ('r7', 4), ('r8', 4), ('r9', 4), ('r10', 4), ('r11', 4), ('r12', 4), ('sp', 4), ('lr', 4), ('pc', 4), ('cpsr', 4), ('d0', 8), ('d1', 8), ('d2', 8), ('d3', 8), ('d4', 8), ('d5', 8), ('d6', 8), ('d7', 8), ('d8', 8), ('d9', 8), ('d10', 8), ('d11', 8), ('d12', 8), ('d13', 8), ('d14', 8), ('d15', 8), ('fpsid', 4), ('fpscr', 4), ('fpexc', 4), ('DUMMY', 4), ('DBGDIDR', 4), ('MIDR', 4), ('CTR', 4), ('TCMTR', 4), ('TLBTR', 4), ('DUMMY', 4), ('DUMMY', 4), ('DACR', 4), ('TTBR0_EL1', 4), ('DFAR', 4), ('TTBR1_EL1', 4), ('TTBCR', 4), ('DUMMY', 4), ('DUMMY', 4), ('SCTLR', 4), ('DFSR', 4), ('DLOCKDOWN', 4), ('IFSR', 4), ('FCSEIDR', 4), ('ILOCKDOWN', 4), ('CONTEXTIDR_EL1', 4)]
        expected_reg_map = {'r0': 0, 'r1': 1, 'r2': 2, 'r3': 3, 'r4': 4, 'r5': 5, 'r6': 6, 'r7': 7, 'r8': 8, 'r9': 9, 'r10': 10, 'r11': 11, 'r12': 12, 'sp': 13, 'lr': 14, 'pc': 15, 'cpsr': 16, 'd0': 17, 'd1': 18, 'd2': 19, 'd3': 20, 'd4': 21, 'd5': 22, 'd6': 23, 'd7': 24, 'd8': 25, 'd9': 26, 'd10': 27, 'd11': 28, 'd12': 29, 'd13': 30, 'd14': 31, 'd15': 32, 'fpsid': 33, 'fpscr': 34, 'fpexc': 35, 'DUMMY': 50, 'DBGDIDR': 37, 'MIDR': 38, 'CTR': 39, 'TCMTR': 40, 'TLBTR': 41, 'DACR': 44, 'TTBR0_EL1': 45, 'DFAR': 46, 'TTBR1_EL1': 47, 'TTBCR': 48, 'SCTLR': 51, 'DFSR': 52, 'DLOCKDOWN': 53, 'IFSR': 54, 'FCSEIDR': 55, 'ILOCKDOWN': 56, 'CONTEXTIDR_EL1': 57}

        send_queue = Queue()
        send_queue.put(b"$T05thread:p01.01;#06")  # Reply to ? query for stopped status
        send_queue.put(b"$anything#nn")  # Reply to qSupported
        send_queue.put(target_xml)
        send_queue.put(arm_core_xml)
        send_queue.put(arm_vfp_xml)
        send_queue.put(system_registers_xml)
        send_queue.put(b'OK#xx')

        sock = _make_test_socket()
        _start_sock_thread(sock, _sock_read_and_send, send_queue)

        t = rsp_target.RspTarget('localhost', sock.getsockname()[1])
        self.assertEqual(t._reg_layout, expected_reg_layout)
        self.assertEqual(t._reg_map, expected_reg_map)
        t.close()
        sock.close()

    def test_read_register(self):
        send_queue = Queue()
        send_queue.put(b"$T05thread:p01.01;#06")  # Reply to ? query for stopped status
        send_queue.put(b"$anything#nn")  # Reply to qSupported
        send_queue.put(target_xml)
        send_queue.put(arm_core_xml)
        send_queue.put(arm_vfp_xml)
        send_queue.put(system_registers_xml)
        send_queue.put(b'$12345678#nn')

        sock = _make_test_socket()
        _start_sock_thread(sock, _sock_read_and_send, send_queue)

        t = rsp_target.RspTarget('localhost', sock.getsockname()[1])

        with self.assertRaises(rsp_target.RspTargetError) as cm:
            t.read_register('illegal reg')

        self.assertTrue('illegal reg' in str(cm.exception))
        self.assertEqual(t.read_register('r0'), 0x78563412)

        t.close()
        sock.close()

    def test_write_register(self):
        send_queue = Queue()
        send_queue.put(b"$T05thread:p01.01;#06")  # Reply to ? query for stopped status
        send_queue.put(b"$anything#nn")  # Reply to qSupported
        send_queue.put(target_xml)
        send_queue.put(arm_core_xml)
        send_queue.put(arm_vfp_xml)
        send_queue.put(system_registers_xml)
        send_queue.put(b'$resp#nn')
        send_queue.put(b'$OK#nn')

        sock = _make_test_socket()
        _start_sock_thread(sock, _sock_read_and_send, send_queue)

        t = rsp_target.RspTarget('localhost', sock.getsockname()[1])

        # If the register isn't recognized, RspTarget throws an error
        with self.assertRaises(rsp_target.RspTargetError) as cm:
            t.write_register('illegal reg', 0x1)

        self.assertTrue('illegal reg' in str(cm.exception))

        # If the target doesn't respond OK to the write, RspTarget throws an error
        with self.assertRaises(rsp_target.RspTargetError) as cm:
            t.write_register('r0', 0x1)

        self.assertTrue('r0' in str(cm.exception))
        self.assertTrue('0x1' in str(cm.exception))

        # RspTarget transforms write_register arguments into a properly formed RSP command
        t.write_register('r0', 0x1)
        self.assertEqual(recvbuf, b'$P00=01#4e')

        t.close()
        sock.close()

    def test_read_memory(self):
        send_queue = Queue()
        send_queue.put(b"$T05thread:p01.01;#06")  # Reply to ? query for stopped status
        send_queue.put(b"$anything#nn")  # Reply to qSupported
        send_queue.put(target_xml)
        send_queue.put(arm_core_xml)
        send_queue.put(arm_vfp_xml)
        send_queue.put(system_registers_xml)
        send_queue.put(b'$12345678#nn')
       
        sock = _make_test_socket()
        _start_sock_thread(sock, _sock_read_and_send, send_queue)

        t = rsp_target.RspTarget('localhost', sock.getsockname()[1])
        self.assertEqual(t.read_memory(0x11111111, 4), 0x78563412)

        t.close()
        sock.close()
     
    def test_write_memory(self):
        send_queue = Queue()
        send_queue.put(b"$T05thread:p01.01;#06")  # Reply to ? query for stopped status
        send_queue.put(b"$anything#nn")  # Reply to qSupported
        send_queue.put(target_xml)
        send_queue.put(arm_core_xml)
        send_queue.put(arm_vfp_xml)
        send_queue.put(system_registers_xml)
        send_queue.put(b'$resp#nn')
        send_queue.put(b'$OK#nn')

        sock = _make_test_socket()
        _start_sock_thread(sock, _sock_read_and_send, send_queue)

        t = rsp_target.RspTarget('localhost', sock.getsockname()[1])

        # If the target doesn't respond OK to the write, RspTarget throws an error
        with self.assertRaises(rsp_target.RspTargetError) as cm:
            t.write_memory(0x11111111, 0x1, 1)

        self.assertTrue('0x11111111' in str(cm.exception))

        # RspTarget transforms write_memory arguments into a properly formed RSP command
        t.write_memory(0x11111111, 0x1, 1)
        self.assertEqual(recvbuf, b'$M11111111,1,01#bf')

        t.close()
        sock.close()

    def test_cmd_continue(self):
        send_queue = Queue()
        send_queue.put(b"$T05thread:p01.01;#06")  # Reply to ? query for stopped status
        send_queue.put(b"$anything#nn")  # Reply to qSupported
        send_queue.put(target_xml)
        send_queue.put(arm_core_xml)
        send_queue.put(arm_vfp_xml)
        send_queue.put(system_registers_xml)
        # Normally the gdbstub doesn't send anything back in response to vCont unless the target
        # is already stopped, but we're sending something back just to keep _sock_read_and_send happy
        # (otherwise it would close before reading the vCont command)
        send_queue.put(b'$OK#nn')

        sock = _make_test_socket()
        _start_sock_thread(sock, _sock_read_and_send, send_queue)

        t = rsp_target.RspTarget('localhost', sock.getsockname()[1])

        # RspTarget sends vCont;c
        t.cmd_continue()
        time.sleep(1)
        self.assertEqual(recvbuf, b'$vCont;c#a8')

        t.close()
        sock.close()

    def test_cmd_stop(self):
        send_queue = Queue()
        send_queue.put(b"$T05thread:p01.01;#06")  # Reply to ? query for stopped status
        send_queue.put(b"$anything#nn")  # Reply to qSupported
        send_queue.put(target_xml)
        send_queue.put(arm_core_xml)
        send_queue.put(arm_vfp_xml)
        send_queue.put(system_registers_xml)
        send_queue.put(b'$OK#nn')
        send_queue.put(b'$OK#nn')

        sock = _make_test_socket()
        _start_sock_thread(sock, _sock_read_and_send, send_queue)

        t = rsp_target.RspTarget('localhost', sock.getsockname()[1])

        # RspTarget send vCtrlC
        # Must continue before sending stop, because cmd_stop won't send anything if the target 
        # is already stopped
        t.cmd_continue()
        time.sleep(1)
        t.cmd_stop()
        time.sleep(1)
        self.assertEqual(recvbuf, b'$vCtrlC#4e')

        t.close()
        sock.close()

    def test_cmd_stop_does_nothing_if_already_stopped(self):
        send_queue = Queue()
        send_queue.put(b"$T05thread:p01.01;#06")  # Reply to ? query for stopped status
        send_queue.put(b"$anything#nn")  # Reply to qSupported
        send_queue.put(target_xml)
        send_queue.put(arm_core_xml)
        send_queue.put(arm_vfp_xml)
        send_queue.put(system_registers_xml)
        send_queue.put(b'$OK#nn')

        sock = _make_test_socket()
        _start_sock_thread(sock, _sock_read_and_send, send_queue)

        t = rsp_target.RspTarget('localhost', sock.getsockname()[1])

        # Must continue before sending stop, because cmd_stop won't send anything if the target 
        # is already stopped
        time.sleep(1)
        t.cmd_stop()
        time.sleep(1)
        self.assertEqual(recvbuf, b'$qXfer:features:read:system-registers.xml:0,ffb#9c')
        t.cmd_continue()  # Just sending something to close the test thread

        t.close()
        sock.close()

    def test_cannot_call_cmd_stop_from_another_thread(self):
        send_queue = Queue()
        send_queue.put(b"$T05thread:p01.01;#06")  # Reply to ? query for stopped status
        send_queue.put(b"$anything#nn")  # Reply to qSupported
        send_queue.put(target_xml)
        send_queue.put(arm_core_xml)
        send_queue.put(arm_vfp_xml)
        send_queue.put(system_registers_xml)
        send_queue.put(b'$OK#nn')

        sock = _make_test_socket()
        _start_sock_thread(sock, _sock_read_and_send, send_queue)

        t = rsp_target.RspTarget('localhost', sock.getsockname()[1])

        # Must continue before sending stop, because cmd_stop won't do anything if the target 
        # is already stopped
        t.cmd_continue()
        time.sleep(1)
        fail = False

        def _test_thread():
            try:
                with self.assertRaises(rsp_target.RspTargetError):
                    t.cmd_stop()
            except:
                fail = True

        th1 = threading.Thread(target=_test_thread)
        th1.start()
        th1.join()

        self.assertFalse(fail)
        t.close()
        sock.close()

    def test_cannot_call_cmd_step_from_another_thread(self):
        send_queue = Queue()
        send_queue.put(b"$T05thread:p01.01;#06")  # Reply to ? query for stopped status
        send_queue.put(b"$anything#nn")  # Reply to qSupported
        send_queue.put(target_xml)
        send_queue.put(arm_core_xml)
        send_queue.put(arm_vfp_xml)
        send_queue.put(system_registers_xml)
        send_queue.put(b'$OK#nn')

        sock = _make_test_socket()
        _start_sock_thread(sock, _sock_read_and_send, send_queue)

        t = rsp_target.RspTarget('localhost', sock.getsockname()[1])

        # Must stop before sending step, because cmd_step won't do anything if the target 
        # is running
        t.cmd_stop()
        time.sleep(1)
        fail = False

        def _test_thread():
            try:
                with self.assertRaises(rsp_target.RspTargetError):
                    t.cmd_step()
            except:
                fail = True

        th1 = threading.Thread(target=_test_thread)
        th1.start()
        th1.join()

        self.assertFalse(fail)
        t.close()
        sock.close()

    def test_cmd_stop_blocks_until_callbacks_complete(self):
        self.skipTest("Not sure how to test that something blocks")
        should_wait = True

        # Block return of event thread until test is finished
        def wait_for_signal(addr):
            while should_wait:
                pass

        send_queue = Queue()
        send_queue.put(b"$T05thread:p01.01;#06")  # Reply to ? query for stopped status
        send_queue.put(b"$anything#nn")  # Reply to qSupported
        send_queue.put(target_xml)
        send_queue.put(arm_core_xml)
        send_queue.put(arm_vfp_xml)
        send_queue.put(system_registers_xml)
        send_queue.put(b'$OK#nn')

        sock = _make_test_socket()
        _start_sock_thread(sock, _sock_read_and_send, send_queue)

        t = rsp_target.RspTarget('localhost', sock.getsockname()[1])
        t.on_execute = wait_for_signal
        t.cmd_stop()  # This should cause on_execute to get called

    def test_callbacks_can_call_cmd_stop(self):
        send_queue = Queue()
        send_queue.put(b"$T05thread:p01.01;#06")  # Reply to ? query for stopped status
        send_queue.put(b"$anything#nn")  # Reply to qSupported
        send_queue.put(target_xml)
        send_queue.put(arm_core_xml)
        send_queue.put(arm_vfp_xml)
        send_queue.put(system_registers_xml)
        send_queue.put(b'$OK#nn')

        sock = _make_test_socket()
        _start_sock_thread(sock, _sock_read_and_send, send_queue)

        t = rsp_target.RspTarget('localhost', sock.getsockname()[1])

        # Must stop before sending step, because cmd_step won't do anything if the target 
        # is running
        t.cmd_stop()
        time.sleep(1)
        fail = False

        def _test_thread():
            try:
                t.cmd_stop()
            except:
                fail = True

        th1 = threading.Thread(target=_test_thread)
        th1.start()
        th1.join()

        self.assertFalse(fail)
        t.close()
        sock.close()

    def test_set_sw_breakpoint(self):
        send_queue = Queue()
        send_queue.put(b"$T05thread:p01.01;#06")  # Reply to ? query for stopped status
        send_queue.put(b"$anything#nn")  # Reply to qSupported
        send_queue.put(target_xml)
        send_queue.put(arm_core_xml)
        send_queue.put(arm_vfp_xml)
        send_queue.put(system_registers_xml)
        # Normally the gdbstub doesn't send anything back in response to vCont unless the target
        # is already stopped, but we're sending something back just to keep _sock_read_and_send happy
        # (otherwise it would close before reading the vCont command)
        send_queue.put(b'$OK#nn')

        sock = _make_test_socket()
        _start_sock_thread(sock, _sock_read_and_send, send_queue)

        t = rsp_target.RspTarget('localhost', sock.getsockname()[1])

        t.set_sw_breakpoint(0x12345678)
        time.sleep(1)
        self.assertEqual(recvbuf, b'$Z0,12345678,4#ba')

        t.close()
        sock.close()

    def test_set_hw_breakpoint(self):
        send_queue = Queue()
        send_queue.put(b"$T05thread:p01.01;#06")  # Reply to ? query for stopped status
        send_queue.put(b"$anything#nn")  # Reply to qSupported
        send_queue.put(target_xml)
        send_queue.put(arm_core_xml)
        send_queue.put(arm_vfp_xml)
        send_queue.put(system_registers_xml)
        # Normally the gdbstub doesn't send anything back in response to vCont unless the target
        # is already stopped, but we're sending something back just to keep _sock_read_and_send happy
        # (otherwise it would close before reading the vCont command)
        send_queue.put(b'$OK#nn')

        sock = _make_test_socket()
        _start_sock_thread(sock, _sock_read_and_send, send_queue)

        t = rsp_target.RspTarget('localhost', sock.getsockname()[1])

        t.set_hw_breakpoint(0x12345678)
        time.sleep(1)
        self.assertEqual(recvbuf, b'$Z1,12345678,0#b7')

        t.close()
        sock.close()

    def test_set_write_watchpoint(self):
        send_queue = Queue()
        send_queue.put(b"$T05thread:p01.01;#06")  # Reply to ? query for stopped status
        send_queue.put(b"$anything#nn")  # Reply to qSupported
        send_queue.put(target_xml)
        send_queue.put(arm_core_xml)
        send_queue.put(arm_vfp_xml)
        send_queue.put(system_registers_xml)
        # Normally the gdbstub doesn't send anything back in response to vCont unless the target
        # is already stopped, but we're sending something back just to keep _sock_read_and_send happy
        # (otherwise it would close before reading the vCont command)
        send_queue.put(b'$OK#nn')

        sock = _make_test_socket()
        _start_sock_thread(sock, _sock_read_and_send, send_queue)

        t = rsp_target.RspTarget('localhost', sock.getsockname()[1])

        t.set_write_watchpoint(0x12345678, 4)
        time.sleep(1)
        self.assertEqual(recvbuf, b'$Z2,12345678,4#bc')

        t.close()
        sock.close()

    def test_set_read_watchpoint(self):
        send_queue = Queue()
        send_queue.put(b"$T05thread:p01.01;#06")  # Reply to ? query for stopped status
        send_queue.put(b"$anything#nn")  # Reply to qSupported
        send_queue.put(target_xml)
        send_queue.put(arm_core_xml)
        send_queue.put(arm_vfp_xml)
        send_queue.put(system_registers_xml)
        # Normally the gdbstub doesn't send anything back in response to vCont unless the target
        # is already stopped, but we're sending something back just to keep _sock_read_and_send happy
        # (otherwise it would close before reading the vCont command)
        send_queue.put(b'$OK#nn')

        sock = _make_test_socket()
        _start_sock_thread(sock, _sock_read_and_send, send_queue)

        t = rsp_target.RspTarget('localhost', sock.getsockname()[1])

        t.set_read_watchpoint(0x12345678, 4)
        time.sleep(1)
        self.assertEqual(recvbuf, b'$Z3,12345678,4#bd')

        t.close()
        sock.close()

    def test_set_access_watchpoint(self):
        send_queue = Queue()
        send_queue.put(b"$T05thread:p01.01;#06")  # Reply to ? query for stopped status
        send_queue.put(b"$anything#nn")  # Reply to qSupported
        send_queue.put(target_xml)
        send_queue.put(arm_core_xml)
        send_queue.put(arm_vfp_xml)
        send_queue.put(system_registers_xml)
        # Normally the gdbstub doesn't send anything back in response to vCont unless the target
        # is already stopped, but we're sending something back just to keep _sock_read_and_send happy
        # (otherwise it would close before reading the vCont command)
        send_queue.put(b'$OK#nn')

        sock = _make_test_socket()
        _start_sock_thread(sock, _sock_read_and_send, send_queue)

        t = rsp_target.RspTarget('localhost', sock.getsockname()[1])

        t.set_access_watchpoint(0x12345678, 4)
        time.sleep(1)
        self.assertEqual(recvbuf, b'$Z4,12345678,4#be')

        t.close()
        sock.close()

    def test_remove_sw_breakpoint(self):
        send_queue = Queue()
        send_queue.put(b"$T05thread:p01.01;#06")  # Reply to ? query for stopped status
        send_queue.put(b"$anything#nn")  # Reply to qSupported
        send_queue.put(target_xml)
        send_queue.put(arm_core_xml)
        send_queue.put(arm_vfp_xml)
        send_queue.put(system_registers_xml)
        # Normally the gdbstub doesn't send anything back in response to vCont unless the target
        # is already stopped, but we're sending something back just to keep _sock_read_and_send happy
        # (otherwise it would close before reading the vCont command)
        send_queue.put(b'$OK#nn')
        send_queue.put(b'$E#nn')  # Error response to trying to remove breakpoint

        sock = _make_test_socket()
        _start_sock_thread(sock, _sock_read_and_send, send_queue)

        t = rsp_target.RspTarget('localhost', sock.getsockname()[1])

        t.remove_sw_breakpoint(0x12345678)
        time.sleep(1)
        self.assertEqual(recvbuf, b'$z0,12345678,4#da')

        with self.assertRaises(rsp_target.RspTargetError):
            t.remove_sw_breakpoint(0x12345678)
            time.sleep(1)

        t.close()
        sock.close()

    def test_remove_hw_breakpoint(self):
        send_queue = Queue()
        send_queue.put(b"$T05thread:p01.01;#06")  # Reply to ? query for stopped status
        send_queue.put(b"$anything#nn")  # Reply to qSupported
        send_queue.put(target_xml)
        send_queue.put(arm_core_xml)
        send_queue.put(arm_vfp_xml)
        send_queue.put(system_registers_xml)
        # Normally the gdbstub doesn't send anything back in response to vCont unless the target
        # is already stopped, but we're sending something back just to keep _sock_read_and_send happy
        # (otherwise it would close before reading the vCont command)
        send_queue.put(b'$OK#nn')

        sock = _make_test_socket()
        _start_sock_thread(sock, _sock_read_and_send, send_queue)

        t = rsp_target.RspTarget('localhost', sock.getsockname()[1])

        t.remove_hw_breakpoint(0x12345678)
        time.sleep(1)
        self.assertEqual(recvbuf, b'$z1,12345678,0#d7')

        t.close()
        sock.close()

    def test_remove_write_watchpoint(self):
        send_queue = Queue()
        send_queue.put(b"$T05thread:p01.01;#06")  # Reply to ? query for stopped status
        send_queue.put(b"$anything#nn")  # Reply to qSupported
        send_queue.put(target_xml)
        send_queue.put(arm_core_xml)
        send_queue.put(arm_vfp_xml)
        send_queue.put(system_registers_xml)
        # Normally the gdbstub doesn't send anything back in response to vCont unless the target
        # is already stopped, but we're sending something back just to keep _sock_read_and_send happy
        # (otherwise it would close before reading the vCont command)
        send_queue.put(b'$OK#nn')

        sock = _make_test_socket()
        _start_sock_thread(sock, _sock_read_and_send, send_queue)

        t = rsp_target.RspTarget('localhost', sock.getsockname()[1])

        t.remove_write_watchpoint(0x12345678, 4)
        time.sleep(1)
        self.assertEqual(recvbuf, b'$z2,12345678,4#dc')

        t.close()
        sock.close()

    def test_remove_read_watchpoint(self):
        send_queue = Queue()
        send_queue.put(b"$T05thread:p01.01;#06")  # Reply to ? query for stopped status
        send_queue.put(b"$anything#nn")  # Reply to qSupported
        send_queue.put(target_xml)
        send_queue.put(arm_core_xml)
        send_queue.put(arm_vfp_xml)
        send_queue.put(system_registers_xml)
        # Normally the gdbstub doesn't send anything back in response to vCont unless the target
        # is already stopped, but we're sending something back just to keep _sock_read_and_send happy
        # (otherwise it would close before reading the vCont command)
        send_queue.put(b'$OK#nn')

        sock = _make_test_socket()
        _start_sock_thread(sock, _sock_read_and_send, send_queue)

        t = rsp_target.RspTarget('localhost', sock.getsockname()[1])

        t.remove_read_watchpoint(0x12345678, 4)
        time.sleep(1)
        self.assertEqual(recvbuf, b'$z3,12345678,4#dd')

        t.close()
        sock.close()

    def test_remove_access_watchpoint(self):
        send_queue = Queue()
        send_queue.put(b"$T05thread:p01.01;#06")  # Reply to ? query for stopped status
        send_queue.put(b"$anything#nn")  # Reply to qSupported
        send_queue.put(target_xml)
        send_queue.put(arm_core_xml)
        send_queue.put(arm_vfp_xml)
        send_queue.put(system_registers_xml)
        # Normally the gdbstub doesn't send anything back in response to vCont unless the target
        # is already stopped, but we're sending something back just to keep _sock_read_and_send happy
        # (otherwise it would close before reading the vCont command)
        send_queue.put(b'$OK#nn')

        sock = _make_test_socket()
        _start_sock_thread(sock, _sock_read_and_send, send_queue)

        t = rsp_target.RspTarget('localhost', sock.getsockname()[1])

        t.remove_access_watchpoint(0x12345678, 4)
        time.sleep(1)
        self.assertEqual(recvbuf, b'$z4,12345678,4#de')

        t.close()
        sock.close()

    def test_close(self):
        send_queue = Queue()
        send_queue.put(b"$T05thread:p01.01;#06")  # Reply to ? query for stopped status
        send_queue.put(b"$anything#nn")  # Reply to qSupported
        send_queue.put(target_xml)
        send_queue.put(arm_core_xml)
        send_queue.put(arm_vfp_xml)
        send_queue.put(system_registers_xml)

        sock = _make_test_socket()
        _start_sock_thread(sock, _sock_read_and_send, send_queue)

        t = rsp_target.RspTarget('localhost', sock.getsockname()[1])

        self.assertFalse(t._shutdown_flag)

        # Close can only be called by the main thread
        fail = False
        def _test_thread():
            try:
                with self.assertRaises(rsp_target.RspTargetError):
                    t.close()
            except:
                fail = True

        th1 = threading.Thread(target=_test_thread)
        th1.start()
        th1.join()

        self.assertFalse(fail)
        self.assertFalse(t._shutdown_flag)

        t.close()

        # sets the shutdown flag
        self.assertTrue(t._shutdown_flag)

        # sends cmd_stop to the target and detaches. cmd_stop gets sent first, so we won't see
        # it in the recvbuf... we could make some changes to the test send/receive fun to get
        # around this, but, am lazy.
        # XXX cmd_stop is only sent if the target is running. Unless we sent cmd_continue, it
        # thinks the target is not running.
#        self.assertEqual(recvbuf, b'$vCtrlC#4e')

        # detaches from the target
        # we also can't really test this because when the connection gets closed, an empty
        # packet is sent to us, so that's all we see in recvbuf
#        time.sleep(1)
#        self.assertEqual(recvbuf, b'$D;1#b0')

        # closes threads
        # TODO: check.

        sock.close()

    def test_request_xml_files(self):
        send_queue = Queue()
        send_queue.put(b"$T05thread:p01.01;#06")  # Reply to ? query for stopped status
        send_queue.put(b"$anything#nn")  # Reply to qSupported
        send_queue.put(target_xml)
        send_queue.put(arm_core_xml)
        send_queue.put(arm_vfp_xml)
        send_queue.put(system_registers_xml)
        send_queue.put(b'$file 1 contents#nn')  # bogus reply for file request
        send_queue.put(b'$file 2 contents#nn')  # bogus reply for file request
        send_queue.put(b'$file 3 contents#nn')  # bogus reply for file request

        sock = _make_test_socket()
        _start_sock_thread(sock, _sock_read_and_send, send_queue)

        t = rsp_target.RspTarget('localhost', sock.getsockname()[1])

        xml_file_names = ['1.xml', '2.xml', '3.xml']
        xml_contents = t._request_xml_files(xml_file_names)

        t.close()
        sock.close()

        self.assertEqual(xml_contents, [b'ile 1 contents', b'ile 2 contents', b'ile 3 contents'])

    def test_get_stop_reason(self):
        # Test doesn't work because once rsp_target is initialized, the event loop is listening for
        # stop packets. Normally, _get_stop_reason executes *as* the event loop, so we arent't
        # competing with it to pick up stop packets. But if you call _get_stop_reason directly,
        # you are... and that function asks the target to give it a stop packet and directly reads
        # it out of the queue. The event loop snarfs it up before we can catch it, and the test hangs.
        self.skipTest("")
        global debug_print_recv
        global debug_print_send
        debug_print_recv = True
        debug_print_send = True

        logging.basicConfig(level=logging.DEBUG)

        send_queue = Queue()
        send_queue.put(b"$T05thread:p01.01;#06")  # Reply to ? query for stopped status
        send_queue.put(b"$anything#nn")  # Reply to qSupported
        send_queue.put(target_xml)
        send_queue.put(arm_core_xml)
        send_queue.put(arm_vfp_xml)
        send_queue.put(system_registers_xml)
        send_queue.put(b"$T05thread:p01.01;#06")  # Reply to ? query for stopped status
        send_queue.put(b"$anything#nn")  # Reply to close?

        sock = _make_test_socket()
        _start_sock_thread(sock, _sock_read_and_send, send_queue)

        t = rsp_target.RspTarget('localhost', sock.getsockname()[1])

        stop_reason = t._get_stop_reason(b"T05thread:p01.01")

        t.close()
        sock.close()

        logging.basicConfig(level=logging.INFO)

        debug_print_recv = False
        debug_print_send = False

        self.assertEqual(stop_reason, rsp_target.StopReasons.swbreak)



# GDB rsp packets
target_xml = b"""$l<?xml version="1.0"?><!DOCTYPE target SYSTEM "gdb-target.dtd"><target><architecture>arm</architecture><xi:include href="arm-core.xml"/><xi:include href="arm-vfp.xml"/><xi:include href="system-registers.xml"/></target>#53"""

arm_core_xml = b"""$l<?xml version="1.0"?>
<!-- Copyright (C) 2008 Free Software Foundation, Inc.

     Copying and distribution of this file, with or without modification,
     are permitted in any medium without royalty provided the copyright
     notice and this notice are preserved.  -->

<!DOCTYPE feature SYSTEM "gdb-target.dtd">
<feature name="org.gnu.gdb.arm.core">
  <reg name="r0" bitsize="32"/>
  <reg name="r1" bitsize="32"/>
  <reg name="r2" bitsize="32"/>
  <reg name="r3" bitsize="32"/>
  <reg name="r4" bitsize="32"/>
  <reg name="r5" bitsize="32"/>
  <reg name="r6" bitsize="32"/>
  <reg name="r7" bitsize="32"/>
  <reg name="r8" bitsize="32"/>
  <reg name="r9" bitsize="32"/>
  <reg name="r10" bitsize="32"/>
  <reg name="r11" bitsize="32"/>
  <reg name="r12" bitsize="32"/>
  <reg name="sp" bitsize="32" type="data_ptr"/>
  <reg name="lr" bitsize="32"/>
  <reg name="pc" bitsize="32" type="code_ptr"/>

  <!-- The CPSR is register 25, rather than register 16, because
       the FPA registers historically were placed between the PC
       and the CPSR in the "g" packet.  -->
  <reg name="cpsr" bitsize="32" regnum="25"/>
</feature>
#81"""

arm_vfp_xml = b"""$l<?xml version="1.0"?>
<!-- Copyright (C) 2008 Free Software Foundation, Inc.

     Copying and distribution of this file, with or without modification,
     are permitted in any medium without royalty provided the copyright
     notice and this notice are preserved.  -->
<!DOCTYPE feature SYSTEM "gdb-target.dtd">
<feature name="org.gnu.gdb.arm.vfp">
  <reg name="d0" bitsize="64" type="float"/>
  <reg name="d1" bitsize="64" type="float"/>
  <reg name="d2" bitsize="64" type="float"/>
  <reg name="d3" bitsize="64" type="float"/>
  <reg name="d4" bitsize="64" type="float"/>
  <reg name="d5" bitsize="64" type="float"/>
  <reg name="d6" bitsize="64" type="float"/>
  <reg name="d7" bitsize="64" type="float"/>
  <reg name="d8" bitsize="64" type="float"/>
  <reg name="d9" bitsize="64" type="float"/>
  <reg name="d10" bitsize="64" type="float"/>
  <reg name="d11" bitsize="64" type="float"/>
  <reg name="d12" bitsize="64" type="float"/>
  <reg name="d13" bitsize="64" type="float"/>
  <reg name="d14" bitsize="64" type="float"/>
  <reg name="d15" bitsize="64" type="float"/>

  <reg name="fpsid" bitsize="32" type="int" group="float"/>
  <reg name="fpscr" bitsize="32" type="int" group="float"/>
  <reg name="fpexc" bitsize="32" type="int" group="float"/>
</feature>
#6d"""

system_registers_xml = b"""$l<?xml version="1.0"?><!DOCTYPE target SYSTEM "gdb-target.dtd"><feature name="org.qemu.gdb.arm.sys.regs"><reg name="DUMMY" bitsize="32" group="cp_regs"/><reg name="DBGDIDR" bitsize="32" group="cp_regs"/><reg name="MIDR" bitsize="32" group="cp_regs"/><reg name="CTR" bitsize="32" group="cp_regs"/><reg name="TCMTR" bitsize="32" group="cp_regs"/><reg name="TLBTR" bitsize="32" group="cp_regs"/><reg name="DUMMY" bitsize="32" group="cp_regs"/><reg name="DUMMY" bitsize="32" group="cp_regs"/><reg name="DACR" bitsize="32" group="cp_regs"/><reg name="TTBR0_EL1" bitsize="32" group="cp_regs"/><reg name="DFAR" bitsize="32" group="cp_regs"/><reg name="TTBR1_EL1" bitsize="32" group="cp_regs"/><reg name="TTBCR" bitsize="32" group="cp_regs"/><reg name="DUMMY" bitsize="32" group="cp_regs"/><reg name="DUMMY" bitsize="32" group="cp_regs"/><reg name="SCTLR" bitsize="32" group="cp_regs"/><reg name="DFSR" bitsize="32" group="cp_regs"/><reg name="DLOCKDOWN" bitsize="32" group="cp_regs"/><reg name="IFSR" bitsize="32" group="cp_regs"/><reg name="FCSEIDR" bitsize="32" group="cp_regs"/><reg name="ILOCKDOWN" bitsize="32" group="cp_regs"/><reg name="CONTEXTIDR_EL1" bitsize="32" group="cp_regs"/></feature>#58"""
