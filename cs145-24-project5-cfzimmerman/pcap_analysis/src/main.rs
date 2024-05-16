use clap::{Parser, Subcommand};
use csv::Writer;
use pcap_analysis::{
    flows::PcapAnalyzer,
    output::{CsvFiveTuple, CsvFlowletPath},
};
use std::{
    collections::HashMap,
    fs::File,
    io::{stdout, BufWriter, Write},
    path::PathBuf,
    time::Duration,
};

/// Cli program to extract data from mininet pcap files.
/// The network is expected to log Eth(Ipv4) frames and use
/// flowlet-based switching.
#[derive(Parser, Debug)]
#[command(about)]
pub struct CliArgs {
    /// Path to a directory containing .pcap files
    pcap_dir: PathBuf,

    /// Desired path for the output csv. The file is opened in truncate mode.
    /// Optional - defaults to stdout.
    csv_path: Option<PathBuf>,

    #[command(subcommand)]
    parse_mode: ParseMode,
}

#[derive(Debug, Subcommand)]
pub enum ParseMode {
    /// Prints out all the unique five tuples processed in the pcap files.
    FiveTuples,
    /// Extracts and aggregates all the flowlets between ip addresses logged
    /// by the pcap files
    ///
    /// Paths are determined by timestamp frequency within a window.
    Flowlets {
        /// How long a switch waits before starting a new flowlet in milliseconds.
        window_ms: u64,
    },
}

fn main() -> anyhow::Result<()> {
    let args = CliArgs::parse();
    let pcaps = PcapAnalyzer::list_pcap_files(&args.pcap_dir)?;
    let mut tracker = PcapAnalyzer::default();

    let mut line_ct = 0;
    for pcap in pcaps {
        match tracker.load_pcap(&pcap) {
            Ok(ct) => line_ct += ct,
            Err(e) => {
                if !e.to_string().contains("End of file") {
                    eprintln!("error on {:?}", pcap.as_path());
                    eprintln!("{:#?}", e);
                }
                continue;
            }
        }
    }
    let writer: Box<dyn Write> = match args.csv_path {
        Some(path) => Box::new(BufWriter::new(File::create(path)?)),
        None => Box::new(stdout()),
    };
    let mut csv = Writer::from_writer(writer);

    match args.parse_mode {
        ParseMode::FiveTuples => {
            let mut five_tuples: HashMap<CsvFiveTuple, usize> = HashMap::new();
            for ((ip_src, ip_dst), flow) in &mut tracker.flows {
                for pkt in flow.inspect_packets() {
                    *five_tuples
                        .entry(CsvFiveTuple {
                            source_ip: *ip_src,
                            dest_ip: *ip_dst,
                            protocol: pkt.ip_protocol.clone(),
                            src_port: pkt.tcp_src_port,
                            dst_port: pkt.tcp_dst_port,
                            freq: None,
                        })
                        .or_default() += 1;
                }
            }
            for (mut five_tuple, freq) in five_tuples {
                five_tuple.freq = Some(freq);
                csv.serialize(five_tuple)?;
            }
        }
        ParseMode::Flowlets { window_ms } => {
            for ((ip_src, ip_dst), flow) in &mut tracker.flows {
                if let Some(ref flowlet_list) =
                    flow.aggregate_flowlets(Duration::from_millis(window_ms))
                {
                    for (sw_list, hit_ct) in flowlet_list {
                        csv.serialize(CsvFlowletPath::new(*ip_src, *ip_dst, *hit_ct, sw_list))?;
                    }
                }
            }
        }
    }

    // println!("{:?}", tracker.flows.keys().collect::<Vec<_>>());
    println!("Lines parsed: {line_ct}");
    Ok(())
}
