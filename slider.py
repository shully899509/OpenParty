import os
import sys
from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.uic import loadUi
from PyQt5.QtCore import pyqtSlot, QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QFileDialog
import cv2

BASE_DIR = os.path.dirname(__file__)
path = BASE_DIR.replace('\\'[0], '/')


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        loadUi('poseVideo.ui', self)
        self.setWindowTitle('Video Player')
        # create a timer
        self.timer = QTimer()
        # set timer timeout callback function
        self.timer.timeout.connect(self.playleftVideo)
        self.timer.timeout.connect(self.playrightVideo)
        # set control_bt callback clicked  function
        self.playButton.clicked.connect(self.playTimer)
        self.stopButton.clicked.connect(self.stopTimer)
        self.browseButton.clicked.connect(self.openFile)
        self.leftexportButton.clicked.connect(self.leftexportVideo)
        self.rightexportButton.clicked.connect(self.rightexportVideo)
        self.exportButton.clicked.connect(self.convertVideo)
        self.gotoButton.clicked.connect(self.jumpVideo)
        self.slider.valueChanged.connect(self.skipFrame)
        left = QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Left), self)
        left.activated.connect(self.skipLeft)
        right = QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Right), self)
        right.activated.connect(self.skipRight)
        up = QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Up), self)
        up.activated.connect(self.skipUp)
        down = QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Down), self)
        down.activated.connect(self.skipDown)
        space = QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Space), self)
        space.activated.connect(self.space)
        open = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+O"), self)
        open.activated.connect(self.openFile)

    def jumpVideo(self):
        jump = int(self.gotoLine.text())
        self.cap.set(1, jump)
        self.slider.setValue(int(self.cap.get(cv2.CAP_PROP_POS_FRAMES)))
        self.cap.set(1, int(self.cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1)
        self.playrightVideo()
        self.cap.set(1, int(self.cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1)
        self.playleftVideo()

    def skipUp(self):
        self.cap.set(1, int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))+999)
        self.playleftVideo()
        self.cap.set(1, int(self.cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1)
        self.playrightVideo()

    def skipDown(self):
        self.cap.set(1, int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))-1001)
        self.playleftVideo()
        self.cap.set(1, int(self.cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1)
        self.playrightVideo()

    def skipLeft(self):
        self.cap.set(1, int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))-2)
        ret, image = self.cap.read()
        progress = str(int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))) + ' / ' \
                   + str(int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT)))
        self.progresslabel.setText(progress)
        self.slider.setValue(int(self.cap.get(cv2.CAP_PROP_POS_FRAMES)))
        # convert image to RGB format
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        # crop image
        image = image[240:480, 0:360]
        # resize image
        image = cv2.resize(image, (531, 551))
        # get image infos
        height, width, channel = image.shape
        step = channel * width
        # create QImage from image
        qImg = QImage(image.data, width, height, step, QImage.Format_RGB888)
        # show image in img_label
        self.display.setPixmap(QPixmap.fromImage(qImg))
        self.cap.set(1, int(self.cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1)
        self.playrightVideo()

    def skipRight(self):
        self.playleftVideo()
        self.cap.set(1, int(self.cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1)
        self.playrightVideo()

    def space(self):
        if self.timer.isActive():
            self.timer.stop()
        else:
            self.timer.start()

    def convertVideo(self):
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        write_video = cv2.VideoCapture(self.file_name)
        input_fps = write_video.get(cv2.CAP_PROP_FPS)
        file = self.file_name.split('.')[0]
        file_name = file + '_converted_.mp4'
        print(file_name)
        out = cv2.VideoWriter(file_name, fourcc, input_fps, (int(write_video.get(3)), int(write_video.get(4))))
        while write_video.isOpened():
            ret, frame = write_video.read()
            if ret is True:
                print(write_video.get(cv2.CAP_PROP_POS_FRAMES))
                out.write(frame)
            else:
                break
        out.release()

    def leftexportVideo(self):
        start = self.startline.text()
        end = self.endline.text()
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        write_video = cv2.VideoCapture(self.file_name)
        input_fps = write_video.get(cv2.CAP_PROP_FPS)
        out = cv2.VideoWriter(path+'/export_left_'+start+'_'+end+'.mp4', fourcc, input_fps, (360, 240))
        write_video.set(1, int(start)-1)
        for cur in range(int(end)-int(start)+1):
            ret, frame = write_video.read()
            progress = str(int(write_video.get(cv2.CAP_PROP_POS_FRAMES))) + ' / ' \
                       + str(int(end))
            self.exportLabel.setText(progress)
            print(progress)
            image = frame[240:480, 0:360]
            out.write(image)
        out.release()

    def rightexportVideo(self):
        start = self.startline.text()
        end = self.endline.text()
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        write_video = cv2.VideoCapture(self.file_name)
        input_fps = write_video.get(cv2.CAP_PROP_FPS)
        out1 = cv2.VideoWriter(path + '/export_right_' + start + '_' + end + '.mp4', fourcc, input_fps, (360, 240))
        write_video.set(1, int(start)-1)
        for cur in range(int(end)-int(start)+1):
            progress = str(int(write_video.get(cv2.CAP_PROP_POS_FRAMES))) + ' / ' \
                       + str(int(end))
            self.exportLabel.setText(progress)
            ret, frame = write_video.read()
            progress = str(int(write_video.get(cv2.CAP_PROP_POS_FRAMES))) + ' / ' \
                       + str(int(end))
            self.exportLabel.setText(progress)
            print(progress)
            image1 = frame[240:480, 360:720]
            out1.write(image1)
        out1.release()

    def skipFrame(self):
        value = self.slider.value()
        self.cap.set(1, value)

    def playleftVideo(self):
         # read image in BGR format
        ret, image = self.cap.read()
        if ret is True:
            progress = str(int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))) + ' / ' \
                       + str(int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT)))
            self.progresslabel.setText(progress)
            self.slider.setValue(int(self.cap.get(cv2.CAP_PROP_POS_FRAMES)))
            # convert image to RGB format
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            # crop image
            image = image[240:480, 0:360]
            # resize image
            image = cv2.resize(image, (531, 551))
            # get image infos
            height, width, channel = image.shape
            step = channel * width
            # create QImage from image
            qImg = QImage(image.data, width, height, step, QImage.Format_RGB888)
            # show image in img_label
            self.display.setPixmap(QPixmap.fromImage(qImg))
        else:
            progress = str(int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))) + ' / ' \
                       + str(int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT)))
            self.progresslabel.setText(progress)
            self.slider.setValue(int(self.cap.get(cv2.CAP_PROP_POS_FRAMES)))

    def playrightVideo(self):
        # read image in BGR format
        ret, image = self.cap.read()
        if ret is True:
            progress = str(int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))) + ' / ' \
                       + str(int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT)))
            self.progresslabel.setText(progress)
            self.slider.setValue(int(self.cap.get(cv2.CAP_PROP_POS_FRAMES)))
            # convert image to RGB format
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            # crop image
            image = image[240:480, 360:720]
            # resize image
            image = cv2.resize(image, (531, 551))
            # get image infos
            height, width, channel = image.shape
            step = channel * width
            # create QImage from image
            qImg = QImage(image.data, width, height, step, QImage.Format_RGB888)
            # show image in img_label
            self.display_second.setPixmap(QPixmap.fromImage(qImg))

    def openFile(self):
        self.videoFileName = QFileDialog.getOpenFileName(self, 'Select Video File')
        self.file_name = list(self.videoFileName)[0]
        self.cap = cv2.VideoCapture(self.file_name)
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.slider.setMinimum(0)
        self.slider.setMaximum(int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT)))
        self.timer.start(fps)

    def playTimer(self):
        # start timer
        self.timer.start(20)

    def stopTimer(self):
        # stop timer
        self.timer.stop()


app = QApplication(sys.argv)
widget = MainWindow()
widget.show()
sys.exit(app.exec_())