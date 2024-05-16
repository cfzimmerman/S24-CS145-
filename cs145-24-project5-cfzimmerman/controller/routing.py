from math import ceil
from typing import List, Tuple, Set
from ftree_topo import Topo, Ports, Port, Ip, Layer


Routes = List[Tuple[Ip, Layer, List[Port]]]


def all_tp_ports(topo: Topo, ports: Ports, target_tp: str) -> List[Port]:
    # Returns all ports of a target type from the given node
    res: List[int] = []
    for dest in ports:
        (tp, _) = topo.id_node(dest)
        if tp == target_tp:
            res.append(ports[dest])
    assert len(res) > 0
    return res


class MultiCoreRoutes:
    # Returns a list of all Ip, port tuples needed to construct
    # the routing tree for the given switch.
    @staticmethod
    def get_routes(topo: Topo, sw_name: str) -> Routes:
        (tp, id) = topo.id_node(sw_name)
        if tp == topo.TOR:
            return MultiCoreRoutes.tor(topo, id)
        if tp == topo.AGG:
            return MultiCoreRoutes.agg(topo, id)
        if tp == topo.CORE:
            return MultiCoreRoutes.core(topo, id)
        raise Exception("Uncaught sw_name: {}".format(sw_name))

    # Returns a list of Ip, port tuples identifying the forwarding rules
    # for this TOR switch
    @staticmethod
    def tor(topo: Topo, tor_id: int) -> Routes:
        routes: Routes = []
        ports: Ports = topo.tor_ports(tor_id)

        aggs = all_tp_ports(topo, ports, topo.AGG)
        child_hosts: Set[int] = set(topo.hosts_from_tor(tor_id))
        for host in range(topo.MIN_ID, topo.MIN_ID + topo.HOST_CT):
            ip = topo.host_ip(host)
            if host in child_hosts:
                routes.append(
                    (ip, [ports[topo.host_name(host)]]))
                continue
            routes.append((ip, aggs))

        return routes

    # Returns a list of Ip, port tuples identifying the forwarding rules
    # for this Aggregator switch
    @staticmethod
    def agg(topo: Topo, agg_id: int) -> Routes:
        routes: Routes = []
        ports: Ports = topo.agg_ports(agg_id)

        hosts_in_pod: Set[int] = set()
        for tor in topo.tors_from_agg(agg_id):
            tor_port = ports[topo.tor_name(tor)]
            for host in topo.hosts_from_tor(tor):
                routes.append((topo.host_ip(host), [tor_port]))
                hosts_in_pod.add(host)

        all_cores = all_tp_ports(topo, ports, topo.CORE)
        for host in range(topo.MIN_ID, topo.MIN_ID + topo.HOST_CT):
            if host in hosts_in_pod:
                continue
            routes.append((topo.host_ip(host), all_cores))

        return routes

    # Returns a list of Ip, port tuples identifying the forwarding rules
    # for this Core switch
    @ staticmethod
    def core(topo: Topo, core_id: int) -> Routes:
        routes: Routes = []
        ports: Ports = topo.core_ports(core_id)

        aggs: List[int] = topo.aggs_from_core(core_id)
        aggs.sort()

        for host in range(topo.MIN_ID, topo.MIN_ID + topo.HOST_CT):
            pod = ceil(host / (topo.half_k ** 2))
            agg: str = topo.agg_name(aggs[pod - 1])
            routes.append((topo.host_ip(host), [ports[agg]]))

        return routes
