import socket
import re
import xml.etree.ElementTree as ET
import threading
from queue import Empty
from time import sleep
import logging

import monk.execution.signals as signals
from monk.backends.rsp_helpers.gdbrsp import GdbRsp
from monk.utils.helpers import hexbyte, byte_order_int, hexaddr, hexval

from monk.backends.rsp_helpers.regs.arm import reg_layout as arm_reg_layout, reg_map as arm_reg_map

SMALL_DELAY = 0.0001
_gdbrsp = None  # After initialization, this is a GdbRsp object with a connection to the target


class RspTargetError(Exception):
    pass


class StopReasons:
    # These are arbitrary strings, they don't correspond to the RSP protocol at all. They're
    # used by GdbRsp internally to communicate the type of breakpoint that was encountered.
    swbreak = "swbreak"
    hwbreak = "hwbreak"
    rwatch = "rwatch"
    wwatch = "wwatch"


class RspTarget():
    def __init__(self, host, port):
        # THE ORDER IN WHICH THINGS ARE INITIALIZED IN THIS CONSTRUCTOR MATTERS.
        # Modify it at your own peril.

        # Signals notification
        #
        # This is the interface exposed to code that handles user-defined hooks. These functions
        # get called when RspTarget detects one of these events from the target. Code that handles
        # hooks needs to override these functions with ones that look at the address the event
        # occured at, and calls any hooks registered to receive that event at that address.
        self.on_read = lambda addr: addr
        self.on_write = lambda addr: addr
        self.on_access = lambda addr: addr
        self.on_execute = lambda addr: addr

        self._shutdown_flag = False  # Set by close() to tell event thread to terminate
        # Set by cmd_stop() to indicate that the user stopped execution, and so handling of a stop
        # event should _not_ restart execution of the guest. The only thing that can restart execution
        # of the guest in this state is cmd_continue()
        self._user_stopped = False

        # To handle some weirdness with how breakpoints get set/unset when they're hit, this variable
        # is used to store the most recently hit breakpoint address, so that it can be restored just
        # before continuing execution again.
        self._saved_bp = None

        # This locks RSP so that multiple threads sharing the same RSP connection do not interleave
        # their requests and subsequently receive a response not meant for them, or otherwise
        # corrupt the communication. This lock should be acquired at the beginning of any RSP operation 
        # - e.g. reading memory - to ensure that both the command that's sent and the reply from the 
        # target (if any) are sent/received before any other thread is allowed to use the RSP 
        # connection.
        self._rsp_lock = threading.Lock()
        # This lock is used around commands that execute or stop the target, so that the target
        # does not resume execution in the middle of event callbacks. This lock is also picked up by
        # the event thread when it begins processing a stop event. Effectively this means that calls
        # to cmd_continue and cmd_stop will block until a callback is not running.
        self._event_lock = threading.Lock()

        self._main_thread_id = threading.get_ident()
        # Thread to dispatch stop events. We don't start the thread yet because we don't want any
        # stop events to be handled until RspTarget is fully initialized.
        self._stop_events_thread = threading.Thread(target=self._handle_stop_packets)

        self._rsp = GdbRsp(host, port)
        self._clear_rsp()  # Clear out anything that might be in the recv buf
        # We have to figure out if the target is stopped before calling cmd_stop because cmd_stop
        # depends upon that flag.
        self._target_is_stopped = self._is_target_stopped()
        self.cmd_stop()
        self._negotiate_features()
        self._reg_layout, self._reg_map = self._get_reg_layout()
        # TODO: Fix automatic register layout parsing so this isn't hard-coded
        self._reg_layout, self._reg_map = (arm_reg_layout, arm_reg_map)

        self._stop_events_thread.start()

    def _clear_rsp(self):
        """
        Clears the receive queue and stop queue of the RSP connection. Only intended to be 
        called during initialization of RspTarget, since it has a guaranteed 1 second delay
        """
        while self._rsp.recv(timeout=1):
            pass

        # TODO: Make these interfaces the same in _rsp.
        try:
            while self._rsp.stop_queue.get(timeout=1):
                pass
        except Empty:
            pass

    def _negotiate_features(self):
        self._rsp.send(b'qSupported:multiprocess+;swbreak+;hwbreak+;qRelocInsn+;fork-events+;exec-events+;vContSupported+;QThreadEvents+;no-resumed+;xmlRegisters=i386')  # Pretty likely we're saying we support stuff here that we don't
        r = self._rsp.recv()  # Don't care what the stub says it supports

    # TEMPORARY
    def get_all_regs(self):
        registers = {}
        offset = 0

        # Ask the target for the register values
        self._rsp_lock.acquire()
        self._rsp.send(b'g')  # Ask for all of the registers
        data = self._rsp.recv()
        self._rsp_lock.release()

        expected_chrs = 0
        for regname, size in self._reg_layout:
            expected_chrs += size * 2
        
        consumed_chrs = 0

        # Register data is returned sequentially according to the XML register layout we got earlier
        for regname, size in self._reg_layout:
            num_chrs = size * 2  # two hex chrs is one byte
            consumed_chrs += num_chrs
            
            # If there isn't enough data to fill out the entire register map, quit early.
            if consumed_chrs > len(data):
                break

            registers[regname] = int(data[offset : offset + num_chrs], 16)
            offset += num_chrs

        return registers

    def _handle_stop_packets(self):
        """
        Loop forever waiting for stop packets from the target
        """
        while True:
            if self._shutdown_flag:
                return

            self._event_lock.acquire()
            try:
                # This timeout must be kept short in order to avoid delaying other functions which
                # require the event lock
                packet = self._rsp.stop_queue.get(timeout=SMALL_DELAY)
            except Empty:
                self._event_lock.release()
                # We put a small sleep here in order to let other functions which require
                # the event lock to pick it up before we try again. Technically things work
                # without this, but main thread operations requiring the event lock will get
                # starved and run much slower.
                sleep(SMALL_DELAY)
                continue

            # TODO: Since we track all of the breakpoints locally (in execution/control.py, because
            # we have to in order to associate an address with its callbacks) we can probably skip
            # checking what type of breakpoint/stop event we hit, and just dispatch the address to
            # all of the handlers. It's simpler and likely more efficient than querying the stub.

            # run() and stop() both have to be disabled while handling events. Running the guest
            # will mess up the target state that the event handlers and user callbacks depend on.
            # And stopping the guest again, while it's already stopped, will change the stop 
            # reason and subsequently change the handlers that get notified.
            logging.getLogger(__name__).debug("_handle_stop_packet target_is_stopped = True")
            self._target_is_stopped = True
            logging.getLogger(__name__).debug("_handle_stop_packet()")
            logging.getLogger(__name__).debug("getting stop reason...")
            bp_type = self._get_stop_reason(packet)
            logging.getLogger(__name__).debug("stop reason = %s" % bp_type)

            logging.getLogger(__name__).debug("determining event handler...")
            # Call the appropriate event handler for the type of breakpoint encountered.
            # The event handlers are overridden by control.hooks 
            if bp_type == StopReasons.swbreak:
                logging.getLogger(__name__).debug("getting pc...")
                addr = self.read_register('pc')
                logging.getLogger(__name__).debug("pc = %s" % addr)

                # If the callback unsets the breakpoint for the current address, this will get set
                self._callback_unset_bp = False
                logging.getLogger(__name__).debug("got swbreak, removing breakpoint")

                # Try to remove the breakpoint at the current address; if it fails, the target
                # probably already removed it for us. We have to remove the breakpoint, step,
                # and then set the breakpoint again because otherwise when we continue the target
                # will immediately hit the breakpoint again without executing.
                # TODO: We can remove this now, we don't set our breakpoints to persist w/ the stub.
                try:
                    self.remove_sw_breakpoint(addr)
                except RspTargetError:
                    pass

                logging.getLogger(__name__).debug("calling on_execute")
                self.on_execute(addr)

                # XXX The callback may have unset this breakpoint. We don't want to set it again
                # in that case.
                if not self._callback_unset_bp:
                    logging.getLogger(__name__).debug("resetting breakpoint")
                    # Step the target one instruction, then reset the breakpoint at the target address
                    # XXX This won't actually step the target if the user stopped the target. Need to
                    # save the bp address to re-set next time the target actually successfully steps or
                    # continues execution. For the continue case, if there is a breakpoint to re-set,
                    # we should step, set the breakpoint, and continue - much like we're trying to do
                    # here
                    self._saved_bp = addr

            # TODO: If we step, will it trigger a swbreak if we hit a breakpoint, or do we need to
            # manually check for callbacks at that address?
            else:
                logging.getLogger(__name__).debug("unrecognized stop reason")

            # Invoking continue here assumes that we'll never have a stop packet queued at this point.
            # We could check...
            self.cmd_continue()

            self._event_lock.release()
            logging.getLogger(__name__).debug("finished handling event")

    def _is_target_stopped(self):
        """
        Determine if the target is running or not. This is only meant to be called during 
        setup of the RspTarget, because it has a delay in it while it waits for a reply 
        that may or may not come. Using this at runtime would have a huge performance 
        impact. Instead, RspTarget keeps track of whether or not the target is running as 
        it receives notification packets and sends commands from/to the target.
        """
        self._rsp.send(b'?')

        try:
            reply = self._rsp.stop_queue.get(timeout=1)
        except Empty:
            reply = None

        is_stopped = False
        logging.getLogger(__name__).debug("_is_target_stopped got reply %s" % reply)

        # The ? query receives a stop reason if the target is stopped, or nothing if not.
        if reply:
           is_stopped = True

        logging.getLogger(__name__).debug("_is_target_stopped returning %s" % is_stopped)

        return is_stopped

    def read_register(self, regname):
        """
        Read target register

        :param str regname: The register to read
        :return: The register value
        :raises RspTargetError: if the register is not successfully read
        """
        raise_err = False

        # if regname is an int, assume it's the int identifier of the register in the map
        if type(regname) == int:
            regnum = regname
        else:
            try:
                regnum = self._reg_map[regname]
            except KeyError:
                raise_err = True

            if raise_err:
                raise RspTargetError("Unable to read register '%s': register unknown" % regname)

        self._rsp_lock.acquire()
        self._rsp.send(b'p%s' % hexbyte(regnum))
        response = self._rsp.recv()
        self._rsp_lock.release()

        if _is_error_reply(response):
            raise RspTargetError("Unable to read register '{}' with index {}, received error '{}'".format(regname, regnum, response))

        response = byte_order_int(response)  # TODO: Timeouts for reads

        return response

    def write_register(self, regname, val):
        """
        Write target register

        :param str regname: The register to write
        :param int val: The value to write
        :raises RspTargetError: if the register is not successfully written
        """
        raise_err = False

        try:
            regnum = self._reg_map[regname]
        except KeyError:
            raise_err = True

        if raise_err:
            raise RspTargetError("Failed to write register '%s': register unknown" % regname)

        self._rsp_lock.acquire()
        self._rsp.send(b'P%s=%s' % (hexbyte(regnum), hexbyte(val)))
        response = self._rsp.recv()
        self._rsp_lock.release()

        if not b'OK' in response:
            raise RspTargetError("Failed to write register '%s' with value %s: target error"
                                 % (regname, hex(val)))

    def read_memory(self, addr, size):
        """
        Read target memory
        
        :param int addr: The memory address to read from
        :param int size: The number of bytes to read
        :rtype: int
        :return: the memory read
        """
        # Make the bold assumption that this is never going to be called for anything
        # bigger than an int, so we can return an int.
        self._rsp_lock.acquire()
        self._rsp.send(b'm%s,%d' % (hexaddr(addr), size))
        reply = self._rsp.recv()
        self._rsp_lock.release()

        reply = byte_order_int(reply)

        return reply

    def write_memory(self, addr, val, size):
        self._rsp_lock.acquire()
        self._rsp.send(b'M%s,%d,%s' %(hexaddr(addr), size, hexval(val, size * 2)))
        reply = self._rsp.recv()
        self._rsp_lock.release()

        if not b'OK' in reply:
            raise RspTargetError("Failed to write memory at address %s" % (hex(addr)))

    def _guard_execution(self, cmd_str):
        """
        Guard target execution against running from user callbacks or calling execution
        routines when the target is not stopped or has been stopped by the user and should
        not be started again automatically.

        :param str cmd_str: A string representation of the command that's being called
        :raises RspTargetError: When this function is executed from a callback thread
        :returns bool: False when the target should not execute the command, True when it should
        """
        cur_thread_id = threading.get_ident()
        is_main_thread = cur_thread_id == self._main_thread_id
        is_event_thread = cur_thread_id == self._stop_events_thread.ident

        if not is_main_thread and not is_event_thread:
            raise RspTargetError("Callbacks cannot call %s" % cmd_str)

        # If the target is running, then there's no reason to send a continue cmd
        if not self._target_is_stopped:
            logging.getLogger(__name__).debug("Target is not stopped, ignoring %s" % cmd_str)
            return False

        if is_event_thread and self._user_stopped:
            logging.getLogger(__name__).debug("Ignoring %s command from event thread - the "
                                              "user had previously stopped the target" % cmd_str)
            return False

        return True
       

    def _acquire_event_lock_on_empty_stop_queue(self):
        """
        Ensures that at the time the event lock is acquired, the stop queue is empty
        """

        self._event_lock.acquire()

        while not self._rsp.stop_queue.empty():
            self._event_lock.release()
            sleep(SMALL_DELAY)
            self._event_lock.acquire()

    def cmd_step(self):
        if not self._guard_execution("step"):
            return

        is_main_thread = threading.get_ident() == self._main_thread_id

        # Make sure the event loop isn't executing - there's a slight race condition between
        # when the event is queued and when the event loop picks it up. Hopefully this isn't
        # a problem.
        # Narrator voice: it was. A small delay had to be added to the event loop to give this
        # function a chance to pick up the event lock.
        if is_main_thread:
            # Make sure no stop events are pending that the event loop should process
            self._acquire_event_lock_on_empty_stop_queue()

        self._rsp_lock.acquire()
        self._rsp.send(b'vCont;s')

        # # Wait for the stop packet to arrive; if we try to send commands before the target
        # has stopped again, the target will ignore them.
        # TODO: Figure out if we ever need the SIGINT stop packet that this generates - i.e.
        # if stepping will also produce a SIGTRAP if it hits a software breakpoint, or not.
        # If it won't produce a SIGTRAP, we need to push this stop event back into the
        # queue so that it gets handled by the event loop.
        try:
            self._rsp.stop_queue.get(timeout=1)
        except Empty:
            pass  # Maybe?

        self._rsp_lock.release()

        # Run any callbacks for the new address
        addr = self.read_register('pc')
        self.on_execute(addr)

        if self._saved_bp:
            logging.getLogger(__name__).debug("re-setting saved breakpoint")
            self.set_sw_breakpoint(self._saved_bp)
            self.saved_bp = None

        if is_main_thread:
            self._event_lock.release()

        logging.getLogger(__name__).debug("cmd_step finished")

    def cmd_continue(self):
        if not self._guard_execution("continue"):
            return

        is_main_thread = threading.get_ident() == self._main_thread_id

        # un-setting user_stopped before (potentially) stepping, so that it will actually step
        self._user_stopped = False

        if self._saved_bp:
            # We have to step and set the breakpoint rather than issuing continue and then setting it
            # because a) we could miss the breakpoint address in the time between when the target
            # continues and we set the breakpoint, and b) also the target has to be stopped for us to
            # set breakpoints.
            logging.getLogger(__name__).debug("stepping before re-setting saved breakpoint")
            # cmd_step will re-set the saved breakpoint as part of its logic, so no need to do it here
            self.cmd_step()

        # Make sure the event loop isn't executing - there's a slight race condition between
        # when the event is queued and when the event loop picks it up. Hopefully this isn't
        # a problem.
        if is_main_thread:
            self._event_lock.acquire()

        self._rsp_lock.acquire()
        self._target_is_stopped = False
        logging.getLogger(__name__).debug("Sending continue cmd")
        self._rsp.send(b'vCont;c')
        logging.getLogger(__name__).debug("Sent continue cmd")
        self._rsp_lock.release()

        if is_main_thread:
            self._event_lock.release()

    def cmd_stop(self):
        self._user_stopped = True

        # If the target is already stopped, don't send a packet. vCtrlC receives an empty packet
        # as a reply from QEMU when the target is already stopped, but receives no reply if it is
        # running. This is actually annoyingly difficult to handle without causing delays, so we
        # just keep track of whether the target is running so we can avoid it.
        if self._target_is_stopped:
            return

        self._event_lock.acquire()
        self._rsp_lock.acquire()
        self._target_is_stopped = True
        self._rsp.send(b'vCtrlC')

        # TODO: Check for an error, and unset _user_stopped if it seems like the target didn't
        # actually stop.
        self._rsp_lock.release()
        self._event_lock.release()

    def set_sw_breakpoint(self, addr):
        self._rsp_lock.acquire()
        self._rsp.send(b'Z0,%s,4' % hexaddr(addr))
        status = self._rsp.recv()

        logging.getLogger(__name__).debug("set_sw_breakpoint: status = %s" % status)

        if status != b'OK':
            raise RspTargetError("Unable to set SW breakpoint - target error '%s'" % status)

        self._rsp_lock.release()

    def set_hw_breakpoint(self, addr):
        self._rsp_lock.acquire()
        self._rsp.send(b'Z1,%s,0' % hexaddr(addr))
        status = self._rsp.recv()

        logging.getLogger(__name__).debug("set_hw_breakpoint: status = %s" % status)

        if status != b'OK':
            raise RspTargetError("Unable to set HW breakpoint - target error")

        self._rsp_lock.release()

    def set_write_watchpoint(self, addr, sz):
        self._rsp_lock.acquire()
        self._rsp.send(b'Z2,%s,%s' % (hexaddr(addr), str(sz).encode('utf-8')))
        self._rsp_lock.release()

    def set_read_watchpoint(self, addr, sz):
        self._rsp_lock.acquire()
        self._rsp.send(b'Z3,%s,%s' % (hexaddr(addr), str(sz).encode('utf-8')))
        self._rsp_lock.release()

    def set_access_watchpoint(self, addr, sz):
        self._rsp_lock.acquire()
        self._rsp.send(b'Z4,%s,%s' % (hexaddr(addr), str(sz).encode('utf-8')))
        self._rsp_lock.release()

    def remove_sw_breakpoint(self, addr):
        """
        Remove a software breakpoint.

        :param int addr: the address of the breakpoint
        :raises RspTargetError: if the target returns an error code
        """
        logging.getLogger(__name__).debug("rsp_target.remove_sw_breakpoint: {}".format(hex(addr)))
        self._rsp_lock.acquire()
        self._rsp.send(b'z0,%s,4' % hexaddr(addr))
        status = self._rsp.recv()
        self._rsp_lock.release()

        # If we're in a callback and we just unset the breakpoint at the current pc, we set
        # a flag so that the event loop won't reset the current breakpoint before continuing
        # target execution.
        if threading.get_ident() != self._main_thread_id and \
           threading.get_ident() != self._stop_events_thread.ident and \
           addr == self.read_register('pc'):
            self._callback_unset_bp = True

        # In keeping with gdbstubs doing more or less whatever the heck they want, if removing
        # a breakpoint results in an error from the target, it probably doesn't mean that removing
        # the breakpoint actually failed. This is... neat, to say the least.
        #
        # I found some documentation on the internet that GDB apparently just ignores errors it
        # gets from the target in basically all cases. I've made the decision to have this function
        # raise the error, but at the backends/rsp.py interface I have it ignore the error. This makes
        # it easy to propagate the errors up later if that seems wise.
        # 
        # If this becomes onerous, it's fine to just choose to ignore the error here. There are plenty
        # of places in RspTarget where we *could* look for error codes and we don't, anyway.

        if status and chr(status[0]) == 'E':
            raise RspTargetError("Unable to remove software breakpoint: %s" % status)

    def remove_hw_breakpoint(self, addr):
        self._rsp_lock.acquire()
        self._rsp.send(b'z1,%s,0' % hexaddr(addr))
        self._rsp_lock.release()

    def remove_write_watchpoint(self, addr, sz):
        self._rsp_lock.acquire()
        self._rsp.send(b'z2,%s,%s' % (hexaddr(addr), str(sz).encode('utf-8')))
        self._rsp_lock.release()

    def remove_read_watchpoint(self, addr, sz):
        self._rsp_lock.acquire()
        self._rsp.send(b'z3,%s,%s' % (hexaddr(addr), str(sz).encode('utf-8')))
        self._rsp_lock.release()

    def remove_access_watchpoint(self, addr, sz):
        self._rsp_lock.acquire()
        self._rsp.send(b'z4,%s,%s' % (hexaddr(addr), str(sz).encode('utf-8')))
        self._rsp_lock.release()

    def close(self):
        """
        Close the RSP connection and kill all threads. Note that this can only be called by the
        main thread, not callbacks.
        """
        if threading.get_ident() != self._main_thread_id:
            # XXX It might be nice to allow the user to call close() from their own threads, as
            # long as they're not callbacks. But I'm not sure how we do this, because I'm not
            # sure how we can join/kill the main thread, and I'm also not sure that's the reason
            # that close() hangs when called from callbacks...
            raise RspTargetError("Cannot call close() from callbacks or any thread other than the main user thread.")

        self._shutdown_flag = True
        self._stop_events_thread.join()
        self.cmd_stop()
        self._detach()
        self._rsp.close()

    def _detach(self):
        self._rsp_lock.acquire()
        self._rsp.send(b'D;1')
        self._rsp.recv(timeout=1)  # Reply should be 'OK' -- XXX do we care? Use timeout at least.
        self._rsp_lock.release()

    def _get_reg_layout(self):
        """
        Queries the gdbserver for the register layout of the target and stores a 
        list of (regname, regsize) tuples. This uses a list of tuples because 
        order matters - the order the registers are listed in is the order in which 
        they are represented in queries to the gdbstub to get the register values.

        This method does not properly order all of the registers. The meaning of the XML files
        and each register's associated index is an internal GDB implementation detail. To 
        support arbitrary machines, we'll have to RE how GDB maps the XML files to the register
        layout. For now... I've hardcoded the ARM register layout.

        :rtype: tuple
        :return: (register layout, register map) or None if unable to get register layout
        """

        self._rsp_lock.acquire()
        self._rsp.send(b'qXfer:features:read:target.xml:0,ffb')
        response = self._rsp.recv()
        self._rsp_lock.release()

        try:
            xml_files = _get_xml_file_names(response)
        except ET.ParseError:
            print("Unable to parse XML file names '%s' " % response)
            return None

        xml_contents = self._request_xml_files(xml_files)

        return _get_register_info(xml_contents)

    def _request_xml_files(self, xml_files):
        xml_contents = []

        # Request the xml file contents from the gdbstub. The XML files each describe a group 
        # of registers, providing their names and sizes.
        for f in xml_files:
            self._rsp_lock.acquire()
            self._rsp.send(b'qXfer:features:read:%s:0,ffb' % f.encode('utf-8'))
            response = self._rsp.recv()
            self._rsp_lock.release()

            response = response[1:]
            xml_contents.append(response)

        return xml_contents

    def _get_stop_reason(self, packet):
        """
        Determines the stop reason for packet. Assumes packet is a stop reply packet.
        :param bytes packet: stop reply packet
        :rtype: str 
        """
        stop_reason = None
        logging.getLogger(__name__).debug("_get_stop_reason")
        logging.getLogger(__name__).debug(packet)

        # Stop reply packet indicates target stopped due to a signal
        if chr(packet[0]) == 'T':
            logging.getLogger(__name__).debug("_get_stop_reason() stop is signal")
            signal_code = int(packet[1:3])
            logging.getLogger(__name__).debug("__get_stop_reason() signal code = %s" % signal_code)

            if signal_code == signals.SIGINT:
                logging.getLogger(__name__).debug("SIGINT")
            elif signal_code == signals.SIGTRAP:
                logging.getLogger(__name__).debug("SIGTRAP")
                # Request the stop reason from the target
                self._rsp_lock.acquire()
                self._rsp.send(b'?')
                logging.getLogger(__name__).debug("Getting reason response...")
                stop_reason_packet = self._rsp.stop_queue.get()
                logging.getLogger(__name__).debug("Got response.")
                self._rsp_lock.release()

                # Assume the reply is TXXthread:nn again and get XX
                signal_code = int(stop_reason_packet[1:3])
                logging.getLogger(__name__).debug(signal_code)
                stop_reason = _decode_stop_reason(signal_code)
                logging.getLogger(__name__).debug(stop_reason)

        return stop_reason


