[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-24ddc0f5d75046c5622901739e7c5dd533143b0c8e959d652212380cedb1ea36.svg)](https://classroom.github.com/a/_z5SoHgh)
# Project 4: Reliable Transport

## Objective

* Implement a simple reliable transport protocol.
* Understand the mechanisms required to reliably transfer data
* Understand how different sliding window protocols work

## Getting Started

To start this project, you will first need to get the [infrastructure setup](https://github.com/minlanyu/cs145-site/blob/spring2024/infra.md) and clone this repository with submodules
```
git clone --recurse-submodules <your repository>
```

Run `./pull_update.sh` to pull project updates (if any). You might need to merge conflicts manually: most of the time, you just need to accept incoming changes; reach to TF if it is hard to merge. This step also applies to all subsequent projects. 

## Overview

In this project, you will build a simple reliable transport protocol, RTP, **on top of UDP**. Your RTP implementation must provide in­ order, reliable delivery of UDP datagrams in the presence of events like packet loss, delay, corruption, duplication, and re­ordering.

There are a variety of ways to ensure a message is reliably delivered from a sender to a receiver. You are to implement a sender (`sender`) and a receiver (`receiver`) that follows the following RTP specification.

**You will do this project in the same VM as previous projects.**

### UDP sockets
This project is built on top of UDP. You **MUST NOT** use TCP sockets. For background, you can check out [UDP - Client And Server Example Programs In Python](https://pythontic.com/modules/socket/udp-client-server-example). Here's the high-level workflow: At the receiver, you can create a socket and bind it to a specific port. The sender can then create a socket and send traffic directly to the receiver based on its IP and port. (Note, this is the difference with TCP: the sender doesn't need to run `connect` to establish a connection.) Both the sender and the receiver can use `sendto` and `recvfrom` to communicate with each other. 

The key is to understand Python socket [`bind`](https://pythontic.com/modules/socket/bind), [`recvfrom`](https://pythontic.com/modules/socket/recvfrom) and [`sendto`](https://pythontic.com/modules/socket/sendto) APIs. 

### RTP Specification
RTP sends data in the format of a header, followed by a chunk of data.

RTP has four header types: `START`, `END`, `DATA`, and `ACK`, all following the same format:

```
PacketHeader:
  int type;      // 0: START; 1: END; 2: DATA; 3: ACK
  int seq_num;   // Described below
  int length;    // Length of data; 0 for ACK, START and END packets
  int checksum;  // 32-bit CRC
```

To initiate a connection, `sender` starts with a `START` packet and waits for an ACK for this `START` packet. After sending the `START` message, additional packets in the same connection are sent using the `DATA` message type, adjusting `seq_num` appropriately. After everything has been transferred, the connection should be terminated with `sender` sending an `END` message and waiting for the corresponding ACK for this message.

For each connection, `seq_num` starts from 0 (i.e., the first `START` packet has `seq_num` 0). The `seq_num` of ACK for `START` is 1. The `seq_num` of `DATA` packets then starts from 1 and gets incremented following the detailed specifications below. 

In this project, we use `seq_num` and cumulative `ACK` at the packet level instead of bytes.

<!--
Additional notes:
- it's okay for the timer to reset anytime any packet is received
- the receiver can stay alive at the end
- non-data packets can be constructed with / emptystring
-->

### Packet Size
An important limitation is the maximum size of your packets. The UDP protocol has an 8 byte header, and the IP protocol underneath it has a header of 20 bytes. Because we will be using Ethernet networks, which have a maximum frame size of 1500 bytes, this leaves 1472 bytes for your entire `packet` structure (including both the header and the chunk of data).

### Outline

Overall, this project has the following components:

* [Part 1](#part1): Implement `sender`
* [Part 2](#part2): Implement `receiver`
* [Part 3](#part3): Optimizations
* [Submission Instructions](#submission-instr)

We provide scaffolding code in `sender_reciver`. 

* Use `sudo pip install scapy` in the VM to install `scapy` package required by this project.

<a name="part1"></a>
## Part 1: Implement `sender`

`sender` should read an input message and transmit it to a specified receiver using UDP sockets following the RTP protocol. It should split the input message into appropriately sized chunks of data, and append a `checksum` to each packet. `seq_num` should increment by one for each additional packet in a connection. Please use the 32-bit CRC header we provide in `sender_receiver/util.py`, in order to add a checksum to your packet.

You will implement reliable transport using a sliding window mechanism. The size of the window (`window-size`) will be specified in the command line. `sender` must accept cumulative `ACK` packets from `receiver`.

After transferring the entire message, you should send an `END` message to mark the end of the connection. Note that the ACK packet of the `END` message might get dropped while the receiver already exited, making a retransmission in vain. To handle this situation, `sender` should start a 500 milliseconds timer once it sends the `END` message. `sender` can exit if (1) it receives the ACK packet of `END` or (2) 500 milliseconds have passed after it sends `END`.

`sender` must ensure reliable data transfer under the following four types of network errors:

- Loss of arbitrary levels;
- Re­ordering of ACK messages;
- Duplication of any amount for any packet;
- Delay in the arrivals of ACKs.

To handle cases where `ACK` packets are lost, you should implement a 500 milliseconds *retransmission timer* to automatically retransmit packets that were never acknowledged. Whenever the window moves forward (i.e., some ACK(s) are received and some new packets are sent out), you reset the timer. If after 500ms the window still has not advanced, you retransmit all packets in the window because they are all never acknowledged.

### Running `sender`
`sender` should be invoked as follows:

`python sender.py [Receiver IP] [Receiver Port] [Window Size] < [Message]`

* `Receiver IP`: The IP address of the host that `receiver` is running on.
* `Receiver Port`: The port number on which `receiver` is listening.
* `Window Size`: Maximum number of outstanding packets.
* `Message`: The message to be transferred. It can be a text as well as a binary message.


<a name="part2"></a>
## Part 2: Implement `receiver`

`receiver` needs to handle only one `sender` at a time and should ignore `START` messages while in the middle of an existing connection. It must receive and store the message sent by the sender on disk completely and correctly.

`receiver` should also calculate the checksum value for the data in each `packet` it receives using the header mentioned in part 1. If the calculated checksum value does not match the `checksum` provided in the header, it should drop the packet (i.e. not send an ACK back to the sender).

For each packet received, it sends a cumulative `ACK` with the `seq_num` it expects to receive next. If it expects a packet of sequence number `N`, the following two scenarios may occur:

1. If it receives a packet with `seq_num` not equal to `N`, it sends back an `ACK` with `seq_num=N`. Here `receiver` still buffers out-of-order packets. 
2. If it receives a packet with `seq_num=N`, it will check for the highest sequence number (say `M`) of the in­order packets it has already received and send `ACK` with `seq_num=M+1`.

If the next expected `seq_num` is `N`, `receiver` will drop all packets with `seq_num` greater than or equal to `N + window_size` to maintain a `window_size` window.

`receiver` can exit once it sends the ACK packet of the `END` message.

Put the programs written in parts 1 and 2 of this project into a folder called `RTP-base`.

Some useful debug tips

* You can try to print the state maintained (e.g. sequence number interval of current window) in the sender and receiver. 
* You need to use `sys.stdout.flush()` to force everything in the buffer to the terminal ([learn more](https://stackoverflow.com/questions/10019456/usage-of-sys-stdout-flush-method)). 
### Running `receiver`
`receiver` should be invoked as follows:
`python receiver.py [Receiver Port] [Window Size] > Message`

* `Receiver Port`: The port number on which `receiver` is listening for data.
* `Window Size`: Maximum number of outstanding packets.
* `Message`: The received message received.

NOTE: Your code should pass the tests below before the optimizations

<a name="part3"></a>
## Part 3: Optimizations

For this part of the project, you will make a few modifications to the programs written in the previous two sections. Consider how the programs written in the previous sections would behave for the following case where there is a window of size 3:

<img src="base_case.PNG" title="Inefficient transfer of data" alt="" width="250" height="250"/>

In this case `receiver` would send back two ACKs both with the sequence number set to 0 (as this is the next packet it is expecting). This will result in a timeout in `sender` and a retransmission of packets 0, 1 and 2. However, since `receiver` has already received and buffered packets 1 and 2. Thus, there is an unnecessary retransmission of these packets.

In order to account for situations like this, you will be modifying your `receiver` and `sender` accordingly (save these different versions of the program in a folder called `RTP-opt`):

* `receiver` will not send cumulative ACKs anymore; instead, it will send back an ACK with `seq_num` set to whatever it was in the data packet (i.e., if a sender sends a data packet with `seq_num` set to 2, `receiver` will also send back an ACK with `seq_num` set to 2). It should still drop all packets with `seq_num` greater than or equal to `N + window_size`, where `N` is the next expected `seq_num`.
* `sender` must maintain information about all the ACKs it has received in its current window and maintain a 500 milliseconds *retransmission timer* (Note: just one timer for all packets in the current window) to retransmit packets that were not acknowledged in the current window. So, for example, packet 0 having a timeout would not necessarily result in a retransmission of packets 1 and 2.

For a more concrete example, here is how your improved `sender` and `receiver` should behave for the case described at the beginning of this section:

<img src="improvement.PNG" title="only ACK necessary data" alt="" width="250" height="250"/>

`receiver` individually ACKs both packet 1 and 2.

<img src="improvement_2.PNG" title="only send unACKd data" alt="" width="250" height="250"/>

`sender` receives these ACKs and denotes in its buffer that packets 1 and 2 have been received. Then, the it waits for the 500 ms timeout and only retransmits packet 0 again.

The command line parameters passed to these new `sender` and `receiver` are the same as the previous two sections.

NOTE: Your code with optimizations in Part 3 should still pass the testing below. We will also manually check your code for your optimization implementation.

## Testing Your Solutions

We provide a proxy-based testing script to help verify the correctness of your solution. 
The testing script initiates connections with your receiver and sender separately, and forward packets with random delay, reordering, drops, or modifications. 

Before the test, you should put these files to the same folder:
    Solution files: receiver.py, send.py, util.py
    Test files: proxy.py, test_message.txt, compare.sh

Following the fours steps to test: 
1. start the receiver: `python sender_receiver/receiver.py [port_recv] [window_size] > [output_file]`
    * Eg, `python sender_receiver/receiver.py 40000 128 > test_scripts/output.txt`. 
    * Receiver listens on port 40000.
2. start the proxy: `python test_scripts/proxy.py localhost [port_send] localhost [port_recv] [error_type]`
    * Eg, `python test_scripts/proxy.py localhost 50000 localhost 40000 0123`. 
    * Proxy listens on port 50000 (waiting for connection from sender); proxy connects to port 40000; 
    * 0123 means we choose all four types of errors. You may check proxy.py code to see how we inject different types of errors. 
3. start the sender: `python sender_receiver/sender.py localhost [port_send] [window_size] < test_scripts/test_message.txt`
    * Eg, `python sender_receiver/sender.py localhost 50000 128 < test_scripts/test_message.txt`. 
    * Sender connects to port 50000 (where proxy is listening on -- here completes the packet forwarding). 
4. compare result: `bash test_scripts/compare.sh [output_file] test_message.txt`
    * Eg, `bash test_scripts/compare.sh test_scripts/output.txt test_scripts/test_message.txt`. 
    * You should delete the old `output.txt` before testing your new solution. 
    * If you see *SUCCESS: Message received matches message sent!* printed, then you solution passes the test!

<a name="submission-instr"></a>
## Submission and Grading

### What to submit
You are expected to submit the following documents:

1. The source code for `sender` and `receiver` from parts 1 and 2: all source files should be in a folder called `RTP-base`.
2. The source code for `sender` and `receiver` from part 3: all source files should be in a folder called `RTP-opt`.

Please make sure all files are in the `project4/` folder of your master branch.

### Grading 

Your code in both Part 2 (RTP-base) and Part 3 (RTP-opt) should pass our testing scripts with all four types of network errors. The total grades is 100:

- 60: RTP-base passes test
    - 10: built on top of UDP (doesn't use TCP sockets)
    - 15: correctly implement cumulative ACK
    - 15: correctly implement timeout and retransmission
    - 20: correct received message
- 40: RTP-opt passes test 
    - 15: doesn't send cumulative ACKs
    - 15: correctly implement timeout and retransmission
    - 10: correct received message
- Deductions based on late policies
- For this project, you are not required to modify the report (but please feel free to include citations and grading notes there).


## Acknowledgements
This programming project is based on UC Berkeley's Project 2 from EE 122: Introduction to Communication Networks, and Johns Hopkins University's Project 2 from EN.601.414/614: Computer Networks.

## Survey
Please fill out the Canvas survey after completing this project. 2 extra points will be given once you have finished it.
