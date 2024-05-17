# What is P4?

P4 (Programming Protocol-Independent Packet Processors) is a programming language used to specify the data plane behavior of programmable switches. Before P4, programmable switches’ behavior was defined using many different opaque, vendor-specific languages. As an open-source project, P4 provides a transparent and consistent language for writing programmable switches.

For this course, we use the P4_16 specification. This distinction from the P4_14 specification may be important if you need to look at any external documentation about language semantics or functions.

# What P4 is not

We use several technologies that you might be unfamiliar with in this course. While this document is meant to explain P4 specifically, it is useful to draw clear boundaries around P4's purpose and why we need these other tools.

P4 is not a network emulator. It does not emulate network operations and links between switches. It only specifies the behavior of switches which themselves can be embedded in a network. We use Mininet as a network emulator for this course. You can find more information about what it does [here](https://github.com/mininet/mininet/wiki/Introduction-to-Mininet#what).

P4 is not a controller. That is P4 does not operate in the control plane only the data plane. This is an especially important point as there is a link between a controller program and a P4 program, creating an opportunity for confusion. The way we build controllers in this class uses [P4utils](https://github.com/nsg-ethz/p4-utils) python library which is meant to make it more convenient to build P4 networks on top of mininet. Check the docs for more info!

# Basic Language Constructs

At first glance, P4 looks a lot like a C program with a few special keywords

You can use constructs similar to C macros to define program level constants such as
`#define MACRO_NAME 1`.

P4 supports many native types; however, for this course, it will typically be sufficient to work with bitstrings. You can initialize variables using both decimal and hexadecimal values, for the latter just prepend the value with “0x”. For instance, to declare and initialize a variable foo in the following way

`bit<8> foo = 0xa2;`

Also similar to C, you can cast between different lengths of bitstrings. For instance, to cast the foo variable to a 16-bit bitstring you would write

`(bit<16>)foo`

P4 also supports abstract data types through the “typedef” keyword. This is useful to give some context for the type of data a certain variable might hold. For instance, you might declare a type for IPv4 addresses and instantiate a variable of this type as

`typedef bit<32> ip4Addr_t;`

`ip4Addr_t ip4addr = 0xfeedface;`

# Components of a P4 Program

At the end of each P4 application code for this course, you will find the following lines of code:

`V1Switch(MyParser(),`

`MyVerifyChecksum(),`

`MyIngress(),`

`MyEgress(),`

`MyComputeChecksum(),`

`MyDeparser() ) main;`

This code is useful for understanding the components which make up a definition of a P4 switch. In this course, we will not work with the checksum components, so you can always just use the same code as given in Project 0.

Then, we can think of a P4 program as defining the actions in each stage of a pipeline of the form:

Parser -> Ingress Processing -> Egress Processing -> Deparser

_Technically, there is also queuing between the Parser and Ingress Processing as well as the Ingress Processing and Egress Processing_

When a packet arrives at the P4 switch, it will go through this pipeline and leave through the port defined by the P4 program.

In this tutorial, we use `l2fwd.p4` as an example to walk through the key components you need to know in P4.

# Parser

To process packets at a switch, we first classify packets into classes (i.e., flows), and then define the operations for each class of packets (e.g., each flow). We define a flow based on a specific pattern of several packet header fields. For example, a flow can be defined as a specific combination of “five-tuple” (e.g., source IP=10.0.0.1, destination IP=10.0.0.15, protocol=TCP, source TCP port=2000, destination TCP port=8080). A flow can also be defined in wildcards (e.g., source IP=10.0.0.\*, destination IP=100.0.0.\*).

The parsing stage extracts headers and sets metadata information for an incoming packet. This information can be consumed by later stages in the pipeline.

You shouldn’t have to change the parser function signature in this course. That is, it should always look something like:

    parser MyParser(packet_in packet,
    out headers hdr,
    inout metadata meta,
    inout standard_metadata_t standard_metadata) {
    ...
    }

The packet object contains raw packet data. We will need to extract data from the raw packet and store them in the other objects in the function signature, as these will be the only data structures accessible to later stages of the pipeline.

The `standard_metadata` object contains information that is automatically set when a packet arrives at a switch, like arrival time. The complete definition of the object can be found in the P4_16 specification.

### Defining Headers and Metadata Structures

The headers and metadata structures are defined by you and will differ across programs that you write in this course. The specific structures of each protocol header (e.g. Ethernet, IP, UDP, TCP, VLAN etc.) is often given to you; though, you may find it useful at certain points to write custom protocol headers. Each protocol header is declared using the `header` keyword in place of a typical `struct` keyword.

 We use `header` to define a protocol header (e.g., Ethernet), which consists of several header fields. For example, we define `header ethernet_t` which includes `dstAddr`, `srcAddr`, and `etherType`. Each field needs to has a fixed number of bits as specified in the type (e.g., `bit<16>`).
Finally, we need to define `struct headers` to describe which packet headers are in the packet. In our example, we only need to use Ethernet header in packets. 

The metadata structure can consist of pretty much whatever you want. One common use is to store information that is computed in earlier stages for consumption in later stages in the packet pipeline.

**Note:** Not all of the fields that you define in the metadata and headers structures need to be set. For instance, if your program takes different actions for a TCP or UDP packet, you may include a field for both a TCP and UDP header in your headers structure. You can determine if a specific header field has been set by calling the `isValid()` function, and you can use the `setValid()` and `setInvalid()` member functions on header fields to control the output of the `isValid()` function.

### Writing a parser

The `parser` part is used to tell P4 switches which headers to parse in the incoming packets. In our example, we only parse the ethernet header for each packet. The `parser` takes as input the packet and metadata, outputting the parsed header and metadata.

For P4, it is perhaps best to think of a parser as a state machine. That is, a construct which begins in a certain state, performs some actions in a state, transitions to another state (maybe depending on some information stored in the packet), and continues along in this way until some end state is reached.

In P4, the beginning state of a parser is called `start` so that the beginning of a parser definition will look like:

    parser MyParser(packet_in packet,
    out headers hdr,
    inout metadata meta,
    inout standard_metadata_t standard_metadata) {

        state start {
            /* parse the ethernet header */
            packet.extract(hdr.ethernet);
            transition accept;
        }

    }

Each state is defined as a C-like program block. Then, there is some parsing that is done, in this case, calling the `extract` method on `packet` to get the Ethernet header data stored in the packet. Finally, there is a transition to `accept` which is the special end state to signal that parsing is complete.

It is often useful to choose the next state to transition to based on information in the last parsing step. For instance, if the packet contains IP data (has ethertype 0x800), we may want to extract the IP header data after extracting the Ethernet header data. However, if the packet does not contain IP data (ethertype other than 0x800), we may want to stop parsing. To perform this conditional parsing, you should use a `select` statement:

    parser MyParser(packet_in packet,
                out headers hdr,
                inout metadata meta,
                inout standard_metadata_t standard_metadata) {

        state start {
            /* parse the ethernet header */
            packet.extract(hdr.ethernet);
            transition select(hdr.ethernet.etherType) {
                0x800: parse_ipv4;
                default: accept
            };
        }

        state parse_ipv4 {
            packet.extract(hdr.ip4);
            transition accept;
        }
    }

The `select` statement lets you build more complex parsers and thus more complex data plane logic that relies on more packet information. While the P4 language also supports `switch` statements, they are not allowed to be used in the parser, so you should always use a `select` statement.

_Note: Packet headers must be parsed in order! At the start of packet parsing, there is no assumption made about the structure of packet data, instead the P4 packet is merely a bit array. Calling the extract method reads in the size of the header field in bits and then imposes the structure defined by the protocol header on those bits, moving a read pointer forward to allow for further extraction in later steps._

## Ingress Processing

This stage is perhaps the most complicated of the packet processing and where the data plane interfaces with the control plane (i.e., the controller in our case). Ingress processing includes a pipeline of *match-action tables*. 

### Match-Action Tables

You can think of a match-action table as a set of mapping rules between *keys* and *actions*. In the P4 program, we only specify the structure of the table in the compilation stage: how to form keys and the actions that are possible. The controller program later installs mapping rules in the match-action table at runtime. When the switch sees packets, it looks through the mapping rules in match-action tables and sees if packet information matches the key from any of the mappings and performing the action specified by that mapping. 

In the example below, we want to define a `dmac` table which is the forwarding table based on destination MAC address. P4 describes the structure of the table: keys are destination MAC/Ethernet addresses in packet headers `hdr.ethernet.dstAddr`, actions are `forward`, `drop`, or `NoAction`. The controller then installs rules in the table, such as:
- For `hdr.ethernet.dstAddr==00:00:00:00:00:00`, `drop` the packet.
- For `hdr.ethernet.dstAddr==00:00:0a:00:00:01`, `forward` to port number 1.

We now discuss the components in a match tables are themselves defined by several components: *keys* and *actions*.

#### Keys
In the table, a key is some collection of packet information for which you might want to take different actions on. The packet information are usually packet header fields such as destination IP, five-tuples. In the example below, the key is the Ethernet destination address (`dstAddr`). 

As you can see, we will use the destination MAC address parameter to match a packet and we will use the forwarding action that we created earlier as a possible action

For each key field, you should also specify a matching rule. For this course, we focus on two matching rules: `exact` and `lpm`. The `exact` rule is self-explanatory, a packet matches the mapping only if the packet data matches exactly the key installed by the controller. For Ethernet addresses, we usually do `exact` matches.

`lpm` is an acronym for longest-prefix matching. Most commonly used in combination with Layer-3 IP routing, the rule states that if the packet information matches some prefix key installed by the controller. If the packet matches more than one installed keys, the longest prefix key is used. For instance, say a match table specifies that a packet’s IPv4 address should be used as a key and that the controller installs two mappings with keys `192.168.*.*` and `192.168.254.*`. If a packet arrives at the switch with IPv4 address `192.168.0.0`, the first mapping will be used. However, if a packet arrives at the switch with IPv4 address `192.168.254.254`, the second mapping will be used because the address matches both keys but the second prefix is longer.

A table can use multiple fields as keys as well and they need not have the same match rules (e.g. both IPv4 destination and source addresses but one with `exact` matching and one with `lpm` matching) and a packet only takes the rule's actions when if the packet information matches all the keys according to their specified match rules.
For example, you can map on multiple fields like this: 
```
    key = { 
        hdr.xx: lpm; 
        meta.yy: exact; 
    }
```

#### Actions

This is simply a list of the possible actions that that the switch can perform at a table. Example actions include `forward` a packet, `drop` a packet, insert an VLAN tag into the packet header, or sending the packet to following tables.Typically, you should include `NoAction` in this list, as this can often be a suitable default action.

You can also define a `default_action` which will be performed if there is no rule installed by the controller which has a key matching packet data.

You should also define a `size` field for the table.

Action constructs are declared within the ingress processing block. Actions can be thought of almost like a function. You can define your own actions and they work in the p4 code to process the packets a certain way. 
 
Like functions, these constructs take some number of arguments and perform some computation using the information in those arguments or packet headers/metadata. However, `action`s cannot return any data as there is no well-defined caller in the P4 program. Instead, `action`s can store data in the `meta` object that may be consumed by downstream stages.

The arguments to actions will be set by the controller program when it installs mappings to a match table.

For example, the example below defines two action functions `drop` and `forward`. The `forward` function takes an argument of `egress_port` and sets the `egress_spec` in the `standard_metadata` to this port. Setting the `standard_metadata` tells the switch to which port to forward the packet. So when the controller installs mappings with a `forward` action, it should also specify the egress port the packet should forward to. 

#### Apply
Once a match table has been defined, they must be applied to have any effect. In the most simple case, this is achieved by calling the `apply()` member function of the table. This function returns an object which has as one of its member variables `action_run`: the action that was performed by the table on the packet being processed. This information can then be used to conditionally apply additional tables.

A complete example of a simple ingress processing component is given in the `p4src/l2fwd.p4` code and replicated here:

```
    control MyIngress(inout headers hdr,
    inout metadata meta,
    inout standard_metadata_t standard_metadata) {

        /* define two actions, drop and forward */
        action drop() {

            mark_to_drop(standard_metadata);
        }

        /* forward action takes as input the egress_port */
        /* set the output port to that argument */
        action forward(bit<9> egress_port) {
            standard_metadata.egress_spec = egress_port;
        }

        /* define the dmac table, serving as the forwarding table */
        table dmac {
            /* match the ethernet destination address */
            key = {
                hdr.ethernet.dstAddr: exact;
            }

            /* define the list of actions */
            actions = {
                forward;
                drop;
                NoAction;
            }
            size = 256;
            default_action = NoAction;
        }

        apply {

            dmac.apply();

        }

    }
```

The following example shows how to conditionally apply the second table: 
```
    apply {
        switch (table_a.apply().action_run) {
            action_name: {
                // code here to execute if table executed action_name
                table_b.apply();
            }
            default: {
                // Code here to execute if table executed any of the
                // actions not explicitly mentioned in other cases.
            }
        }
    }
```

## Egress Processing

This can typically be left as the default which is seen in Project 0. The only time it may useful to work with egress processing in this course is in relation to cloning/recirculating which is discussed later.

## Deparsing

Perhaps the easiest component of a P4 application is the deparsing stage. In this stage, we are undoing the work we did in the parsing stage. The `deparser` puts the packet header fields back together so the switch can send out the packets. 

In this stage, you will call the emit member function of the packet object and sequentially pass the headers that you extracted during the parsing stage. Then, if you extracted Ethernet and IP headers in the parsing stage, you will have a deparser that looks like

    control MyDeparser(packet_out packet, in headers hdr) {
        apply {
        /* deparse the ethernet header */
        packet.emit(hdr.ethernet);
        packet.emit(hdr.ip4);
        }
    }

**Note:** Like in parsing, deparsing must be done in-order with the outermost header of a packet being written first. Also, if a field of the hdr object is marked as invalid, then the P4 program will skip over the emission of that header. This can be useful when working with UDP or TCP traffic where only one of the headers should be marked as valid for a given packet, but your code can include both emission statements without error.

# Registers

Registers provides stateful storage for packet processing in P4. Essentially, registers are an array of counters with user-defined width that can be accessed and modified by every packet. It can be used to store state information for the ingress or egress pipeline. 

For example, the following code define a 8192 registers each with 48 bits in the ingress pipeline: 
```
control MyIngress(inout headers hdr, inout metadata meta,
                  inout standard_metadata_t standard_metadata) {
    register<bit<48>>(8192) register_array;
}
```

You can use read/write functions to access and modify specific register value in actions: 
* void read(result, bit<32> index): function to read the content of register at index. Stores the output at the variable result (which must have the same width). For example, 
    ```
    bit<48> register_value;
    register_array.read(register_value, 0);
    ```
* void write(bit<32> index, value): function that write vale (also with the same width) at the register index. 

# Controller-Side Operations

P4 controller is a separate piece of code that sets match-action rules for P4 program. The controller needs to be run after P4 program gets started. In this course, we focus on python-written controller. 

For example, assume action `set_nhop` in the table `ipv4_lpm` matches on pacekt `dst_ip`; the following code will set a match-action rule that tells the switch to route any packet with `dst_ip` of `10.0.0.1` to port 1: 
```
controller.table_add("ipv4_lpm", "set_nhop", ["10.0.0.1"], ["1"])
```

You can specify multiple matching keys as follows: 
```
controller.table_add("table_name", "action_name", [str(src_ip), str(dst_ip)], [str(num_nhops)])
```

You can specify multiple mapped values (i.e., action parameters): 
```
controller.table_add("ipv4_lpm", "ecmp_group", [str(dst_ip)], [str(ecmp_group_id), str(num_nhops)])
```

# Useful Functions

## Hash

Hashing is a function that map data of arbitrary size to fixed-size values. 
For example, in Project 3, when you implement the ECMP function which hashes on the five tuples of a flow, maps the flow to a fixed number of possible paths, and save the result in the metadata. For a more general description of hashing, you can reference [this article](https://medium.com/coinmonks/gentle-introduction-to-hashing-61295dbcc0c5).

P4 includes the built-in function `hash(...)` that implements several hash functions. The function takes several arguments:

1. The location to store the hash value. Typically, you use a metadata field.
2. The hashing algorithm to use. You typically want to use either `HashAlgorithm.crc16` or `HashAlgorithm.crc32`
3. The base for the hash algorithm (or the hash seed). You can just use `(bit<1>)0` or any number that satisfies the restrictions of the hash algorithm.
4. The fields to hash over following the form `{field1, field2, … }`
5. The maximum value of the hash output. For example, if you specify it as 2,your hash values are either 0 or 1. The maximum value is restricted to be a power of 2.

## Clone/Recirulate packets

When a packet arrives at a switch, it goes through each stage of the pipeline, and leaves the switch on a output port. Now we discuss an alternative option for the packet flow in P4 that is useful for your course projects. 
We introduce three functions: `clone`, `clone3`, and `recirculate`.

1. `clone(in CloneType type, in bit<32> session)`

    We use `clone` and `clone3` functions to replicate a packet. 
    - `in CloneType type` indicates the type of cloning to perform. This should be one of the following: `CloneType.I2E` or `CloneType.E2E`. `CloneType.I2E` means that the switch runs `clone` at the end of the ingress processing and sends two (distinguishable) copies of the packet to the egress pipeline once ingress processing is complete. `CloneType.E2E` means that the switch runs `clone` at the end of the egress processing as this sends the original packet on to its appropriate output port and sends the copy of the packet back to the beginning of the egress pipeline. 
    - `in bit<32> session` is the mirror id or session id. The switch uses the mirroring ID `mirror_session_id` to know to which port the packet should be cloned to. The controller can configure this mapping as follows:  
        ```
        def add_mirroring_ids(self):
            for sw_name, controller in self.controllers.items():
                controller.mirroring_add(100, 1)
        ```
        After specifying this mapping, the switch sends all the packets cloned with `mirror_session_id` of 100 to switch port 1. 

2. `clone3(in CloneType type, in bit<32> session, in T metadata)`

    `clone3` is similar to `clone` which also replicates a packet. The main difference is that it has a third argument `in T metadata`. This is the metadata object that you define and want to put in the cloned packet. The metadata field is the same as that on a normal packet as we described in the Parser part. 

3. `recirculate(in T metadata)`.

   The `recirculate` function does not replicate a packet. Instead, at the end of egress processing, the switch does not forward the packet to the network, but sends the packet to the beginning of the ingress pipeline again. 
   
   `in T metadata` indicates the metadata you put in the recirculated packet. However, there is a bug in `p4utils` library, for `recirculate` function to work properly: you should just call it with curly brackets as parameter, e.g., `recirculate({})` instead of putting a metadata. 

During ingress or egress processing, we can distinguish a cloned or recirculated packet from the regular packets by checking the value of the `standard_metadata.instance_type` field of the `standard_metadata_t` object. The mapping between packet types and values of this field can be found [here](https://github.com/p4lang/switch/blob/master/p4src/includes/intrinsic.p4#L74). You may find it useful to copy these definitions into your code to help distinguish between different types of packets.

**Note:** These functions do not have an immediate effect on packet processing. That is, any logic after the call to these functions will continue to operate as normal. It is not until the end of either ingress or egress processing (depending on the exact function call) that the cloning or recirculating actually happens.


# Miscellaneous

The `hdr`, `meta`, and `standard_metadata` object instances are per-packet instances that persist for the lifetime of a packet processing. That is, they are implicitly created at the beginning of a packet processing and are destroyed once a packet leaves a switch.

Like in other programming languages, you may find it useful to isolate type definitions from actual logic in a declaration-definition paradigm.

Later on in the course when ingress and egress processing become more complex, you may also find it useful to separate parsing and deparsing logic from those components.

You may not be able to use certain types of statements (often conditional statements) in certain parts of a P4 program. For instance, you may not use conditional statements like “if” or “switch” in actions. Instead, you must rely on selectively applying tables and installing appropriate rules via the controller program. More information about restrictions like these may be found in the [P4 spec](https://p4.org/p4-spec/docs/P4-16-v1.2.1.pdf). However, you may find it more time effective to test out if you can include certain statements in code locations by including them and then trying to compile the P4 program. There are often good error messages that indicate whether or not certain statements are prohibited.

# Further Reading

https://p4.org/p4-spec/docs/P4-16-v1.2.1.pdf - The complete specification of the P4_16 language. Pretty dense, but useful as a reference.

https://github.com/p4lang/tutorials - Tutorials on how to complete a variety computations. In particular, here're some [slides](https://github.com/p4lang/tutorials/blob/master/P4_tutorial.pdf).

https://p4.org/p4-spec/docs/PSA.html#sec-clone - The whole document may be useful, but I include this section which begins with a discussion of cloning, followed by resubmission (which we don’t focus on), and then recirculation.
