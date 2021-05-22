# Welcome to PyShine
# This is client code to receive video and audio frames over UDP/TCP

import cv2, imutils, socket
import numpy as np
import time, os
import base64
import threading, wave, pyaudio, pickle, struct

# workaround to start client after server when executing start commands in the same time
time.sleep(1)


# For details visit pyshine.com
BUFF_SIZE = 65536

BREAK = False
client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, BUFF_SIZE)
host_name = socket.gethostname()
host_ip = '192.168.100.30'  # socket.gethostbyname(host_name)
print(host_ip)
port = 9688
message = b'Hello'

#client_socket.setblocking(False)
client_socket.sendto(message, (host_ip, port))

#
# client_socket2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# client_socket2.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, BUFF_SIZE)
# client_socket2.setblocking(False)

def video_stream():
    cv2.namedWindow('RECEIVING VIDEO')
    cv2.moveWindow('RECEIVING VIDEO', 10, 360)
    fps, st, frames_to_count, cnt = (0, 0, 20, 0)
    while True:
        packet, _ = client_socket.recvfrom(BUFF_SIZE)
        data = base64.b64decode(packet, ' /')
        npdata = np.fromstring(data, dtype=np.uint8)

        frame = cv2.imdecode(npdata, 1)
        frame = cv2.putText(frame, 'FPS: ' + str(fps), (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        cv2.imshow("RECEIVING VIDEO", frame)
        key = cv2.waitKey(1) & 0xFF

        if key == ord('q'):
            client_socket.close()
            os._exit(1)
            break



        # if key == ord('p'):
        #     print('trying to send a message')
        #     message = b'pause pretty please'
        #     client_socket2.sendto(message, (host_ip, port+1))

            # HOST, PORT = "localhost", 9999
            # # Create a socket (SOCK_STREAM means a TCP socket)
            # with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            #     # Connect to server and send data
            #     sock.connect((HOST, PORT))
            #     sock.sendall(bytes(message + "\n", "utf-8"))
            #
            #     # Receive data from the server and shut down
            #     received = str(sock.recv(1024), "utf-8")
            # print("Sent:     {}".format(message))
        # else:
        #     print('im idle but still sending message')
        #     message = b'do nothing'
        #     client_socket2.sendto(message, (host_ip, port+1))

            # HOST, PORT = "localhost", 9999
            # # Create a socket (SOCK_STREAM means a TCP socket)
            # with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            #     # Connect to server and send data
            #     sock.connect((HOST, PORT))
            #     sock.sendall(bytes(message + "\n", "utf-8"))
            #
            #     # Receive data from the server and shut down
            #     received = str(sock.recv(1024), "utf-8")
            # print("Sent:     {}".format(message))

        if cnt == frames_to_count:
            try:
                fps = round(frames_to_count / (time.time() - st))
                st = time.time()
                cnt = 0
            except:
                pass
        cnt += 1

    client_socket.close()
    cv2.destroyAllWindows()


def audio_stream():
    p = pyaudio.PyAudio()
    CHUNK = 1024
    stream = p.open(format=p.get_format_from_width(2),
                    channels=2,
                    rate=44100,
                    output=True,
                    frames_per_buffer=CHUNK)

    # create socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socket_address = (host_ip, port - 1)
    print('server listening at', socket_address)
    client_socket.connect(socket_address)
    print("CLIENT CONNECTED TO", socket_address)
    data = b""
    payload_size = struct.calcsize("Q")
    while True:
        try:
            while len(data) < payload_size:
                packet = client_socket.recv(4 * 1024)  # 4K
                if not packet: break
                data += packet
            packed_msg_size = data[:payload_size]
            data = data[payload_size:]
            msg_size = struct.unpack("Q", packed_msg_size)[0]
            while len(data) < msg_size:
                data += client_socket.recv(4 * 1024)
            frame_data = data[:msg_size]
            data = data[msg_size:]
            frame = pickle.loads(frame_data)
            stream.write(frame)

        except:

            break

    client_socket.close()
    print('Audio closed', BREAK)
    os._exit(1)


from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=2) as executor:
    executor.submit(audio_stream)
    executor.submit(video_stream)