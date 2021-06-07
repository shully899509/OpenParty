from PyQt5.QtCore import pyqtSlot, QTimer, QObject, pyqtSignal, QThread
import cv2
import logging, random, imutils
import os

BASE_DIR = os.path.dirname(__file__)
path = BASE_DIR.replace('\\'[0], '/')

logging.basicConfig(format="%(message)s", level=logging.INFO)

class VideoGen(QThread):
    # queue for storing multiple frames from video file ready to be processed
    def __init__(self, cap, q):
        super().__init__()
        self.cap = cap
        self.q = q
        self.stop_q = False

    def destroy(self):
        self.terminate()
        self.deleteLater()

    # def set_q_stop_t(self):
    #     self.stop_q = True
    #
    # def set_q_stop_f(self):
    #     self.stop_q = False

    def run(self):
        # set how much pixels should be sent using the UDP socket
        # too much will cause lag because of too large packets
        WIDTH = 600

        while self.cap.isOpened():
            try:
                # if self.stop_q:
                #     print('queue is stopped')
                while not self.stop_q:
                    # to be used for updating the slider position
                    current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))

                    ret, frame = self.cap.read()
                    # frame = imutils.resize(frame, width=WIDTH)
                    # print('adding frame to queue')

                    frame = imutils.resize(frame, width=WIDTH)
                    self.q.put((ret, frame, current_frame))
                    # logging.info('{} {}'.format('insert into q ', current_frame))
                    # print('sent frame: ', self.q.qsize())
                    # frame_no += 1
                    # print('after add frame')
            except Exception as e:
                logging.error(e)
                break
        print('Player closed')
        self.cap.release()