import socket
import random
import sys
import time
import signal
from scapy.all import Packet
from scapy.all import IntField

""" Implemented in Python 3.7.2 """
""" Usage: python3 proxy <sender addr> <sender port> <receiver addr> <receiver port> <error type>"""

class PacketHeader(Packet):
    name = "PacketHeader"
    fields_desc = [
        IntField("type", 0),
        IntField("seq_num", 0),
        IntField("length", 0),
        IntField("checksum", 0),
    ]
def get_seq_num(pkt):
    if len(pkt) > 1500:
        print ('Error! Packet size exceeds 1500')
    pkt_header = PacketHeader(pkt[:16])
    type = 'START/END'
    if pkt_header.type == 2:
        type = 'DATA'
    elif pkt_header.type == 3:
        type = 'ACK'
    return (type, pkt_header.seq_num)

def main():
    bind_addr = sys.argv[1]
    bind_port = int(sys.argv[2])
    receiver_addr = sys.argv[3]
    receiver_port = int(sys.argv[4])
    sender_addr = sys.argv[1]
    sender_port = [0]
    options = sys.argv[5] #error types
    start_stage = 0

    def run(from_addr, from_port, from_socket, to_addr, to_port, to_socket, start_stage):
        def delay():
            """ Delay a packet by 0.02 seconds. """
            pkt, address = from_socket.recvfrom(2048)
            print ("Got it: Delay. %s: %d" % get_seq_num(pkt))
            time.sleep(0.4)
            to_socket.sendto(pkt, (to_addr, to_port))
            pass

        def reorder():
            """ Take in 6 packets, reorder them, and send them out. """
            num = 6 # Take in 6 packets.
            packet_list = []

            for i in range(0, num):
                try:
                    pkt, address = from_socket.recvfrom(2048)
                    print ("Got it: Reorder. %s: %d" % get_seq_num(pkt))
                    packet_list.append(pkt)
                except socket.error:
                    break

            random.shuffle(packet_list)

            for pkt in packet_list:
                to_socket.sendto(pkt, (to_addr, to_port))
            pass

        def drop():
            """ Drop the next available packet. """
            pkt, address = from_socket.recvfrom(2048)
            print ("Got it: Drop. %s: %d" % get_seq_num(pkt))
            return

        def jam():
            """ Randomly change a character from the packet to a. """
            pkt, address = from_socket.recvfrom(2048)
            i = random.randint(0, len(pkt) - 1)
            pkt = pkt[:i] + b'a' + pkt[i:]
            print ("Got it: Jam. %s: %d" % get_seq_num(pkt))
            to_socket.sendto(pkt, (to_addr, to_port))
            pass

        if start_stage < 10 or random.randint(1, 100) > 20:
            pkt, address = from_socket.recvfrom(2048, socket.MSG_DONTWAIT)
            if address[1] != receiver_port and address[1] != bind_port:
                sender_port.pop(0)
                sender_port.append(address[1])
            print ("Got it: No messing. %s: %d" % get_seq_num(pkt))

            to_socket.sendto(pkt, (to_addr, to_port))
        else:
            # Different ways of messing up the transmission.
            mode = int(options[random.randint(1, len(options)) - 1])
            if mode == 1:
                delay()
            elif mode == 3:
                drop()
            elif mode == 2:
                reorder()
            else:
                jam()

    sender_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receiver_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    sender_socket.settimeout(0.1)   # Socket will only block for 0.1 seconds.
    receiver_socket.settimeout(0.1) # Socket will only block for 0.1 seconds.

    sender_socket.bind((bind_addr, bind_port))

    while True:
        # The proxy alternatively forwards messages from sender to receiver and from receiver to sender. Each
        # turn transmits at most 5 packets.
        try:
            for i in range(0, 5):
                run(sender_addr, sender_port, sender_socket, receiver_addr, receiver_port, receiver_socket, start_stage)
                start_stage = start_stage + 1
        except socket.error:
            pass

        try:
            for i in range(0, 5):
                run(receiver_addr, receiver_port, receiver_socket, sender_addr, sender_port[0], sender_socket, start_stage)
                start_stage = start_stage + 1
        except socket.error:
            pass

if __name__ == "__main__":
    main()
