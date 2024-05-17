#!/usr/bin/python3

import json
import os
import sys

def test_fat_tree():
	print("Testing l3 fwd")
		
	print("Controller Unit Tests")
	# get all hostnames and their IP addresses
	host_ips = []
	hosts = []
	for i in range(1, 17):
		hosts += ['h{0}'.format(i)]
		host_ips += ['10.0.0.{0}'.format(i)]

	print("Unit Test: Ping mesh")
	print("(might take a while)")
	# Try to use pingall to test whether the network get connected after chaning to L3 fwd
	c = 0
	for h in hosts:
		for ip in host_ips:
			assert (", 0% packet loss" in os.popen('mx {0} ping -c 1 {1}'.format(h, ip)).read())
			c += 1
			print(int(c * 100.0 / (16 * 16)), '% complete.', end='\r', flush=True)
	
	print("")
	print("Test passed")
if __name__ == '__main__':
	test_fat_tree()