use crate::flows::FlowletPath;
use serde::{Deserialize, Serialize};
use std::net::Ipv4Addr;

#[derive(Debug, Serialize, Deserialize)]
pub struct CsvFlowletPath {
    source_ip: Ipv4Addr,
    dest_ip: Ipv4Addr,
    hits: usize,
    switches: String,
}

impl CsvFlowletPath {
    pub fn new(source_ip: Ipv4Addr, dest_ip: Ipv4Addr, hits: usize, path: &FlowletPath) -> Self {
        let mut switches = String::with_capacity(path.len() * 4);
        for sw_name in path.iter() {
            if !switches.is_empty() {
                switches.push(' ');
            }
            switches.push_str(sw_name.get());
        }
        CsvFlowletPath {
            source_ip,
            dest_ip,
            hits,
            switches,
        }
    }
}

#[derive(Debug, Serialize, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct CsvFiveTuple {
    pub source_ip: Ipv4Addr,
    pub dest_ip: Ipv4Addr,
    pub protocol: String,
    pub src_port: u16,
    pub dst_port: u16,
    pub freq: Option<usize>,
}
