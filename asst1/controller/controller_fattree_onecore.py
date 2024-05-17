#! /usr/bin/python3

# ./controller/controller_fattree_onecore.py [k]
#   Insert P4 table entries to route traffic among hosts for FatTree topology
#   with [k] value
from p4utils.utils.helper import load_topo
from p4utils.utils.sswitch_thrift_API import SimpleSwitchThriftAPI
from routing import OneCoreRoutes
import sys
import os

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))  # noqa: E402
sys.path.insert(0, parent_dir)  # noqa: E402
from ftree_topo import Topo


def usage():
    print(
        "Usage: ./controller/controller_fattree_onecore.py [k]\n\t\
        Insert P4 table entries to route traffic among hosts for FatTree \
        topology with [k] value")


class RoutingController(object):

    def __init__(self):
        self.topo = None
        try:
            self.topo = load_topo("topology.json")
        except Exception as e:
            print("Failed to open the topology database file 'topology.json'. \
            Did you run the network with 'p4run'?\n\tCause: {}".format(e))
            exit(1)
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
            controller.table_set_default("dmac", "drop", [])

    def route(self):
        k = 4
        try:
            k = int(sys.argv[1])
        except Exception as e:
            print("Failed to parse the argument [k]! Cause: {}".format(e))
            usage()
            exit(1)
        topo = Topo(k)

        for sw_name, controller in self.controllers.items():
            for (dmac, port) in OneCoreRoutes.get_routes(topo, sw_name):
                controller.table_add("dmac", "forward", [
                    dmac], [str(port)])

    def main(self):
        self.route()


if __name__ == "__main__":
    controller = RoutingController().main()
