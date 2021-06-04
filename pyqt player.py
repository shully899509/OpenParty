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

from PyQt5.QtCore import QRunnable, Qt, QThreadPool
from pynput import keyboard

BASE_DIR = os.path.dirname(__file__)
path = BASE_DIR.replace('\\'[0], '/')

logging.basicConfig(format="%(message)s", level=logging.INFO)


class VideoGen(QThread):
    def __init__(self, cap, q):
        # print('init video gen')
        super().__init__()
        self.cap = cap
        self.q = q
        # print('finished init')

    def run(self):
        # print('in gen run')
        WIDTH = 600
        # print(self.cap.isOpened())
        # frame_no = 1
        while (self.cap.isOpened()):
            try:
                current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
                ret, frame = self.cap.read()
                # frame = imutils.resize(frame, width=WIDTH)
                # print('adding frame to queue')

                frame = imutils.resize(frame, width=WIDTH)
                self.q.put((ret, frame, current_frame))
                # print('sent frame: ', self.q.qsize())
                # frame_no += 1
                # print('after add frame')
            except Exception as e:
                break
                # print(e)
                # os._exit(1)
        print('Player closed')
        BREAK = True
        self.cap.release()


import threading


class PlayVideo(QThread):
    def __init__(self, cap, q, progresslabel, progressBar, frame, totalFrames, fps,
                 playButton, stopButton, fpsLabel):

        self.cap = cap
        self.playButton = playButton
        self.stopButton = stopButton
        self.fpsLabel = fpsLabel

        # print('init video gen')
        super().__init__()
        self.q = q
        self.progresslabel = progresslabel
        self.progressBar = progressBar
        self.frame = frame
        self.totalFrames = totalFrames
        self.fps = fps
        self.TS = (0.5 / self.fps)

        self.progressBar.sliderReleased.connect(self.skipFrame)
        #
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(totalFrames)


        self.timer = QTimer()
        self.timer.timeout.connect(self.playVideo)
        self.timer.start(self.TS * 1000)

        self.playButton.clicked.connect(self.playTimer)
        self.stopButton.clicked.connect(self.stopTimer)

        self.slider_pressed = False
        self.progressBar.sliderPressed.connect(self.when_slider_pressed)

        self.fps2 = 0
        self.st = 0
        self.frames_to_count = 1
        self.cnt = 0

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
        #print(value)

    def playVideo(self):
        # read image in BGR format
        ret, frame, current_frame = self.q.get()

        if ret is True:
            progress = self.frame_to_timestamp(current_frame, self.fps) + ' / ' \
                       + self.frame_to_timestamp(self.totalFrames, self.fps)
            self.progresslabel.setText(progress)
            # logging.info(current_frame)
            # logging.info(threading.current_thread().ident)
            self.progressBar.setValue(current_frame)

            try:
                encoded, buffer = cv2.imencode('.jpeg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                message = base64.b64encode(buffer)
                client_addr_new1 = ('192.168.0.106', 9689)  # udp ip to local client
                self.server_socket.sendto(message, client_addr_new1)
            except Exception as e:
                logging.error(e)

            print(frame)
            # self.timer.stop()

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
            # print('after show image')

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

            # restart timer with new TS
            self.timer.start(self.TS * 1000)

        else:
            print('return false')
            progress = str(current_frame) + ' / ' \
                       + str(self.totalFrames)
            self.progresslabel.setText(progress)
            self.progressBar.setValue(current_frame)


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


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        loadUi('open.ui', self)
        self.setWindowTitle('Video Player')
        self.totalFrames = 0
        self.fps = 0
        self.q = queue.Queue(maxsize=10)
        self.threadVideoGen = QThread()
        self.threadVideoPlay = QThread()
        self.threadAudio = QThread()
        self.openButton.clicked.connect(self.openFile)

    def openFile(self):
        self.videoFileName = QFileDialog.getOpenFileName(self, 'Select Video File')
        self.file_name = list(self.videoFileName)[0]
        self.cap = cv2.VideoCapture(self.file_name)
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        print('Opening file {} with fps {}'.format(list(self.videoFileName)[0], self.fps))

        # command = "ffmpeg -i {} -ab 160k -ac 2 -ar 44100 -vn {} -y".format(self.videoFileName[0], 'temp.wav')
        # os.system(command)

        self.totalFrames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.startVideoGen()
        self.startVideoPlay()
        # self.startAudio()

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


app = QApplication(sys.argv)
widget = MainWindow()
widget.show()
sys.exit(app.exec_())
