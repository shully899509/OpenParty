import os
import sys
from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.uic import loadUi
from PyQt5.QtCore import pyqtSlot, QTimer, QObject, pyqtSignal, QThread
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QFileDialog
import cv2
from datetime import timedelta
import queue
import time
import logging, random, imutils

from PyQt5.QtCore import QRunnable, Qt, QThreadPool

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
        frame_no = 1
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
                step = channel * width
                # create QImage from image
                qImg = QImage(frame.data, width, height, step, QImage.Format_RGB888)

                self.q.put((ret, qImg, current_frame))
                print('sent frame: ', self.q.qsize())
                frame_no += 1
                # print('after add frame')
            except Exception as e:
                break
                #print(e)
                #os._exit(1)
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
            logging.info(current_frame)
            # logging.info(threading.current_thread().ident)
            self.progressBar.setValue(current_frame)
            # print('set progress bar')

            # show image in img_label
            # print('before show image')
            self.frame.setPixmap(QPixmap.fromImage(qImg))
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
            # time.sleep(TS)
        else:
            print('return false')
            progress = str(current_frame) + ' / ' \
                       + str(self.totalFrames)
            self.progresslabel.setText(progress)
            self.progressBar.setValue(current_frame)


    # def skipFrame(self):
    #     value = self.progressBar.value()
    #     self.cap.set(1, value)


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

        # create a timer
        # self.timer = QTimer()
        # self.timer.timeout.connect(self.startVideoPlay)

        self.openButton.clicked.connect(self.openFile)
        # self.openButton.clicked.connect(self.runTasks)
        # open = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+O"), self)
        # open.activated.connect(self.openFile)

        # self.progressBar.valueChanged.connect(self.skipFrame)

        # self.progressBar.setMinimum(0)
        # self.progressBar.setMaximum(0)

    def openFile(self):
        global cap
        self.videoFileName = QFileDialog.getOpenFileName(self, 'Select Video File')
        self.file_name = list(self.videoFileName)[0]

        cap = cv2.VideoCapture(self.file_name)

        self.fps = cap.get(cv2.CAP_PROP_FPS)
        print('Opening file {} with fps {}'.format(list(self.videoFileName)[0], self.fps))
        self.totalFrames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        # self.progressBar.setMinimum(0)
        # self.progressBar.setMaximum(self.totalFrames)
        # self.progressBar.setValue(0)
        self.startVideoGen()
        self.startVideoPlay()
        # self.timer.start(self.fps)



    #
    #
    # def frame_to_timestamp(self, frame, fps):
    #     return str(timedelta(seconds=(frame / fps)))
    #
    # def playVideo(self):
    #     # read image in BGR format
    #     print('getting frame')
    #     ret, image = self.q.get()
    #     print('got frame')
    #     fps = self.cap.get(cv2.CAP_PROP_FPS)
    #     if ret is True:
    #         progress = self.frame_to_timestamp(int(self.cap.get(cv2.CAP_PROP_POS_FRAMES)), fps) + ' / ' \
    #                    + self.frame_to_timestamp(int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT)), fps)
    #         self.progresslabel.setText(progress)
    #         self.progressBar.setValue(int(self.cap.get(cv2.CAP_PROP_POS_FRAMES)))
    #         # convert image to RGB format
    #         image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    #         # get image infos
    #         height, width, channel = image.shape
    #         step = channel * width
    #         # create QImage from image
    #         qImg = QImage(image.data, width, height, step, QImage.Format_RGB888)
    #         # show image in img_label
    #         self.frame.setPixmap(QPixmap.fromImage(qImg))
    #     else:
    #         progress = str(int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))) + ' / ' \
    #                    + str(int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT)))
    #         self.progresslabel.setText(progress)
    #         self.progressBar.setValue(int(self.cap.get(cv2.CAP_PROP_POS_FRAMES)))


    # def skipFrame(self):
    #     global cap
    #     value = self.progressBar.value()
    #     cap.set(1, value)

    def startVideoGen(self):
        global cap
        self.threadVideoGen = VideoGen(self.q)
        self.threadVideoGen.start()

    def startVideoPlay(self):
        global cap
        # print('starting play')
        self.threadVideoPlay = PlayVideo(self.q, self.progresslabel, self.progressBar, self.frame,
                                         self.totalFrames, self.fps, self.playButton, self.stopButton)
        self.threadVideoPlay.start()


app = QApplication(sys.argv)
widget = MainWindow()
widget.show()
sys.exit(app.exec_())
