use anyhow::bail;
use pcap_parser::{create_reader, PcapBlockOwned};
use pnet::packet::{
    ethernet::{EtherTypes, EthernetPacket},
    ip::IpNextHeaderProtocols,
    ipv4::Ipv4Packet,
    tcp::TcpPacket,
    Packet,
};
use std::{
    cmp::Ordering,
    collections::{BinaryHeap, HashMap, HashSet},
    fs::{read_dir, File},
    io::BufReader,
    net::Ipv4Addr,
    path::{Path, PathBuf},
    rc::Rc,
    time::Duration,
};

pub type FlowletPath = Box<[Rc<MininetSwitch>]>;

/// Used to track packet logs associated with a given (ip to ip) flow.
#[derive(Debug, Default)]
pub struct FlowLogs {
    packets: BinaryHeap<TimestampAsc>,
}

impl FlowLogs {
    pub fn inspect_packets(&self) -> impl Iterator<Item = &PacketSnapshot> {
        self.packets.iter().map(|wrapper| &wrapper.0)
    }

    /// Adds the given packet to the internal log tracker
    fn add_packet(&mut self, pkt: PacketSnapshot) {
        self.packets.push(TimestampAsc(pkt))
    }

    /// Given a flowlet tracker, drains the contents, sorts them, and returns an
    /// immutable list of the switch names in that flowlet.
    fn finish_flowlet(flows: &mut HashSet<Rc<MininetSwitch>>) -> FlowletPath {
        let mut listed: Vec<Rc<MininetSwitch>> = flows.drain().collect();
        listed.sort();
        listed.into()
    }

    /// Drains self-contained packet data, aggregating individual packets into flowlets
    /// based on timestamps.
    pub fn aggregate_flowlets(&mut self, timeout: Duration) -> Option<HashMap<FlowletPath, usize>> {
        let Some(mut last_time) = self.packets.peek().map(|pkt| pkt.0.timestamp) else {
            return None;
        };
        let mut flowlets: HashMap<FlowletPath, usize> = HashMap::new();

        let mut in_flow: HashSet<Rc<MininetSwitch>> = HashSet::new();
        let mut hit_count: usize = 0;

        while let Some(pkt) = self.packets.pop() {
            let pkt = pkt.0;
            if pkt.timestamp > last_time + timeout {
                *flowlets
                    .entry(Self::finish_flowlet(&mut in_flow))
                    .or_default() += hit_count;
                hit_count = 0;
            }
            last_time = pkt.timestamp;
            hit_count += 1;
            in_flow.insert(pkt.sw_name);
        }
        if !in_flow.is_empty() {
            *flowlets
                .entry(Self::finish_flowlet(&mut in_flow))
                .or_default() += hit_count;
        }

        Some(flowlets)
    }
}

/// Contains the metadata held for each packet on an (ip to ip) flow
#[derive(Debug, PartialEq, Eq)]
pub struct PacketSnapshot {
    pub timestamp: Duration,
    pub ip_protocol: String,
    pub tcp_src_port: u16,
    pub tcp_dst_port: u16,
    pub sw_name: Rc<MininetSwitch>,
}

/// Supports retrieving, parsing, and analyzing Eth + Ipv4 flows tracked
/// in pcap files.
#[derive(Debug, Default)]
pub struct PcapAnalyzer {
    pub flows: HashMap<(Ipv4Addr, Ipv4Addr), FlowLogs>,
}

#[derive(Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct MininetSwitch(String);

impl MininetSwitch {
    pub fn get(&self) -> &str {
        &self.0
    }
}

impl PcapAnalyzer {
    /// Given a directory of pcap files, reads the contents and returns an
    /// iterator over all files with the ".pcap" extension.
    pub fn list_pcap_files(dir_path: &Path) -> anyhow::Result<impl Iterator<Item = PathBuf>> {
        Ok(read_dir(dir_path)?
            .flatten()
            .map(|entry| entry.path())
            .filter(|path| {
                let Some(ext) = path.extension() else {
                    return false;
                };
                ext == "pcap"
            }))
    }

