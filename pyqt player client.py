# TODO: (only sent audio, still need sync) receive audio packets and sync with video
# DONE: try to connect to host AFTER clicking on 'start' button
# TODO: fix crash when video is ended or trying to reconnect
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
import pickle
import threading

logging.basicConfig(format="%(message)s", level=logging.INFO)


class PlayVideo(QThread):
    def __init__(self, frame, fpsLabel, threadChat, playButton, stopButton, chat_socket,
                 progressBar, progresslabel):
        super().__init__()

        self.frame = frame
        self.fpsLabel = fpsLabel

        self.playButton = playButton
        self.stopButton = stopButton
        self.progressBar = progressBar
        self.progresslabel = progresslabel

        self.timer = QTimer()
        self.timer.timeout.connect(self.playVideo)
        self.timer.start(0.5)

        self.threadChat = threadChat

        self.playButton.clicked.connect(self.playTimer)
        self.stopButton.clicked.connect(self.stopTimer)

        self.fps, self.st, self.frames_to_count, self.cnt = (0, 0, 20, 0)

        self.BUFF_SIZE = 65536
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, self.BUFF_SIZE)
        self.socket_address = ('192.168.0.106', 9685)  # client ip
        print('Reading from:', self.socket_address)
        self.client_socket.bind(self.socket_address)
        self.client_socket.setblocking(False)

        self.progressBar.sliderPressed.connect(self.when_slider_pressed)
        self.progressBar.sliderReleased.connect(self.moveProgressBar)

        self.chat_socket = chat_socket

        self.slider_pressed = False
        self.set_total_frames = False

    def frame_to_timestamp(self, frame, fps):
        return str(timedelta(seconds=(frame / fps)))

    def send_message(self, message):
        message = '{}: {}'.format(self.threadChat.nickname, message)
        self.chat_socket.send(message.encode('ascii'))

    def playTimer(self):
        # start timer
        self.send_message('/play')

    def stopTimer(self):
        # stop timer
        self.send_message('/pause')

    def when_slider_pressed(self):
        self.slider_pressed = True

    def moveProgressBar(self):
        value = self.progressBar.value()
        self.send_message('/skipto ' + str(value))
        self.slider_pressed = False

    def playVideo(self):
        try:
            packet_ser, _ = self.client_socket.recvfrom(self.BUFF_SIZE)

            packet = pickle.loads(packet_ser)

            # TODO: receive total_frames and real_fps from the chat TCP socket only once
            # can't since server can open different video file and client metadata doesn't update
            # consider sending total_frames and real_fps to client over TCP chat everytime we change the file
            current_frame_no = packet["frame_nb"]
            total_frames = packet["total_frames"]
            real_fps = packet["fps"]
            if not self.set_total_frames:
                self.progressBar.setMinimum(0)
                self.progressBar.setMaximum(total_frames)
                self.set_total_frames = True

            if self.slider_pressed is False:
                self.progressBar.setValue(current_frame_no)

            progress = self.frame_to_timestamp(current_frame_no, real_fps) + ' / ' \
                       + self.frame_to_timestamp(total_frames, real_fps)
            self.progresslabel.setText(progress)

            data = base64.b64decode(packet["frame"], ' /')
            npdata = np.fromstring(data, dtype=np.uint8)
            frame = cv2.imdecode(npdata, 1)

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

        # because of socket being non-blocking
        # we must pass the error when not receiving frames (video is paused)
        except BlockingIOError:
            pass
        except Exception as e:
            logging.error(e)

        # print('received')

        def quit(self):
            print('closed thread')


class TcpChat(QThread):
    def __init__(self, chat_socket):
        super().__init__()
        self.nickname = 'test_user'  # input("Choose your nickname: ")

        self.client = chat_socket
        self.client.connect(('192.168.0.106', 7976))  # connecting client to server
        # self.client.setblocking(False)

    def receive(self):
        while True:  # making valid connection
            try:
                message = self.client.recv(1024).decode('ascii')
                if message == 'NICKNAME':
                    self.client.send(self.nickname.encode('ascii'))
                else:
                    print(message)  # received in bytes
            except Exception as e:  # case on wrong ip/port details
                print("An error occured on the server side!")
                logging.error(e)
                self.client.close()
                break

    def write(self):
        while True:  # message layout
            message = '{}: {}'.format(self.nickname, input(''))
            self.client.send(message.encode('ascii'))

    def run(self):
        receive_thread = threading.Thread(target=self.receive)  # receiving multiple messages
        receive_thread.start()
        write_thread = threading.Thread(target=self.write)  # sending messages
        write_thread.start()


class AudioRec(QThread):
    def __init__(self):
        super().__init__()

        self.host_name = socket.gethostname()
        self.host_ip = '192.168.0.106'  # client ip
        print(self.host_ip)
        self.port = 9631
        # For details visit: www.pyshine.com
        self.q = queue.Queue(maxsize=100)

        self.BUFF_SIZE = 65536
        self.audio_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.audio_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, self.BUFF_SIZE)
        self.socket_address = (self.host_ip, self.port)
        self.audio_socket.bind(self.socket_address)
        self.p = pyaudio.PyAudio()
        self.CHUNK = 1024
        self.stream = self.p.open(format=self.p.get_format_from_width(2),
                                  channels=2,
                                  rate=44100,
                                  output=True,
                                  frames_per_buffer=self.CHUNK)

        self.timer = QTimer()
        self.timer.timeout.connect(self.playAudio)
        self.timer.start(1000 * 0.8 * self.CHUNK / 44100)

        t1 = threading.Thread(target=self.getAudioData, args=())
        t1.start()
        print('Now Playing...')

    def getAudioData(self):
        while True:
            try:
                self.frame, _ = self.audio_socket.recvfrom(self.BUFF_SIZE)
                self.q.put(self.frame)
            except BlockingIOError:
                pass
            except Exception as e:
                logging.error(e)

    def playAudio(self):
        if not self.q.empty():
            frame = self.q.get()
            self.stream.write(frame)


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        loadUi('open_client.ui', self)
        self.frame.setScaledContents(True)
        self.setWindowTitle('OpenParty Client')
        self.totalFrames = 0
        self.fps = 0
        self.threadVideoGen = QThread()
        self.threadVideoPlay = QThread()
        self.threadAudio = QThread()
        self.threadChat = QThread()
        self.readHost.clicked.connect(self.startAllThreads)

        self.HEADER_LENGTH = 10
        self.chat_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.chat_started = False

    def startAllThreads(self):
        if not self.chat_started:
            self.startTcpChat()
            self.chat_started = True
        if not self.threadAudio.isRunning():
            self.startAudio()
        if not self.threadVideoPlay.isRunning():
            self.startVideoPlay()

    def closeEvent(self, event):
        print('closed manually')
        self.chat_socket.close()
        self.threadVideoPlay.terminate()
        self.threadAudio.terminate()
        self.threadChat.terminate()
        os._exit(1)

    def startVideoPlay(self):
        self.threadVideoPlay = PlayVideo(self.frame, self.fpsLabel, self.threadChat,
                                         self.playButton, self.stopButton,
                                         self.chat_socket,
                                         self.progressBar, self.progresslabel)
        self.threadVideoPlay.start()

    def startAudio(self):
        self.threadAudio = AudioRec()
        self.threadAudio.start()

    def startTcpChat(self):
        self.threadChat = TcpChat(self.chat_socket)
        self.threadChat.start()


app = QApplication(sys.argv)
widget = MainWindow()
widget.show()
sys.exit(app.exec_())
