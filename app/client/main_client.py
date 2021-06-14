# DONE: (only sent audio, still need sync) receive audio packets and sync with video
# DONE: try to connect to host AFTER clicking on 'start' button
# TODO: fix crash when video is ended or trying to reconnect
import socket
import sys

from PyQt5.uic import loadUi
from PyQt5.QtCore import QThread
from PyQt5.QtWidgets import QApplication, QMainWindow
import logging
import os
import psutil
from ClientVideo import PlayVideo
from ClientAudio import AudioRec
from ClientTcpChat import TcpChat
from pycaw.pycaw import AudioUtilities

logging.basicConfig(format="%(message)s", level=logging.INFO)


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        loadUi('open_client.ui', self)
        self.frame.setScaledContents(True)
        self.setWindowTitle('OpenParty Client')
        self.totalFrames = 0
        self.fps = 0
        self.thread_video_gen = QThread()
        self.thread_video_play = QThread()
        self.thread_audio_play = QThread()
        self.thread_chat = QThread()
        self.readHost.clicked.connect(self.start_all_threads)

        self.HEADER_LENGTH = 10
        self.chat_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.chat_started = False

        self.volumeSlider.setMinimum(0)
        self.volumeSlider.setMaximum(100)
        self.volumeSlider.setValue(50)
        self.volumeSlider.sliderReleased.connect(self.set_volume)

        self.process_name = psutil.Process(os.getpid()).name()
        self.volume_set = False

    def start_all_threads(self):
        if not self.chat_started:
            print('Trying connection to {}'.format(self.hostAddressBox.text()))
            self.start_tcp_chat()
            self.chat_started = True
        if not self.thread_audio_play.isRunning():
            self.start_audio()
        if not self.thread_video_play.isRunning():
            self.start_video_play()

        for session in AudioUtilities.GetAllSessions():
            if session.Process and session.Process.name() == self.process_name:
                self.volume = session.SimpleAudioVolume
                self.volume.SetMasterVolume(0.5, None)
                self.volumeSlider.setValue(50)
                self.volume_set = True

    def closeEvent(self, event):
        try:
            print('closed manually')
            self.chat_socket.close()
            self.thread_video_play.terminate()
            self.thread_audio_play.terminate()
            self.thread_chat.terminate()
        except:
            os._exit(1)

    def start_video_play(self):
        self.thread_video_play = PlayVideo(self.frame, self.fpsLabel, self.thread_chat,
                                           self.playButton, self.stopButton,
                                           self.chat_socket,
                                           self.progressBar, self.progresslabel)
        self.thread_video_play.start()

    def start_audio(self):
        self.thread_audio_play = AudioRec()
        self.thread_audio_play.start()

    def start_tcp_chat(self):
        self.thread_chat = TcpChat(self.chat_socket, self.hostAddressBox.text())
        self.thread_chat.start()

    def set_volume(self):
        if self.volume_set:
            value = self.volumeSlider.value()
            self.volume.SetMasterVolume(value / 100, None)
        else:
            self.volumeSlider.setValue(50)


app = QApplication(sys.argv)
widget = MainWindow()
widget.show()
sys.exit(app.exec_())
