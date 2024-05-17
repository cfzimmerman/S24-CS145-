#! /usr/bin/python3

# python3 tests/test_circle_topo.py
# 	Test the correctness of implementing the circle topology
#	1. Read the topology config json file and verify its correctness
#	2. Run ping command between each pair of nodes

import json
import os
import sys

from os.path import dirname, abspath
d = dirname(dirname(abspath(__file__))) 
os.chdir(d)

def test_circle_topology():
	print("Testing circle topology\n")

	# Read file topology/p4app_circle.json
	f = None
	try:
		f = open("topology/p4app_circle.json", "r")
	except Exception as err:
		print("Cannot open file topology/p4app_circle.json.\n\tCause: {}".format(err))
		exit(1)
	
	# Verify link count, switch count and host count for the topology
	try:
		topo = json.load(f)
		print("Unit Test 1: Link Count")
		assert len(topo['topology']['links']) == 6
		print("Test passed\n")

		print("Unit Test 2: Switch Count")
		assert (len(topo['topology']['switches'])) == 3
		print("Test passed\n")

		print("Unit Test 3: Host Count")
		assert len(topo['topology']['hosts']) == 3
		print("Test passed\n")
	except Exception as e:
		print("Test failed!\n\tCause: {}".format(f.name, e))
		exit(1)

	# Verify the controller enables the connection between each pair of hosts
	host_ips = []
	hosts = []
	for i in range(1, 4):
		hosts += ['h{0}'.format(i)]
		host_ips += ['10.0.0.{0}'.format(i)]

	print("Unit Test 4: Ping mesh")
	c = 0
	for h in hosts:
		for ip in host_ips:
			try: 
				assert (" 0% packet loss" in os.popen('mx {0} ping -c 1 {1}'.format(h, ip)).read())
			except Exception as e:
				print("Ping mesh test failed")
				exit(1)
			c += 1
			print(int(c * 100.0 / (3 * 3)),'% complete.', end='\r', flush=True)
	
	print("")
	print("Test passed")

if __name__ == '__main__':
	test_circle_topology()