# CS 145 Project 0

## Author and collaborators

### Author name

Cory Zimmerman, cfzimmerman@college.harvard.edu

### Collaborators

None

## Report

**Forwarding rules:**
The JSON file seems to set up the nodes and edges in the graph. Within that structure, it seems the forwarding rules map how packets flow through the graph. The mindset I took while working on this was, for each node, determine where the packet wants to go from the perspective of a host, and determine the best adjacent node a packet should be forwarded to at any given switch. So, when one host wants to send data to another host, it passes a packet to a switch. Because each switch has routing logic directing a packet towards its ultimate destination, the packet flows through the graph until it reaches the target address (presuming the switches are configured to handle the target address).

After looking through the given example, I drew a picture and followed the syntax from the line example to express the same idea for the circle. Drawing at `./ps0_drawing.png`.

**Throughput:**

- Video app:
  - Server `h1`, client `h2`: bandwidth of `46kbps`
  - Server `h2`, client `h1`: bandwidth of `46kbps`
  - Server `h3`, client `h1`: bandwidth of `46kbps`
- lperf:
  - Server `h1`, client `h2`: bandwidth of `1.14Mbits/sec`
  - Server `h2`, client `h1`: bandwidth of `1.14Mbits/sec`
  - Server `h2`, client `h1`: bandwidth of `1.14Mbits/sec`

## Citations

## Grading notes (if any)

## Extra credit attempted (if any)
