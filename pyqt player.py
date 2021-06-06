# TODO: send audio packets through UDP socket and sync with video
# TODO: move code into separate .py files for each module
# TODO: replace send frames to hardcoded client addresses with list of addresses from chat TCP connection
# TODO: fix crash when trying to open another video
import base64
import os
import socket
import sys
from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.uic import loadUi
from PyQt5.QtCore import pyqtSlot, QTimer, QObject, pyqtSignal, QThread
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QFileDialog, QLabel, QGraphicsScene, QGraphicsView
import cv2
from datetime import timedelta
import queue
import time
import logging, random, imutils
import os
import pyaudio, wave, subprocess
import select
import pickle

from PyQt5.QtCore import QRunnable, Qt, QThreadPool
from pynput import keyboard

BASE_DIR = os.path.dirname(__file__)
path = BASE_DIR.replace('\\'[0], '/')

logging.basicConfig(format="%(message)s", level=logging.INFO)


class VideoGen(QThread):
    # queue for storing multiple frames from video file ready to be processed
    def __init__(self, cap, q):
        super().__init__()
        self.cap = cap
        self.q = q

    def run(self):
        # set how much pixels should be sent using the UDP socket
        # too much will cause lag because of too large packets
        WIDTH = 600

        while self.cap.isOpened():
            try:
                # to be used for updating the slider position
                current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))

                ret, frame = self.cap.read()
                # frame = imutils.resize(frame, width=WIDTH)
                # print('adding frame to queue')

                frame = imutils.resize(frame, width=WIDTH)
                self.q.put((ret, frame, current_frame))
                # logging.info('{} {}'.format('insert into q ', current_frame))
                # print('sent frame: ', self.q.qsize())
                # frame_no += 1
                # print('after add frame')
            except Exception as e:
                logging.error(e)
                break
                # os._exit(1)
        print('Player closed')
        BREAK = True
        self.cap.release()


