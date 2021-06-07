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
import threading

from PyQt5.QtCore import QRunnable, Qt, QThreadPool
from pynput import keyboard

BASE_DIR = os.path.dirname(__file__)
path = BASE_DIR.replace('\\'[0], '/')

logging.basicConfig(format="%(message)s", level=logging.INFO)


class LocalAudio(QThread):
    playAudioSignal = pyqtSignal()

    playSignal = pyqtSignal()
    stopSignal = pyqtSignal()

    def destroy(self):
        self.terminate()
        self.deleteLater()

    def __init__(self, playButton, stopButton, progressBar, audioProgressLabel, video_fps):
        super().__init__()

        self.playAudioSignal.connect(self.play_audio)
        self.audioProgressLabel = audioProgressLabel
        self.video_fps = video_fps

        # signals used by TCP chat thread in order to play/pause the timer from the exterior
        self.playSignal.connect(self.play_timer)
        self.stopSignal.connect(self.stop_timer)

        # seek audio to slider position when released
        self.progressBar = progressBar
        self.progressBar.sliderReleased.connect(self.move_slider)

        # bind play/pause buttons
        self.playButton = playButton
        self.stopButton = stopButton
        self.playButton.clicked.connect(self.play_timer)
        self.stopButton.clicked.connect(self.stop_timer)

        self.host_name = socket.gethostname()
        self.host_ip = '192.168.0.106'  # server ip
        print('audio host at ', self.host_ip)
        self.port = 9633

        self.BUFF_SIZE = 65536
        self.audio_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.audio_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, self.BUFF_SIZE)

        # self.audio_socket.bind((self.host_ip, (self.port)))
        self.CHUNK = 1024
        self.wf = wave.open("temp.wav")
        self.p = pyaudio.PyAudio()
        print('server listening at', (self.host_ip, (self.port)), self.wf.getframerate())
        self.stream = self.p.open(format=self.p.get_format_from_width(self.wf.getsampwidth()),
                                  channels=self.wf.getnchannels(),
                                  rate=self.wf.getframerate(),
                                  input=True, output=True,
                                  frames_per_buffer=self.CHUNK)
        print('audio framerate', self.wf.getframerate())
        self.data = None
        self.sample_rate = self.wf.getframerate()

        self.client_addr = ('192.168.0.106', 9634)  # client ip

        self.timer = QTimer()
        self.timer.timeout.connect(self.play_audio)

        self.total_frames = self.wf.getnframes()

    # restart the timer when play button is pressed
    def play_timer(self):
        self.timer.start(1000 * 0.8 * self.CHUNK / self.sample_rate)
        self.is_paused = False

    # stop the timer when pause button is pressed
    def stop_timer(self):
        self.timer.stop()
        self.is_paused = True

    def move_slider(self):
        try:
            self.timer.stop()
            value = self.progressBar.value()
            time.sleep(0.05)
            if not self.is_paused:
                self.timer.start(1000 * 0.8 * self.CHUNK / self.sample_rate)

            self.wf.setpos(int((value / self.video_fps) * self.sample_rate))
            # print('skipped to ', (value/25))
        except Exception as e:
            logging.error(e)

    def move_slider_client(self, value):
        time.sleep(0.05)
        self.wf.setpos(int((value / self.video_fps) * self.sample_rate))

    def play_audio(self):
        # print('chunk {}, sample rate {}, second {}'.format(self.wf.tell(),
        #                                                    self.sample_rate,
        #                                                    self.wf.tell()/self.sample_rate))

        self.data = self.wf.readframes(self.CHUNK)
        current_position = self.wf.tell()
        progress = str(timedelta(seconds=(current_position / self.sample_rate))) + ' / ' \
                   + str(timedelta(seconds=(self.total_frames / self.sample_rate)))
        self.audioProgressLabel.setText(progress)

        self.audio_socket.sendto(self.data, self.client_addr)
        self.stream.write(self.data)
