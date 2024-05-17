/*

Summary: this module does L3 forwarding. For more info on this module, read the project README.

*/

/* -*- P4_16 -*- */
#include <core.p4>
#include <v1model.p4>

#define IP_UDP 0x06
#define IP_TCP 0x11

/*

Summary: The following section defines the protocol headers used by packets. 
These include the IPv4, TCP, and Ethernet headers. A header declaration in P4 
includes all the field names (in order) together with the size (in bits) of each 
field. Metadata is similar to a header but only holds meaning during switch processing.
It is only part of the packet while the packet is in the switch pipeline and is 
removed when the packet exits the switch.

*/


/*************************************************************************
*********************** H E A D E R S  ***********************************
*************************************************************************/

const bit<16> TYPE_IPV4 = 0x800;

typedef bit<9>  egressSpec_t;
typedef bit<48> macAddr_t;
typedef bit<32> ip4Addr_t;


header ethernet_t {
    macAddr_t dstAddr;
    macAddr_t srcAddr;
    bit<16>   etherType;
}

header ipv4_t {
    bit<4>    version;
    bit<4>    ihl;
    bit<6>    dscp;
    bit<2>    ecn;
    bit<16>   totalLen;
    bit<16>   identification;
    bit<3>    flags;
    bit<13>   fragOffset;
    bit<8>    ttl;
    bit<8>    protocol;
    bit<16>   hdrChecksum;
    ip4Addr_t srcAddr;
    ip4Addr_t dstAddr;
}

header tcp_t {
    bit<16> srcPort;
    bit<16> dstPort;
    bit<32> seqNo;
    bit<32> ackNo;
    bit<4>  dataOffset;
    bit<4>  res;
    bit<1>  cwr;
    bit<1>  ece;
    bit<1>  urg;
    bit<1>  ack;
    bit<1>  psh;
    bit<1>  rst;
    bit<1>  syn;
    bit<1>  fin;
    bit<16> window;
    bit<16> checksum;
    bit<16> urgentPtr;
}

header udp_t {
    bit<16> srcPort;
    bit<16> dstPort;
    bit<16> len;
    bit<16> checksum;
}

struct headers {
    ethernet_t   ethernet;
    ipv4_t       ipv4;
    tcp_t        tcp;
    udp_t        udp;
}

struct metadata {
    bit<14>  ecmp_hash;
    bit<14>  ecmp_group_id;
    bit<1>   multi_port;

    // Either the tcp or udp handlers will fill these.
    // The hash function will use them.
    bit<16> srcPort;
    bit<16> dstPort;
}

/*

Summary: the following section defines logic required to parse a packet's headers. 
Packets need to be parsed in the same order they are added to a packet. See 
headers.p4 to see header declarations. Deparsing can be thought of as stitching 
the headers back into the packet before it leaves the switch. Headers need to be 
deparsed in the same order they were parsed.

*/

/*************************************************************************
*********************** P A R S E R  *******************************
*************************************************************************/

parser MyParser(packet_in packet,
                out headers hdr,
                inout metadata meta,
                inout standard_metadata_t standard_metadata) {
    state start {
        packet.extract(hdr.ethernet);
        packet.extract(hdr.ipv4);
        
        meta.ecmp_hash = 0;
        meta.ecmp_group_id = 0;
        meta.multi_port = 0;

        transition select(hdr.ipv4.protocol) {
            IP_TCP: parse_tcp;
            IP_UDP: parse_udp;
            default: accept;
        }
    }

    state parse_tcp {
        packet.extract(hdr.tcp);
        hdr.tcp.setValid();
        hdr.udp.setInvalid();
        meta.srcPort = hdr.tcp.srcPort; 
        meta.dstPort = hdr.tcp.dstPort;
        transition accept;
    }

    state parse_udp {
        packet.extract(hdr.udp);
        hdr.udp.setValid();
        hdr.tcp.setInvalid();
        meta.srcPort = hdr.udp.srcPort; 
        meta.dstPort = hdr.udp.dstPort;
        transition accept;
    }
}

/*************************************************************************
***********************  D E P A R S E R  *******************************
*************************************************************************/

