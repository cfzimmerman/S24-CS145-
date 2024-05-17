#! /usr/bin/python3

# ./topology/generate_binary_topo.py [num_layers]
#   Generate the Binary Tree topology config file `topology/p4app_bin.json` 
#   with [num_layers] layers

import sys

# Usage function
def usage():
    print("Usage: ./topology/generate_binary_topo.py [num_layers]\n\tGenerate the Binary Tree topology config file `topology/p4app_binary.json` with [num_layers] layers")

# The topology config file template
template = '''{
  "p4_src": "p4src/l2fwd.p4",
  "cli": true,
  "pcap_dump": true,
  "enable_log": true,
  "topology": {
    "assignment_strategy": "l2",
    "links": [%s],
    "hosts": {
%s
    },
    "switches": {
%s
    }
  }
}
'''

# Get the number of layers from command line argument (choose from 4, 5, 6, 7)
I = 4 # by default we have 4 layers
try:
    I = int(sys.argv[1])
except Exception as e:
    print("Failed to parse the argument [num_layers]! Cause: {}".format(e))
    usage()
    exit(1) 

# Set switch name initials and bandwidths
if I == 4:
    device_symbol = ["a", "b", "c", "d", "h"]
    link_bw = [2, 1, 1, 1]
elif I == 5: 
    device_symbol = ["a", "b", "c", "d", "e", "h"]
    link_bw = [2, 1, 1, 1, 1]
elif I == 6:
    device_symbol = ["a", "b", "c", "d", "e", "f", "h"]
    link_bw = [2, 1, 1, 1, 1, 1]
elif I == 7:
    device_symbol = ["a", "b", "c", "d", "e", "f", "g", "h"]
    link_bw = [2, 1, 1, 1, 1, 1, 1]
else:
    print("The number of layers should be 4, 5, 6, or 7")
    usage()
    sys.exit(1)
print("There are {} layers in the Binary topology".format(I))

# Generate host list string
host_num = 2 ** (I)
hosts = ''
for host_i in range(host_num):
    if host_i == host_num - 1:
        hosts += '\t"h%d": {}' % (host_i + 1,)
    else:
        hosts += '\t"h%d": {},\n' % (host_i + 1,)
print("Host list: {}".format(hosts))

# Generate switch list string
switches = ''
for layer_id in range(I):
    device_num = 1<<layer_id
    for device_id in range(device_num):
        sw_name = "%s%d" % (device_symbol[layer_id], device_id + 1)
        if layer_id == I - 1 and device_id == device_num - 1:    
            switches += '\t"%s": {}' % (sw_name,)
        else:
            switches += '\t"%s": {}, \n' % (sw_name,)
print("Switch list: {}".format(switches))

# Generate link list string
links = ''
for layer_id in range(I):
    device_num = 1<<layer_id
    for device_id in range(device_num):
        links += '["%s%d", "%s%d", {"bw": %d}], ' % (device_symbol[layer_id], device_id + 1, device_symbol[layer_id + 1], device_id * 2 + 1, link_bw[layer_id])
        links += '["%s%d", "%s%d", {"bw": %d}], ' % (device_symbol[layer_id], device_id + 1, device_symbol[layer_id + 1], device_id * 2 + 1 + 1, link_bw[layer_id])
links = links[ :-2]
print("Link list: {}".format(links))

# Write the generated config JSON to file
f = None
try:
    f = open("topology/p4app_binary.json", "w")
except Exception as e:
    print("Failed to open file topology/p4app_binary.json to write the JSON config! Cause: {}".format(e))
try:
    f.write(template % (links, hosts, switches))
except Exception as e:
    print("Failed to write to file topology/p4app_binary.json! Cause: {}".format(e))

print("Successfully generate Binary topology config file topology/p4app_binary.json")