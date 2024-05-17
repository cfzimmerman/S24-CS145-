#!/usr/bin/python3

import time
import os

print("Testing ECMP")

print("Test 1")
os.system("sudo tcpdump -enn -i a1-eth1 > tcpdump_log.output 2> /dev/null &")
os.system("sudo mx h4 ping -c 3 10.0.0.2 > /dev/null 2> /dev/null")
time.sleep(3)
os.system("sudo killall tcpdump")
time.sleep(1)

with open("tcpdump_log.output", "r") as f:
  contents = f.read()
  assert("ICMP echo reply" in contents)
  assert("ICMP echo request" not in contents)

print("Passed")

print("Test 2")
os.system("sudo tcpdump -enn -i a2-eth1 > tcpdump_log.output 2> /dev/null  &")
os.system("sudo mx h1 ping -c 3 10.0.0.2 > /dev/null 2> /dev/null ")
time.sleep(3)
os.system("sudo killall tcpdump")
time.sleep(1)

with open("tcpdump_log.output", "r") as f:
  contents = f.read()
  assert(len(contents) == 1)

print("Passed")

print("Test 3")
os.system("sudo tcpdump -enn -i a1-eth1 > tcpdump_log.output 2> /dev/null &")
os.system("sudo mx h2 ping -c 3 10.0.0.4 > /dev/null 2> /dev/null")
time.sleep(3)
os.system("sudo killall tcpdump")
time.sleep(1)

with open("tcpdump_log.output", "r") as f:
  contents = f.read()
  assert("ICMP echo reply" not in contents)
  assert("ICMP echo request" in contents)

print("Passed")

os.system("sudo rm -rf tcpdump_log.output")
