#! /usr/bin/python3

# ./topology/generate_fattree_topo.py [K]
#   Generate the FatTree topology config file `topology/p4app_fattree.json`
#   with [K] value

import sys
import json
import os
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))  # noqa: E402
sys.path.insert(0, parent_dir)  # noqa: E402
from ftree_topo import Topo


def usage():
    print(
        "Usage: ./topology/generate_fattree_topo.py [K]\n\t\
        Generate the FatTree topology config file \
        `topology/p4app_fattree.json` with [K] value")


template = {
    "p4_src": "p4src/l2fwd.p4",
    "cli": True,
    "pcap_dump": True,
    "enable_log": True,
    "topology": {
        "assignment_strategy": "l2",
        "default_bw": 1,
        "links": [],
        "hosts": {},
        "switches": {}
    }
}
links = template["topology"]["links"]
hosts = template["topology"]["hosts"]
switches = template["topology"]["switches"]

# Get the K value from command line argument (choose from 4, 6, 8)
k = 4  # by default we K=4
try:
    k = int(sys.argv[1])
except Exception as e:
    print("Failed to parse the argument [K]! Cause: {}".format(e))
    usage()
    exit(1)

if k != 4 and k != 6 and k != 8:
    print("K should be 4, 6, or 8!")
    usage()
    exit(1)

print("K={} in the FatTree topology".format(k))

# Generate the topology details, number of hosts,
# tor switches, agg switches, and core switches

topo = Topo(k)
link_bw = {"bw": 1}

# Generate hosts and host links
for host in range(1, topo.HOST_CT + 1):
    host_name = topo.host_name(host)
    hosts[host_name] = {}

    tor = topo.tor_from_host(host)
    links.append([host_name, topo.tor_name(tor), link_bw])

print("\nHost list: {}".format(hosts))

# Generate switches and switch links
for tor in range(1, topo.TOR_CT + 1):
    tor_name = topo.tor_name(tor)
    switches[tor_name] = {}

    for agg in topo.aggs_from_tor(tor):
        links.append([tor_name, topo.agg_name(agg), link_bw])

for agg in range(1, topo.AGG_CT + 1):
    agg_name = topo.agg_name(agg)
    switches[agg_name] = {}

    for core in topo.cores_from_agg(agg):
        links.append([agg_name, topo.core_name(core), link_bw])

for core in range(1, topo.CORE_CT + 1):
    switches[topo.core_name(core)] = {}

print("\nSwitch list: {}".format(switches))

print("\nLink list: {}".format(links))

# Write the generated config JSON to file
f = None
try:
    f = open("topology/p4app_fattree.json", "w")
except Exception as e:
    print("Failed to open file topology/p4app_fattree.json to write the \
    JSON config! Cause: {}".format(e))
try:
    f.write(json.dumps(template, indent=4))
except Exception as e:
    print("Failed to write to file topology/p4app_fattree.json! \
    Cause: {}".format(e))

print("Successfully generated a FatTree topology config file at \
topology/p4app_fattree.json")
