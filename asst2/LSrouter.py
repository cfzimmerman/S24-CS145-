####################################################
# LSrouter.py
# Name: Cory Zimmerman
# HUID: 21483389
# EXTRA CREDIT
#####################################################

from router import Router
from packet import Packet
from json import dumps, loads
import networkx as nx
# from typing import Dict, List, Tuple


# Port = int
# Addr = str
# Cost = int
# Time = int
# PacketId = int
# LsNeighbors = List[Tuple[Addr, Cost]]

"""
Each graph node may have the following fields:
{
    "port": int, optional,
    "last_packet_id": int, optional,
}

Each graph edge may have the following fields:
{
    "weight": int, required
}
"""


class LinkStatePayload:
    """
    Manages the link state info this router sends when it originates
    a LinkState update.
    """

    def __init__(
        self,
        source_addr,  # : Addr,
        packet_id,  # : packet_id,
        ls_neighbors  # : LsNeighbors
    ):
        self.source_addr = source_addr
        self.packet_id = packet_id
        self.ls_neighbors = ls_neighbors

    def serialize(self):  # -> str
        """
        Returns this payload as a json string
        """
        return dumps({
            "source_addr": self.source_addr,
            "packet_id": self.packet_id,
            "ls_neighbors": self.ls_neighbors
        })

    @staticmethod
    def deserialize(msg):
        """
        Builds a LinkStatePayload object from a payload json string
        """
        parsed = loads(msg)
        return LinkStatePayload(
            parsed["source_addr"],
            parsed["packet_id"],
            parsed["ls_neighbors"]
        )


class LSrouter(Router):
    """Link state routing protocol implementation."""

    # A value of infinity suitable for the tested networks
    INF = 16

    def __init__(self, addr, heartbeatTime):
        Router.__init__(self, addr)  # initialize superclass - don't remove
        self.heartbeatTime = heartbeatTime
        self.last_time = 0
        self.next_packet_id = 0

        # Tracks current understanding of all weighted edges in the network
        self.graph = nx.DiGraph()
        # Maps destination addresses to an outbound port
        # : Dict[Addr, Port]
        self.fwd_table = {}

    def handlePacket(self, port, packet):
        """
        Process incoming packet.
        port: the port number on which the packet arrived.
        packet: the received packet instance.

        This method is called whenever a packet arrives on port number port.
        Check whether the packet is a traceroute packet or a routing packet
        and handle it appropriately.
        Methods and fields of the packet class are defined in packet.py
        """
        if packet.isTraceroute():
            if packet.dstAddr in self.fwd_table:
                self.send(self.fwd_table[packet.dstAddr], packet)
            return

        assert packet.isRouting()
        ls_payload = LinkStatePayload.deserialize(packet.content)

        if (ls_payload.packet_id <=
            self.__get_last_packet_id(ls_payload.source_addr)
                or ls_payload.source_addr == self.addr):
            # Update is outdated or redundant. We're done.
            return

        self.__set_last_packet_id(
            ls_payload.source_addr, ls_payload.packet_id)

        for (dest_addr, cost) in ls_payload.ls_neighbors:
            if cost == self.INF:
                self.graph.remove_edge(ls_payload.source_addr, dest_addr)
            else:
                self.graph.add_edge(ls_payload.source_addr,
                                    dest_addr, weight=cost,
                                    last_packet_id=ls_payload.packet_id)
        self.__recompute_paths()
        # Forward the update
        for nb_addr in self.graph.neighbors(self.addr):
            nb_port = self.__get_neighbor_port(nb_addr)
            if nb_port == port:
                continue
            self.send(nb_port, packet)

    def handleNewLink(self, port, addr, cost):
        """
        Called when a new link is added for this router.
        port: the port number on which the link was added.
        endpoint: the address of the other endpoint of the link.
        cost: the link cost.
        """
        self.graph.add_node(addr, port=port)
        self.graph.add_edge(self.addr, addr, weight=cost)
        self.__recompute_paths()
        self.__broadcast_my_ls()

    def handleRemoveLink(self, port):
        """
        Handle removed link.
        port: the port number on which the link was removed.
        This method is called when the existing link on port number port is
        disconnected.
        """
        # Find the neighbor that got dropped.
        nb_addr = None
        for addr in self.graph.neighbors(self.addr):
            if port == self.__get_neighbor_port(addr):
                nb_addr = addr
                break

        assert nb_addr is not None
        # Broadcast with a cost of inf so others know to drop the
        # edge. Then actually delete it.
        self.__set_edge_cost(self.addr, nb_addr, self.INF)
        self.__broadcast_my_ls()

        self.graph.remove_edge(self.addr, nb_addr)
        self.__recompute_paths()

    def handleTime(self, timeMillisecs):
        """
        This method is called regularly for sending routing packets at
        regular intervals.
        """
        if timeMillisecs - self.last_time >= self.heartbeatTime:
            self.last_time = timeMillisecs
            self.__broadcast_my_ls()

    def debugString(self):
        """
        This method is called by the network visualization to display current
        router details
        """
        return str({
            "fwd": self.fwd_table,
            "nodes": self.graph.nodes(data=True),
            "edges": self.graph.edges(data=True)
        })

    def __broadcast_my_ls(self):
        """
        Generates a LinkStatePayload from this router's current
        state and sends an update to all neighbors.
        """
        # : LsNeighbors
        ls_neighbors = [(nb_addr, self.__get_edge_cost(self.addr, nb_addr))
                        for nb_addr in self.graph.neighbors(self.addr)]

        ls_payload_str = LinkStatePayload(
            self.addr, self.next_packet_id, ls_neighbors).serialize()
        self.next_packet_id += 1

        for nb_addr in self.graph.neighbors(self.addr):
            packet = Packet(Packet.ROUTING, self.addr,
                            nb_addr, content=ls_payload_str)
            self.send(self.__get_neighbor_port(nb_addr), packet)

    def __recompute_paths(self):
        """
        Runs Dijkstra's algorithm to compute shortest paths, and
        rewrites the forwarding table to reflect the new connectivity
        of the graph.
        """
        paths = nx.single_source_dijkstra_path(self.graph, self.addr)
        new_fwd = {}
        for addr, path in paths.items():
            if len(path) < 2:
                continue
            next_hop = path[1]
            new_fwd[addr] = self.__get_neighbor_port(next_hop)
        self.fwd_table = new_fwd

    def __get_edge_cost(self, e_start, e_end):
        """
        Retrieves the cost of the edge between e_start and e_end
        from the graph. Panics if the edge is not present or
        no cost is set.
        """
        return self.graph.edges[e_start, e_end]["weight"]

    def __set_edge_cost(self, e_start, e_end, cost):
        """
        Sets the cost of an edge between e_start and e_end
        """
        nx.set_edge_attributes(
            self.graph, {(e_start, e_end): {"weight": cost}})

    def __get_neighbor_port(self, nb_addr):
        """
        Retrieves the port between self and neighbor. Panics
        if the port has not been set.
        """
        return self.graph.nodes[nb_addr]["port"]

    def __get_last_packet_id(self, addr):
        """
        Returns the last packet id if one exists. Else, -1.
        """
        if not self.graph.has_node(addr):
            return -1
        return self.graph.nodes[addr].get("last_packet_id", -1)

    def __set_last_packet_id(self, addr, packet_id):
        """
        Sets the given packet id to the node at addr.
        """
        if not self.graph.has_node(addr):
            self.graph.add_node(addr)
        self.graph.nodes[addr]["last_packet_id"] = packet_id
