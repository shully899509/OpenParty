import socket, cv2, pickle, struct
import imutils
import threading


server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
host_name = socket.gethostname()
host_ip = '192.168.100.121'
print('HOST IP:', host_ip)
port = 9999
socket_address = (host_ip,port)
server_socket.bind(socket_address)
server_socket.listen()
print('listening at:', socket_address)

def start_video_stream():
    client_socket, addr = server_socket.accept()
    vid = cv2.VideoCapture('C:/repos/OpenParty/vids/test.avi')
    try:
        print('client {} connected'.format(addr))
        if client_socket:
            while(vid.isOpened()):
                img, frame = vid.read()

                frame = imutils.resize(frame, width=320)
                a = pickle.dumps(frame)
                message = struct.pack("Q", len(a)) + a
                client_socket.sendall(message)
                cv2.imshow("transmitting to cache server", frame)
                key = cv2.waitKey(1) & 0xFF
                if key==ord('q'):
                    client_socket.close()
                    break
    except Exception as e:
        print(f"Cache server {addr} disconnected")
        pass

while True:
    start_video_stream()
