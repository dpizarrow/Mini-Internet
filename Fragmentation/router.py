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
        self.fragment_dict = {}

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

    def check_routes(self, ip: str, port: int) -> tuple:

        """_
        Check if there is a route to the destination address. Uses round-robin to select the next hop

        Args:
            ip (str): IP of the destination
            port (int): Port of the destination
        Returns:
            bool: True if there is a route, False otherwise
        """   

        for route in self.route_list:
            route = route.split(' ')
            
            port_low = int(route[1])
            port_high = int(route[2])
            if ip == route[0] and port in range(port_low, port_high + 1):

                hop_ip = route[3]
                hop_port = int(route[4])
                hop_mtu = int(route[5])

                # Move the route to the end of the list
                self.route_list.remove(' '.join(route))
                self.route_list.append(' '.join(route))

                return (hop_ip, hop_port, hop_mtu)
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

        """
        Fragment an IP packet if it's larger than the MTU

        Args:
            packet (dict): Packet to fragment
            mtu (int): MTU of the network
        Returns:
            list: List of fragments
        """

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
        
        """
        Reassemble an IP packet from a list of fragments

        Args:
            fragments (list): List of fragments
        Returns:
            dict: Reassembled packet
        """   

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

        """
        Add a packet to the fragment dictionary based on its ID

        Args:
            packet (dict): Packet to add
        """    

        if packet['ID'] not in self.fragment_dict:
            self.fragment_dict[packet['ID']] = [self.create_packet(packet)]
        else:
            self.fragment_dict[packet['ID']].append(self.create_packet(packet))

    def run(self) -> None:

        """
        Main loop of the router. It waits for packets and forwards them if necessary
        """        

        # Wait in a loop for packets

        while True:
            packet, _ = self.sock.recvfrom(1024)
            packet = self.parse_packet(packet)

            print_with_color(f"Received packet for: {packet['IP']}:{packet['Port']}", self.color)

            # If the TTL is 0, drop the packet

            if packet['TTL'] == 0:
                print_with_color("Packet has TTL = 0, discarding", self.color)
                continue

            else:

                # If the packet is for the router, print it

                if packet['IP'] == self.ip and packet['Port'] == self.port:
                    self.add_packet_to_dict(packet)
                    reassembled_packet = self.reassemble_IP_packet(self.fragment_dict[packet['ID']])
                    if reassembled_packet:
                        print_with_color(f"Reassembled packet {reassembled_packet['Message']}", self.color)
                        del self.fragment_dict[packet['ID']]

                else:

                    # Check if there is a route to the destination address

                    route = self.check_routes(packet['IP'], int(packet['Port']))

                    # If there is a route, forward the packet

                    if route:
                        print_with_color(f"Redirecting message for {packet['IP']}:{packet['Port']} to {route[0]}:{route[1]}, MTU is {route[2]}", self.color)
                        route_mtu = route[2]
                        print_with_color(f'Fragmenting packet with MTU {route_mtu}', self.color)
                        fragments = self.fragment_IP_packet(packet, route_mtu)
                        print_with_color(f'Fragmented packet into {fragments}', self.color)
                        for fragment in fragments:
                            packet = self.parse_packet(fragment.encode())
                            self.forward_packet(packet, (route[0], route[1]))
                    else:

                        # No route found, print the error

                        print_with_color(f"No routes found to {packet['IP']}:{packet['Port']}", self.color)

if __name__ == "__main__":
    ip = sys.argv[1]
    port = sys.argv[2]
    table_path = sys.argv[3]
    r = Router(ip, port, table_path)
    r.run()
    




    

    