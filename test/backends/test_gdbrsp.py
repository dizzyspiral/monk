import unittest
from unittest.mock import MagicMock
import sys
import socket
import threading
from queue import Queue
import time
import tracemalloc  # Temporary

import monk.backends.rsp_helpers.gdbrsp as gdbrsp


tracemalloc.start()
recvbuf = b''


def _sock_listen(sock, _):
    sock.listen()
    conn, addr = sock.accept()
    conn.close()

def _sock_send(sock, args):
    sock.listen()
    conn, addr = sock.accept()

    send_queue = args[0]

    while not send_queue.empty():
        conn.send(send_queue.get())
        gdbrsp = conn.recv(1)  # Get the '+' acknowledgement

    time.sleep(1)  # Wait for gdbrsp to be done with the socket
    conn.close()

def _sock_recv(sock, _):
    global recvbuf
    sock.listen()
    conn, addr = sock.accept()
    recvbuf = conn.recv(1024)
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


class TestGdbRsp(unittest.TestCase):
    def test_get_first_packet_indices(self):
        start, end = gdbrsp._get_first_packet_indices(b'$somedata#nn')
        self.assertEqual(start, 1)
        self.assertEqual(end, 9)

        start, end = gdbrsp._get_first_packet_indices(b'#xx$somedata#nn')
        self.assertEqual(start, 4)
        self.assertEqual(end, 12)

        start, end = gdbrsp._get_first_packet_indices(b'#xx$somedata#nn$#nn')
        self.assertEqual(start, 4)
        self.assertEqual(end, 12)


    def test_is_stop_packet(self):
        self.assertTrue(gdbrsp._is_stop_packet(b'S'))
        self.assertTrue(gdbrsp._is_stop_packet(b'T'))
        self.assertTrue(gdbrsp._is_stop_packet(b'W'))
        self.assertTrue(gdbrsp._is_stop_packet(b'X'))
        self.assertTrue(gdbrsp._is_stop_packet(b'w'))
        self.assertTrue(gdbrsp._is_stop_packet(b'N'))
        self.assertTrue(gdbrsp._is_stop_packet(b'O'))
        self.assertTrue(gdbrsp._is_stop_packet(b'F'))

        self.assertFalse(gdbrsp._is_stop_packet(b'b'))
        self.assertFalse(gdbrsp._is_stop_packet(b''))
        self.assertFalse(gdbrsp._is_stop_packet(None))
        self.assertFalse(gdbrsp._is_stop_packet(b'OK'))

    def test_make_packet(self):
        self.assertEqual(gdbrsp._make_packet(b'somedata'), b'$somedata#4e')

    def test_make_checksum(self):
        self.assertEqual(gdbrsp._make_checksum(b'somedata'), b'4e')

    def test_gdbrsp_init(self):
        sock = _make_test_socket()

        _start_sock_thread(sock, _sock_listen)

        g = gdbrsp.GdbRsp('localhost', sock.getsockname()[1])
        self.assertTrue(g._sock)
        self.assertTrue(g._read_selector)
        self.assertTrue(g._write_selector)
        self.assertTrue(g._read_thread)
        self.assertTrue(g._write_thread)

        g.close()
        sock.close()

    def test_gdbrsp_init_raises_if_cannot_connect(self):
        with self.assertRaises(gdbrsp.GdbRspError) as cm:
            gdbrsp.GdbRsp('localhost', 4444)  # Some port number that probably isn't in use

        # Make sure that the error message is sufficiently diagnostic
        self.assertTrue('localhost' in str(cm.exception))
        self.assertTrue('4444' in str(cm.exception))

    def test_gdbrsp_close(self):
        sock = _make_test_socket()
        _start_sock_thread(sock, _sock_listen)

        g = gdbrsp.GdbRsp('localhost', sock.getsockname()[1])
        self.assertTrue(g._sock)
        self.assertTrue(g._read_selector)
        self.assertTrue(g._write_selector)
        self.assertTrue(g._read_thread)
        self.assertTrue(g._write_thread)

        g.close()
        self.assertEqual(g._sock.fileno(), -1)  # Closed socket fileno == -1
        self.assertFalse(g._read_thread.is_alive())
        self.assertFalse(g._write_thread.is_alive())

        sock.close()

    def test_gdbrsp_recv(self):
        send_queue = Queue()
        packet = b"$somedata#4e"
        data = b"somedata"
        send_queue.put(packet)

        sock = _make_test_socket()
        _start_sock_thread(sock, _sock_send, send_queue)
        g = gdbrsp.GdbRsp('localhost', sock.getsockname()[1])
        self.assertEqual(g.recv(), data)

        g.close()
        sock.close()

    def test_gdbrsp_recv_multiple(self):
        # Sockets being sockets, it's possible for two or more RSP packets to be read out
        # of the socket buffer at once. This tests that gdbrsp recognizes each packet even
        # when they arrive together.
        send_queue = Queue()
        packet = b"$somedata#11$otherdata#22$lastdata#33"
        data = [b"somedata", b"otherdata", b"lastdata"]
        send_queue.put(packet)

        sock = _make_test_socket()
        _start_sock_thread(sock, _sock_send, send_queue)
        g = gdbrsp.GdbRsp('localhost', sock.getsockname()[1])
        self.assertEqual(g.recv(), data[0])
        self.assertEqual(g.recv(), data[1])
        self.assertEqual(g.recv(), data[2])

        g.close()
        sock.close()

    def test_gdbrsp_recv_bad_packet(self):
        # Tests that gdbrsp ignores packets it doesn't recognize or can't parse
        send_queue = Queue()
        packet = b"somedata#aa"
        send_queue.put(packet)

        sock = _make_test_socket()
        _start_sock_thread(sock, _sock_send, send_queue)
        g = gdbrsp.GdbRsp('localhost', sock.getsockname()[1])
        self.assertEqual(g.recv(timeout=1), None)

        g.close()
        sock.close()

    def test_gdbrsp_send(self):
        packet = b'$somedata#4e'
        data = b'somedata'

        sock = _make_test_socket()
        _start_sock_thread(sock, _sock_recv)
        g = gdbrsp.GdbRsp('localhost', sock.getsockname()[1])
        g.send(data)
        time.sleep(.1)  # Wait for packet to be sent and received
        self.assertEqual(recvbuf, packet)

        g.close()
        sock.close()

    def test_stop_packet_gets_queued_to_stop_queue(self):
        stop_codes = [b'S', b'T', b'W', b'X', b'w', b'N', b'O', b'F']
        send_queue = Queue()
        for code in stop_codes:
            # Yeah okay so I shouldn't use the tested code to test the code. But I did. Oops.
            send_queue.put(gdbrsp._make_packet(code))

        sock = _make_test_socket()
        _start_sock_thread(sock, _sock_send, send_queue)
        g = gdbrsp.GdbRsp('localhost', sock.getsockname()[1])
        time.sleep(.1)  # Wait for packet to be sent and received
        self.assertFalse(g.stop_queue.empty())

        for code in stop_codes:
            self.assertEqual(g.stop_queue.get(), code)

        g.close()
        sock.close()
