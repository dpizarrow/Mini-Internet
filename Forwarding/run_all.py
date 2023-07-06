import router_ttl as rttl
import router as r
import threading as th
import sys

from colorama import Fore


colors = [Fore.RED, Fore.BLUE, Fore.GREEN, Fore.MAGENTA, Fore.YELLOW, Fore.BLACK, Fore.WHITE]

def create_routers(num_routers, version):
    for i in range(0, num_routers):
        router = r.Router("127.0.0.1", 8880 + i, f"{version}/rutas_R{i}_{version}.txt", colors[i - 1])
        thread = th.Thread(target=router.run, args=())
        thread.start()

def create_routers_ttl(num_routers, version):
    for i in range(1, num_routers + 1):
        router = rttl.Router("127.0.0.1", 8880 + i, f"{version}/rutas_R{i}_{version}.txt", colors[i - 1])
        thread = th.Thread(target=router.run, args=())
        thread.start()

if __name__ == "__main__":
    num_router = int(sys.argv[1])
    version = sys.argv[2]
    ttl = int(sys.argv[3])
    
    # If a ttl is specified, create the routers with ttl

    if ttl:
        create_routers_ttl(num_router, version)
    else:
        create_routers(num_router, version)