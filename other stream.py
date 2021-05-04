import socket, cv2, pickle, struct

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
host_name = socket.gethostname()
host_ip = socket.gethostbyname(host_name)

print('HOST IP:', host_ip)

port = 9999
socket_adress = (host_ip, port)

server_socket.bind(socket_adress)

server_socket.listen(5)
print('LISTENING AT:', socket_adress)

while True:
    client_socket, addr = server_socket.accept()
    print('GOT CONNECTION FROM:', addr)
    if client_socket:
        video = 'vids/test.avi'
        vid = cv2.VideoCapture(video)
        while vid.isOpened():
            img,frame = vid.read()
            a = pickle.dumps(frame)
            message = struct.pack("Q", len(a)) + a
            client_socket.sendall(message)
            cv2.imshow('TRANSMITING VIDEO:', frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                client_socket.close()