# DONE: (needs sync) send audio packets through UDP socket and sync with video
# DONE: move code into separate .py files for each module
# TODO: replace send frames to hardcoded client addresses with list of addresses from chat TCP connection
# DONE: fix crash when trying to open another video
# DONE: fix TCP chat so it updates all clients when receiving message
import sys

from PyQt5.uic import loadUi
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog
import cv2
import queue
import os
import psutil
from pycaw.pycaw import AudioUtilities
import logging

from VideoGen import VideoGen
from ServerVideo import PlayVideo
from ServerAudio import LocalAudio
from ServerTcpChat import TcpChat

logging.basicConfig(format="%(message)s", level=logging.INFO)


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        loadUi('open.ui', self)
        self.frame.setScaledContents(True)
        self.setWindowTitle('OpenParty Server')
        self.totalFrames = 0
        self.fps = 0
        self.openButton.clicked.connect(self.open_file)

        self.threadVideoGen = QThread()
        self.threadVideoPlay = QThread()
        self.threadAudio = QThread()
        self.threadChat = QThread()

        self.volumeSlider.setMinimum(0)
        self.volumeSlider.setMaximum(100)
        self.volumeSlider.setValue(50)
        self.volumeSlider.sliderReleased.connect(self.set_volume)

        self.process_name = psutil.Process(os.getpid()).name()
        self.volume_set = False

        self.session_active = True
        while not self.session_active:
            pass

    # initialize threads for each component
    def start_video_gen(self):
        self.threadVideoGen = VideoGen(self.cap, self.q, self.totalFrames)
        self.threadVideoGen.start()

    def start_audio(self):
        self.threadAudio = LocalAudio(self.playButton, self.stopButton,
                                      self.progressBar, self.audioProgressLabel,
                                      self.fps)
        self.threadAudio.start()

    def start_video_play(self):
        self.threadVideoPlay = PlayVideo(self.cap, self.q, self.progresslabel, self.progressBar, self.frame,
                                         self.totalFrames, self.fps, self.playButton, self.stopButton,
                                         self.fpsLabel, self.threadVideoGen, self.threadAudio)
        self.threadVideoPlay.start()

    def start_tcp_chat(self):
        if not self.threadChat.isRunning():
            print('starting chat thread...')
            self.threadChat = TcpChat(self.threadVideoPlay, self.threadAudio)
            self.threadChat.start()
        else:
            self.threadChat.update_threads(self.threadVideoPlay, self.threadAudio)

    # after opening file start threads for each component
    def open_file(self):
        try:
            if self.threadVideoPlay.isRunning():
                self.threadVideoPlay.stopSignal.emit()
            if self.threadAudio.isRunning():
                self.threadAudio.stopSignal.emit()

            if self.threadAudio.isRunning():
                self.threadAudio.destroy()
            if self.threadVideoPlay.isRunning():
                self.threadVideoPlay.destroy()
            if self.threadVideoGen.isRunning():
                self.threadVideoGen.destroy()

            self.threadVideoGen = QThread()
            self.threadVideoPlay = QThread()
            self.threadAudio = QThread()

            self.videoFileName = QFileDialog.getOpenFileName(self, 'Select Video File')
            self.file_name = list(self.videoFileName)[0]
            if not self.file_name == "":
                self.cap = cv2.VideoCapture(self.file_name)
                # if not self.cap:
                #     raise Exception('file not valid')
                self.fps = self.cap.get(cv2.CAP_PROP_FPS)
                self.q = queue.Queue(maxsize=1000)
                self.totalFrames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

                print('Opening file {} with fps {}'.format(list(self.videoFileName)[0], self.fps))

                # extract and convert audio from the video file into a temp.wav to be sent
                # set the bitrate, number of channels, sample size and overwrite old file with same name
                command = "ffmpeg -i \"{}\" -ab 160k -ac 2 -ar 44100 -vn {} -y".format(self.videoFileName[0], 'temp.wav')
                os.system(command)

                self.start_video_gen()
                self.start_audio()
                self.start_video_play()
                self.start_tcp_chat()

                for session in AudioUtilities.GetAllSessions():
                    if session.Process and session.Process.name() == self.process_name:
                        self.volume = session.SimpleAudioVolume
                        self.volume.SetMasterVolume(0.5, None)
                        self.volumeSlider.setValue(50)
                        self.volume_set = True
        except Exception as e:
            logging.error(e)

    def set_volume(self):
        if self.volume_set:
            value = self.volumeSlider.value()
            self.volume.SetMasterVolume(value / 100, None)
        else:
            self.volumeSlider.setValue(50)

    # when exiting the UI make sure the threads are closed
    def closeEvent(self, event):
        try:
            print('closed manually')
            self.threadChat.terminate()
            if self.threadVideoPlay.isRunning():
                self.threadVideoPlay.destroy()
            if self.threadAudio.isRunning():
                self.threadAudio.destroy()
            if self.threadVideoGen.isRunning():
                self.threadVideoGen.destroy()
        except:
            os._exit(1)




# run main component
app = QApplication(sys.argv)
widget = MainWindow()
widget.show()
sys.exit(app.exec_())
