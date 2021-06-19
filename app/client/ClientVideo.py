import base64
import queue
import socket
import threading

import numpy as np
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTimer, QThread
import cv2
from datetime import timedelta
import time
import logging
import pickle

logging.basicConfig(format="%(message)s", level=logging.INFO)


class PlayVideo(QThread):
    def __init__(self, frame, fpsLabel, threadChat, playButton, stopButton, chat_socket,
                 progressBar, progresslabel):
        super().__init__()

        self.chat_socket = chat_socket
        self.threadChat = threadChat

        self.frame = frame
        self.fpsLabel = fpsLabel

        self.playButton = playButton
        self.stopButton = stopButton
        self.progressBar = progressBar
        self.progresslabel = progresslabel

        self.timer = QTimer()
        self.timer.timeout.connect(self.play_video)
        self.timer.start(1/25)



        self.playButton.clicked.connect(self.play_timer)
        self.stopButton.clicked.connect(self.stop_timer)

        self.fps, self.st, self.frames_to_count, self.cnt = (0, 0, 20, 0)

        self.BUFF_SIZE = 65536
        self.video_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.video_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, self.BUFF_SIZE)

        self.host_name = socket.gethostname()
        #self.host_ip = socket.gethostbyname(self.host_name)
        self.host_ip = '127.0.0.1'
        self.port = 9689
        self.socket_address = (self.host_ip, self.port)  # client ip

        self.video_socket.bind(self.socket_address)
        # self.video_socket.setblocking(False)

        self.progressBar.sliderPressed.connect(self.when_slider_pressed)
        self.progressBar.sliderReleased.connect(self.move_progress_bar)



        self.slider_pressed = False
        self.set_total_frames = False

        self.q = queue.Queue(maxsize=100)
        t1 = threading.Thread(target=self.get_video_data, args=())
        t1.start()

    def frame_to_timestamp(self, frame, fps):
        return str(timedelta(seconds=(frame / fps)))

    def send_message(self, message):
        user_msg = pickle.dumps({"user": self.threadChat.nickname, "msg": message})
        self.chat_socket.send(user_msg)

    def play_timer(self):
        # start timer
        self.send_message('/play')

    def stop_timer(self):
        # stop timer
        self.send_message('/pause')

    def when_slider_pressed(self):
        self.slider_pressed = True

    def move_progress_bar(self):
        value = self.progressBar.value()
        self.send_message('/skipto ' + str(value))
        self.slider_pressed = False

    # should implement sending frames from VideoGen server side
    # and then make sync with video here
    def get_video_data(self):
        while self.threadChat.nickname == "":
            # print('wait video')
            # time.sleep(0.1)
            pass
        while True:
            try:
                rec_frame, _ = self.video_socket.recvfrom(self.BUFF_SIZE)
                self.q.put(rec_frame)
            except BlockingIOError:
                pass
            except Exception as e:
                logging.error(e)

    def play_video(self):
        if not self.q.empty():
            # print(self.q.qsize())
            try:
                packet_ser = self.q.get()
                packet = pickle.loads(packet_ser)

                # TODO: receive total_frames and real_fps from the chat TCP socket only once
                # can't since server can open different video file and client metadata doesn't update
                # consider sending total_frames and real_fps to client over TCP chat everytime we change the file
                current_frame_no = packet["frame_nb"]
                total_frames = packet["total_frames"]
                real_fps = packet["fps"]
                # if not self.set_total_frames:
                self.progressBar.setMinimum(0)
                self.progressBar.setMaximum(total_frames)
                    # self.set_total_frames = True

                if self.slider_pressed is False:
                    self.progressBar.setValue(current_frame_no)

                progress = self.frame_to_timestamp(current_frame_no, real_fps) + ' / ' \
                           + self.frame_to_timestamp(total_frames, real_fps)
                self.progresslabel.setText(progress)

                data = base64.b64decode(packet["frame"], ' /')
                npdata = np.fromstring(data, dtype=np.uint8)
                frame = cv2.imdecode(npdata, 1)

                # convert image to RGB format
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                # get image infos
                height, width, channel = frame.shape
                # print(height, width, channel)
                step = channel * width
                # create QImage from image
                qImg = QImage(frame.data, width, height, step, QImage.Format_RGB888)

                self.frame.setPixmap(QPixmap.fromImage(qImg))

                self.fpsLabel.setText(str(round(self.fps, 1)))
                if self.cnt == self.frames_to_count:
                    try:
                        self.fps = round(self.frames_to_count / (time.time() - self.st))
                        self.st = time.time()
                        self.cnt = 0
                    except:
                        pass
                self.cnt += 1

            # except BlockingIOError:
            #     pass
            except Exception as e:
                logging.error(e)
