#! /usr/bin/python3

# ./controller/controller_fattree_l3.py
#   Insert P4 table entries to route traffic among hosts for FatTree topology
#   under L3 routing

from p4utils.utils.helper import load_topo
from p4utils.utils.sswitch_thrift_API import SimpleSwitchThriftAPI
from routing import MultiCoreRoutes
from ftree_topo import Topo
from random import random


class RoutingController(object):

    def __init__(self):
        self.topo = load_topo("topology.json")
        self.controllers = {}
        self.init()

    def init(self):
        self.connect_to_switches()
        self.reset_states()
        self.set_table_defaults()

    def connect_to_switches(self):
        for p4switch in self.topo.get_p4switches():
            thrift_port = self.topo.get_thrift_port(p4switch)
            self.controllers[p4switch] = SimpleSwitchThriftAPI(thrift_port)

    def reset_states(self):
        [controller.reset_state() for controller in self.controllers.values()]

    def set_table_defaults(self):
        for controller in self.controllers.values():
            controller.table_set_default("ipv4_lpm", "drop", [])

    def route(self):
        topo = Topo(4)
        for sw_name, controller in self.controllers.items():
            filled_ecmp = False
            (layer, id) = topo.id_node(sw_name)
            for (ip, ports) in MultiCoreRoutes.get_routes(topo, sw_name):
                assert type(ports) is list
                if len(ports) == 1:
                    # If there's only a single port available, use it directly
                    # and don't bother hashing.
                    controller.table_add(
                        "ipv4_lpm", "set_nhop", [ip], [str(ports[0])])
                    continue

                assert layer == topo.TOR or layer == topo.AGG
                # Install an ecmp_group mapping for this ip
                ecmp_group = topo.get_ecmp_group(layer)
                num_nhops = len(ports)
                controller.table_add("ipv4_lpm", "ecmp_group", [ip],
                                     [str(ecmp_group), str(num_nhops)])

                # Fill the ecmp_group match table for this switch with
                # randomized port mappings. These mappings only need
                # to be installed once per switch.
                if not filled_ecmp:
                    for bucket in range(topo.get_max_hash(num_nhops)):
                        hash_ind = int(random() * 1000) % num_nhops
                        controller.table_add("ecmp_group_to_nhop", "set_nhop",
                                             [str(bucket), str(ecmp_group)],
                                             [str(ports[hash_ind])])
                    filled_ecmp = True

    def main(self):
        self.route()


if __name__ == "__main__":
    controller = RoutingController().main()