    /// Returned the pcap info from a mininet-generated pcap file
    fn mininet_pcap(path: &Path) -> Option<MininetSwitch> {
        let Some(name) = path.file_name().and_then(|os_name| os_name.to_str()) else {
            return None;
        };
        let mut dash_split = name.split('-');
        let Some(sw_name) = dash_split.next() else {
            return None;
        };
        Some(MininetSwitch(sw_name.to_string()))
    }

    /// Given a path to a pcap file, opens it, parses the contents, and adds them
    /// to an internal flow tracker.
    /// Pcap contents are only parsed if they're in the form of Eth(Ipv4(_))
    /// Returns the number of lines read.
    pub fn load_pcap(&mut self, path: &Path) -> anyhow::Result<usize> {
        let mut pcap_iter = create_reader(65_536, BufReader::new(File::open(path)?))?;
        let Some(pcap_metadata) = Self::mininet_pcap(path) else {
            bail!("Failed to parse pcap metadata");
        };
        let pcap_metadata = Rc::new(pcap_metadata);
        let mut lines_read = 0;
        while let Ok((size, block)) = pcap_iter.next() {
            lines_read += 1;
            let PcapBlockOwned::Legacy(block) = block else {
                pcap_iter.consume(size);
                continue;
            };
            let timestamp = Duration::new(block.ts_sec.into(), block.ts_usec * 1000);
            let Some(eth_frame) = EthernetPacket::new(block.data) else {
                eprintln!("Failed to parse eth frame");
                pcap_iter.consume(size);
                continue;
            };
            if eth_frame.get_ethertype() != EtherTypes::Ipv4 {
                pcap_iter.consume(size);
                continue;
            }
            let Some(ip_frame) = Ipv4Packet::new(eth_frame.payload()) else {
                eprintln!("Failed to parse ipv4 frame");
                pcap_iter.consume(size);
                continue;
            };
            if ip_frame.get_next_level_protocol() != IpNextHeaderProtocols::Tcp {
                eprintln!(
                    "Encountered non-Tcp transport: {:?}",
                    ip_frame.get_next_level_protocol()
                );
                pcap_iter.consume(size);
                continue;
            }
            let Some(tcp_frame) = TcpPacket::new(ip_frame.payload()) else {
                eprintln!("Failed to parse tcp frame");
                pcap_iter.consume(size);
                continue;
            };
            let pkt = PacketSnapshot {
                timestamp,
                ip_protocol: ip_frame.get_next_level_protocol().to_string(),
                tcp_src_port: tcp_frame.get_source(),
                tcp_dst_port: tcp_frame.get_destination(),
                sw_name: pcap_metadata.clone(),
            };
            self.flows
                .entry((ip_frame.get_source(), ip_frame.get_destination()))
                .or_default()
                .add_packet(pkt);
            pcap_iter.consume(size);
        }
        Ok(lines_read)
    }
}

/// Inverts ordering on packet timestamps so lowest times show
/// up highest in the heap.
#[derive(Debug)]
struct TimestampAsc(PacketSnapshot);

impl PartialEq for TimestampAsc {
    fn eq(&self, other: &Self) -> bool {
        self.0.timestamp.eq(&other.0.timestamp)
    }
}

impl Eq for TimestampAsc {}

impl PartialOrd for TimestampAsc {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(match self.0.timestamp.cmp(&other.0.timestamp) {
            Ordering::Less => Ordering::Greater,
            Ordering::Equal => Ordering::Equal,
            Ordering::Greater => Ordering::Less,
        })
    }
}

impl Ord for TimestampAsc {
    fn cmp(&self, other: &Self) -> Ordering {
        self.partial_cmp(other)
            .expect("partial_cmp always returns Some")
    }
}
