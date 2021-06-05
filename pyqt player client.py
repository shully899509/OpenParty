import base64
import os
import socket
import sys

import numpy as np
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
import errno

from PyQt5.QtCore import QRunnable, Qt, QThreadPool
from pynput import keyboard

BASE_DIR = os.path.dirname(__file__)
path = BASE_DIR.replace('\\'[0], '/')

logging.basicConfig(format="%(message)s", level=logging.INFO)

class PlayVideo(QThread):
    def __init__(self, frame, fpsLabel, threadChat, playButton, stopButton, chat_socket, HEADER_LENGTH):
        super().__init__()

        self.frame = frame
        self.fpsLabel = fpsLabel
        # self.progressBar.sliderReleased.connect(self.skipFrame)
        #
        # self.progressBar.setMinimum(0)
        # self.progressBar.setMaximum(totalFrames)

        self.playButton = playButton
        self.stopButton = stopButton

        self.timer = QTimer()
        self.timer.timeout.connect(self.playVideo)
        self.timer.start(0.5)

        self.threadChat = threadChat
        #
        self.playButton.clicked.connect(self.playTimer)
        self.stopButton.clicked.connect(self.stopTimer)
        #
        # self.slider_pressed = False
        # self.progressBar.sliderPressed.connect(self.when_slider_pressed)
        #
        # self.fps2 = 0
        # self.st = 0
        # self.frames_to_count = 1
        # self.cnt = 0

        self.fps, self.st, self.frames_to_count, self.cnt = (0, 0, 20, 0)

        self.BUFF_SIZE = 65536
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, self.BUFF_SIZE)
        self.socket_address = ('192.168.0.106', 9689)
        print('Reading from:', self.socket_address)
        self.client_socket.bind(self.socket_address)
        self.client_socket.setblocking(False)

        self.chat_socket = chat_socket
        self.HEADER_LENGTH = HEADER_LENGTH

        # cv2.namedWindow('RECEIVING VIDEO')
        # cv2.resizeWindow('RECEIVING VIDEO', 640, 480)

        # self.playVideo()

    def when_slider_pressed(self):
        self.timer.stop()

    def frame_to_timestamp(self, frame, fps):
        return str(timedelta(seconds=(frame / fps)))

    def send_message(self, message):
        # If message is not empty - send it
        if message:
            # Encode message to bytes, prepare header and convert to bytes, like for username above, then send
            message = message.encode('utf-8')
            message_header = f"{len(message):<{self.HEADER_LENGTH}}".encode('utf-8')
            self.chat_socket.send(message_header + message)
        try:
            # Receive our "header" containing username length, it's size is defined and constant
            username_header = self.chat_socket.recv(self.HEADER_LENGTH)

            # If we received no data, server gracefully closed a connection, for example using socket.close() or socket.shutdown(socket.SHUT_RDWR)
            if not len(username_header):
                print('Connection closed by the server')
                sys.exit()

            # Convert header to int value
            username_length = int(username_header.decode('utf-8').strip())

            # Receive and decode username
            username = self.chat_socket.recv(username_length).decode('utf-8')

            # Now do the same for message (as we received username, we received whole message, there's no need to check if it has any length)
            message_header = self.chat_socket.recv(self.HEADER_LENGTH)
            message_length = int(message_header.decode('utf-8').strip())
            message = self.chat_socket.recv(message_length).decode('utf-8')

            # Print message
            print(f'{username} > {message}')
        except IOError as e:
            # This is normal on non blocking connections - when there are no incoming data error is going to be raised
            # Some operating systems will indicate that using AGAIN, and some using WOULDBLOCK error code
            # We are going to check for both - if one of them - that's expected, means no incoming data, continue as normal
            # If we got different error code - something happened
            if e.errno != errno.EAGAIN and e.errno != errno.EWOULDBLOCK:
                print('Reading error: {}'.format(str(e)))
                sys.exit()
        except Exception as e:
            # Any other exception - something happened, exit
            print('Reading error: '.format(str(e)))
            sys.exit()

    def playTimer(self):
        # start timer
        self.send_message('/play')

    def stopTimer(self):
        # stop timer
        self.send_message('/pause')

    def skipFrame(self):
        value = self.progressBar.value()
        # self.q.close()
        # self.q = queue.Queue(maxsize=50)
        self.cap.set(1, value)
        self.timer.start(self.TS * 1000)
        # print(value)

    def playVideo(self):
        try:
            packet, _ = self.client_socket.recvfrom(self.BUFF_SIZE)
            data = base64.b64decode(packet, ' /')
            npdata = np.fromstring(data, dtype=np.uint8)
            frame = cv2.imdecode(npdata, 1)

            # print(frame)

            # cv2.imshow("RECEIVING VIDEO", frame)

            # convert image to RGB format
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            # get image infos
            height, width, channel = frame.shape
            # print(height, width, channel)
            step = channel * width
            # create QImage from image
            qImg = QImage(frame.data, width, height, step, QImage.Format_RGB888)

            self.frame.setPixmap(QPixmap.fromImage(qImg))

            self.fpsLabel.setText(str(round(self.fps, 1)))
            if self.cnt == self.frames_to_count:
                try:
                    self.fps = round(self.frames_to_count / (time.time() - self.st))
                    self.st = time.time()
                    self.cnt = 0
                except:
                    pass
            self.cnt += 1

        except BlockingIOError:
            pass
        except Exception as e:
            logging.error(e)
        # print('received')

        def quit(self):
            print('closed thread')

