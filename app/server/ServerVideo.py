import base64
import socket
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTimer, pyqtSignal, QThread
import cv2
from datetime import timedelta
import time
import logging
import os
import pickle

BASE_DIR = os.path.dirname(__file__)
path = BASE_DIR.replace('\\'[0], '/')

logging.basicConfig(format="%(message)s", level=logging.INFO)


class PlayVideo(QThread):
    playSignal = pyqtSignal()
    stopSignal = pyqtSignal()
    is_paused = True

    def destroy(self):
        if self.video_socket:
            self.video_socket.close()
        self.terminate()
        self.deleteLater()

    def __init__(self, cap, q, progresslabel, progressBar, frame, totalFrames, fps,
                 playButton, stopButton, fpsLabel, threadVideoGen, threadAudio):

        super().__init__()
        self.threadVideoGen = threadVideoGen
        self.threadAudio = threadAudio

        # signals used by TCP chat thread in order to play/pause the timer from the exterior
        self.playSignal.connect(self.play_timer)
        self.stopSignal.connect(self.stop_timer)

        # ui properties inherited from MainWindow class
        self.cap = cap
        self.playButton = playButton
        self.stopButton = stopButton
        self.fpsLabel = fpsLabel

        # queue fetching frames from VideoGen module
        self.q = q

        # UI elements from main module
        self.progresslabel = progresslabel
        self.progressBar = progressBar
        self.frame = frame
        self.totalFrames = totalFrames
        self.fps_metadata = fps
        self.frame_freq = (1 / self.fps_metadata)

        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(totalFrames)
        self.progressBar.setValue(0)

        # timer to loop the frame displaying function
        self.timer = QTimer()
        self.timer.timeout.connect(self.play_video)

        # bind play/pause buttons
        self.playButton.clicked.connect(self.play_timer)
        self.stopButton.clicked.connect(self.stop_timer)

        # properties for slider functionality
        self.slider_pressed = False
        self.progressBar.sliderPressed.connect(self.when_slider_pressed)
        self.progressBar.sliderReleased.connect(self.move_progress_bar)

        # properties to sync the metadata FPS with how fast the frames are processed
        self.fps_actual = 0
        self.time_prev_frame = 0
        self.frames_to_count = 1
        self.cnt = 0
        self.current_second = 0

        # properties for UDP socket to send the frames to clients
        self.BUFF_SIZE = 65536
        self.video_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.video_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, self.BUFF_SIZE)
        host_name = socket.gethostname()
        # self.host_ip = socket.gethostbyname(host_name)
        self.host_ip = '127.0.0.1'
        print('udp ip connect: ', self.host_ip)
        self.port = 9688
        self.video_socket.bind((self.host_ip, self.port))

        self.client_port = 9689
        self.clients = []

    # fetch clients from Tcp chat module
    def update_clients(self, clients):
        self.clients = clients

    # convert frame number to timestamp
    def frame_to_timestamp(self, frame, fps):
        return str(timedelta(seconds=(frame / fps)))

    # restart the timer when play button is pressed
    def play_timer(self):
        try:
            self.timer.start(self.frame_freq * 1000)
            self.is_paused = False
        except Exception as e:
            logging.error('timer start err: {}'.format(e))

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
            value = self.progressBar.value()

            # stop video playback timer
            self.timer.stop()
            # signal queue thread to stop generating
            self.threadVideoGen.stop_q = True

            # empty remaining frames stored in queue
            while not self.q.empty():
                # print(self.q.qsize())
                self.q.get()

            self.cap.set(1, value)
            self.threadVideoGen.stop_q = False
            self.slider_pressed = False
            if not self.is_paused:
                self.timer.start(self.frame_freq * 1000)


        except Exception as e:
            logging.error(e)

    def move_progress_bar_client(self, value):
        # timer for video playback is stopped and resumed in Tcp Chat class by the signal
        # signal queue thread to stop generating
        self.threadVideoGen.stop_q = True

        # empty remaining frames stored in queue
        while not self.q.empty():
            # print(self.q.qsize())
            self.q.get()

        self.cap.set(1, value)
        self.threadVideoGen.stop_q = False

    # function for displaying and sending frames
    # will be ran in a loop using the timer to sync the FPS
    def play_video(self):
        try:
            # read image from queue
            ret, frame, current_frame_no = self.q.get()

            if ret is True:
                # update progress bar location at each frame
                progress = self.frame_to_timestamp(current_frame_no, self.fps_metadata) + ' / ' \
                           + self.frame_to_timestamp(self.totalFrames, self.fps_metadata)
                self.progresslabel.setText(progress)

                # to sync with audio progress
                self.current_second = current_frame_no / self.fps_metadata

                # stop updating slider in UI while clicked while continuing playback
                if self.slider_pressed is False:
                    self.progressBar.setValue(current_frame_no)

                # encode frame and send to clients
                try:
                    encoded, buffer = cv2.imencode('.jpeg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    encoded_frame = base64.b64encode(buffer)

                    # TODO: maybe send total_frames and fps only once in the TCP connection
                    msg_pair = {"frame_nb": current_frame_no,
                                "total_frames": self.totalFrames,
                                "frame": encoded_frame,
                                "fps": self.fps_metadata}
                    packed_message = pickle.dumps(msg_pair)

                    # print(self.clients)
                    for client in self.clients:
                        self.video_socket.sendto(packed_message, (client, self.client_port))
                except Exception as e:
                    logging.error('video: {}'.format(e))

                # # display frame in player
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

                # because frame processing time if fluctuating
                # we need to sync it to the FPS fetched from the metadata

                # sync with audio timestamp
                if self.current_second < self.threadAudio.current_second and self.frame_freq > 0:
                    self.frame_freq -= 0.001
                elif self.current_second > self.threadAudio.current_second:
                    self.frame_freq += 0.001

                # source for sync with fps:
                # https://pyshine.com/How-to-send-audio-video-of-MP4-using-sockets-in-Python/
                # sync with metadata fps
                if self.cnt == self.frames_to_count:
                    try:
                        self.fps_actual = (self.frames_to_count / (time.time() - self.time_prev_frame))
                        self.time_prev_frame = time.time()
                        self.cnt = 0
                        if self.fps_actual > self.fps_metadata:
                            self.frame_freq += 0.001
                        elif self.fps_actual < self.fps_metadata and self.frame_freq > 0:
                            self.frame_freq -= 0.001
                        else:
                            pass
                    except Exception as e:
                        print(e)
                self.cnt += 1

                # print(self.fps_metadata, self.fps_actual)

                self.fpsLabel.setText(str(round(self.fps_actual, 1)))

                # restart and update timer with new frame frequency
                self.timer.start(self.frame_freq * 1000)

                # restart playback at end of video and pause
                if current_frame_no >= self.totalFrames - 5:
                    try:
                        self.stop_timer()
                        self.threadAudio.stopSignal.emit()
                        self.move_progress_bar_client(0)
                        self.threadAudio.move_slider_client(0)
                        logging.info('Server finished playback')
                    except Exception as e:
                        logging.error('reset playback err: ', e)
        except Exception as e:
            logging.error(e)
