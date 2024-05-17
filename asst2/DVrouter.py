####################################################
# DVrouter.py
# Name: Cory Zimmerman
# HUID: 21483389
#####################################################

from copy import deepcopy
from router import Router
from packet import Packet
from json import dumps, loads


"""
Applies distance vector routing using the following rules:
- Structures:
    - Distance vectors are (address, cost) maps
    - Next-hop neighbors are stored in (port, neighbor) maps
- When a router wants to broadcast a message, send to every neighbor
  via their associated port. Before sending, each neighbor's message
  is trimmed so they don't get entries based on their own paths.
- When a new link is added, that port is initialized as a Neighbor. If
  any new or optimal paths are discovered because of this addition, the
  new distance vector is broadcasted to all neighbors.
- When a packet is received, if the update has no change or gives a cheaper
  path somewhere, apply the update and notify neighbors. Otherwise, if the
  update indicates a dropped link or increased cost, re-evaluate all paths
  currently routing through the affected port and broadcast the new DV.
- When a link is removed, remove the neighbor entry and treat the event
  like bad news, recomputing and emitting the DV.
"""


class Neighbor:
    """Tracks metadata related to a next-hop neighbor"""

    def __init__(self, addr, port, cost, dv):
        """addr: str, port: int, cost: int, dv: DistanceVector"""
        self.addr = addr
        self.port = port
        self.cost = cost
        self.dv = dv


class DVrouter(Router):
    """Distance vector routing protocol implementation."""

    # A suitable value for infinity in the tested networks
    INF = 16

    def __init__(self, addr, heartbeatTime):
        """
        addr: str, the address of this router
        heartbeatTime: how often to send out a heartbeat update
        """
        Router.__init__(self, addr)  # initialize superclass - don't remove
        self.heartbeatTime = heartbeatTime
        self.last_time = 0

        # Python3 types aren't supported by the course tests:
        # Cost = int, Addr = str, Port = int
        # DistanceVector = Dict[Addr, Cost]
        #
        # self.my_dv: DistanceVector = {addr: 0}
        # self.fwd_table: Dict[Addr, Port] = {}
        # self.neighbors: Dict[Port, Neighbor] = {}
        self.my_dv = {addr: 0}
        self.fwd_table = {}
        self.neighbors = {}

    def handleNewLink(self, port, addr, cost):
        """
        Handle new link.
        port: the port number on which the link was added.
        endpoint: the address of the other endpoint of the link.
        cost: the link cost.

        This method is called whenever a new link is added on port number port
        connecting to a router or client with address endpoint and link cost
        cost.
        """
        neighbor = Neighbor(addr, port, cost, {addr: 0})
        self.neighbors[port] = neighbor
        if self.__update_better_path(neighbor):
            self.__broadcast_dv()

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
        parsed = loads(packet.content)
        neighbor = self.neighbors[port]
        assert self.neighbors[port].addr == parsed["addr"]
        neighbor_old_dv = neighbor.dv
        neighbor.dv = parsed["dv"]

        # If a route through this neighbor is now more expensive or
        # nonexistent, then we need to recompute all routes with
        # that in mind. Without purging data related to this
        # neighbor, bad news would be incorrectly ignored by the
        # Bellman Ford inequality.
        if self.__is_bad_news(neighbor_old_dv, neighbor.dv):
            self.__wipe_port(port)
            self.__broadcast_dv()
            return

        # Otherwise, if the update prompted a positive change in the routing
        # table, share that update with neighbors.
        if self.__update_better_path(neighbor):
            self.__broadcast_dv()

    def handleRemoveLink(self, port):
        """
        Handle removed link.
        port: the port number on which the link was removed.

        This method is called when the existing link on port number
        port is disconnected.
        """
        del self.neighbors[port]
        self.__wipe_port(port)
        self.__broadcast_dv()

    def handleTime(self, timeMillisecs):
        """
        This method is called regularly for sending routing packets at
        regular intervals.
        """
        if self.last_time + self.heartbeatTime < timeMillisecs:
            self.__broadcast_dv()
            self.last_time = timeMillisecs

    def debugString(self):
        """
        This method is called by the network visualization to print current
        router details.
        Return any string that will be helpful for debugging.
        This method is for your own use and will not be graded.
        """
        return dumps({"dv": self.my_dv, "fwd": self.fwd_table}, indent=4)

    def __broadcast_dv(self):
        """
        Sends a routing payload to every next-hop
        neighbor tracked in the neighbors dict
        """
        for neighbor in self.neighbors.values():
            copied_dv = deepcopy(self.my_dv)
            # "Poison" any routes going through this neighbor
            for addr, port in self.fwd_table.items():
                if port == neighbor.port:
                    del copied_dv[addr]
            payload = dumps({
                "dv": copied_dv,
                "addr": self.addr,
            })
            packet = Packet(Packet.ROUTING, self.addr,
                            neighbor.addr, content=payload)
            self.send(neighbor.port, packet)

    def __update_better_path(self, nb):
        """Examines an incoming distance vector from a neighbor.
        If any of the neighbor's entries offers a
        better path than is currently available, update the distance
        vector and forwarding table.
        If an update occurred, returns True. Unless this is called
        in a loop, broadcast_div should be called when this returns
        True."""
        updated_my_dv = False

        for addr, cost in nb.dv.items():
            if addr not in self.my_dv:
                self.my_dv[addr] = self.INF
            proposed_cost = cost + nb.cost
            if self.my_dv[addr] <= proposed_cost:
                continue
            self.my_dv[addr] = proposed_cost
            self.fwd_table[addr] = nb.port
            # If there's no viable path, remove it.
            if self.my_dv[addr] >= self.INF:
                del self.my_dv[addr]
                del self.fwd_table[addr]
            updated_my_dv = True

        return updated_my_dv

    def __is_bad_news(self, prev_dv, new_dv):
        """
        Returns whether a distance vector update indicates an increase in
        cost or a dropped link.
        """
        for addr, cost in prev_dv.items():
            if addr not in new_dv or new_dv[addr] > prev_dv[addr]:
                return True
        return False

    def __wipe_port(self, port):
        """
        Removes all routes using this port and recomputes alternate
        routes using cached neighbor distance vectors.
        """
        for fwd_addr in list(self.fwd_table.keys()):
            if self.fwd_table[fwd_addr] == port:
                del self.fwd_table[fwd_addr]
                del self.my_dv[fwd_addr]
        for nb in self.neighbors.values():
            self.__update_better_path(nb)
