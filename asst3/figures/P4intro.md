## P4 Program
The P4 Program is the code that runs in the switches. It is responsible for telling the P4 switches how to process each packet.

For the line topology, the P4 Program is in `p4src/l2fwd.p4`.
In this project, you do not need to edit the P4 code, but in future projects, writing P4 code is a central part. For this project, understanding the P4 code will help with writing and understanding the controller code.

### Tools in P4
Flows, tables, and actions are key concepts in P4 that are used to process packets. We will introduce flows, tables, and actions one by one.

#### Flows

A flow is defined as a specific pattern of several packet header fields. For example, a flow can be defined as a specific combination of “five-tuple” (e.g., source IP=10.0.0.1, destination IP=10.0.0.15, protocol=TCP, source TCP port=2000, destination TCP port=8080).
A flow can also be defined in wildcards (e.g., source IP=10.0.0.\*, destination IP=100.0.0.\*).
P4 provides `header` grammar to define specific packet headers (e.g., IP header, TCP header, VLAN header).
P4 also provides `parser` grammar to extract useful information in packet headers (e.g., extracting IP addresses, and TCP ports, and define them as a flow).

#### Actions
An action defines how to process a packet.
For example, an action can be forwarding a packet to a certain port (physical port on switches), an action can be dropping a packet, inserting an VLAN tag into the packet header, or sending the packet to another table (will be mentioned later).
Actions can be thought of as functions. You can define your own actions and they work in the p4 code to process the packets a certain way.
P4 provides `action` grammar to define the action.

#### Tables
A table consists of a list of rules, and each rule consists of a flow(criteria matching the flow, like destination ip, five-tuple, etc.) and the action to run for the flow.
Each rule defines how to perform actions on a specific flow.

For example, we can define a table named “dmac”. We will have this be responsible for processing packets and deciding what to do with each packet based on the destination MAC address. We can define rules like:

- For DMAC 00:00:00:00:00:00, drop the packet.
- For DMAC ff:ff:ff:ff:ff:ff, broadcast the packet to all ports.
- For DMAC 00:00:0a:00:00:01, send to port number 1.

A p4 program can have multiple tables that work together. For example, if we have another table called `dip`, we can add another rule in `dmac` as follows:
- For other DMAC, send the packet to table “dip”.

P4 provides `table` grammar to define tables.

Although you define tables in P4, **P4 is not responsible to fill in the tables with rules**. Rules are filled in with controllers.

<!-- In this project, you need to write the P4 program to define flow tables in those switches. We provide you with a code skeleton in `p4src/line_topo.p4` file, and you only need to fill in some blanks in the code skeleton.
There are several parts in the skeleton program, which are `headers`, `parsers`, `checksum verification`, `ingress processing`, `egress processing`, `checksum computation`, `deparser`, and `switch`. -->
<!--In your project, you need to fill in codes in the ``headers``, ``parsers``, ``ingress processing``, and ``deparser`` part. The most important part is the ``ingress processing`` part, which defines the core components, including forwarding table and actions. The rest 3 parts defines headers you want to extract from packets. In the beginning, you only need to consider the *destination MAC address* header.
-->
### Sections in P4 programs
In a p4 program, there are many sections to the code. These sections are the ones we will be focusing on: `headers`, `parsers`, `checksum verification`, `ingress processing`, `egress processing`, `checksum computation`, `deparser`.

#### Headers
The `headers` part is used to define packet headers. For example, ethernet headers, IP headers, and TCP headers.
The code is shown in the following figure. We use `typedef` to define header fields, like MAC addresses. We use `header` to define a packet header, which consists of specific header fields.
You can ignore the `metadata` for this project, but it will come into play in later projects.
After defining all headers, we need to define `headers` to describe which packet headers are in the packet. In this project, we only need to use the first packet header in packets, i.e., the ethernet header.

<img src="./figures/p1_headers.png" width="650">

#### Parsers
The `parser` part is used to tell P4 switches which headers to parse in the incoming packets. In this example, only the ethernet header needs to be parsed for each packet.
We define a `parser` in this part, taking as input the packet and metadata, outputting the parsed header and metadata.
The `extract` function for packets puts the header data for the packet into the structure given, in this case hdr.ethernet.

<img src="./figures/p1_parser.png" width="650">

#### Ingress processing
The `ingress processing` part is used to process the parsed header. In this project, we will forward the packet to the corresponding physical port based on the destination MAC address in the ethernet header.
We define a `control` in this part, and the parameters are the parsed header "hdr", and the metadata.
Within the `control`, we define `action` and `table`. An `action` is a function processing the packet, and a `table` is the flow table in the P4 switch.

In this part, we define an `action` called "forward", which is used to set the output port of the packet.  The "forward" action takes as input the egress port. Then, it sets the egress_spec in the standard_metadata to the port inputted as a parameter. Changing the standard_metadata tells the switch to which port the packet should be forwarded.

We also define a `table` named "dmac", which is the forwarding table for packets. This table is a look-up table for P4 switch. Each part of the `key` section is a parameter of the packet that will be used to match a packet to an action. The `exact` part specifies the type of matching to do on that parameter.
The actions section is a list of possible actions that the rules for the table will match to. As said earlier, the rules of the table will be filled in at the controller.

As you can see, we will use the destination MAC address parameter to match a packet and we will use the forwarding action that we created earlier as a possible action

<img src="./figures/p1_control.png" width="650">

#### Deparser
The `deparser` part is used to deparse the corresponding header, so the packet can be sent out with the header. Here we only need to deparse the ethernet header.

<img src="./figures/p1_deparser.png" width="650">

For more information about P4, please refer to the following documents:
- <https://github.com/p4lang/tutorials>
- <https://github.com/p4lang/tutorials/blob/master/P4_tutorial.pdf>

<!--
We provide some examples of defining actions. There are two significant actions: ``drop`` and ``forward``, which means droping the packet and forward this packet to a specific port of this switch. These actions are the most basic actions that you will use in all future projects.

<img src="./figures/action.png" width="600">

We also provide an example of defining a table for forwarding. In this example, we only need to forward packets according to their destination MAC address. Therefore, we define a table like this

<img src="./figures/table.png" width="550">

We define the flow key as the destination MAC address, and set the matching mode to *exact match*. Here we include the ``forward`` action and ``NoAction`` in this table, and set the default action to ``NoAction``.
-->
