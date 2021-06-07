# TODO: (only sent audio, still need sync) receive audio packets and sync with video
# DONE: try to connect to host AFTER clicking on 'start' button
# TODO: fix crash when video is ended or trying to reconnect
import socket
import sys


from PyQt5.uic import loadUi
from PyQt5.QtCore import pyqtSlot, QTimer, QObject, pyqtSignal, QThread
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QFileDialog, QLabel, QGraphicsScene, QGraphicsView
import logging, random, imutils
import os
from app.client.ClientVideo import PlayVideo
from app.client.ClientAudio import AudioRec
from app.client.ClientTcpChat import TcpChat

logging.basicConfig(format="%(message)s", level=logging.INFO)


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
        self.readHost.clicked.connect(self.start_all_threads)

        self.HEADER_LENGTH = 10
        self.chat_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.chat_started = False

    def start_all_threads(self):
        if not self.chat_started:
            self.start_tcp_chat()
            self.chat_started = True
        if not self.threadAudio.isRunning():
            self.start_audio()
        if not self.threadVideoPlay.isRunning():
            self.start_video_play()

    def closeEvent(self, event):
        print('closed manually')
        self.chat_socket.close()
        self.threadVideoPlay.terminate()
        self.threadAudio.terminate()
        self.threadChat.terminate()
        os._exit(1)

    def start_video_play(self):
        self.threadVideoPlay = PlayVideo(self.frame, self.fpsLabel, self.threadChat,
                                         self.playButton, self.stopButton,
                                         self.chat_socket,
                                         self.progressBar, self.progresslabel)
        self.threadVideoPlay.start()

    def start_audio(self):
        self.threadAudio = AudioRec()
        self.threadAudio.start()

    def start_tcp_chat(self):
        self.threadChat = TcpChat(self.chat_socket)
        self.threadChat.start()


app = QApplication(sys.argv)
widget = MainWindow()
widget.show()
sys.exit(app.exec_())