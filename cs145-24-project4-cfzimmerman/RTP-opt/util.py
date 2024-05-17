import binascii
from scapy.all import Packet, IntField
from enum import Enum


class PacketType(Enum):
    '''Maps packet variants to their numbers in the spec'''
    START = 0
    END = 1
    DATA = 2
    ACK = 3


class PacketHeader(Packet):
    name = "PacketHeader"
    fields_desc = [
        IntField("type", 0),
        IntField("seq_num", 0),
        IntField("length", 0),
        IntField("checksum", 0),
    ]

    def get_type(self) -> PacketType:
        '''Returns the enum packet type associated
        with the type number contained in this packet'''
        num = self.type
        if num == PacketType.START.value:
            return PacketType.START
        if num == PacketType.END.value:
            return PacketType.END
        if num == PacketType.DATA.value:
            return PacketType.DATA
        if num == PacketType.ACK.value:
            return PacketType.ACK
        raise Exception(f"Could not match {num} to PacketType variant")


def compute_checksum(pkt):
    return binascii.crc32(bytes(pkt)) & 0xffffffff
