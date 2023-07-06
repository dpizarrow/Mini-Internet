import sys 
import socket

from colorama import Fore, Style

from random import randrange

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
        self.fragment_dict = {}
        self.asn_list = []

        # Read the routing table file and fill the route_list

        self.read_routing_table()

        # Generate the ASN list from the route_list

        self.generate_asn()

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
            'TTL': int(packet[2]),
            'ID': int(packet[3]),
            'Offset': int(packet[4]),
            'Size': packet[5],
            'Flag': int(packet[6]),
            'Message': packet[7]
        }
    
    def create_packet(self, parsed_packet:dict) -> str:

        """
        Create a packet from a dictionary

        Args:
            parsed_packet (dict): Dictionary with the packet information
        Returns:
            str: Packet with the format IP,Port,Message
        """        

        return ','.join([str(v) for v in parsed_packet.values()])
    
    def read_routing_table(self) -> None:
        
        """
        Read the routing table file and fill the route_list
        """  

        with open(self.table_path, 'r') as f:
            self.route_list = f.readlines()
            self.route_list = [x.strip() for x in self.route_list]

    def generate_asn(self) -> None:

        """
        Generate the ASN list from the route_list
        """        

        for route in self.route_list:
            # ASN is everything except the first and last 3 elements
            asn = route.split(' ')[1:-3]
            self.asn_list.append(asn)

    def create_BGP_message(self) -> str:
        
        """
        Create a BGP message from the route_list

        Returns:
            str: Message with the format BGP_ROUTES Port ASN1 ASN2 ASN ... END_ROUTES
        """        
        bgp_message = 'BGP_ROUTES\n'
        bgp_message += f'{self.port}\n'
        for route in self.route_list:
            # Exclude the first and las 3 elements
            asn = route.split(' ')[1:-3]
            bgp_message += f'{" ".join(asn)}\n'
        bgp_message += 'END_ROUTES'
        return bgp_message
    
    def get_neighbors(self) -> list:
        
        """

        Get a list of neighbors from the route_list

        Returns:
            list: List of neighbors with the format (IP, Port)
        """        
        neighbors = []
        for route in self.route_list:
            route = route.split(' ')
            neighbors.append((route[3], int(route[4])))
        return neighbors
    
    def extract_BGP_routes(self, bgp_message: str) -> list:
        
        """
        Extract the BGP routes from a BGP message

        Args:
            bgp_message (str): BGP message with the format BGP_ROUTES Port ASN1 ASN2 ASN ... END_ROUTES

        Returns:
            list: List of BGP routes with the format [ASN1, ASN2, ASN, ...]
        """        
        bgp_message = bgp_message.split('\n')
        bgp_message = bgp_message[2:-1]
        bgp_message = [x.split(' ') for x in bgp_message]
        return bgp_message
    

    def create_start_BGP(self, neighbor: tuple) -> str:
        
        """
        Create a START_BGP message to send to a neighbor

        Args:
            neighbor (tuple): Neighbor address with the format (IP, Port)

        Returns:
            str: IP Packet with the START_BGP message
        """        
        start_bgp_message = {
            'IP': neighbor[0],
            'Port': neighbor[1],
            'TTL': 20,
            'ID': str(randrange(1000)),
            'Offset': 0,
            'Size': str(len("START_BGP")).zfill(8),
            'Flag': 0,
            'Message': "START_BGP"
        }

        start_bgp_message = self.create_packet(start_bgp_message)

        return start_bgp_message
    
    def create_BGP_routes(self, neighbor: tuple) -> str:

        """
        Create a BGP_ROUTES message to send to a neighbor

        Args:
            neighbor (tuple): Neighbor address with the format (IP, Port)

        Returns:
            str: IP Packet with the BGP_ROUTES message
        """

        bgp_routes = self.create_BGP_message()
            
        bgp_message_packet = {
            'IP': neighbor[0],
            'Port': neighbor[1],    
            'TTL': 20,
            'ID': str(randrange(1000)),
            'Offset': 0,
            'Size': str(len(bgp_routes)).zfill(8),
            'Flag': 0,
            'Message': bgp_routes
        }

        bgp_message_packet = self.create_packet(bgp_message_packet)
        return bgp_message_packet

    def run_BGP(self) -> None:
        
        """
        Run the BGP algorithm
        """        

        # Set timeout to 10 seconds

        self.sock.settimeout(10)
        neighbors = self.get_neighbors()
        
        # Send a START_BGP message to each neighbor

        for neighbor in neighbors:
            start_bgp_message = self.create_start_BGP(neighbor)

            bgp_message_packet = self.create_BGP_routes(neighbor)

            self.sock.sendto(start_bgp_message.encode(), neighbor)
            self.sock.sendto(bgp_message_packet.encode(), neighbor)

        while True:
            try:
                packet, _ = self.sock.recvfrom(1024)
                packet = self.parse_packet(packet)
            
            # We enter here if the timeout is reached

            except:
                print_with_color(f"Router {self.ip}:{self.port} finished BGP", self.color)
                table = self.generate_routing_table()
                print_with_color(f'Routing table after BGP {table}', self.color)
                self.sock.settimeout(None)

                # Update self.route_list
                self.table_path = f'rutas/BGP_{self.port}.txt'
                self.read_routing_table()
                break
            else:

                # If we receive a START_BGP message, we ignore it

                if packet['Message'] == 'START_BGP':
                    continue

                recv_routes = self.extract_BGP_routes(packet['Message'])

                modified = False
                for route in recv_routes:
                    # If the route is to itself, ignore it
                    if str(self.port) in route:
                        continue

                    known = False
                    found_idx = None
                    for idx, r in enumerate(self.asn_list):
                        if route[0] == r[0]:
                            known = True
                            found_idx = idx
                            break
                    
                    # If we don't know the route, add it to the list

                    if not known:
                        updated_route = route + [str(self.port)]
                        self.asn_list.append(updated_route)
                        modified = True

                    # If we know the route, update it if it's shorter
                    
                    if known:
                        updated_route = route + [str(self.port)]
                        if len(updated_route) < len(self.asn_list[found_idx]):
                            self.asn_list[found_idx] = updated_route
                            modified = True

                # If we modified the list, send the new routes to all neighbors
                
                if modified:
                    for neighbor in neighbors:
                        bgp_routes = self.asn_list
                        
                        # print_with_color(f"Sending to {neighbor}: {bgp_routes}", self.color)
                        bgp_routes = 'BGP_ROUTES\n' + f'{self.port}\n' + '\n'.join([' '.join(x) for x in bgp_routes]) + '\nEND_ROUTES'
                        bgp_message = {
                            'IP': neighbor[0],
                            'Port': neighbor[1],
                            'TTL': 20,
                            'ID': str(randrange(1000)),
                            'Offset': 0,
                            'Size': str(len(bgp_routes)).zfill(8),
                            'Flag': 0,
                            'Message': bgp_routes
                        }
                        bgp_message_packet = self.create_packet(bgp_message)
                        print_with_color(f"Sending to {neighbor}: {bgp_routes}", self.color)
                        self.sock.sendto(bgp_message_packet.encode(), neighbor)

    def generate_routing_table(self) -> list:

        """
        Generate the routing table and write it to a file

        Returns:
            list: List of entries in the new routing table
        """        

        entries = []
        for asn in self.asn_list:
            for route in self.route_list:
                full_route = route.split(' ')
                route = route.split(' ')[1:-3]

                # If the ASN is the last one in the route, it's the destination

                if asn[-2] == route[0]:
                    dest_ip = full_route[-3]
                    dest_port = full_route[-2]
                    break
            entries.append(f'127.0.0.1 {" ".join([str(a) for a in asn])} {dest_ip} {dest_port} 1000')
        
        with open(f'rutas/BGP_{self.port}.txt', 'w') as f:
            f.write('\n'.join(entries))

        print_with_color(f'Wrote routing table to rutas/BGP_{self.port}.txt', self.color)

        return entries                    


    def check_routes(self, ip: str, port: int) -> tuple:

        """
        Check if a route to a destination exists

        Args:
            ip (str): IP of the destination
            port (int): Port of the destination
        
        Returns:
            tuple: Tuple containing the next hop IP, port and MTU, or None if the route doesn't exist
        """        

        hop_ip = None
        hop_port = None
        hop_mtu = None

        for route in self.route_list:
            route = route.split(' ')
            dest_port = int(route[1])
            
            if ip == route[0] and port == dest_port:
                hop_ip = route[-3]
                hop_port = int(route[-2])
                hop_mtu = int(route[-1])
                break  # Exit the loop since the desired route is found
        
        if hop_ip is not None:
            return (hop_ip, hop_port, hop_mtu)
        else:
            return None


    def forward_packet(self, packet: dict, forward_address: tuple) -> None:
            
            """
            Forward a packet to the next hop
    
            Args:
                packet (dict): Packet to forward
            """        
    
            # Create a packet from the dictionary

            packet['TTL'] -= 1

            packet = self.create_packet(packet)
    

            # Send the packet to the next hop
            self.sock.sendto(packet.encode(), forward_address)

    def fragment_IP_packet(self, packet: dict, mtu: int) -> list:
        packet_str = self.create_packet(packet)
        packet_size = len(packet_str.encode())
        packet_list = packet_str.split(',')

        packet_headers = packet_list[:7]
        packet_message = packet_list[7]

        header_size = len((','.join(packet_headers) + ',').encode())
        message_size = len(packet_message.encode())

        fragments = []

        offset = int(packet_headers[4])
        flag = packet_headers[6]

        # If the packet is smaller than the MTU, return it in a list

        if packet_size <= mtu:
            fragments.append(packet_str)
        else:
            while message_size > 0:
                fragment = packet_headers.copy()
                if message_size > mtu - header_size:
                    fragment[4] = str(offset)
                    
                    # Update size so that its size is 8

                    fragment[5] = str(mtu - header_size).zfill(8)

                    fragment[6] = "1"
                    fragment.append(packet_message[:mtu - header_size])
                    fragments.append(','.join(fragment))

                    packet_message = packet_message[mtu - header_size:]
                    message_size = len(packet_message.encode())

                    offset += mtu - header_size
                else:
                    fragment[4] = str(offset)
                    fragment[5] = str(message_size).zfill(8)
                    fragment[6] = flag
                    fragment.append(packet_message)
                    fragments.append(','.join(fragment))
                    message_size = 0
        return fragments
       
    def reassemble_IP_packet(self, fragments: list) -> dict:
        
        # # For each fragment, convert it to a list

        # if len(fragments) == 1 and ''.join(fragments[0])[6] == '0':
        #     # print(f'Only 1 fragment')
        #     to_ret = ''.join(fragments[0])
        #     return self.parse_packet(to_ret.encode())
            
        
        # else:
        
            fragments = [fragment.split(',') for fragment in fragments]
            
            # Sort the fragments by offset

            fragments.sort(key=lambda x: int(x[4]))

            cur_offset = 0
            message = ""
            cur_size = 0
            if (int(fragments[0][4]) != 0):
                return None
            if (int(fragments[-1][6]) != 0):
                return None
            
            print_with_color(f'Reassembling {len(fragments)} fragments', self.color)
            # print(f'First fragment: {fragments[0]}')
            # print(f'Last fragment: {fragments[-1]}')
            
            for fragment in fragments:
                if int(fragment[4]) != cur_offset:
                    return None
                message += fragment[7]
                cur_offset += int(fragment[5])
                cur_size += int(fragment[5])
            
            ret_packet = fragments[0][0:7]
            ret_packet.append(message)
            ret_packet[5] = str(cur_size).zfill(8)
            ret_packet = ','.join(ret_packet)
            return self.parse_packet(ret_packet.encode())
        
    def add_packet_to_dict(self, packet):
        if packet['ID'] not in self.fragment_dict:
            self.fragment_dict[packet['ID']] = [self.create_packet(packet)]
        else:
            self.fragment_dict[packet['ID']].append(self.create_packet(packet))

    def run(self) -> None:

        """
        Main loop of the router. It waits for packets and forwards them if necessary
        """        

        # Wait in a loop for packets

        neighbors = self.get_neighbors()

        while True:
            packet, _ = self.sock.recvfrom(1024)
            packet = self.parse_packet(packet)

            # If the packet contains a start bgp message, run the bgp protocol

            if 'START_BGP' in packet['Message']:
                self.run_BGP()

            # If the packet has TTL = 0, drop it

            elif packet['TTL'] == 0:
                print_with_color(f'Dropped packet with TTL = 0', self.color)

            elif packet['IP'] == self.ip and packet['Port'] == self.port:
                print_with_color(f'Message from {packet["IP"]}:{packet["Port"]}: {packet["Message"]}', self.color)

            else:
                route = self.check_routes(packet['IP'], packet['Port'])
                if route is not None:
                    print_with_color(f'Forwarding packet to {route[0]}:{route[1]}', self.color)
                    self.forward_packet(packet, (route[0], route[1]))
                else:
                    print_with_color(f'No route to {packet["IP"]}:{packet["Port"]}', self.color)


if __name__ == "__main__":
    ip = sys.argv[1]
    port = sys.argv[2]
    table_path = sys.argv[3]
    r = Router(ip, port, table_path)

    r.run()

    # r = Router('127.0.0.1', 8881, 'rutas/rutas_R1_v3_mtu.txt')
    # print(r.route_list)
    # print(r.asn_list)
    