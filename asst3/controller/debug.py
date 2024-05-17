from routing import MultiCoreRoutes
from ftree_topo import Topo

topo = Topo(4)

for t in range(1, topo.AGG_CT + 1):
    target = f"a{t}"
    print("\n", target)
    for entry in MultiCoreRoutes.get_routes(topo, target):
        print(entry)
