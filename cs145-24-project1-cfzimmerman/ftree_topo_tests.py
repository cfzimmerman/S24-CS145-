from ftree_topo import Topo
from typing import List, Tuple

# This file is to help test and visually debug link assignment

k = 4
topo = Topo(k)

for host in range(topo.MIN_ID, topo.HOST_CT + topo.MIN_ID):
    tor = topo.tor_from_host(host)
    print(f"host: {host}, tor: {tor}, dmac: {topo.host_dmac(host)}")

for tor in range(topo.MIN_ID, topo.TOR_CT + topo.MIN_ID):
    tor_name = topo.tor_name(tor)
    (tp, num) = topo.id_node(tor_name)
    assert tp == topo.TOR and num == tor

    print(f"tor: {tor}, agg: {topo.aggs_from_tor(tor)}")

for agg in range(topo.MIN_ID, topo.AGG_CT + topo.MIN_ID):
    agg_name = topo.agg_name(agg)
    (tp, num) = topo.id_node(agg_name)
    assert tp == topo.AGG and num == agg

    print(f"agg: {agg}, core: {topo.cores_from_agg(agg)}")

for core in range(topo.MIN_ID, topo.CORE_CT + topo.MIN_ID):
    core_name = topo.core_name(core)
    (tp, num) = topo.id_node(core_name)
    assert tp == topo.CORE and num == core


print(f"\nmax host_id: {topo.HOST_CT}")
print(f"max tor_id: {topo.TOR_CT}")
print(f"max agg_id: {topo.AGG_CT}")
print(f"max core id: {topo.CORE_CT}")


def gen_top_down_links():
    top_down_links: List[Tuple[str, str]] = []
    for core in range(topo.MIN_ID, topo.CORE_CT + topo.MIN_ID):
        core_name = topo.core_name(core)
        for agg in topo.aggs_from_core(core):
            top_down_links.append((topo.agg_name(agg), core_name))

    for agg in range(topo.MIN_ID, topo.AGG_CT + topo.MIN_ID):
        agg_name = topo.agg_name(agg)
        for tor in topo.tors_from_agg(agg):
            top_down_links.append((topo.tor_name(tor), agg_name))

    for tor in range(topo.MIN_ID, topo.TOR_CT + topo.MIN_ID):
        tor_name = topo.tor_name(tor)
        for host in topo.hosts_from_tor(tor):
            top_down_links.append((topo.host_name(host), tor_name))

    return top_down_links


def gen_bottom_up_links() -> List[Tuple[str, str]]:
    bottom_up_links: List[Tuple[str, str]] = []
    for host in range(topo.MIN_ID, topo.HOST_CT + topo.MIN_ID):
        tor = topo.tor_from_host(host)
        bottom_up_links.append((topo.host_name(host), topo.tor_name(tor)))

    for tor in range(topo.MIN_ID, topo.TOR_CT + topo.MIN_ID):
        tor_name = topo.tor_name(tor)
        for agg in topo.aggs_from_tor(tor):
            bottom_up_links.append((tor_name, topo.agg_name(agg)))

    for agg in range(topo.MIN_ID, topo.AGG_CT + topo.MIN_ID):
        agg_name = topo.agg_name(agg)
        for core in topo.cores_from_agg(agg):
            bottom_up_links.append((agg_name, topo.core_name(core)))

    return bottom_up_links


top_down_links = gen_top_down_links()
bottom_up_links = gen_bottom_up_links()
top_down_links.sort()
bottom_up_links.sort()
assert top_down_links == bottom_up_links

print("✅ Tests passed")