control MyDeparser(packet_out packet, in headers hdr) {
    apply {
        packet.emit(hdr.ethernet);
        packet.emit(hdr.ipv4);
        // only one of these should be marked valid
        packet.emit(hdr.tcp);
        packet.emit(hdr.udp);
    }
}


/*************************************************************************
************   C H E C K S U M    V E R I F I C A T I O N   *************
*************************************************************************/

control MyVerifyChecksum(inout headers hdr, inout metadata meta) {
    apply {  }
}


/*************************************************************************
**************  I N G R E S S   P R O C E S S I N G   *******************
*************************************************************************/

control MyIngress(inout headers hdr,
                  inout metadata meta,
                  inout standard_metadata_t standard_metadata) {

    // ECMP Only
    // ecmp_group_id: ecmp group ID for this switch, specified by controller
    // num_nhops: the number of total output ports, specified by controller
    action ecmp_group(bit<14> ecmp_group_id, bit<16> num_nhops) {
        hash(meta.ecmp_hash,
            HashAlgorithm.crc16,
            (bit<1>) 0,
            {
                hdr.ipv4.srcAddr,
                hdr.ipv4.dstAddr,
                hdr.ipv4.protocol,
                // these are either from TCP or UDP and are provided
                // at the parsing stage
                meta.srcPort,
                meta.dstPort
            },
            // this is the number of hashed values mapped to ports
            num_nhops * num_nhops * 10
        );
        meta.multi_port = 1;
        meta.ecmp_group_id = ecmp_group_id;
    }

    // dropped packets will not get forwarded
    action drop() {
        mark_to_drop(standard_metadata);
    }

    // set next hop
    // port: the egress port for this packet
    action set_nhop(egressSpec_t egress_port) {
        standard_metadata.egress_spec = egress_port;
    }

    // For Task 1, this table maps dstAddr to the set_nhop action (essentially just mapping dstAddr to an output port)
    // For ECMP, this table maps dstAddr to either the set_nhop action or the ecmp_group action. 
    // The action ecmp_group is actually calculating the hash value and kicking off ecmp logic
    table ipv4_lpm {
        key = {
            hdr.ipv4.dstAddr: lpm;
        }

        actions = {
            set_nhop;
            ecmp_group;
            drop;
            NoAction;
        }

        size = 256;
        default_action = NoAction;
    }

    // This table matches hash values to ports. My controller
    // installs mappings randomly across equal paths.
    table ecmp_group_to_nhop {
        key = {
            meta.ecmp_hash: exact;
            meta.ecmp_group_id: exact;
        }

        actions = {
            set_nhop;
            drop;
            NoAction;
        }

        size = 256;
        default_action = NoAction;
    }

    apply {
        // If only a single route is available, ipv4_lpm will find the
        // next hop. Otherwise, a hash will be computed, and
        // ecmp_group_to_nhop will map that hash to a port for this
        // ecmp group.
        ipv4_lpm.apply();
        if (meta.multi_port == 1) {
            ecmp_group_to_nhop.apply();
        }
    }
}

/*************************************************************************
****************  E G R E S S   P R O C E S S I N G   *******************
*************************************************************************/

control MyEgress(inout headers hdr,
                 inout metadata meta,
                 inout standard_metadata_t standard_metadata) {
    apply {  }
}

/*************************************************************************
*************   C H E C K S U M    C O M P U T A T I O N   **************
*************************************************************************/

control MyComputeChecksum(inout headers hdr, inout metadata meta) {
    apply {
    update_checksum(
	    hdr.ipv4.isValid(),
            { hdr.ipv4.version,
	          hdr.ipv4.ihl,
              hdr.ipv4.dscp,
              hdr.ipv4.ecn,
              hdr.ipv4.totalLen,
              hdr.ipv4.identification,
              hdr.ipv4.flags,
              hdr.ipv4.fragOffset,
              hdr.ipv4.ttl,
              hdr.ipv4.protocol,
              hdr.ipv4.srcAddr,
              hdr.ipv4.dstAddr },
              hdr.ipv4.hdrChecksum,
              HashAlgorithm.csum16);    
    }
}

/*************************************************************************
***********************  S W I T C H  *******************************
*************************************************************************/

//switch architecture
V1Switch(
MyParser(),
MyVerifyChecksum(),
MyIngress(),
MyEgress(),
MyComputeChecksum(),
MyDeparser()
) main;
