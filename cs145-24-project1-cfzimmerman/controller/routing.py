import sys
import os
from math import ceil
from typing import List, Tuple, Set

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))  # noqa: E402
sys.path.insert(0, parent_dir)  # noqa: E402
from ftree_topo import Topo, Ports, Port, Dmac


Routes = List[Tuple[Dmac, Port]]


# Returns the port pointing to a node of the target type with the
# minimum address
# If skip_parity 0 or 1 is provided, odd or even ids are skipped
def min_tp_port(topo: Topo, ports: Ports, target_tp: str,
                skip_parity=2) -> Port:
    res: int | None = None
    for dest in ports:
        (tp, id) = topo.id_node(dest)
        if tp != target_tp or id % 2 == skip_parity:
            continue
        if res is None:
            res = ports[dest]
            continue
        res = min(res, ports[dest])

    assert res is not None
    return res


class OneCoreRoutes:
    # Returns a list of all DMAC, port tuples needed to construct
    # the routing tree for the given switch.
    @staticmethod
    def get_routes(topo: Topo, sw_name: str) -> Routes:
        (tp, id) = topo.id_node(sw_name)
        if tp == topo.TOR:
            return OneCoreRoutes.tor(topo, id)
        if tp == topo.AGG:
            return OneCoreRoutes.agg(topo, id)
        if tp == topo.CORE:
            return OneCoreRoutes.core(topo, id)
        raise Exception("Uncaught sw_name: {}".format(sw_name))

    # Returns a list of DMAC, port tuples identifying the forwarding rules
    # for this TOR switch
    @staticmethod
    def tor(topo: Topo, tor_id: int) -> Routes:
        routes: Routes = []
        ports: Ports = topo.tor_ports(tor_id)
        left_agg = min_tp_port(topo, ports, topo.AGG)

        child_hosts: Set[int] = set(topo.hosts_from_tor(tor_id))
        for host in range(topo.MIN_ID, topo.MIN_ID + topo.HOST_CT):
            dmac = topo.host_dmac(host)
            if host in child_hosts:
                routes.append(
                    (dmac, ports[topo.host_name(host)]))
                continue
            routes.append(
                (dmac, left_agg))

        return routes

    # Returns a list of DMAC, port tuples identifying the forwarding rules
    # for this Aggregator switch
    def agg(topo: Topo, agg_id: int) -> Routes:
        routes: Routes = []
        ports: Ports = topo.agg_ports(agg_id)
        left_core = min_tp_port(topo, ports, topo.CORE)

        added_hosts: Set[int] = set()
        for tor in topo.tors_from_agg(agg_id):
            tor_port = ports[topo.tor_name(tor)]
            for host in topo.hosts_from_tor(tor):
                routes.append((topo.host_dmac(host), tor_port))
                added_hosts.add(host)

        for host in range(topo.MIN_ID, topo.MIN_ID + topo.HOST_CT):
            if host in added_hosts:
                continue
            routes.append((topo.host_dmac(host), left_core))

        return routes

    # Returns a list of DMAC, port tuples identifying the forwarding rules
    # for this Core switch
    def core(topo: Topo, core_id: int) -> Routes:
        routes: Routes = []
        ports: Ports = topo.core_ports(core_id)

        aggs = topo.aggs_from_core(core_id)
        aggs.sort()

        host: int = 1
        for agg in aggs:
            agg_port = ports[topo.agg_name(agg)]
            for _ in range(topo.HOST_CT // topo.k):
                routes.append((topo.host_dmac(host), agg_port))
                host += 1

        return routes


class MultiCoreRoutes:
    # Returns a list of all DMAC, port tuples needed to construct
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

    # Returns a list of DMAC, port tuples identifying the forwarding rules
    # for this TOR switch
    @staticmethod
    def tor(topo: Topo, tor_id: int) -> Routes:
        return OneCoreRoutes.tor(topo, tor_id)

    # Returns a list of DMAC, port tuples identifying the forwarding rules
    # for this Aggregator switch
    @staticmethod
    def agg(topo: Topo, agg_id: int) -> Routes:
        routes: Routes = []
        ports: Ports = topo.agg_ports(agg_id)

        added_hosts: Set[int] = set()
        for tor in topo.tors_from_agg(agg_id):
            tor_port = ports[topo.tor_name(tor)]
            for host in topo.hosts_from_tor(tor):
                routes.append((topo.host_dmac(host), tor_port))
                added_hosts.add(host)

        for host in range(topo.MIN_ID, topo.MIN_ID + topo.HOST_CT):
            if host in added_hosts:
                continue
            port = min_tp_port(topo, ports, topo.CORE,
                               skip_parity=((host + 1) % 2))
            routes.append((topo.host_dmac(host), port))

        return routes

    # Returns a list of DMAC, port tuples identifying the forwarding rules
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
            routes.append((topo.host_dmac(host), ports[agg]))

        return routes

    ''' I believe these should route optimally. Unfortunately, it seems that's
    not actually what the assignment wants (as I realize after writing them 😅).


    # Returns the core group this host belongs to
    def __core_group_from_host(topo: Topo, host: int) -> int:
        pod_sz = topo.half_k ** 2
        num_in_pod = ((host - 1) % pod_sz) + 1
        return ceil(num_in_pod / topo.half_k)

    # Returns a list of DMAC, port tuples identifying the forwarding rules
    # for this TOR switch
    @staticmethod
    def tor(topo: Topo, tor_id: int) -> Routes:
        routes: Routes = []
        ports: Ports = topo.tor_ports(tor_id)

        aggs: List[int] = topo.aggs_from_tor(tor_id)
        aggs.sort()

        child_hosts: Set[int] = set(topo.hosts_from_tor(tor_id))
        for host in range(topo.MIN_ID, topo.MIN_ID + topo.HOST_CT):
            dmac = topo.host_dmac(host)
            if host in child_hosts:
                routes.append(
                    (dmac, ports[topo.host_name(host)]))
                continue
            group = MultiCoreRoutes.__core_group_from_host(topo, host)
            agg = topo.agg_name(aggs[group - 1])
            routes.append((dmac, ports[agg]))

        return routes

    # Returns a list of DMAC, port tuples identifying the forwarding rules
    # for this Aggregator switch
    @staticmethod
    def agg(topo: Topo, agg_id: int) -> Routes:
        routes: Routes = []
        ports: Ports = topo.agg_ports(agg_id)

        cores: List[int] = topo.cores_from_agg(agg_id)
        cores.sort()

        added_hosts: Set[int] = set()
        for tor in topo.tors_from_agg(agg_id):
            tor_port = ports[topo.tor_name(tor)]
            for host in topo.hosts_from_tor(tor):
                routes.append((topo.host_dmac(host), tor_port))
                added_hosts.add(host)

        for host in range(topo.MIN_ID, topo.MIN_ID + topo.HOST_CT):
            if host in added_hosts:
                continue
            group = MultiCoreRoutes.__core_group_from_host(topo, host)
            core = topo.core_name(cores[group - 1])
            routes.append((topo.host_dmac(host), ports[core]))

        return routes

    '''
