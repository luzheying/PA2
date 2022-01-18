import struct
import sys
from socket import *
from tcpclient import generate_packet

#data receiver

#calculate checksum for incoming content. data here is the encoded version of content that needs to be sent
def cal_checksum(data):
    checksum = 0
    for num in range(len(data)):
        if num % 2 == 0:   
            checksum = checksum + (data[num] << 8)
        elif num % 2 == 1:  
            checksum = checksum + data[num]
    checksum = 65535 - (checksum % 65536)    
    return checksum

#unpack method for incomming packet
def unpack(packet):
    header = packet[:20]
    source_port, dest_port, seqnum, acknum, header_length, flags, window_size, checksum, urgent = struct.unpack("!HHIIBBHHH", header)

    ack = (flags >> 4) == 1
    fin = int(flags % 2 == 1)
    packet_contents = packet[20:]

    return source_port, dest_port, seqnum, acknum, header_length, ack, fin, window_size, packet_contents



if __name__ == '__main__':
    if (len(sys.argv) != 5):
        exit("argument error")
    #read command line with format as tcpserver file listening_port address_for_acks port_for_acks
    file = sys.argv[1]
    listening_port = int(sys.argv[2])
    address_for_acks = sys.argv[3]
    port_for_acks = int(sys.argv[4])

    recvfile = open(file, 'w')
    # UDP for data exchange
    serverSocket = socket(AF_INET,SOCK_DGRAM)
    serverSocket.bind(('',listening_port))
    print("The server is ready to receive")

    next_acknum = 0
    # Receive first packet
    packet, addr = serverSocket.recvfrom(1024)
    source_port, dest_port, seqnum, acknum, header_length,ack, fin, window_size, contents = unpack(packet)
    checksum = cal_checksum(packet)
    packet_valid = checksum == 0 and next_acknum == acknum
    if packet_valid:
        recvfile.write(contents.decode('utf-8'))
        #increase next_acknum indicating expecting packet
        next_acknum += 1


    # TCP for ACKs
    ackSocket = socket(AF_INET, SOCK_STREAM) 
    # ack socket connect
    ackSocket.connect((address_for_acks, port_for_acks))
    out_port = ackSocket.getsockname()[1]
    ack_packet = generate_packet(out_port, port_for_acks,
                                   seqnum, acknum, packet_valid,
                                   False, 1, "")
    ackSocket.send(ack_packet)

    while True:
        #after the tcp connection for sending ACK is established, server will keep receiving file contents
        packet, addr = serverSocket.recvfrom(1024)
        source_port, dest_port, seqnum, acknum, header_length,ack, fin, window_size, contents = unpack(packet)
        checksum = cal_checksum(packet)
        #check for packet, if it is in the right sequence or if it is corrupted
        packet_valid = checksum == 0 and next_acknum == acknum
        if packet_valid:
            recvfile.write(contents.decode('utf-8'))
            #increase next_acknum indicating expecting packet
            next_acknum += 1
        ack_packet = generate_packet(out_port, port_for_acks,
                                        seqnum, acknum, packet_valid,
                                        fin, 1, "")
        ackSocket.send(ack_packet)
        if fin == 1:
            #if it is the last packet
            break

    #close all socket and files when file exchange is done
    serverSocket.close()
    ackSocket.close()
    recvfile.close()