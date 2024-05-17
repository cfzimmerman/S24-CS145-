###############################################################################
# receiver.py
###############################################################################

import sys
import socket
from util import compute_checksum, PacketHeader, PacketType
from typing import Tuple, Optional, List
from heapq import heappush, heappop, heapify

IpV4Addr = Tuple[str, int]


class PktFromSender:
    '''Wrapper over the info contained in a sender message'''

    def __init__(self, header: PacketHeader, addr: IpV4Addr, payload: bytes):
        self.header = header
        self.addr = addr
        self.payload = payload


class RtpReceiver:
    '''A one-way interface for connecting to an RtpSender and
    receiving a steady, ordered stream of packets.'''

    def __init__(self, window_size: int, listen_ip: str, listen_port: int):
        '''Instantiation blocks until the connection has been established'''

        assert window_size > 0

        self.__window_size = window_size
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__socket.bind((listen_ip, listen_port))

        self.__next_seqno = 0
        # buffer is a min heap indexed by next_seqno
        self.__buffer: List[Tuple[int, PktFromSender]] = []

        # loop and block until handshaking the sender
        while True:
            pkt = self.__receive_pkt()
            if pkt is None:
                # drop packets that are corrupted
                continue
            if pkt.header.get_type() != PacketType.START:
                # ignore inbound packets until we get one that's a handshake
                continue
            assert (pkt.header.seq_num == 0)
            self.__next_seqno = 1
            self.__send_ack(pkt.addr, self.__next_seqno)
            return

    def __buffer_contains(self, seqno: int) -> bool:
        '''Scans the buffer, and returns true if an entry with
        this seqno already exists.'''

        for mem in self.__buffer:
            if mem[0] == seqno:
                return True
        return False

    def pipe(self, file):
        '''Listens to the connection, writing in-order output to the
        given file until the sender closes the connection'''

        while True:
            pkt = self.__receive_pkt()
            if pkt is None:
                # don't bother with corrupted packets
                continue

            if not self.__buffer_contains(pkt.header.seq_num):
                heappush(self.__buffer, (pkt.header.seq_num, pkt))

            while (0 < len(self.__buffer) and
                    self.__buffer[0][0] <= self.__next_seqno):
                (seqno, buffered) = heappop(self.__buffer)
                assert (seqno == buffered.header.seq_num)

                if seqno == self.__next_seqno:
                    self.__next_seqno += 1
                    if buffered.header.get_type() == PacketType.DATA:
                        txt = buffered.payload.decode('utf-8')
                        file.write(txt)
                        # I'm aware that flushing after every write is a crime,
                        # but lost sender END messages cause pipe to not exit
                        # until the process dies, which drops data. This
                        # guarantees correctness in test cases at the cost of
                        # performance.
                        sys.stdout.flush()

                self.__send_ack(buffered.addr, self.__next_seqno)
                if buffered.header.get_type() == PacketType.END:
                    # in the current setup, END should always be the last
                    # message sent.
                    assert (len(self.__buffer) == 0)
                    return

            # ensure we're only ever buffering window_size many packets
            buffer_overreach = len(self.__buffer) - self.__window_size
            if buffer_overreach > 0:
                del self.__buffer[-buffer_overreach:]
                assert (len(self.__buffer) == self.__window_size)
                heapify(self.__buffer)

    def __send_ack(self, addr: IpV4Addr, seqno: int):
        '''Sends an acknowledgement of packet seqno to addr'''

        header = PacketHeader(
            type=PacketType.ACK.value, seq_num=seqno, length=0)
        header.checksum = compute_checksum(header)
        self.__socket.sendto(bytes(header), addr)

    def __receive_pkt(self) -> Optional[PktFromSender]:
        '''Blocking reads from the socket, returning the output
        as a PktFromSender object. Returns None if the inbound
        data was corrupted.'''

        pkt, address = self.__socket.recvfrom(2048)
        header = PacketHeader(pkt[:16])
        msg = pkt[16:16 + header.length]

        pkt_checksum = header.checksum
        header.checksum = 0
        if compute_checksum(header / msg) != pkt_checksum:
            return None

        return PktFromSender(header, address, msg)


def main():
    if len(sys.argv) != 3:
        sys.exit("Usage: python receiver.py [Receiver Port] [Window Size]")
    receiver_port = int(sys.argv[1])
    window_size = int(sys.argv[2])

    receiver = RtpReceiver(window_size, '127.0.0.1', receiver_port)
    receiver.pipe(sys.stdout)
    sys.stdout.flush()


if __name__ == "__main__":
    main()
