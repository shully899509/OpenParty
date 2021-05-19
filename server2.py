# This is server code to send video and audio frames over UDP/TCP

import cv2, imutils, socket
import numpy as np
import time
import base64
import threading, wave, pyaudio, pickle, struct
import sys
import queue
import os


def receive_message(client_socket):
    try:
        HEADER_LENGTH = 10
        # Receive our "header" containing message length, it's size is defined and constant
        message_header = client_socket.recv(HEADER_LENGTH)

        # If we received no data, client gracefully closed a connection, for example using socket.close() or socket.shutdown(socket.SHUT_RDWR)
        if not len(message_header):
            return False

        # Convert header to int value
        message_length = int(message_header.decode('utf-8').strip())

        # Return an object of message header and message data
        return {'header': message_header, 'data': client_socket.recv(message_length)}

    except:

        # If we are here, client closed connection violently, for example by pressing ctrl+c on his script
        # or just lost his connection
        # socket.close() also invokes socket.shutdown(socket.SHUT_RDWR) what sends information about closing the socket (shutdown read/write)
        # and that's also a cause when we receive an empty message
        return False


# For details visit pyshine.com
q = queue.Queue(maxsize=10)

filename = 'vids\\test.avi'
command = "ffmpeg -i {} -ab 160k -ac 2 -ar 44100 -vn {}".format(filename, 'temp.wav')
os.system(command)

BUFF_SIZE = 65536
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, BUFF_SIZE)
host_name = socket.gethostname()
# host_ip = '192.168.1.21'
host_ip = socket.gethostbyname(host_name)
print(host_ip)
port = 9688
socket_address = (host_ip, port)
server_socket.bind(socket_address)
print('Listening at:', socket_address)

vid = cv2.VideoCapture(filename)
FPS = vid.get(cv2.CAP_PROP_FPS)
global TS
TS = (0.5 / FPS)
BREAK = False
print('FPS:', FPS, TS)
totalNoFrames = int(vid.get(cv2.CAP_PROP_FRAME_COUNT))
durationInSeconds = float(totalNoFrames) / float(FPS)
d = vid.get(cv2.CAP_PROP_POS_MSEC)
print(durationInSeconds, d)


def video_stream_gen():
    WIDTH = 400
    while (vid.isOpened()):
        try:
            _, frame = vid.read()
            frame = imutils.resize(frame, width=WIDTH)
            q.put(frame)
        except:
            os._exit(1)
    print('Player closed')
    BREAK = True
    vid.release()


server_socket2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket2.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, BUFF_SIZE)
server_socket2.setblocking(False)
socket_address2 = ('localhost', 9998)
server_socket2.bind(socket_address2)
print('Listening for pause command at:', socket_address2)


def video_stream():
    global TS
    fps, st, frames_to_count, cnt = (0, 0, 1, 0)
    cv2.namedWindow('TRANSMITTING VIDEO')
    cv2.moveWindow('TRANSMITTING VIDEO', 10, 30)
    while True:
        msg, client_addr = server_socket.recvfrom(BUFF_SIZE)
        print('GOT connection from ', client_addr)
        print('message is ', msg)
        WIDTH = 400

        while True:
            frame = q.get()
            encoded, buffer = cv2.imencode('.jpeg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            message = base64.b64encode(buffer)
            server_socket.sendto(message, client_addr)
            frame = cv2.putText(frame, 'FPS: ' + str(round(fps, 1)), (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                                (0, 0, 255), 2)
            if cnt == frames_to_count:
                try:
                    fps = (frames_to_count / (time.time() - st))
                    st = time.time()
                    cnt = 0
                    if fps > FPS:
                        TS += 0.001
                    elif fps < FPS:
                        TS -= 0.001
                    else:
                        pass
                except:
                    pass
            cnt += 1

            cv2.imshow('TRANSMITTING VIDEO', frame)
            key = cv2.waitKey(int(1000 * TS)) & 0xFF
            if key == ord('q'):
                os._exit(1)
                TS = False
                break
            if key == ord('p'):
                cv2.waitKey(-1)  # wait until any key is pressed

            # read_list = [server_socket]
            # readable, writable, errored = select.select(read_list, [], [])
            # for s in readable:
            #     data, address = s1.recvfrom(MAX)
            #     print(("socket %s received %s bytes from %s" % (s.getsockname(), len(data), address)))
            #     s.sendto(b'Your data was %d bytes' % len(data), address)

            # msg = receive_message(server_socket2)
            # if msg is False:
            #     continue
            # else:
            #     print(msg)




            # last thing i tried

            try:
                conn, addr = server_socket2.accept()
                msg = conn.recvfrom(BUFF_SIZE)
                print(msg)
                if msg == b'do nothing':
                    continue
                conn.close()

            except Exception as e:
                print(e)





            # if msg is None:
            #     continue
            # else:
            #     print(client_addr)

            # currently recvfrom is blocking the processing of the frames
            # socket_address

            # s.bind(server_address)
            #  msg, client_addr = server_socket.recvfrom(BUFF_SIZE)
            #
            #  print('GOT connection from ', client_addr)
            #  print('message is ', msg)
            #  server_socket.sendto(b'received', client_addr)
            #




            #
            # import socketserver
            #
            # class MyTCPHandler(socketserver.BaseRequestHandler):
            #     """
            #     The request handler class for our server.
            #
            #     It is instantiated once per connection to the server, and must
            #     override the handle() method to implement communication to the
            #     client.
            #     """
            #
            #     def handle(self):
            #         # self.request is the TCP socket connected to the client
            #         self.data = self.request.recv(1024).strip()
            #         print("{} wrote:".format(self.client_address[0]))
            #         print(self.data)
            #         # just send back the same data, but upper-cased
            #         self.request.sendall(self.data.upper())
            #
            # HOST, PORT = "localhost", 9999
            # # Create the server, binding to localhost on port 9999
            # with socketserver.TCPServer((HOST, PORT), MyTCPHandler) as server:
            #     # Activate the server; this will keep running until you
            #     # interrupt the program with Ctrl-C
            #     server.serve_forever()

def audio_stream():
    s = socket.socket()
    s.bind((host_ip, (port - 1)))

    s.listen(5)
    CHUNK = 1024
    wf = wave.open("temp.wav", 'rb')
    p = pyaudio.PyAudio()
    print('server listening at', (host_ip, (port - 1)))
    stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                    channels=wf.getnchannels(),
                    rate=wf.getframerate(),
                    input=True,
                    frames_per_buffer=CHUNK)

    client_socket, addr = s.accept()

    # data = client_socket.recvfrom(1024)
    # while data:
    #     print(data)
    #     data = conn.recvfrom(1024)

    while True:
        if client_socket:
            while True:
                data = wf.readframes(CHUNK)
                a = pickle.dumps(data)
                message = struct.pack("Q", len(a)) + a
                client_socket.sendall(message)


from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=3) as executor:
    executor.submit(audio_stream)
    executor.submit(video_stream_gen)
    executor.submit(video_stream)
