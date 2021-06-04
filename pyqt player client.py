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

from PyQt5.QtCore import QRunnable, Qt, QThreadPool
from pynput import keyboard

BASE_DIR = os.path.dirname(__file__)
path = BASE_DIR.replace('\\'[0], '/')

logging.basicConfig(format="%(message)s", level=logging.INFO)

class PlayVideo(QThread):
    def __init__(self, frame):
        super().__init__()

        self.frame = frame

        # self.progressBar.sliderReleased.connect(self.skipFrame)
        #
        # self.progressBar.setMinimum(0)
        # self.progressBar.setMaximum(totalFrames)

        self.timer = QTimer()
        self.timer.timeout.connect(self.playVideo)
        self.timer.start(0.5)
        #
        # self.playButton.clicked.connect(self.playTimer)
        # self.stopButton.clicked.connect(self.stopTimer)
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

        # cv2.namedWindow('RECEIVING VIDEO')
        # cv2.resizeWindow('RECEIVING VIDEO', 640, 480)

        # self.playVideo()

    def when_slider_pressed(self):
        self.timer.stop()

    def frame_to_timestamp(self, frame, fps):
        return str(timedelta(seconds=(frame / fps)))

    def playTimer(self):
        # start timer
        self.timer.start(self.TS * 1000)

    def stopTimer(self):
        # stop timer
        self.timer.stop()

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
            self.frame.setScaledContents(True)

            if self.cnt == self.frames_to_count:
                try:
                    fps = round(self.frames_to_count / (time.time() - self.st))
                    st = time.time()
                    self.cnt = 0
                except:
                    pass
            self.cnt += 1
        except BlockingIOError:
            pass
        except Exception as e:
            logging.error(e)
        # print('received')





class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        loadUi('open_client.ui', self)
        self.setWindowTitle('Video Player')
        self.totalFrames = 0
        self.fps = 0
        self.threadVideoGen = QThread()
        self.threadVideoPlay = QThread()
        self.threadAudio = QThread()
        # self.openButton.clicked.connect(self.openFile)
        self.readHost.clicked.connect(self.startVideoPlay)

    def startVideoPlay(self):
        self.threadVideoPlay = PlayVideo(self.frame)
        self.threadVideoPlay.start()


app = QApplication(sys.argv)
widget = MainWindow()
widget.show()
sys.exit(app.exec_())
