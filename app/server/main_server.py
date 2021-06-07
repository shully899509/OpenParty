# TODO: (needs sync) send audio packets through UDP socket and sync with video
# DONE: move code into separate .py files for each module
# TODO: replace send frames to hardcoded client addresses with list of addresses from chat TCP connection
# DONE: fix crash when trying to open another video
# DONE: fix TCP chat so it updates all clients when receiving message
import sys
from PyQt5.uic import loadUi
from PyQt5.QtCore import QThread
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog
import cv2
import queue
import os

from app.server.VideoGen import VideoGen
from app.server.ServerVideo import PlayVideo
from app.server.ServerAudio import LocalAudio
from app.server.ServerTcpChat import TcpChat


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        loadUi('open.ui', self)
        self.frame.setScaledContents(True)
        self.setWindowTitle('OpenParty Server')
        self.totalFrames = 0
        self.fps = 0
        self.q = queue.Queue(maxsize=10)
        self.openButton.clicked.connect(self.open_file)

        self.threadVideoGen = QThread()
        self.threadVideoPlay = QThread()
        self.threadAudio = QThread()
        self.threadChat = QThread()

    # initialize threads for each component
    def start_video_gen(self):
        self.threadVideoGen = VideoGen(self.cap, self.q)
        self.threadVideoGen.start()

    def start_video_play(self):
        self.threadVideoPlay = PlayVideo(self.cap, self.q, self.progresslabel, self.progressBar, self.frame,
                                         self.totalFrames, self.fps, self.playButton, self.stopButton,
                                         self.fpsLabel)
        self.threadVideoPlay.start()

    def start_audio(self):
        self.threadAudio = LocalAudio(self.playButton, self.stopButton,
                                      self.progressBar, self.audioProgressLabel,
                                      self.fps)
        self.threadAudio.start()

    def start_tcp_chat(self):
        if not self.threadChat.isRunning():
            print('starting chat thread...')
            self.threadChat = TcpChat(self.threadVideoPlay, self.threadAudio)
            self.threadChat.start()
        else:
            self.threadChat.update_threads(self.threadVideoPlay, self.threadAudio)

    # after opening file start threads for each component
    def open_file(self):
        if self.threadVideoPlay.isRunning():
            self.threadVideoPlay.stopSignal.emit()
        if self.threadAudio.isRunning():
            self.threadAudio.stopSignal.emit()

        if self.threadVideoGen.isRunning():
            self.threadVideoGen.destroy()
        if self.threadVideoPlay.isRunning():
            self.threadVideoPlay.destroy()
        if self.threadAudio.isRunning():
            self.threadAudio.destroy()
        self.threadVideoGen = QThread()
        self.threadVideoPlay = QThread()
        self.threadAudio = QThread()

        self.videoFileName = QFileDialog.getOpenFileName(self, 'Select Video File')
        self.file_name = list(self.videoFileName)[0]
        self.cap = cv2.VideoCapture(self.file_name)
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        print('Opening file {} with fps {}'.format(list(self.videoFileName)[0], self.fps))

        # extract and convert audio from the video file into a temp.wav to be sent
        command = "ffmpeg -i {} -ab 160k -ac 2 -ar 44100 -vn {} -y".format(self.videoFileName[0], 'temp.wav')
        os.system(command)

        self.totalFrames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.start_audio()
        self.start_video_gen()
        self.start_video_play()
        self.start_tcp_chat()

    # when exiting the UI make sure the threads are closed properly
    def closeEvent(self, event):
        print('closed manually')
        if self.threadVideoGen.isRunning():
            self.threadVideoGen.destroy()
        if self.threadVideoPlay.isRunning():
            self.threadVideoPlay.destroy()
        if self.threadAudio.isRunning():
            self.threadAudio.destroy()
        self.threadChat.terminate()


# run main component
app = QApplication(sys.argv)
widget = MainWindow()
widget.show()
sys.exit(app.exec_())
