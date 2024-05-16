from p4utils.utils.helper import load_topo
from p4utils.utils.sswitch_thrift_API import SimpleSwitchThriftAPI
import sys


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
            controller.table_set_default("dipv4", "drop", [])
            controller.table_set_default("group_info_to_port", "drop", [])

    def route(self):
        HOST_LEFT = "10.0.0.1"
        HOST_RIGHT = "10.0.0.2"

        for sw_name, controller in self.controllers.items():
            # this isn't scalable, but it works for an irregular topology
            if sw_name == "s1":
                port_home = self.topo.node_to_node_port_num(sw_name, "h1")
                controller.table_add("dipv4", "forward",
                                     [HOST_LEFT], [str(port_home)])

                port_up = self.topo.node_to_node_port_num(sw_name, "s2")
                controller.table_add("group_info_to_port",
                                     "forward", ["1", str(0)], [str(port_up)])

                port_down = self.topo.node_to_node_port_num(sw_name, "s3")
                controller.table_add("group_info_to_port",
                                     "forward", ["1", str(1)], [str(port_down)])

                controller.table_add(
                    "dipv4", "fill_metadata", [HOST_RIGHT], ["1", str(2)])
                continue

            if sw_name == "s2":
                port_left = self.topo.node_to_node_port_num(sw_name, "s1")
                controller.table_add("dipv4", "forward",
                                     [HOST_LEFT], [str(port_left)])

                port_right = self.topo.node_to_node_port_num(sw_name, "s4")
                controller.table_add("dipv4", "forward",
                                     [HOST_RIGHT], [str(port_right)])
                continue

            if sw_name == "s3":
                port_left = self.topo.node_to_node_port_num(sw_name, "s1")
                controller.table_add("dipv4", "forward",
                                     [HOST_LEFT], [str(port_left)])

                port_right = self.topo.node_to_node_port_num(sw_name, "s4")
                controller.table_add("dipv4", "forward",
                                     [HOST_RIGHT], [str(port_right)])
                continue

            if sw_name == "s4":
                port_home = self.topo.node_to_node_port_num(sw_name, "h2")
                controller.table_add("dipv4", "forward",
                                     [HOST_RIGHT], [str(port_home)])

                port_up = self.topo.node_to_node_port_num(sw_name, "s2")
                controller.table_add("group_info_to_port",
                                     "forward", ["1", str(0)], [str(port_up)])

                port_down = self.topo.node_to_node_port_num(sw_name, "s3")
                controller.table_add("group_info_to_port",
                                     "forward", ["1", str(1)], [str(port_down)])

                controller.table_add(
                    "dipv4", "fill_metadata", [HOST_LEFT], ["1", str(2)])
                continue

            print(f"❌ cases above should have caught: {sw_name}")

#        k = 4
#        host_num = k * k * k // 4
#        half_k = k // 2
#
#        for sw_name, controller in self.controllers.items():
#            sw_num = int(sw_name[1:]) - 1
#            if sw_name[0] == 't':
#                for agg_offset in range(half_k):
#                    out_port = self.topo.node_to_node_port_num(sw_name, "a%d" % (
#                        (sw_num // half_k) * half_k + agg_offset + 1,))
#                    for buckets_per_offset in range(half_k):
#                        controller.table_add("group_info_to_port", "forward", ["1", "%d" % (
#                            agg_offset * half_k + buckets_per_offset,)], ["%d" % (out_port,)])
#                for host_id in range(host_num):
#                    if host_id >= sw_num * half_k and host_id < (sw_num + 1) * half_k:
#                        out_port = self.topo.node_to_node_port_num(
#                            sw_name, "h%d" % (host_id + 1,))
#                        controller.table_add("dipv4", "forward", [
#                                             "10.0.0.%d" % (host_id + 1,)], ["%d" % (out_port,)])
#                    else:
#                        controller.table_add("dipv4", "fill_metadata", ["10.0.0.%d" % (
#                            host_id + 1,)], ["1", "%d" % (half_k * half_k,)])
#            elif sw_name[0] == 'a':
#                for core_offset in range(half_k):
#                    out_port = self.topo.node_to_node_port_num(sw_name, "c%d" % (
#                        (sw_num % half_k) * half_k + core_offset + 1,))
#                    for buckets_per_offset in range(half_k):
#                        controller.table_add("group_info_to_port", "forward", ["1", "%d" % (
#                            buckets_per_offset * half_k + core_offset,)], ["%d" % (out_port,)])
#                for host_id in range(host_num):
#                    min_host_id = (sw_num // half_k) * half_k * half_k
#                    max_host_id = min_host_id + half_k * half_k
#                    if host_id >= min_host_id and host_id < max_host_id:
#                        out_port = self.topo.node_to_node_port_num(
#                            sw_name, "t%d" % (host_id // half_k + 1,))
#                        controller.table_add("dipv4", "forward", [
#                                             "10.0.0.%d" % (host_id + 1,)], ["%d" % (out_port,)])
#                    else:
#                        controller.table_add("dipv4", "fill_metadata", ["10.0.0.%d" % (
#                            host_id + 1,)], ["1", "%d" % (half_k * half_k,)])
#            elif sw_name[0] == 'c':
#                for host_id in range(host_num):
#                    pod_num = host_id // (half_k * half_k)
#                    target = "a%d" % (pod_num * half_k +
#                                      sw_num // half_k + 1,)
#                    out_port = self.topo.node_to_node_port_num(sw_name, target)
#                    controller.table_add("dipv4", "forward", [
#                                         "10.0.0.%d" % (host_id + 1,)], ["%d" % (out_port,)])

    def main(self):
        self.route()


if __name__ == "__main__":
    controller = RoutingController().main()
