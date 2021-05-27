# This is server code to send video and audio frames over UDP/TCP

import cv2, imutils, socket
import numpy as np
import time
import base64
import threading, wave, pyaudio, pickle, struct
import sys
import queue
import os
from _thread import *


# For details visit pyshine.com
q = queue.Queue(maxsize=10)


# function called by trackbar, sets the next frame to be read
def getFrame(frame_nr):
    global vid
    vid.set(cv2.CAP_PROP_POS_FRAMES, frame_nr)

filename = 'vids\\monty.mp4'
command = "ffmpeg -i {} -ab 160k -ac 2 -ar 44100 -vn {} -y".format(filename, 'temp.wav')
os.system(command)


def multi_threaded_client(connection):
    connection.send(str.encode('Server is working:'))
    while True:
        data = connection.recv(2048)
        response = 'Server message: ' + data.decode('utf-8')
        if not data:
            break
        connection.sendall(str.encode(response))
    connection.close()




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
        except Exception as e:
            print(e)
            os._exit(1)
    print('Player closed')
    BREAK = True
    vid.release()

list_of_clients = []

def video_stream():



    try:
        BUFF_SIZE = 65536
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, BUFF_SIZE)

        host_name = socket.gethostname()
        # host_ip = '192.168.1.21'
        host_ip = socket.gethostbyname(host_name)
        print('ip connect: ', host_ip)

        host_ip = '127.0.0.1'

        print(host_ip)
        port = 9688
        socket_address = (host_ip, port)
        # server_socket.bind(socket_address)
        print('Listening at:', socket_address)

        global TS
        fps, st, frames_to_count, cnt = (0, 0, 1, 0)
        cv2.namedWindow('TRANSMITTING VIDEO')
        cv2.moveWindow('TRANSMITTING VIDEO', 10, 30)
        cv2.createTrackbar("Frame", "TRANSMITTING VIDEO", 0, totalNoFrames, getFrame)
    except Exception as e:
        print(e)

    while True:

        WIDTH = 400


        while True:
            # print('frame sending')
            frame = q.get()
            encoded, buffer = cv2.imencode('.jpeg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            message = base64.b64encode(buffer)

            client_addr_new = ('127.0.0.1', 9689)
            server_socket.sendto(message, client_addr_new)
            # print('frame sent')
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
                except Exception as e:
                    print(e)
            cnt += 1

            cv2.imshow('TRANSMITTING VIDEO', frame)
            cv2.setTrackbarPos("Frame", "TRANSMITTING VIDEO", int(vid.get(cv2.CAP_PROP_POS_FRAMES)))


            key = cv2.waitKey(int(1000 * TS)) & 0xFF
            if key == ord('q'):
                os._exit(1)
                TS = False
                break
            if key == ord('p'):
                cv2.waitKey(-1)  # wait until any key is pressed


from pynput import keyboard
paused = False  # global to track if the audio is paused
def local_audio():
    print('pornit local')

    wf = wave.open("temp.wav", 'rb')
    CHUNK = 1024
    p = pyaudio.PyAudio()

    def on_press(key):
        global paused
        print(key)
        if key == keyboard.Key.space:
            if stream.is_stopped():  # time to play audio
                print('play pressed')
                stream.start_stream()
                paused = False
                return False
            elif stream.is_active():  # time to pause audio
                print('pause pressed')
                stream.stop_stream()
                paused = True
                return False
        return False

    # define callback
    def callback(in_data, frame_count, time_info, status):
        data = wf.readframes(frame_count)
        return (data, pyaudio.paContinue)

    stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                    channels=wf.getnchannels(),
                    rate=wf.getframerate(),
                    output=True,
                    frames_per_buffer=CHUNK,
                    stream_callback=callback)

    # start the stream
    stream.start_stream()

    while stream.is_active() or paused == True:
        with keyboard.Listener(on_press=on_press) as listener:
            listener.join()
        time.sleep(0.1)

    # stop stream
    stream.stop_stream()
    stream.close()
    wf.close()

    # close PyAudio
    p.terminate()

import select
def receive_command():
    HEADER_LENGTH = 10
    IP = "127.0.0.1"
    PORT = 1234
    server_port = 9688
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((IP, PORT))

    # This makes server listen to new connections
    server_socket.listen()

    # List of sockets for select.select()
    sockets_list = [server_socket]
    clients = {}
    print(f'Listening for connections on {IP}:{PORT}...')

    # Handles message receiving
    def receive_message(client_socket):

        try:

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

    while True:

        # Calls Unix select() system call or Windows select() WinSock call with three parameters:
        #   - rlist - sockets to be monitored for incoming data
        #   - wlist - sockets for data to be send to (checks if for example buffers are not full and socket is ready to send some data)
        #   - xlist - sockets to be monitored for exceptions (we want to monitor all sockets for errors, so we can use rlist)
        # Returns lists:
        #   - reading - sockets we received some data on (that way we don't have to check sockets manually)
        #   - writing - sockets ready for data to be send thru them
        #   - errors  - sockets with some exceptions
        # This is a blocking call, code execution will "wait" here and "get" notified in case any action should be taken
        read_sockets, _, exception_sockets = select.select(sockets_list, [], sockets_list)

        # Iterate over notified sockets
        for notified_socket in read_sockets:

            # If notified socket is a server socket - new connection, accept it
            if notified_socket == server_socket:

                # Accept new connection
                # That gives us new socket - client socket, connected to this given client only, it's unique for that client
                # The other returned object is ip/port set
                client_socket, client_address = server_socket.accept()

                # Client should send his name right away, receive it
                user = receive_message(client_socket)

                # If False - client disconnected before he sent his name
                if user is False:
                    continue

                # Add accepted socket to select.select() list
                sockets_list.append(client_socket)

                # Also save username and username header
                clients[client_socket] = user

                print('Accepted new connection from {}:{}, username: {}'.format(*client_address,
                                                                                user['data'].decode('utf-8')))




                # video_stream()


            # Else existing socket is sending a message
            else:

                # Receive message
                message = receive_message(notified_socket)

                # If False, client disconnected, cleanup
                if message is False:
                    print('Closed connection from: {}'.format(clients[notified_socket]['data'].decode('utf-8')))

                    # Remove from list for socket.socket()
                    sockets_list.remove(notified_socket)

                    # Remove from our list of users
                    del clients[notified_socket]

                    continue

                # Get user by notified socket, so we will know who sent the message
                user = clients[notified_socket]

                print(f'Received message from {user["data"].decode("utf-8")}: {message["data"].decode("utf-8")}')

                # Iterate over connected clients and broadcast message
                for client_socket in clients:

                    # But don't sent it to sender
                    if client_socket != notified_socket:
                        # Send user and message (both with their headers)
                        # We are reusing here message header sent by sender, and saved username header send by user when he connected
                        client_socket.send(user['header'] + user['data'] + message['header'] + message['data'])

        # It's not really necessary to have this, but will handle some socket exceptions just in case
        for notified_socket in exception_sockets:
            # Remove from list for socket.socket()
            sockets_list.remove(notified_socket)

            # Remove from our list of users
            del clients[notified_socket]

def audio_stream():
    print('pornit client')

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

    while True:
        if client_socket:
            while True:
                data = wf.readframes(CHUNK)
                a = pickle.dumps(data)
                message = struct.pack("Q", len(a)) + a
                client_socket.sendall(message)


from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=4) as executor:
    # executor.submit(audio_stream)
    executor.submit(video_stream_gen)
    executor.submit(video_stream)
    executor.submit(receive_command)
    # executor.submit(local_audio)
