#! /usr/bin/python3

# ./tests/test_fat_topo.py [k]
# 	Test the correctness of implementing the FatTree topology
#	1. Read the topology config json file and verify its correctness
#	2. Run ping command between each pair of nodes

import json
import os
import sys
import random as rdm

# Usage function
def usage():
    print("Usage: ./tests/test_fat_topo.py [k]\n\tTest the correctness of implementing the FatTree topology with [k] value")

def test_fat_tree(k):
    print("Testing FatTree for k =", k)

    k_info = {}
    k_info[4] = { 'links' : 48, 'switches' : 20, 'hosts' : 16 }
    k_info[6] = { 'links' : 162, 'switches' : 45, 'hosts' : 54 }
    k_info[8] = { 'links' : 384, 'switches' : 80, 'hosts' : 128 }

    # Read file topology/p4app_fattree.json
    f = None
    try:
        f = open("topology/p4app_fattree.json", "r")
    except Exception as err:
        print("Cannot open file topology/p4app_fattree.json.\n\tCause: {}".format(err))
        exit(1)

    # Verify link count, switch count and host count for the topology
    try:
        print("Unit Test 1: Link Count")
        topo = json.load(f)
        assert len(topo['topology']['links']) == k_info[k]['links']
        print("Test passed\n")

        print("Unit Test 2: Switch Count")
        assert (len(topo['topology']['switches'])) == k_info[k]['switches']
        print("Test passed\n")

        print("Unit Test 3: Host Count")
        assert len(topo['topology']['hosts']) == k_info[k]['hosts']
        print("Test passed\n")
    except Exception as e:
        print("Parse json file {} error!\n\tCause: {}".format(f.name, e))
        exit(1)

    # Verify the controller enables the connection between each pair of hosts
    host_ips = []
    hosts = []
    for i in range(1, k_info[k]['hosts'] + 1):
        hosts += ['h{0}'.format(i)]
        host_ips += ['10.0.0.{0}'.format(i)]

    print("Unit Test 4: Ping mesh")
    c = 0
    test_count = 256
    total_host_pairs = (k * k * k // 4) ** 2
    test_probability = test_count / total_host_pairs
    for h in hosts:
        for ip in host_ips:
            if rdm.uniform(0.0, 1.0) <= test_probability:
                assert ("0% packet loss" in os.popen('mx {0} ping -c 1 {1}'.format(h, ip)).read())
            c += 1
            print(int(c * 100.0 / (k_info[k]['hosts']**2)), '% complete.', end='\r', flush=True)
    
    print("")
    print("Test passed")
    
if __name__ == '__main__':
    k = 4
    try:
        k = int(sys.argv[1])
    except Exception as e:
        print("Failed to parse the argument [k]! Cause: {}".format(e))
        usage()
        exit(1)
    test_fat_tree(k)
