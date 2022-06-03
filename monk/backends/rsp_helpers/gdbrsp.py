import socket
import re
from queue import Queue, Empty
import threading
import selectors
import logging

from ...utils.helpers import hexbyte


class GdbRspError(Exception):
    pass


class GdbRsp():
    """ Asynchronously sends and receives packets on a RSP connection """

    _checksum_pattern = re.compile(b'#..')

    def __init__(self, host, port):
        # Stop packets, encountered on breakpoints or exceptions, are put in this public queue
        # instead of GdbRsp's read_queue. This makes it so that they are never confused with data,
        # and also makes it easier for a dedicated thread to process stop events.
        self.stop_queue = Queue()

        self._sock_lock = threading.Lock()
        self._send_queue = Queue()
        self.read_queue = Queue()
        self._shutdown_flag = False

        # Connect to gdbstub
        self._sock = socket.socket()

        err_msg = ""
        try:
            self._sock.connect((host, port))
        except ConnectionRefusedError:
            self._sock.close()
            err_msg = ("Unable to connect to gdbstub at %s" % ":".join([host, str(port)]))

        if err_msg:
            raise(GdbRspError(err_msg))

        # Set up async selectors
        self._read_selector = selectors.DefaultSelector()
        self._read_selector.register(self._sock, selectors.EVENT_READ)
        self._write_selector = selectors.DefaultSelector()
        self._write_selector.register(self._sock, selectors.EVENT_WRITE)

        # Set up async threads
        self._read_thread = threading.Thread(target=self._do_recv)
        self._write_thread = threading.Thread(target=self._do_send)
        self._read_thread.start()
        self._write_thread.start()

    def send(self, data):
        logging.getLogger(__name__).debug("send() %s" % data)

        try:
            packet = _make_packet(data)
        except TypeError:
            # Turn a regular string into bytes
            packet = _make_packet(data.encode('utf-8'))

        self._send_queue.put(packet)
        logging.getLogger(__name__).debug("send finished")

    def _do_send(self):
        """ Sends packets queued in the send queue to the target """
        while True:
            if self._shutdown_flag:
                return

            # Do not block indefinitely for data. Instead, check every second if close()
            # was called, and terminate this thread if so.
            try:
                packet = self._send_queue.get(timeout=1)
            except Empty:
                continue

            logging.getLogger(__name__).debug("_do_send() %s" % packet)
            self._write_selector.select()
            logging.getLogger(__name__).debug("_do_send() write selector acquired")
            self._sock_lock.acquire()
            logging.getLogger(__name__).debug("_do_send() write socket lock acquired")

            try:
                self._sock.send(packet)
            except BrokenPipeError:
                # If the other end of the socket connection has closed, it's time to shutdown.
                self._shutdown_flag = True

            logging.getLogger(__name__).debug("_do_send() packet sent")
            self._sock_lock.release()

    def recv(self, timeout=None):
        packet = None

        try:
            packet = self.read_queue.get(timeout=timeout)
        except Empty:
            pass

        return packet

    def _do_recv(self):
        """
        Receives packets from the target and queues packet data. If the read packet is a 
        stop packet, it goes into stop_queue. Otherwise, it goes in the read queue.
        """
        recv_buf = b''

        while True:
            if self._shutdown_flag:
                return

            # Do not block indefinitely for data. Instead, check every second if close()
            # was called, and terminate this thread if so.
            events = self._read_selector.select(timeout=1)

            if not events:
                continue
                
            self._sock_lock.acquire()

            # Read until we've read a checksum
            while not re.search(self._checksum_pattern, recv_buf):
                # It's possible to get stuck here if there is no checksum, e.g. if the remote
                # side sends part of a packet and hangs. This is probably unlikely to happen
                # and also not result in the remote closing the socket, in which case this
                # stops blocking due to an exception.
                try:
                    recv_buf += self._sock.recv(1024)
                except ConnectionResetError:
                    # If the other side closed the connection, it's time to shut down.
                    self._shutdown_flag = True

                # Ignore bare acknowledgements
                if recv_buf == b'+':
                    break

                # Check periodically to see if close() was called. If it was, abort the
                # current read and close this thread.
                if self._shutdown_flag:
                    self._sock_lock.release()
                    return

            self._sock_lock.release()

            try:
                start, end = _get_first_packet_indices(recv_buf)
            except GdbRspError:
                # If _get_first_packet_indices threw this error, then either start or end
                # could not be found. This means the data is a bare '+' ack, or it's corrupt.
                # In either case, ignore it.
                recv_buf = b''
                continue

            # Get the packet, then remove it from the buffer
            packet = recv_buf[start:end]
            recv_buf = recv_buf[end:]

            # TODO: Check that the packet is one that we actually handle. Unrecognized packets
            # should be ignored.

            # OK is an acknolwedgement, and '' is an error. In both cases, don't ack.
            if not packet == b'OK' or not packet == b'':
                # Send an ack. Directly append to send queue, because ack doesn't need checksum
                self._send_queue.put(b'+')

            if _is_stop_packet(packet):
                self.stop_queue.put(packet)
            else:
                self.read_queue.put(packet)

    def close(self):
        """ Close connection to gdbstub, terminate read/write threads, and close selectors """
        self._shutdown_flag =  True
        self._write_thread.join()
        self._read_thread.join()

        try:
            self._sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            # This can happen if the remote connection has closed - ignore
            pass
            
        self._sock.close()
        self._read_selector.close()
        self._write_selector.close()


def _get_first_packet_indices(data):
    # It's possible that we read more than one packet from the socket. We need to
    # get just the first one.
    start = data.find(b'$')

    # If we somehow don't have a packet start symbol - $ - then this is corrupt data.
    # Ignore it.
    if start == -1:
        raise GdbRspError("Packet start marker not found")

    end = data.find(b'#', start)

    # This should never happen, because the recv function looks for the checksum when
    # reading data. But for good measure, make sure it exists too.
    if end == -1:
        raise GdbRspError("Packet checksum not found")

    # Return start + 1 because that is the first character of the packet data
    return start + 1, end

def _make_checksum(data):
    checksum = sum(b for b in data) % 256
    checksum = hexbyte(checksum)

    return checksum

def _make_packet(data):
    packet = b'$%s#%s' % (data, _make_checksum(data))
    return packet

def _is_stop_packet(packet):
    if not packet:
        return False

    # An "OK" response is not a stop packet, but would otherwise register as one.
    if b'OK' in packet:
        return False

    stop_code = chr(packet[0])

    return stop_code in ('S', 'T', 'W', 'X', 'w', 'N', 'O', 'F')
