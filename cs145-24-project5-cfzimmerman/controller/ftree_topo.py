from typing import List, Tuple, Dict
from math import ceil

Ip = str
Port = int
Ports = Dict[Ip, Port]
Layer = str

# Wrapper over element relations in a fat tree topology


class Topo:
    def __init__(self, k: int):
        self.HOST: Layer = "h"
        self.TOR: Layer = "t"
        self.AGG: Layer = "a"
        self.CORE: Layer = "c"

        self.k = k
        self.half_k = k // 2

        self.MIN_ID = 1
        self.HOST_CT = k * k * k // 4
        self.TOR_CT = k * k // 2
        self.AGG_CT = k * k // 2
        self.CORE_CT = k * k // 4

    # UP: Returns the TOR number the Host should link with
    def tor_from_host(self, host_num: int) -> int:
        return ceil(host_num / self.half_k)

    # UP: Returns the Aggregator numbers the TOR should link with
    def aggs_from_tor(self, tor_num) -> List[int]:
        base: int = ((tor_num - 1) // self.half_k) * self.half_k
        return [base + num for num in range(1, self.half_k + 1)]

    # UP: Returns the Core numbers the Aggregator should link with
    def cores_from_agg(self, agg_num) -> List[int]:
        group: int = (agg_num - 1) % self.half_k
        base: int = 1 + (group * self.half_k)
        return [core for core in range(base, base + self.half_k)]

    # DOWN: Returns the Host numbers a TOR should link with
    def hosts_from_tor(self, tor_num: int) -> List[int]:
        right_host: int = tor_num * self.half_k
        return [host for host in range(right_host,
                                       right_host - self.half_k, -1)]

    # DOWN: Returns the TOR numbers an aggregator should link with
    def tors_from_agg(self, agg_num: int) -> List[int]:
        pod: int = ceil(agg_num / self.half_k)
        right_tor: int = pod * self.half_k
        return [tor for tor in range(right_tor, right_tor - self.half_k, -1)]

    # DOWN: Returns the Aggregator numbers a core should link with
    def aggs_from_core(self, core_num: int) -> List[int]:
        group: int = ceil(core_num / self.half_k)
        return [agg for agg in range(group, (self.half_k * self.k) + 1,
                                     self.half_k)]

    # Returns the topology name of a host node
    def host_name(self, host_num: int) -> str:
        return "{}{}".format(self.HOST, host_num)

    # Returns the topology name of a TOR switch
    def tor_name(self, tor_num: int) -> str:
        return "{}{}".format(self.TOR, tor_num)

    # Returns the topology name of an aggregator switch
    def agg_name(self, agg_num: int) -> str:
        return "{}{}".format(self.AGG, agg_num)

    # Returns the topology name of a core switch
    def core_name(self, core_num: int) -> str:
        return "{}{}".format(self.CORE, core_num)

    # Returns the split ID of a node in the topology.
    #
    # Ex: id_node("t7") yields (self.TOR, 7)
    def id_node(self, name: str) -> Tuple[str, int]:
        tp = name[0]
        num = int(name[1:])

        if tp == self.HOST:
            return (self.HOST, num)
        if tp == self.TOR:
            return (self.TOR, num)
        if tp == self.AGG:
            return (self.AGG, num)
        if tp == self.CORE:
            return (self.CORE, num)
        raise Exception("Failed to parse into node tuple: ", name)

    # Returns the maximum hash value this many ports will be modded by
    def get_max_hash(self, num_ports: int) -> int:
        return num_ports * num_ports * 10

    # Returns the id ecmp group of the given topology type.
    def get_ecmp_group(self, layer: Layer) -> int:
        if layer == self.HOST:
            return 0
        if layer == self.TOR:
            return 1
        if layer == self.AGG:
            return 2
        if layer == self.CORE:
            return 3
        raise Exception("Failed to parse layer: ", layer)

    # Returns the ip address of the given host
    def host_ip(self, host: int) -> Ip:
        third = (host >> 16) % 256
        second = (host >> 8) % 256
        first = host % 256
        return "10.{}.{}.{}/32".format(third, second, first)

    # Returns the port assignments for this TOR. Dict is [id, portno]

    def tor_ports(self, tor: int) -> Ports:
        ports: Dict[str, int] = {}
        port = 1

        hosts = self.hosts_from_tor(tor)
        hosts.sort()
        for host in hosts:
            ports[self.host_name(host)] = port
            port += 1

        aggs = self.aggs_from_tor(tor)
        aggs.sort()
        for agg in aggs:
            ports[self.agg_name(agg)] = port
            port += 1

        assert port == self.k + 1
        assert len(ports) == self.k
        return ports

    # Returns the port assignments for this Aggregator.
    def agg_ports(self, agg: int) -> Ports:
        ports: Dict[str, int] = {}
        port = 1

        cores = self.cores_from_agg(agg)
        cores.sort()
        for core in cores:
            ports[self.core_name(core)] = port
            port += 1

        tors = self.tors_from_agg(agg)
        tors.sort()
        for tor in tors:
            ports[self.tor_name(tor)] = port
            port += 1

        assert port == self.k + 1
        assert len(ports) == self.k
        return ports

    # Returns the port assignments for this Core.
    def core_ports(self, core: int) -> Ports:
        ports: Dict[str, int] = {}
        port = 1

        aggs = self.aggs_from_core(core)
        aggs.sort()
        for agg in aggs:
            ports[self.agg_name(agg)] = port
            port += 1

        assert port == self.k + 1
        assert len(ports) == self.k
        return ports
