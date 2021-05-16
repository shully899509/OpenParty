import socket
import sys


# Create a UDP socket
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# Bind the socket to the port
host_name = socket.gethostname()
ip = socket.gethostbyname(host_name)
port = 5678

server_address = (ip, port)
s.bind(server_address)
print("Do Ctrl+c to exit the program !!")

print('listening at:',ip)

s.setblocking(False)

while True:
    print("####### Server is listening #######")
    data, address = s.recvfrom(4096)
    print("\n\n 2. Server received: ", data.decode('utf-8'), "\n\n")
    #send_data = input("Type some text to send => ")
    # send_data = 'I received the message bro'
    # s.sendto(send_data.encode('utf-8'), address)
    # print("\n\n 1. Server sent : ", send_data,"\n\n")