class PlayVideo(QThread):
    playSignal = pyqtSignal()
    stopSignal = pyqtSignal()

    def __init__(self, cap, q, progresslabel, progressBar, frame, totalFrames, fps,
                 playButton, stopButton, fpsLabel):

        super().__init__()

        # signals used by TCP chat thread in order to play/pause the timer from the exterior
        self.playSignal.connect(self.playTimer)
        self.stopSignal.connect(self.stopTimer)

        # ui properties inherited from MainWindow class
        self.cap = cap
        self.playButton = playButton
        self.stopButton = stopButton
        self.fpsLabel = fpsLabel

        self.q = q
        self.progresslabel = progresslabel
        self.progressBar = progressBar
        self.frame = frame
        self.totalFrames = totalFrames
        self.fps = fps
        self.TS = (0.5 / self.fps)

        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(totalFrames)

        # timer to loop the frame displaying function
        self.timer = QTimer()
        self.timer.timeout.connect(self.playVideo)
        self.timer.start(self.TS * 1000)

        # bind play/pause buttons
        self.playButton.clicked.connect(self.playTimer)
        self.stopButton.clicked.connect(self.stopTimer)

        # properties for slider functionality
        self.slider_pressed = False
        self.progressBar.sliderPressed.connect(self.when_slider_pressed)
        self.progressBar.sliderReleased.connect(self.moveProgressBar)

        # properties to sync the FPS with how fast the frames are processed
        self.fps2 = 0
        self.st = 0
        self.frames_to_count = 1
        self.cnt = 0

        # properties for UDP socket to send the frames to clients
        self.BUFF_SIZE = 65536
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, self.BUFF_SIZE)
        host_name = socket.gethostname()
        # host_ip = '192.168.1.21'
        self.host_ip = socket.gethostbyname(host_name)
        print('udp ip connect: ', self.host_ip)
        port = 9688
        self.socket_address = (self.host_ip, port)
        self.server_socket.bind(self.socket_address)
        print('Listening at:', self.socket_address)

        self.cnt = 1

    # convert frame number to timestamp
    def frame_to_timestamp(self, frame, fps):
        return str(timedelta(seconds=(frame / fps)))

    # restart the timer when play button is pressed
    def playTimer(self):
        self.timer.start(self.TS * 1000)
        # print('play thread ', self.TS * 1000)

    # stop the timer when pause button is pressed
    def stopTimer(self):
        self.timer.stop()
        # print('stop thread')

    # stop updating the progress bar while slider is clicked
    def when_slider_pressed(self):
        self.slider_pressed = True

    # when slider is released try to empty queue and move to selected frame number
    def moveProgressBar(self):
        try:
            self.timer.stop()
            while not self.q.empty(): self.q.get()
            time.sleep(0.05)
            self.timer.start(self.TS * 1000)
        except Exception as e:
            logging.error(e)
        value = self.progressBar.value()
        self.cap.set(1, value)
        self.slider_pressed = False

    def moveProgressBarClient(self, value):
        self.cap.set(1, value)

    # function for displaying and sending frames
    # will be ran in a loop using the timer to sync the FPS
    def playVideo(self):
        # read image from queue
        ret, frame, current_frame_no = self.q.get()



        # if self.cnt == 1: print(frame)

        if ret is True:
            progress = self.frame_to_timestamp(current_frame_no, self.fps) + ' / ' \
                       + self.frame_to_timestamp(self.totalFrames, self.fps)
            self.progresslabel.setText(progress)
            # logging.info(current_frame)
            # logging.info(threading.current_thread().ident)

            # stop updating slider in UI while clicked while continuing playback
            if self.slider_pressed is False:
                self.progressBar.setValue(current_frame_no)

            try:
                encoded, buffer = cv2.imencode('.jpeg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                encoded_frame = base64.b64encode(buffer)

                # TODO: send total_frames and fps only once in the TCP connection
                msg_pair = {"frame_nb": current_frame_no,
                            "total_frames": self.totalFrames,
                            "frame": encoded_frame,
                            "fps": self.fps}
                packed_message = pickle.dumps(msg_pair)


                # if self.cnt == 1: print(buffer)
                # self.cnt += 1

                # TODO: send the message to the list of clients stored from the TCP socket
                client_addr_new1 = ('192.168.0.106', 9689)  # udp ip to local client
                client_addr_new2 = ('192.168.0.106', 9685)  # others
                client_addr_new = [client_addr_new1, client_addr_new2]
                for client in client_addr_new:
                    self.server_socket.sendto(packed_message, client)
            except Exception as e:
                logging.error(e)

            # convert image to RGB format
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            # get image infos
            height, width, channel = frame.shape
            # print(height, width, channel)
            step = channel * width
            # create QImage from image
            qImg = QImage(frame.data, width, height, step, QImage.Format_RGB888)

            # show image in UI frame label
            self.frame.setPixmap(QPixmap.fromImage(qImg))

            # because frame processing time if fluctuating
            # we need to sync it to the FPS fetched from the metadata
            self.fpsLabel.setText(str(round(self.fps2, 1)))
            if self.cnt == self.frames_to_count:
                try:
                    self.fps2 = (self.frames_to_count / (time.time() - self.st))
                    self.st = time.time()
                    self.cnt = 0
                    if self.fps2 > self.fps:
                        self.TS += 0.001
                    elif self.fps2 < self.fps:
                        self.TS -= 0.001
                    else:
                        pass
                except Exception as e:
                    print(e)
            self.cnt += 1

            # restart and update timer with new TS
            self.timer.start(self.TS * 1000)

        else:
            print('return false')
            progress = str(current_frame_no) + ' / ' \
                       + str(self.totalFrames)
            self.progresslabel.setText(progress)
            self.progressBar.setValue(current_frame_no)


from pygame import mixer
import audioop


class LocalAudio(QThread):
    def __init__(self):
        super().__init__()
        self.paused = False

    def run(self):
        # factor = 0.5
        #
        # with wave.open('temp.wav', 'rb') as wav:
        #     p = wav.getparams()
        #     with wave.open('temp.wav', 'wb') as audio:
        #         audio.setparams(p)
        #         frames = wav.readframes(p.nframes)
        #         audio.writeframesraw(audioop.mul(frames, p.sampwidth, factor))

        # mixer.init()
        # mixer.music.load('temp.wav')
        # mixer.music.play()

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
                    # subprocess.call(["amixer", "-D", "pulse", "sset", "Master", "10%-"])
                    paused = False
                    return False
                elif stream.is_active():  # time to pause audio
                    print('pause pressed')
                    stream.stop_stream()
                    self.paused = True
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

        while stream.is_active() or self.paused == True:
            with keyboard.Listener(on_press=on_press) as listener:
                listener.join()
            time.sleep(0.1)

        # stop stream
        stream.stop_stream()
        stream.close()
        wf.close()

        # close PyAudio
        p.terminate()


class TcpChat(QThread):
    def __init__(self, threadVideoPlay):
        super().__init__()
        self.threadVideoPlay = threadVideoPlay

        self.HEADER_LENGTH = 10

        self.IP = "192.168.0.106"
        self.PORT = 1234

        # Create a socket
        # socket.AF_INET - address family, IPv4, some otehr possible are AF_INET6, AF_BLUETOOTH, AF_UNIX
        # socket.SOCK_STREAM - TCP, conection-based, socket.SOCK_DGRAM - UDP, connectionless, datagrams, socket.SOCK_RAW - raw IP packets
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # SO_ - socket option
        # SOL_ - socket option level
        # Sets REUSEADDR (as a socket option) to 1 on socket
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Bind, so server informs operating system that it's going to use given IP and port
        # For a server using 0.0.0.0 means to listen on all available interfaces, useful to connect locally to 127.0.0.1 and remotely to LAN interface IP
        self.server_socket.bind((self.IP, self.PORT))

        # This makes server listen to new connections
        self.server_socket.listen()

        # List of sockets for select.select()
        self.sockets_list = [self.server_socket]

        # List of connected clients - socket as a key, user header and name as data
        self.clients = {}

        print(f'Listening for TCP chat connections on {self.IP}:{self.PORT}...')

    def receive_message(self, client_socket):
        try:

            # Receive our "header" containing message length, it's size is defined and constant
            message_header = client_socket.recv(self.HEADER_LENGTH)

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

    def run(self):
        print('running chat')
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
            read_sockets, _, exception_sockets = select.select(self.sockets_list, [], self.sockets_list)

            # Iterate over notified sockets
            for notified_socket in read_sockets:

                # If notified socket is a server socket - new connection, accept it
                if notified_socket == self.server_socket:

                    # Accept new connection
                    # That gives us new socket - client socket, connected to this given client only, it's unique for that client
                    # The other returned object is ip/port set
                    client_socket, client_address = self.server_socket.accept()

                    # Client should send his name right away, receive it
                    user = self.receive_message(client_socket)

                    # If False - client disconnected before he sent his name
                    if user is False:
                        continue

                    # Add accepted socket to select.select() list
                    self.sockets_list.append(client_socket)

                    # Also save username and username header
                    self.clients[client_socket] = user

                    print('Accepted new connection from {}:{}, username: {}'.format(*client_address,
                                                                                    user['data'].decode('utf-8')))

                # Else existing socket is sending a message
                else:

                    # Receive message
                    message = self.receive_message(notified_socket)

                    # If False, client disconnected, cleanup
                    if message is False:
                        print(
                            'Closed connection from: {}'.format(self.clients[notified_socket]['data'].decode('utf-8')))

                        # Remove from list for socket.socket()
                        self.sockets_list.remove(notified_socket)

                        # Remove from our list of users
                        del self.clients[notified_socket]

                        continue

                    # Get user by notified socket, so we will know who sent the message
                    user = self.clients[notified_socket]

                    print(f'Received message from {user["data"].decode("utf-8")}: {message["data"].decode("utf-8")}')

                    command = message["data"].decode("utf-8")
                    if command == '/play':
                        self.threadVideoPlay.playSignal.emit()
                        pass
                    elif command == '/pause':
                        self.threadVideoPlay.stopSignal.emit()
                        pass
                    elif command[:7] == '/skipto':
                        try:
                            frame_nb = int(command[8:])
                            self.threadVideoPlay.stopSignal.emit()
                            self.threadVideoPlay.moveProgressBarClient(frame_nb)
                            self.threadVideoPlay.playSignal.emit()
                        except Exception as e:
                            logging.error('Error reading frame skip command\n', e)

                    # Iterate over connected clients and broadcast message
                    for client_socket in self.clients:

                        # But don't sent it to sender
                        if client_socket != notified_socket:
                            # Send user and message (both with their headers)
                            # We are reusing here message header sent by sender, and saved username header send by user when he connected
                            client_socket.send(user['header'] + user['data'] + message['header'] + message['data'])

            # It's not really necessary to have this, but will handle some socket exceptions just in case
            for notified_socket in exception_sockets:
                # Remove from list for socket.socket()
                self.sockets_list.remove(notified_socket)

                # Remove from our list of users
                del self.clients[notified_socket]


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        loadUi('open.ui', self)
        self.frame.setScaledContents(True)
        self.setWindowTitle('OpenParty Server')
        self.totalFrames = 0
        self.fps = 0
        self.q = queue.Queue(maxsize=10)
        self.threadVideoGen = QThread()
        self.threadVideoPlay = QThread()
        self.threadAudio = QThread()
        self.threadChat = QThread()
        self.openButton.clicked.connect(self.openFile)

    # initialize threads for each component
    def startVideoGen(self):
        self.threadVideoGen = VideoGen(self.cap, self.q)
        self.threadVideoGen.start()

    def startVideoPlay(self):
        self.threadVideoPlay = PlayVideo(self.cap, self.q, self.progresslabel, self.progressBar, self.frame,
                                         self.totalFrames, self.fps, self.playButton, self.stopButton,
                                         self.fpsLabel)
        self.threadVideoPlay.start()

    def startAudio(self):
        self.threadAudio = LocalAudio()
        self.threadAudio.start()

    def startTcpChat(self):
        self.threadChat = TcpChat(self.threadVideoPlay)
        self.threadChat.start()

    # after opening file start threads for each component
    def openFile(self):
        self.videoFileName = QFileDialog.getOpenFileName(self, 'Select Video File')
        self.file_name = list(self.videoFileName)[0]
        self.cap = cv2.VideoCapture(self.file_name)
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        print('Opening file {} with fps {}'.format(list(self.videoFileName)[0], self.fps))

        # extract and convert audio from the video file into a temp.wav to be sent
        # command = "ffmpeg -i {} -ab 160k -ac 2 -ar 44100 -vn {} -y".format(self.videoFileName[0], 'temp.wav')
        # os.system(command)

        self.totalFrames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.startVideoGen()
        self.startVideoPlay()
        # self.startAudio()
        self.startTcpChat()

    # when exiting the UI make sure the threads are closed properly
    def closeEvent(self, event):
        print('closed manually')
        self.threadVideoGen.terminate()
        self.threadVideoPlay.terminate()
        self.threadChat.terminate()


# run main component
app = QApplication(sys.argv)
widget = MainWindow()
widget.show()
sys.exit(app.exec_())
