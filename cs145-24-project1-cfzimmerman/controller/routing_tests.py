import sys
import os
from typing import Set, Dict, List

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))  # noqa: E402
sys.path.insert(0, parent_dir)  # noqa: E402
from ftree_topo import Topo
from routing import OneCoreRoutes, MultiCoreRoutes, Routes

# python routing_tests.py _
# Fill in the underscore above with 4, 6, or, 8
k = int(sys.argv[1])
topo = Topo(k)


# Panics if the dmacs in routes aren't equal to the dmacs in expected
def assert_dmac_coverage(expected_dmacs: Set[str], routes: Routes):
    route_dmacs: Set[str] = set()
    for (dmac, _) in routes:
        route_dmacs.add(dmac)
    assert route_dmacs == expected_dmacs


# Returns the number of addresses assigned to each port
def port_census(routes: Routes) -> List[int]:
    counts: Dict[int, int] = {}
    for (_, port) in routes:
        if port not in counts:
            counts[port] = 0
        counts[port] += 1

    return [counts[port] for port in counts]


expected_dmacs: Set[str] = set()
for host in range(topo.MIN_ID, topo.HOST_CT + topo.MIN_ID):
    expected_dmacs.add(topo.host_dmac(host))

'''ONECORE'''

# Test OneCore TOR routing coverage
for tor in range(topo.MIN_ID, topo.TOR_CT + topo.MIN_ID):
    routes = OneCoreRoutes.tor(topo, tor)
    assert_dmac_coverage(expected_dmacs, routes)

    ports = port_census(routes)
    assert len(ports) == topo.half_k + 1

    ports.sort()
    assert ports.pop() == (topo.HOST_CT - topo.half_k)
    assert ports == [1] * topo.half_k

    # print("tor: ", tor)
    # print(routes)

# Test OneCore Aggregator routing coverage
for agg in range(topo.MIN_ID, topo.AGG_CT + topo.MIN_ID):
    routes = OneCoreRoutes.agg(topo, agg)
    assert_dmac_coverage(expected_dmacs, routes)

    ports = port_census(routes)
    assert len(ports) == topo.half_k + 1

    ports.sort()
    assert ports.pop() == topo.HOST_CT - (topo.half_k ** 2)
    assert ports == [topo.half_k] * topo.half_k

    # print("agg: ", agg)
    # print(sorted(routes))

# Test OneCore Core routing coverage
for core in range(topo.MIN_ID, topo.CORE_CT + topo.MIN_ID):
    routes = OneCoreRoutes.core(topo, core)
    assert_dmac_coverage(expected_dmacs, routes)

    ports = port_census(routes)
    assert len(ports) == topo.k
    assert ports == [topo.half_k ** 2] * topo.k

    # print("core: ", core)
    # print(routes)

'''MULTICORE'''

# Test MultiCore Aggregator routing coverage
for agg in range(topo.MIN_ID, topo.AGG_CT + topo.MIN_ID):
    routes = MultiCoreRoutes.agg(topo, agg)
    assert_dmac_coverage(expected_dmacs, routes)

    ports = port_census(routes)
    ports.sort()

    assert ports.pop() + ports.pop() == topo.HOST_CT - (topo.half_k ** 2)
    assert ports == [topo.half_k] * topo.half_k

    # print("agg: ", agg)
    # print(sorted(routes))

# Test MultiCore Core routing coverage
for core in range(topo.MIN_ID, topo.CORE_CT + topo.MIN_ID):
    routes = MultiCoreRoutes.core(topo, core)
    assert_dmac_coverage(expected_dmacs, routes)

    ports = port_census(routes)
    assert ports == [topo.HOST_CT // topo.k] * topo.k

print("✅ passed routing tests")