def _get_xml_file_names(response):
    """
    Extract the XML file names from a binary string

    :param bytes response: The string to extract XML file names from
    """
    xml_files = []

    # ElementTree doesn't like unbound prefix tags, i.e. 'xi:include' in this xml. The quick 
    # and dirty way to get around this is to remove the suffix and just make the prefix the 
    # tag. This might be brittle. The list slicing is to remove the response code from the packet.
    response = response[1:].replace(b':include', b'')
    root = ET.fromstring(response)

    # Parse out the xml file names from the response
    for child in root:
        if child.tag == 'xi':
            xml_files.append(child.attrib['href'])

    return xml_files

def _get_register_info(xml_contents):
    """
    Parse register info out of xml

    :param list xml_contents: list of xml strings
    """
    reg_layout = []
    reg_map = {}
    i = 0

    # Get the register names and sizes from the XML
    for content in xml_contents:
        root = ET.fromstring(content)

        for child in root:
            if child.tag == 'reg':
                reg_layout.append((child.attrib['name'], int(int(child.attrib['bitsize']) / 8)))
                reg_map[child.attrib['name']] = i
                i += 1

    return reg_layout, reg_map

def _decode_stop_reason(signal_code):
    stop_reason = None

    # TODO: Implement the required checks to figure out when read/write watchpoints are hit
    if signal_code == signals.SIGTRAP:
        stop_reason = StopReasons.swbreak

    return stop_reason

def _is_error_reply(packet):
    return packet and chr(packet[0]) == 'E'

