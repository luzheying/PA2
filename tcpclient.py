from os import sendfile
import sys
from socket import *
import struct
import time

#data sender

#calculate checksum for checking if the packet is valid, data here is the packet that receiver has received from the sender. Also is used when generating packet for ACK
def cal_checksum(data):
    checksum = 0
    for num in range(len(data)):
        if num % 2 == 0:     
            checksum = checksum + (data[num] << 8)
        elif num % 2 == 1:   
            checksum = checksum + data[num]
    checksum = 65535 - (checksum % 65536)                       
    return checksum

#generate packet with the pass in parameters
def generate_packet(source,dest,seqnum,acknum,ack,fin,window_size,data):
    if ack == 0 and fin == 0:
        #0x0000
        flag = 0         
    elif ack == 0 and fin == 1:
        #0x0001
        flag = 1         
    elif ack == 1 and fin == 0:
        #0x0010
        flag = 16        
    elif ack == 1 and fin == 1:
        #0x0011
        flag = 17
        #construct a header as packet_header
    header = struct.pack("!HHIIBBHHH", source,
                         dest, seqnum, acknum,
                         5, flag,
                         window_size, 0, 0)
    #calculate checksum for hear along with the encoded content that is going to be sent
    checksum = cal_checksum(header + data.encode('utf=8'))
    header = struct.pack("!HHIIBBHHH", source,
                         dest, seqnum, acknum,
                         5, flag,
                         window_size, checksum, 0)
    #return the generated header along wtih the content
    return header + data.encode('utf-8')


#unpack method for incomming packet
def unpack(packet):
    header = packet[:20]
    source_port, dest_port, seqnum, acknum, header_length,flags, window_size, checksum, urgent = struct.unpack("!HHIIBBHHH", header)

    ack = (flags >> 4) == 1
    fin = int(flags % 2 == 1)
    contents = packet[20:]

    return source_port, dest_port, seqnum, acknum, header_length, ack, fin, window_size, contents




if __name__ == '__main__':
    #read command line with format as tcpclient file address_of_udpl port_number_of_udpl windowsize ack_port_number
    if (len(sys.argv) != 6):
        exit("parameter error")
    file = sys.argv[1]
    address_of_udpl = sys.argv[2]
    port_number_of_udpl = int(sys.argv[3])
    windowsize = int(sys.argv[4])
    ack_port_number = int(sys.argv[5])

    # UDP for data exchange
    clientSocket = socket(AF_INET, SOCK_DGRAM)
    clientSocket.bind(('',port_number_of_udpl-1))
    #initialize all the variable with 0 for packet tracking also RTT calculation 
    seqnum = 0
    acknum = 0
    sent = 0
    retransmitted = 0

    sendfile = open(file)
    tcp_valid = False
    text = sendfile.read(556)
    fin = 0             
    packet = generate_packet(ack_port_number, port_number_of_udpl, seqnum, acknum, 1, fin, 5, text)
    timeout_time = 1

    send_time = time.time()
    clientSocket.sendto(packet, (address_of_udpl,port_number_of_udpl))
    sent += 1
    tcp_established = False

    #TCP for ack
    ackSocket = socket(AF_INET,SOCK_STREAM)
    ackSocket.bind(('',ack_port_number))
    ackSocket.listen(1)
    #untill receive the valid socket it will keep resend ing the packet
    while not tcp_established:
        try:
            recv_sock, addr = ackSocket.accept()
            tcp_established = True
            recv_time = time.time()
            # RTT calculation
            estimated_rtt = recv_time - send_time
            dev_rtt = 0
            recv_sock.settimeout(timeout_time)
        except timeout:
            #if timeout, retransimit
            retransmitted += 1
            clientSocket.sendto(packet, (address_of_udpl,port_number_of_udpl))
            sent += 1
            send_time = time.time()

    # after tcp is connected
    while fin == 0:
        try:
            #receive the ack packet
            ack = recv_sock.recv(1024)
            recv_time = time.time()
            ack_source_port, ack_dest_port, ack_seqnum,ack_acknum, ack_header_length, ack_valid,fin, window_size, contents = unpack(ack)
            if ack_acknum == acknum and ack_valid:
                # RTT calculation
                sample_rtt = recv_time - send_time
                estimated_rtt = estimated_rtt * 0.875 + sample_rtt * 0.125
                dev_rtt = 0.75 * dev_rtt + 0.25 * abs(sample_rtt - estimated_rtt)
                recv_sock.settimeout(estimated_rtt + 4 * dev_rtt)
                #check if it is asked to be terminated
                if fin == 1:
                    break
                #read file for the next sending content
                text = sendfile.read(556)
                #if there is no text can be read / it is the end of the file, fin number will be updated to 1 indicatin it is the last packet
                if text == "":
                    print("all content has been sent")
                    fin = 1
                #update seqnum and acknum when valid ACK is received 
                seqnum += 1
                acknum += 1
                #generate the next packet to sent
                packet = generate_packet(ack_port_number, port_number_of_udpl, seqnum, acknum, 1, fin, windowsize, text)
                #send packet with UDP
                clientSocket.sendto(packet, (address_of_udpl,port_number_of_udpl))
                # increase total sent counter
                sent += 1 
                send_time = time.time()
            else:
                print("invalid packet")
                #increase retrandimitted counter
                retransmitted += 1
                #regenerate the packet
                packet = generate_packet(ack_port_number, port_number_of_udpl, seqnum, acknum, 1, fin, windowsize, text)
                #send packet with UDP
                clientSocket.sendto(packet, (address_of_udpl,port_number_of_udpl))
                sent += 1 
        except timeout:
                print("timeout")
                #increase retrandimitted counter
                retransmitted += 1
                #regenerate the packet
                packet = generate_packet(ack_port_number, port_number_of_udpl, seqnum, acknum, 1, fin, windowsize, text)
                #send packet with UDP
                clientSocket.sendto(packet, (address_of_udpl,port_number_of_udpl))
                sent += 1 
    
    #file exchange ends. All socket and file close
    clientSocket.close()
    ackSocket.close()
    sendfile.close()