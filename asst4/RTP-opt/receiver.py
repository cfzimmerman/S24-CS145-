###############################################################################
# receiver.py
###############################################################################

import sys
import socket
from util import compute_checksum, PacketHeader, PacketType
from typing import Tuple, Optional, List
from heapq import heappush, heappop

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
        # buffer is a min heap indexed by seqno
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
            self.__send_ack(pkt.addr, 0)
            self.__next_seqno = 1
            return

    def pipe(self, file):
        '''Listens to the connection, writing in-order output to the
        given file until the sender closes the connection'''

        while True:
            pkt = self.__receive_pkt()
            if pkt is None:
                # don't bother with corrupted packets
                continue
            if (pkt.header.seq_num < self.__next_seqno + self.__window_size and
                    not self.__buffer_contains(pkt.header.seq_num)):
                # avoid pushing packets that might get acknowledged and then
                # later evicted from the buffer because a smaller seqno packet
                # took its place.
                heappush(self.__buffer, (pkt.header.seq_num, pkt))

            while (0 < len(self.__buffer) and
                   self.__buffer[0][0] <= self.__next_seqno):
                (seqno, buffered) = heappop(self.__buffer)
                assert (seqno == buffered.header.seq_num)

                self.__send_ack(addr=buffered.addr, seqno=seqno)

                if seqno == self.__next_seqno:
                    self.__next_seqno += 1
                    if buffered.header.get_type() == PacketType.DATA:
                        file.write(buffered.payload.decode('utf-8'))
                        # See RTP-base/receiver in the same place for a
                        # rationele of this.
                        sys.stdout.flush()

                if buffered.header.get_type() == PacketType.END:
                    # END should always be the last message sent.
                    assert (len(self.__buffer) == 0)
                    return

            # selective heappush should prevent buffer overreach
            assert (len(self.__buffer) <= self.__window_size)

    def __buffer_contains(self, seqno: int) -> bool:
        '''Scans the buffer, and returns true if an entry with
        this seqno already exists.'''

        for mem in self.__buffer:
            if mem[0] == seqno:
                return True
        return False

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
