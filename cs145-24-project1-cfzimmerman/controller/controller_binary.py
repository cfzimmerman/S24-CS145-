#! /usr/bin/python3

# ./controller/controller_binary.py [num_layers]
#   Insert P4 table entries to route traffic among hosts for Binary Tree topology
#   with [num_layers] layers

from p4utils.utils.helper import load_topo
from p4utils.utils.sswitch_thrift_API import SimpleSwitchThriftAPI
import sys

# Usage function
def usage():
    print("Usage: ./controller/controller_binary.py [num_layers]\n\tInsert P4 table entries to route traffic among hosts for Binary Tree topology with [num_layers] layers")

class RoutingController(object):

    def __init__(self):
        self.topo = None
        try:
            self.topo = load_topo("topology.json")
        except Exception as e:
            print("Failed to open the topology database file 'topology.json'. Cause: {}".format(e))
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
        I = 4 # by default we have 4 layers
        try:
            I = int(sys.argv[1])
        except Exception as e:
            print("Failed to parse the argument [num_layers]! Cause: {}".format(e))
            usage()
            exit(1) 

        host_num = 2 ** (I)
         
        if I == 4:
            # mapping the first letter of sw_name/device_name to the layer number (from top to bottom) in binary tree. 
            device_id_mapping = {"a": 0, "b": 1, "c": 2, "d": 3, "h": 4}
        elif I == 5: 
            device_id_mapping = {"a": 0, "b": 1, "c": 2, "d": 3, "e": 4, "h": 5}
        elif I == 6:
            device_id_mapping = {"a": 0, "b": 1, "c": 2, "d": 3, "e": 4, "f": 5, "h": 6}
        elif I == 7:
            device_id_mapping = {"a": 0, "b": 1, "c": 2, "d": 3, "e": 4, "f": 5, "g": 6, "h": 7}
        else:
            print("The number of layers should be 4, 5, 6, or 7")
            usage()
            sys.exit(1)

        for sw_name, controller in self.controllers.items():
            # get which layer (starting from 0, from top to bottom) the current sw belongs to
            layer_id = device_id_mapping[sw_name[0]]
            # get the device number (starting from 0, from left to right) of the current sw
            device_id = int(sw_name[1:]) - 1

            # for switches in the the top layer, just forward based on whether the (dest) host_id locates in 
            # the left part of the Binary Tree -- forward via the left port (ie, port 1), 
            # or the right part of the Binary Tree -- forward via the right port (ie, port 2).
            if layer_id == 0:
                for host_id in range(host_num):
                    out_port = host_id // (host_num / 2) + 1
                    controller.table_add("dmac", "forward", ["00:00:0a:00:00:%02x" % (host_id + 1,)], ["%d" % (out_port,)])
            # for switches in the other layers, we forward based on whether the (dest) host_id locates in 
            # the left part of the subtree starting from the current sw -- forward via the left port (ie, port 2), 
            # or the right part of the subtree -- forward via the right port (ie, port 3),
            # or ourside of the subtree -- forward to the upper layer via the top port (ie, port 1). 
            else:
                interval = host_num // (2 ** (layer_id + 1))
                axis = 2 * device_id * interval + interval
                for host_id in range(host_num):
                    if host_id in range(axis - interval, axis):
                        out_port = 2
                    elif host_id in range(axis, axis + interval):
                        out_port = 3
                    else:
                        out_port = 1
                    controller.table_add("dmac", "forward", ["00:00:0a:00:00:%02x" % (host_id + 1,)], ["%d" % (out_port,)])


    def main(self):
        self.route()


if __name__ == "__main__":
    controller = RoutingController().main()
