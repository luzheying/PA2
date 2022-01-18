All the files that is submitted:
1. tcpclient.py : Sender of the file
2. tcpserver.py : Receiver of the file
3. sendfile.txt : the file that is needed to be sent
4. receivefile.txt : the file that the contect recevied by the receiver will be written to

For client and server it has to be in this order, otherwise an error will occur, tested on one machine with macOS. 
./newudpl -vv -i "127.0.0.1:41191" -o "127.0.0.1:41194" -L 50
python3 tcpserver.py receivefile.txt 41194 '' 12001
python3 tcpclient.py sendfile.txt '127.0.0.1' 41192 1 12001

./newudpl -vv -i "127.0.0.1:41191" -o "127.0.0.1:41194" -L 50
python3 tcpserver.py receivefile.txt 41194 '192.168.99.105' 12001
python3 tcpclient.py sendfile.txt '127.0.0.1' 41192 1 12001

features:
It will handle the packet loss and delay
bug:
if the last ack sent by sender was lost, tcpserver will not automatically shut down. Instead, it would hang in terminal. If shut it down manually, the receivefile will still be updated. If the sender was shut down manually, it has a chance when resarting the connection between server and sender, the port is still in use. I don't have the chance to test with different machine or two machine together, the command with different port or address might cause corrupt.