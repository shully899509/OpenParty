import base64
import socket
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import pyqtSlot, QTimer, QObject, pyqtSignal, QThread
import cv2
from datetime import timedelta
import time
import logging, random, imutils
import os
import pickle
import threading

BASE_DIR = os.path.dirname(__file__)
path = BASE_DIR.replace('\\'[0], '/')

logging.basicConfig(format="%(message)s", level=logging.INFO)


class PlayVideo(QThread):
    playSignal = pyqtSignal()
    stopSignal = pyqtSignal()
    is_paused = True

    def destroy(self):
        self.terminate()
        self.deleteLater()

    def __init__(self, cap, q, progresslabel, progressBar, frame, totalFrames, fps,
                 playButton, stopButton, fpsLabel):

        super().__init__()

        # signals used by TCP chat thread in order to play/pause the timer from the exterior
        self.playSignal.connect(self.play_timer)
        self.stopSignal.connect(self.stop_timer)

        # ui properties inherited from MainWindow class
        self.cap = cap
        self.playButton = playButton
        self.stopButton = stopButton
        self.fpsLabel = fpsLabel

        self.q = q
        self.progresslabel = progresslabel
        self.progressBar = progressBar
        self.frame = frame
        self.totalFrames = totalFrames
        self.fps = fps
        self.TS = (0.5 / self.fps)

        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(totalFrames)

        # timer to loop the frame displaying function
        self.timer = QTimer()
        self.timer.timeout.connect(self.play_video)
        # self.timer.start(self.TS * 1000)

        # bind play/pause buttons
        self.playButton.clicked.connect(self.play_timer)
        self.stopButton.clicked.connect(self.stop_timer)

        # properties for slider functionality
        self.slider_pressed = False
        self.progressBar.sliderPressed.connect(self.when_slider_pressed)
        self.progressBar.sliderReleased.connect(self.move_progress_bar)

        # properties to sync the FPS with how fast the frames are processed
        self.fps2 = 0
        self.st = 0
        self.frames_to_count = 1
        self.cnt = 0

        # properties for UDP socket to send the frames to clients
        self.BUFF_SIZE = 65536
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, self.BUFF_SIZE)
        host_name = socket.gethostname()
        self.host_ip = socket.gethostbyname(host_name)
        print('udp ip connect: ', self.host_ip)
        port = 9688
        self.socket_address = (self.host_ip, port)
        # self.server_socket.bind(self.socket_address)
        print('Listening at:', self.socket_address)

        self.cnt = 1

        self.fps_mean = 0

    # convert frame number to timestamp
    def frame_to_timestamp(self, frame, fps):
        return str(timedelta(seconds=(frame / fps)))

    # restart the timer when play button is pressed
    def play_timer(self):
        self.timer.start(self.TS * 1000)
        self.is_paused = False

    # stop the timer when pause button is pressed
    def stop_timer(self):
        self.timer.stop()
        self.is_paused = True

    # stop updating the progress bar while slider is clicked
    def when_slider_pressed(self):
        self.slider_pressed = True

    # when slider is released try to empty queue and move to selected frame number
    def move_progress_bar(self):
        try:
            self.timer.stop()
            for i in range(self.q.qsize()): self.q.get()
            time.sleep(0.05)
            if not self.is_paused:
                self.timer.start(self.TS * 1000)
        except Exception as e:
            logging.error(e)
        value = self.progressBar.value()
        self.cap.set(1, value)
        self.slider_pressed = False

    def move_progress_bar_client(self, value):
        for i in range(self.q.qsize()): self.q.get()
        time.sleep(0.05)
        self.cap.set(1, value)

    # function for displaying and sending frames
    # will be ran in a loop using the timer to sync the FPS
    def play_video(self):
        # read image from queue
        ret, frame, current_frame_no = self.q.get()

        # if self.cnt == 1: print(frame)

        if ret is True:
            progress = self.frame_to_timestamp(current_frame_no, self.fps) + ' / ' \
                       + self.frame_to_timestamp(self.totalFrames, self.fps)
            self.progresslabel.setText(progress)
            # logging.info(current_frame)
            # logging.info(threading.current_thread().ident)

            # stop updating slider in UI while clicked while continuing playback
            if self.slider_pressed is False:
                self.progressBar.setValue(current_frame_no)

            try:
                encoded, buffer = cv2.imencode('.jpeg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                encoded_frame = base64.b64encode(buffer)

                # TODO: send total_frames and fps only once in the TCP connection
                msg_pair = {"frame_nb": current_frame_no,
                            "total_frames": self.totalFrames,
                            "frame": encoded_frame,
                            "fps": self.fps}
                packed_message = pickle.dumps(msg_pair)

                # TODO: send the message to the list of clients stored from the TCP socket
                client_addr_new1 = ('192.168.0.106', 9689)  # client ip
                client_addr_new2 = ('192.168.0.106', 9685)  # others
                client_addr_new = [client_addr_new1, client_addr_new2]
                for client in client_addr_new:
                    self.server_socket.sendto(packed_message, client)
            except Exception as e:
                logging.error(e)

            # convert image to RGB format
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            # get image infos
            height, width, channel = frame.shape
            # print(height, width, channel)
            step = channel * width
            # create QImage from image
            qImg = QImage(frame.data, width, height, step, QImage.Format_RGB888)

            # show image in UI frame label
            self.frame.setPixmap(QPixmap.fromImage(qImg))

            # self.threadAudio.playAudioSignal.emit()

            # because frame processing time if fluctuating
            # we need to sync it to the FPS fetched from the metadata
            self.fpsLabel.setText(str(round(self.fps2, 1)))

            # self.fps_mean += self.fps2
            # self.fps_mean /= 2
            # print(self.fps_mean)

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

            # restart and update timer with new TS
            self.timer.start(self.TS * 1000)

        else:
            print('return false')
            progress = str(current_frame_no) + ' / ' \
                       + str(self.totalFrames)
            self.progresslabel.setText(progress)
            self.progressBar.setValue(current_frame_no)
