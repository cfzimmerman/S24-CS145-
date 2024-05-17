###############################################################################
# sender.py
###############################################################################

import sys
import socket
import time
from collections import deque
from util import compute_checksum, PacketHeader, PacketType
from typing import Deque, Optional, Dict, Union


class InFlightPacket:
    """Creates a simple wrapper over data that's been sent but
    not yet acknowledged. `resend_after_sec` is purely for the timer.
    This class makes no network requests"""

    def __init__(self, payload: bytes, resend_after_sec: float):
        self.payload = payload
        self.__timeout_sec = resend_after_sec
        self.__sent_at = time.monotonic()

    def should_resend(self) -> bool:
        '''Returns whether the given timeout number of seconds has elapsed
        since the tracker was last reset'''

        return time.monotonic() - self.__sent_at > self.__timeout_sec

    def reset_timer(self):
        '''Resets the send timer to right now'''

        self.__sent_at = time.monotonic()


class RtpSender:
    '''A one-way interface for connecting to an RtpReceiver and
    transmitting a steady, ordered stream of packets.'''

    HEADER_LEN = 16
    TIMEOUT_SEC = 0.5
    PAYLOAD_MAX_BYTES = 1472 - HEADER_LEN - 16  # the 16 is arbitrary padding

    def __init__(self, window_size: int, receiver_ip: str, receiver_port: int):
        # configures the maximum number of packets that will ever be in flight
        self.__window_size = window_size
        # the target this RtpSender will send messages to
        self.__receiver = (receiver_ip, receiver_port)
        # tracks the sequence number of the next packet to be sent
        self.__curr_seqno = 0

        # holds all pending packets yet to be sent
        self.__send_queue: Deque[bytes] = deque()
        # Tracks the packets sent but not yet acknowledged.
        self.__in_flight: Dict[int, InFlightPacket] = {}
        # an open device socket used for RTP I/O
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__socket.settimeout(self.TIMEOUT_SEC)

    def connect(self) -> None:
        '''Connects the RTP client to the given ip and port.
        Blocking function returns once the connection is established.
        Raises a timeout exception if the client is not available within
        TIMEOUT_SEC seconds. '''

        assert (self.__curr_seqno == 0)
        while True:
            self.__send_pkt_unchecked(
                pkt_type=PacketType.START,
                payload=bytes(0),
                seqno=self.__curr_seqno
            )

            try:
                hdr = self.__await_ack()
                if hdr is None:
                    continue
                if (hdr.get_type() == PacketType.ACK):
                    self.__curr_seqno = 1
                    return
            except socket.timeout:
                continue

    def send(self, payload: Union[bytes, str]) -> None:
        '''Sends the payload to the connected receiver'''

        start = 0
        while True:
            # add packet-sized chunks to the send queue
            excl_end = min(start + self.PAYLOAD_MAX_BYTES + 1, len(payload))
            if start == excl_end:
                break
            self.__send_queue.append(payload[start:excl_end])
            start = excl_end
        self.__manage_window()

    def close(self):
        '''Processes any buffered data and then requests to close
        the connection. Forcibly exits after TIMEOUT_SEC if the
        receiver fails to acknowledge the END request.'''

        self.__manage_window()

        ending_seqno = self.__curr_seqno
        self.__send_pkt_unchecked(
            pkt_type=PacketType.END, payload=bytes(0), seqno=ending_seqno)
        self.__curr_seqno += 1

        while True:
            ack = None
            try:
                ack = self.__await_ack()
            except socket.timeout:
                break
            if ack is not None and ack.seq_num == ending_seqno:
                break
        self.__socket.close()

    def __manage_window(self):
        """Sends packets until all data requested to be sent has been
        transmitted and acknowledged"""

        while 0 < len(self.__send_queue) + len(self.__in_flight):
            while (0 < len(self.__send_queue) and
                   len(self.__in_flight) < self.__window_size):
                payload = self.__send_queue.popleft()
                self.__send_pkt_unchecked(
                    PacketType.DATA, payload, self.__curr_seqno)
                assert self.__curr_seqno not in self.__in_flight
                self.__in_flight[self.__curr_seqno] = InFlightPacket(
                    payload, self.TIMEOUT_SEC)
                self.__curr_seqno += 1

            ack = None
            try:
                ack = self.__await_ack()
            except socket.timeout:
                # resend everything in the window that has been delayed
                # more than TIMEOUT_SEC
                for seqno, tracker in self.__in_flight.items():
                    if tracker.should_resend():
                        self.__send_pkt_unchecked(
                            PacketType.DATA, tracker.payload, seqno)
                        tracker.reset_timer()
                continue

            if ack is None:
                # ack was corrupted, ignore it
                continue

            self.__in_flight.pop(ack.seq_num, None)

    def __send_pkt_unchecked(
        self,
        pkt_type: PacketType,
        payload: bytes,
        seqno: int
    ):
        '''Sends the payload of sequence number into the socket. Does not
        handle any reliability or consider any sender invariants.'''

        header = PacketHeader(
            type=pkt_type.value, seq_num=seqno, length=len(payload))

        body = header if len(payload) == 0 else header / payload
        header.checksum = compute_checksum(body)
        pkt = header if len(payload) == 0 else header / payload
        self.__socket.sendto(bytes(pkt), self.__receiver)

    def __await_ack(self) -> Optional[PacketHeader]:
        '''Makes a blocking read on the socket. Since the RtpSender
        only expects to receive ack messages, receiving a non-ack or
        corrupted message causes the funciton to return None.
        Panics if the socket timeout is exceeded.'''

        pkt, address = self.__socket.recvfrom(self.HEADER_LEN)
        # we only expect to receive ACKs from the receiver
        # ACKs have no payload and are just the size of the header
        header = PacketHeader(pkt)
        pkt_checksum = header.checksum
        header.checksum = 0
        if compute_checksum(header) != pkt_checksum:
            return None

        return header


def main():
    if len(sys.argv) != 4:
        sys.exit(
            "Usage: python sender.py [Receiver IP] \
            [Receiver Port] [Window Size] < [message]")
    receiver_ip = sys.argv[1]
    receiver_port = int(sys.argv[2])
    window_size = int(sys.argv[3])
    msg = sys.stdin.read()

    sender = RtpSender(window_size, receiver_ip, receiver_port)
    sender.connect()
    sender.send(msg)
    sender.close()


if __name__ == "__main__":
    main()
