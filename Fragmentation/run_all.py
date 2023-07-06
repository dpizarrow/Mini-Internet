
import router as r
import threading as th
import sys

from colorama import Fore


colors = [Fore.RED, Fore.BLUE, Fore.GREEN, Fore.MAGENTA, Fore.YELLOW]

def create_routers(num_routers):
    for i in range(1, num_routers + 1):
        router = r.Router("127.0.0.1", 8880 + i, f"rutas/rutas_R{i}_v3_mtu.txt", colors[i - 1])
        thread = th.Thread(target=router.run, args=())
        thread.start()

if __name__ == "__main__":
    num_router = int(sys.argv[1])
    create_routers(num_router)
    

    
