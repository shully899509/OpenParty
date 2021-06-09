from PyQt5.QtCore import QThread
import cv2
import logging, imutils
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

    def run(self):
        # set how much pixels should the frame be resized to be sent to UDP clients
        # too much will cause lag because of UDP packets exceeding max size
        # could set here as parameters for quality in server UI
        WIDTH = 320
        HEIGHT = 240

        while self.cap.isOpened():
            try:
                # if self.stop_q:
                #     print('queue is stopped')
                while not self.stop_q:
                    # to be used for updating the slider position
                    current_frame_nb = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))

                    ret, frame = self.cap.read()

                    frame = imutils.resize(frame, width=WIDTH, height=HEIGHT)
                    self.q.put((ret, frame, current_frame_nb))
            except AttributeError as e:
                if str(e) == "'NoneType' object has no attribute 'shape'":
                    logging.error('Frame not found')
            except Exception as e:
                logging.error('Error in frame generation: {}'.format(e))
        print('Player closed')
        self.cap.release()