class TcpChat(QThread):
    def __init__(self, chat_socket, HEADER_LENGHT):
        super().__init__()
        self.chat_socket = chat_socket
        self.HEADER_LENGTH = HEADER_LENGHT

        self.my_username = input("Username: ")

        # Prepare username and header and send them
        # We need to encode username to bytes, then count number of bytes and prepare header of fixed size, that we encode to bytes as well
        self.username = self.my_username.encode('utf-8')
        self.username_header = f"{len(self.username):<{self.HEADER_LENGTH}}".encode('utf-8')
        self.chat_socket.send(self.username_header + self.username)


        # Create a socket
        # socket.AF_INET - address family, IPv4, some otehr possible are AF_INET6, AF_BLUETOOTH, AF_UNIX
        # socket.SOCK_STREAM - TCP, conection-based, socket.SOCK_DGRAM - UDP, connectionless, datagrams, socket.SOCK_RAW - raw IP packets

    def send_message(self, message):
        # If message is not empty - send it
        if message:
            # Encode message to bytes, prepare header and convert to bytes, like for username above, then send
            message = message.encode('utf-8')
            message_header = f"{len(message):<{self.HEADER_LENGTH}}".encode('utf-8')
            self.chat_socket.send(message_header + message)
        try:
            # Receive our "header" containing username length, it's size is defined and constant
            username_header = self.chat_socket.recv(self.HEADER_LENGTH)

            # If we received no data, server gracefully closed a connection, for example using socket.close() or socket.shutdown(socket.SHUT_RDWR)
            if not len(username_header):
                print('Connection closed by the server')
                sys.exit()

            # Convert header to int value
            username_length = int(username_header.decode('utf-8').strip())

            # Receive and decode username
            username = self.chat_socket.recv(username_length).decode('utf-8')

            # Now do the same for message (as we received username, we received whole message, there's no need to check if it has any length)
            message_header = self.chat_socket.recv(self.HEADER_LENGTH)
            message_length = int(message_header.decode('utf-8').strip())
            message = self.chat_socket.recv(message_length).decode('utf-8')

            # Print message
            print(f'{username} > {message}')
        except IOError as e:
            # This is normal on non blocking connections - when there are no incoming data error is going to be raised
            # Some operating systems will indicate that using AGAIN, and some using WOULDBLOCK error code
            # We are going to check for both - if one of them - that's expected, means no incoming data, continue as normal
            # If we got different error code - something happened
            if e.errno != errno.EAGAIN and e.errno != errno.EWOULDBLOCK:
                print('Reading error: {}'.format(str(e)))
                sys.exit()
        except Exception as e:
            # Any other exception - something happened, exit
            print('Reading error: '.format(str(e)))
            sys.exit()

    def run(self):
        while True:
            message = input(f'{self.my_username} > ')
            self.send_message(message)

class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        loadUi('open_client.ui', self)
        self.frame.setScaledContents(True)
        self.setWindowTitle('Video Player')
        self.totalFrames = 0
        self.fps = 0
        self.threadVideoGen = QThread()
        self.threadVideoPlay = QThread()
        self.threadAudio = QThread()
        self.threadChat = QThread()
        self.readHost.clicked.connect(self.startVideoPlay)
        self.readHost.clicked.connect(self.startTcpChat)

        self.IP = "192.168.0.106"
        self.PORT = 1234
        self.HEADER_LENGTH = 10
        self.chat_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Connect to a given ip and port
        self.chat_socket.connect((self.IP, self.PORT))

        # Set connection to non-blocking state, so .recv() call won;t block, just return some exception we'll handle
        self.chat_socket.setblocking(False)

    def closeEvent(self, event):
        print('closed manually')
        # self.threadVideoPlay.isRunning()
        # self.threadChat.send_message('bye bye')
        self.chat_socket.close()

    def startVideoPlay(self):
        self.threadVideoPlay = PlayVideo(self.frame, self.fpsLabel, self.threadChat,
                                         self.playButton, self.stopButton,
                                         self.chat_socket, self.HEADER_LENGTH)
        self.threadVideoPlay.start()

    def startTcpChat(self):
        self.threadChat = TcpChat(self.chat_socket, self.HEADER_LENGTH)
        self.threadChat.start()





app = QApplication(sys.argv)
widget = MainWindow()
widget.show()
sys.exit(app.exec_())
