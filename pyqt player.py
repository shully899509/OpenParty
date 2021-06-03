import os
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
    def __init__(self, q):
        global cap
        # print('init video gen')
        super().__init__()
        cap = cap
        self.q = q
        # print('finished init')

    def run(self):
        global cap
        # print('in gen run')
        WIDTH = 400
        # print(self.cap.isOpened())
        # frame_no = 1
        while (cap.isOpened()):
            try:
                current_frame = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
                ret, frame = cap.read()
                # frame = imutils.resize(frame, width=WIDTH)
                # print('adding frame to queue')

                # convert image to RGB format
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                # get image infos
                height, width, channel = frame.shape
                # print(height, width, channel)
                step = channel * width
                # create QImage from image
                qImg = QImage(frame.data, width, height, step, QImage.Format_RGB888)

                self.q.put((ret, qImg, current_frame))
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
    def __init__(self, q, progresslabel, progressBar, frame, totalFrames, fps,
                 playButton, stopButton):
        global cap

        self.playButton = playButton
        self.stopButton = stopButton

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
        self.st = 0

        self.timer = QTimer()
        self.timer.timeout.connect(self.playVideo)
        self.timer.start(self.TS * 1000)

        self.playButton.clicked.connect(self.playTimer)
        self.stopButton.clicked.connect(self.stopTimer)

        self.slider_pressed = False
        self.progressBar.sliderPressed.connect(self.when_slider_pressed)

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
        # global cap
        value = self.progressBar.value()
        # self.q.close()
        # self.q = queue.Queue(maxsize=50)
        cap.set(1, value)
        self.timer.start(self.TS * 1000)
        print(value)

    def playVideo(self):
        fps, frames_to_count, cnt = (0, 1, 0)

        # read image in BGR format
        # print('getting frame')
        ret, qImg, current_frame = self.q.get()
        # print('got frame')

        if ret is True:
            progress = self.frame_to_timestamp(current_frame, self.fps) + ' / ' \
                       + self.frame_to_timestamp(self.totalFrames, self.fps)
            self.progresslabel.setText(progress)
            # logging.info(current_frame)
            # logging.info(threading.current_thread().ident)
            self.progressBar.setValue(current_frame)
            # print('set progress bar')

            # show image in img_label
            # print('before show image')

            # scene = QGraphicsScene()
            # scene.addPixmap(QPixmap.fromImage(qImg))

            self.frame.setPixmap(QPixmap.fromImage(qImg))
            self.frame.setScaledContents(True)
            # print('after show image')

            if cnt == frames_to_count:
                try:
                    fps = (frames_to_count / (time.time() - self.st))
                    self.st = time.time()
                    cnt = 0
                    if fps > self.fps:
                        self.TS += 0.001
                    elif fps < self.fps:
                        self.TS -= 0.001
                    else:
                        pass
                except Exception as e:
                    print(e)
            cnt += 1
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
        factor = 0.5

        with wave.open('temp.wav', 'rb') as wav:
            p = wav.getparams()
            with wave.open('temp.wav', 'wb') as audio:
                audio.setparams(p)
                frames = wav.readframes(p.nframes)
                audio.writeframesraw(audioop.mul(frames, p.sampwidth, factor))

        # mixer.init()
        # mixer.music.load('temp.wav')
        # mixer.music.play()

        # wf = wave.open("temp.wav", 'rb')
        # CHUNK = 1024
        # p = pyaudio.PyAudio()
        #
        # def on_press(key):
        #     global paused
        #     print(key)
        #     if key == keyboard.Key.space:
        #         if stream.is_stopped():  # time to play audio
        #             print('play pressed')
        #             stream.start_stream()
        #             subprocess.call(["amixer", "-D", "pulse", "sset", "Master", "10%-"])
        #             paused = False
        #             return False
        #         elif stream.is_active():  # time to pause audio
        #             print('pause pressed')
        #             stream.stop_stream()
        #             self.paused = True
        #             return False
        #     return False
        #
        # # define callback
        # def callback(in_data, frame_count, time_info, status):
        #     data = wf.readframes(frame_count)
        #     return (data, pyaudio.paContinue)
        #
        # stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
        #                 channels=wf.getnchannels(),
        #                 rate=wf.getframerate(),
        #                 output=True,
        #                 frames_per_buffer=CHUNK,
        #                 stream_callback=callback)
        #
        # # start the stream
        # stream.start_stream()
        #
        # while stream.is_active() or self.paused == True:
        #     with keyboard.Listener(on_press=on_press) as listener:
        #         listener.join()
        #     time.sleep(0.1)
        #
        # # stop stream
        # stream.stop_stream()
        # stream.close()
        # wf.close()
        #
        # # close PyAudio
        # p.terminate()


class MainWindow(QMainWindow):
    def __init__(self):
        global cap
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
        global cap
        self.videoFileName = QFileDialog.getOpenFileName(self, 'Select Video File')
        self.file_name = list(self.videoFileName)[0]
        cap = cv2.VideoCapture(self.file_name)
        self.fps = cap.get(cv2.CAP_PROP_FPS)
        print('Opening file {} with fps {}'.format(list(self.videoFileName)[0], self.fps))

        command = "ffmpeg -i {} -ab 160k -ac 2 -ar 44100 -vn {} -y".format(self.videoFileName[0], 'temp.wav')
        os.system(command)

        self.totalFrames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.startVideoGen()
        self.startVideoPlay()
        self.startAudio()

    def startVideoGen(self):
        global cap
        self.threadVideoGen = VideoGen(self.q)
        self.threadVideoGen.start()

    def startVideoPlay(self):
        global cap
        self.threadVideoPlay = PlayVideo(self.q, self.progresslabel, self.progressBar, self.frame,
                                         self.totalFrames, self.fps, self.playButton, self.stopButton)
        self.threadVideoPlay.start()

    def startAudio(self):
        self.threadAudio = LocalAudio()
        self.threadAudio.start()


app = QApplication(sys.argv)
widget = MainWindow()
widget.show()
sys.exit(app.exec_())
