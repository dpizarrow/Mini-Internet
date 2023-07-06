import sys 
import socket

from colorama import Fore, Style

def print_with_color(text, color):
    print(f"{color}{repr(text)}{Style.RESET_ALL}")
    

class Router:
    def __init__(self, ip: str, port: int, table_path: str, color = Fore.WHITE) -> None:
        
        """
        Initialize a Router object

        Args:
            ip (str): IP of the router
            port (int): Port of the router
            table_path (str): Path to the routing table file
            color: Color for the router prints. Default is white
        """        
        self.ip = ip
        self.port = int(port)
        self.table_path = table_path
        self.color = color

        print_with_color(f"Router {self.ip}:{self.port} using table file {self.table_path}", self.color)

        # Create a socket and bind it to the router IP and port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.ip, self.port))

        self.route_list = None

        # Read the routing table file and fill the route_list

        self.read_routing_table()

    def parse_packet(self, packet:bytes) -> dict:

        """
        Parse a packet into a dictionary

        Args:
            packet (bytes): Packet to parse. Each packet has the format IP,Port,Message
        Returns:
            dict: Dictionary with the packet information
        """        

        packet = packet.decode()
        packet = packet.split(',')

        return {
            'IP': packet[0],
            'Port': int(packet[1]),
            'Message': packet[2]
        }
    
    def create_packet(self, parsed_packet:dict) -> str:

        """
        Create a packet from a dictionary

        Args:
            parsed_packet (dict): Dictionary with the packet information
        Returns:
            str: Packet with the format IP,Port,Message
        """        

        return f"{parsed_packet['IP']},{parsed_packet['Port']},{parsed_packet['Message']}"
    
    def read_routing_table(self) -> None:
        with open(self.table_path, 'r') as f:
            self.route_list = f.readlines()
            self.route_list = [x.strip() for x in self.route_list]

    def check_routes(self, ip: str, port: int) -> bool:
        for route in self.route_list:
            route = route.split(' ')
            
            port_low = int(route[1])
            port_high = int(route[2])
            if ip == route[0] and port in range(port_low, port_high + 1):

                hop_ip = route[3]
                hop_port = int(route[4])

                print_with_color(f"Removing route {route}", self.color)
                # Move the route to the end of the list
                self.route_list.remove(' '.join(route))
                self.route_list.append(' '.join(route))

                return (hop_ip, hop_port)
        return None

    def forward_packet(self, packet: dict, forward_address: tuple) -> None:
            
            """
            Forward a packet to the next hop
    
            Args:
                packet (dict): Packet to forward
            """        
    
            # Create a packet from the dictionary

            packet = self.create_packet(packet)
    

            # Send the packet to the next hop
            self.sock.sendto(packet.encode(), forward_address)

    def run(self) -> None:

        """
        Main loop of the router. It waits for packets and forwards them if necessary
        """        

        # Wait in a loop for packets

        while True:
            packet, _ = self.sock.recvfrom(1024)
            packet = self.parse_packet(packet)

            print_with_color(f"Received packet: {packet}", self.color)

            # If the packet is for the router, print it

            if packet['IP'] == self.ip and packet['Port'] == self.port:
                print_with_color(f"Message from {packet['IP']}:{packet['Port']}: {packet['Message']}", self.color)

            else:

                # Check if there is a route to the destination address

                route = self.check_routes(packet['IP'], int(packet['Port']))

                # If there is a route, forward the packet

                if route:
                    print_with_color(f"Redirecting message for {packet['IP']}:{packet['Port']} to {route[0]}:{route[1]}", self.color)
                    self.forward_packet(packet, route)
                else:

                    # No route found, print the error

                    print_with_color(f"No routes found to {packet['IP']}:{packet['Port']}", self.color)


if __name__ == '__main__':
    router_ip = sys.argv[1]
    router_port = int(sys.argv[2])
    router_table_file = sys.argv[3]

    router = Router(router_ip, router_port, router_table_file)
    router.run()
    

    



